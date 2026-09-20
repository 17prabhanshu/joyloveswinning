"""
Firmware C source code parser using tree-sitter.

Extracts functions, variables, defines, structs, enums, and
identifies GPIO/UART/sensor operations deterministically.
"""
import tree_sitter_c as tsc
from tree_sitter import Language, Parser, Node
from typing import Any
from .models import (
    FirmwareModel, FunctionInfo, VariableInfo, StructInfo, StructField,
    EnumInfo, EnumValue, DefineInfo
)

C_LANG = Language(tsc.language())

# Gate 2.1: Verify parser at import time
_check_parser = Parser(C_LANG)
_check_tree = _check_parser.parse(bytes("int x = 5;", "utf8"))
if _check_tree.root_node.children[0].type != "declaration":
    raise RuntimeError("Parser reality check failed: C grammar not functioning correctly")


class FirmwareParser:
    """Parses C/C++ firmware source code into a structured FirmwareModel."""

    def __init__(self):
        self.parser = Parser(C_LANG)

    def parse_file(self, file_path: str) -> FirmwareModel:
        """Parse a C source file into a FirmwareModel."""
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        return self.parse_code(code, file_path)

    def parse_code(self, code: str, file_path: str = "unknown") -> FirmwareModel:
        """Parse C source code string into a FirmwareModel."""
        tree = self.parser.parse(bytes(code, "utf8"))
        root = tree.root_node

        model = FirmwareModel(file_path=file_path)

        for child in root.children:
            if child.type == "function_definition":
                func = self._extract_function(child, code)
                if func:
                    model.functions.append(func)
            elif child.type == "declaration":
                # Could be variable, typedef, or struct/enum declaration
                text = self._text(child, code)
                if "typedef" in text and "enum" in text:
                    enum = self._extract_enum_from_typedef(child, code)
                    if enum:
                        model.enums.append(enum)
                elif "typedef" in text and "struct" in text:
                    struct = self._extract_struct_from_typedef(child, code)
                    if struct:
                        model.structs.append(struct)
                else:
                    var = self._extract_variable(child, code, is_global=True)
                    if var:
                        model.variables.append(var)
            elif child.type == "type_definition":
                text = self._text(child, code)
                if "enum" in text:
                    enum = self._extract_enum_from_typedef(child, code)
                    if enum:
                        model.enums.append(enum)
                elif "struct" in text:
                    struct = self._extract_struct_from_typedef(child, code)
                    if struct:
                        model.structs.append(struct)
            elif child.type == "preproc_def":
                define = self._extract_define(child, code)
                if define:
                    model.defines.append(define)
            elif child.type == "preproc_include":
                inc = self._extract_include(child, code)
                if inc:
                    model.includes.append(inc)
            elif child.type == "struct_specifier":
                struct = self._extract_struct(child, code)
                if struct:
                    model.structs.append(struct)
            elif child.type == "enum_specifier":
                enum = self._extract_enum(child, code)
                if enum:
                    model.enums.append(enum)

        return model

    def _text(self, node: Node, code: str) -> str:
        """Get the source text of a node."""
        return code[node.start_byte:node.end_byte]

    def _extract_function(self, node: Node, code: str) -> FunctionInfo | None:
        """Extract function information from a function_definition node."""
        # Find the declarator (handles storage class specifiers like 'static')
        func_declarator = self._find_child_recursive(node, "function_declarator")
        if not func_declarator:
            return None

        # Get return type - everything before the declarator
        return_type = "void"
        for child in node.children:
            if child.type in ("primitive_type", "type_identifier", "sized_type_specifier"):
                return_type = self._text(child, code)
                break
            elif child.type == "storage_class_specifier":
                continue  # skip static, extern, etc.
            elif child.type == "type_qualifier":
                continue  # skip const, volatile

        # Extract function name
        name = ""
        params: list[dict[str, str]] = []
        for child in func_declarator.children:
            if child.type == "identifier":
                name = self._text(child, code)
            elif child.type == "parameter_list":
                params = self._extract_params(child, code)

        if not name:
            return None

        # Extract body
        body_node = None
        for child in node.children:
            if child.type == "compound_statement":
                body_node = child
                break

        body_text = self._text(body_node, code) if body_node else ""

        # Extract calls, conditions, etc. from the body
        calls: list[str] = []
        conditions: list[str] = []
        loops: list[str] = []
        gpio_ops: list[str] = []
        uart_ops: list[str] = []
        sensor_reads: list[str] = []
        timer_ops: list[str] = []

        if body_node:
            # Extract function calls
            calls = self._extract_call_names(body_node, code)

            # Extract condition expressions (not full if blocks)
            conditions = self._extract_conditions(body_node, code)

            # Extract loop info
            loops = self._extract_loop_types(body_node, code)

            # Categorize calls by type
            for call in calls:
                call_lower = call.lower()
                if any(kw in call_lower for kw in ("gpio", "pin", "digital")):
                    gpio_ops.append(call)
                if any(kw in call_lower for kw in ("uart", "serial", "printf", "print")):
                    uart_ops.append(call)
                if any(kw in call_lower for kw in ("sensor", "read_temp", "adc", "analog")):
                    sensor_reads.append(call)
                if any(kw in call_lower for kw in ("timer", "delay", "millis", "tick")):
                    timer_ops.append(call)

        return FunctionInfo(
            name=name,
            params=params,
            return_type=return_type,
            start_line=node.start_point.row + 1,
            end_line=node.end_point.row + 1,
            body_text=body_text,
            calls=calls,
            conditions=conditions,
            loops=loops,
            gpio_ops=gpio_ops,
            uart_ops=uart_ops,
            sensor_reads=sensor_reads,
            timer_ops=timer_ops,
        )

    def _extract_call_names(self, node: Node, code: str) -> list[str]:
        """Extract function call names from a node tree."""
        calls: list[str] = []

        def visit(n: Node):
            if n.type == "call_expression":
                # The first child of a call_expression is the function name
                func_node = n.children[0] if n.children else None
                if func_node:
                    if func_node.type == "identifier":
                        calls.append(self._text(func_node, code))
                    elif func_node.type == "field_expression":
                        calls.append(self._text(func_node, code))
            for child in n.children:
                visit(child)

        visit(node)
        return calls

    def _extract_conditions(self, node: Node, code: str) -> list[str]:
        """Extract condition expressions from if/while/for statements."""
        conditions: list[str] = []

        def visit(n: Node):
            if n.type in ("if_statement", "while_statement"):
                # Find the parenthesized_expression (condition)
                for child in n.children:
                    if child.type == "parenthesized_expression":
                        # Get the inner expression (without outer parens)
                        inner = self._text(child, code)
                        # Strip outer parentheses
                        if inner.startswith("(") and inner.endswith(")"):
                            inner = inner[1:-1].strip()
                        conditions.append(inner)
                        break
                    elif child.type == "condition_clause":
                        conditions.append(self._text(child, code))
                        break
            elif n.type == "for_statement":
                # Extract the condition part of for loop
                parts = [c for c in n.children if c.type not in (
                    "for", "(", ")", ";", "compound_statement")]
                if len(parts) >= 2:
                    conditions.append(self._text(parts[1], code))
            for child in n.children:
                visit(child)

        visit(node)
        return conditions

    def _extract_loop_types(self, node: Node, code: str) -> list[str]:
        """Extract loop type descriptions."""
        loops: list[str] = []

        def visit(n: Node):
            if n.type == "for_statement":
                loops.append("for")
            elif n.type == "while_statement":
                loops.append("while")
            elif n.type == "do_statement":
                loops.append("do-while")
            for child in n.children:
                visit(child)

        visit(node)
        return loops

    def _extract_params(self, node: Node, code: str) -> list[dict[str, str]]:
        """Extract function parameters."""
        params: list[dict[str, str]] = []
        for child in node.children:
            if child.type == "parameter_declaration":
                ptype = ""
                pname = ""
                for pchild in child.children:
                    if pchild.type in ("primitive_type", "type_identifier",
                                       "sized_type_specifier"):
                        ptype = self._text(pchild, code)
                    elif pchild.type == "identifier":
                        pname = self._text(pchild, code)
                    elif pchild.type == "pointer_declarator":
                        for ppchild in pchild.children:
                            if ppchild.type == "identifier":
                                pname = self._text(ppchild, code)
                        ptype += "*"
                if pname or ptype:
                    params.append({"name": pname or "unnamed", "type": ptype or "unknown"})
        return params

    def _extract_variable(self, node: Node, code: str,
                          is_global: bool) -> VariableInfo | None:
        """Extract variable declaration information."""
        var_type = ""
        var_name = ""
        value = None
        is_const = False

        for child in node.children:
            if child.type in ("primitive_type", "type_identifier",
                              "sized_type_specifier"):
                var_type = self._text(child, code)
            elif child.type == "type_qualifier":
                txt = self._text(child, code)
                if txt == "const":
                    is_const = True
                elif txt == "volatile":
                    pass  # track if needed
            elif child.type == "storage_class_specifier":
                continue  # static, extern
            elif child.type == "init_declarator":
                for ichild in child.children:
                    if ichild.type == "identifier":
                        var_name = self._text(ichild, code)
                    elif ichild.type == "pointer_declarator":
                        for ppchild in ichild.children:
                            if ppchild.type == "identifier":
                                var_name = self._text(ppchild, code)
                        var_type += "*"
                    elif ichild.type == "number_literal":
                        value = self._text(ichild, code)
                    elif ichild.type == "string_literal":
                        value = self._text(ichild, code)
                    elif ichild.type in ("true", "false"):
                        value = self._text(ichild, code)
            elif child.type == "identifier" and not var_name:
                var_name = self._text(child, code)

        if var_name:
            return VariableInfo(
                name=var_name,
                type=var_type,
                is_global=is_global,
                is_const=is_const,
                value=value,
                line=node.start_point.row + 1,
            )
        return None

    def _extract_define(self, node: Node, code: str) -> DefineInfo | None:
        """Extract preprocessor #define."""
        name = ""
        val = None
        for child in node.children:
            if child.type == "identifier":
                name = self._text(child, code)
            elif child.type == "preproc_arg":
                val = self._text(child, code).strip()
        if name:
            return DefineInfo(name=name, value=val, line=node.start_point.row + 1)
        return None

    def _extract_include(self, node: Node, code: str) -> str | None:
        """Extract #include path."""
        for child in node.children:
            if child.type in ("system_lib_string", "string_literal"):
                return self._text(child, code)
        return None

    def _extract_enum(self, node: Node, code: str) -> EnumInfo | None:
        """Extract enum definition."""
        name = ""
        values: list[EnumValue] = []
        for child in node.children:
            if child.type == "type_identifier":
                name = self._text(child, code)
            elif child.type == "enumerator_list":
                for enum_child in child.children:
                    if enum_child.type == "enumerator":
                        ename = ""
                        evalue = None
                        for ec in enum_child.children:
                            if ec.type == "identifier":
                                ename = self._text(ec, code)
                            elif ec.type == "number_literal":
                                evalue = self._text(ec, code)
                        if ename:
                            values.append(EnumValue(name=ename, value=evalue))
        if name or values:
            return EnumInfo(name=name or "anonymous", values=values,
                           line=node.start_point.row + 1)
        return None

    def _extract_enum_from_typedef(self, node: Node, code: str) -> EnumInfo | None:
        """Extract enum from a typedef declaration."""
        enum_node = self._find_child(node, "enum_specifier")
        if not enum_node:
            return None
        enum = self._extract_enum(enum_node, code)
        # Try to get typedef name
        typedef_name = ""
        for child in node.children:
            if child.type == "type_identifier":
                typedef_name = self._text(child, code)
        if enum and typedef_name:
            enum.name = typedef_name
        return enum

    def _extract_struct(self, node: Node, code: str) -> StructInfo | None:
        """Extract struct definition."""
        name = ""
        fields: list[StructField] = []
        for child in node.children:
            if child.type == "type_identifier":
                name = self._text(child, code)
            elif child.type == "field_declaration_list":
                for fc in child.children:
                    if fc.type == "field_declaration":
                        fname = ""
                        ftype = ""
                        for ffc in fc.children:
                            if ffc.type in ("primitive_type", "type_identifier"):
                                ftype = self._text(ffc, code)
                            elif ffc.type == "field_identifier":
                                fname = self._text(ffc, code)
                        if fname:
                            fields.append(StructField(name=fname, type=ftype))
        if name or fields:
            return StructInfo(name=name or "anonymous", fields=fields,
                             line=node.start_point.row + 1)
        return None

    def _extract_struct_from_typedef(self, node: Node, code: str) -> StructInfo | None:
        """Extract struct from typedef."""
        struct_node = self._find_child(node, "struct_specifier")
        if not struct_node:
            return None
        struct = self._extract_struct(struct_node, code)
        typedef_name = ""
        for child in node.children:
            if child.type == "type_identifier" and child != struct_node:
                typedef_name = self._text(child, code)
        if struct and typedef_name:
            struct.name = typedef_name
        return struct

    def _find_child(self, node: Node, child_type: str) -> Node | None:
        """Find first direct child of given type."""
        for child in node.children:
            if child.type == child_type:
                return child
        return None

    def _find_child_recursive(self, node: Node, child_type: str) -> Node | None:
        """Find first child of given type recursively."""
        for child in node.children:
            if child.type == child_type:
                return child
            found = self._find_child_recursive(child, child_type)
            if found:
                return found
        return None
