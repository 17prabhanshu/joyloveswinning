"""
Firmware Analyzer — Parses C source code and extracts structural information.

Uses regex-based parsing to extract functions, variables, constants,
conditions, hardware I/O interactions, state variables, and error handling.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from ps3_agent.schemas import FirmwareProject, FirmwareSymbol, FirmwareUnderstanding

logger = logging.getLogger(__name__)

# Regex patterns for C source analysis
RE_FUNCTION = re.compile(
    r"^(?:static\s+)?(?:void|int\w*|bool|float|double|char|uint\w+|int\w+)\s+"
    r"(\w+)\s*\(([^)]*)\)\s*\{",
    re.MULTILINE,
)
RE_DEFINE = re.compile(r"#define\s+(\w+)\s+(.+?)(?:\s*//.*)?$", re.MULTILINE)
RE_CONDITION = re.compile(
    r"if\s*\((.+?)\)\s*\{", re.MULTILINE
)
RE_HW_CALL = re.compile(
    r"(GPIO_Write|HAL_GPIO_WritePin|digitalWrite|analogRead|UART_Print|"
    r"HAL_ADC_GetValue|Serial\.\w+|printf|puts)\s*\(",
    re.MULTILINE,
)
RE_STATE_VAR = re.compile(
    r"(?:static\s+)?(?:volatile\s+)?(?:\w+)\s+(\w*(?:state|status|mode|flag|count)\w*)\s*[=;]",
    re.MULTILINE | re.IGNORECASE,
)
RE_ENUM = re.compile(r"typedef\s+enum\s*\{([^}]+)\}\s*(\w+)", re.DOTALL)
RE_ERROR_HANDLER = re.compile(
    r"(?:if\s*\(.+?(?:error|err|fail|fault|disconnect|invalid|null|NULL).+?\)\s*\{|"
    r"(?:handle|report|log)_(?:error|fault|failure)\s*\()",
    re.MULTILINE | re.IGNORECASE,
)


def analyze_firmware(project: FirmwareProject) -> FirmwareUnderstanding:
    """Parse all source files in the project and build a FirmwareUnderstanding."""
    all_functions: list[FirmwareSymbol] = []
    all_variables: list[str] = []
    all_constants: dict[str, Any] = {}
    all_io_points: list[str] = []
    all_state_vars: list[str] = []
    all_conditions: list[str] = []
    all_error_handlers: list[str] = []

    for filepath in project.source_files:
        p = Path(filepath)
        if not p.exists():
            logger.warning(f"Source file not found: {filepath}")
            continue

        try:
            source = p.read_text(encoding="utf-8", errors="replace")
            lines = source.split("\n")
        except Exception as e:
            logger.error(f"Failed to read {filepath}: {e}")
            continue

        filename = p.name

        # Extract functions
        for match in RE_FUNCTION.finditer(source):
            name = match.group(1)
            # Find the line number
            line_num = source[:match.start()].count("\n") + 1
            # Find hw interactions and conditions in function body
            # Find matching closing brace
            start_pos = match.end()
            brace_count = 1
            pos = start_pos
            while pos < len(source) and brace_count > 0:
                if source[pos] == "{":
                    brace_count += 1
                elif source[pos] == "}":
                    brace_count -= 1
                pos += 1
            func_body = source[start_pos:pos]

            hw_in_func = list(set(m.group(1) for m in RE_HW_CALL.finditer(func_body)))
            cond_in_func = [m.group(1).strip() for m in RE_CONDITION.finditer(func_body)]

            all_functions.append(FirmwareSymbol(
                name=name,
                kind="function",
                file=filename,
                line=line_num,
                conditions=cond_in_func,
                hw_interactions=hw_in_func,
            ))

        # Extract #define constants
        for match in RE_DEFINE.finditer(source):
            name = match.group(1)
            value = match.group(2).strip()
            try:
                all_constants[name] = int(value)
            except ValueError:
                try:
                    all_constants[name] = float(value)
                except ValueError:
                    all_constants[name] = value

        # Extract conditions
        for match in RE_CONDITION.finditer(source):
            cond = match.group(1).strip()
            if cond not in all_conditions:
                all_conditions.append(cond)

        # Extract hardware I/O calls
        for match in RE_HW_CALL.finditer(source):
            call = match.group(1)
            if call not in all_io_points:
                all_io_points.append(call)

        # Extract state variables
        for match in RE_STATE_VAR.finditer(source):
            var = match.group(1)
            if var and var not in all_state_vars:
                all_state_vars.append(var)

        # Extract enums as state info
        for match in RE_ENUM.finditer(source):
            enum_body = match.group(1)
            enum_name = match.group(2)
            members = [m.strip().split("=")[0].strip()
                       for m in enum_body.split(",") if m.strip()]
            for member in members:
                if member and member not in all_variables:
                    all_variables.append(member)

        # Extract error handlers
        for match in RE_ERROR_HANDLER.finditer(source):
            handler_text = match.group(0).strip()[:80]
            line_num = source[:match.start()].count("\n") + 1
            all_error_handlers.append(f"{filename}:{line_num}: {handler_text}")

    logger.info(
        f"Analysis complete: {len(all_functions)} functions, "
        f"{len(all_conditions)} conditions, {len(all_io_points)} I/O points, "
        f"{len(all_state_vars)} state variables"
    )

    return FirmwareUnderstanding(
        project_id=project.id,
        functions=all_functions,
        variables=all_variables,
        constants=all_constants,
        io_points=all_io_points,
        state_variables=all_state_vars,
        conditions=all_conditions,
        error_handlers=all_error_handlers,
    )


def extract_source_context(filepath: str, line: int, context_lines: int = 3) -> str:
    """Return the source code around a given line."""
    p = Path(filepath)
    if not p.exists():
        return f"[File not found: {filepath}]"
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").split("\n")
        start = max(0, line - context_lines - 1)
        end = min(len(lines), line + context_lines)
        result = []
        for i in range(start, end):
            marker = ">>>" if i == line - 1 else "   "
            result.append(f"{marker} {i + 1:4d} | {lines[i]}")
        return "\n".join(result)
    except Exception as e:
        return f"[Error reading {filepath}: {e}]"
