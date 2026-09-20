"""
Behavior Graph Builder — Creates a graph representation of firmware behavior.

Maps FirmwareUnderstanding to a BehaviorGraph with nodes for functions,
states, conditions, and hardware I/O, and edges for their relationships.
"""
from __future__ import annotations

import re
from ps3_agent.schemas import BehaviorGraph, BehaviorNode, BehaviorEdge, FirmwareUnderstanding


def _slugify(text: str) -> str:
    """Create a safe ID from text."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", text)[:50]


def build_behavior_graph(understanding: FirmwareUnderstanding) -> BehaviorGraph:
    """Build a behavior graph from firmware understanding."""
    nodes: list[BehaviorNode] = []
    edges: list[BehaviorEdge] = []
    node_ids: set[str] = set()

    def add_node(nid: str, label: str, kind: str, **kwargs):
        if nid not in node_ids:
            node_ids.add(nid)
            nodes.append(BehaviorNode(
                id=nid, label=label, kind=kind,
                file=kwargs.get("file"), line=kwargs.get("line"),
                metadata=kwargs.get("metadata", {}),
            ))

    def add_edge(source: str, target: str, kind: str, condition: str | None = None):
        if source in node_ids and target in node_ids:
            edges.append(BehaviorEdge(
                source=source, target=target, kind=kind, condition=condition,
            ))

    # 1. Function nodes
    for func in understanding.functions:
        fid = f"func-{_slugify(func.name)}"
        add_node(fid, func.name, "function",
                 file=func.file, line=func.line,
                 metadata={"conditions": func.conditions, "hw": func.hw_interactions})

    # 2. State variable nodes
    for var in understanding.state_variables:
        vid = f"state-{_slugify(var)}"
        add_node(vid, var, "state")

    # 3. Hardware I/O nodes
    for io in understanding.io_points:
        iid = f"io-{_slugify(io)}"
        kind = "hardware_output" if "Write" in io or "Print" in io else "hardware_input"
        add_node(iid, io, kind)

    # 4. Condition nodes (only interesting ones with comparisons)
    for cond in understanding.conditions:
        if any(op in cond for op in [">", "<", ">=", "<=", "==", "!="]):
            cid = f"cond-{_slugify(cond)}"
            add_node(cid, cond, "condition")

    # 5. Constant nodes for important thresholds
    for name, value in understanding.constants.items():
        if isinstance(value, (int, float)) and value != 0:
            cid = f"const-{_slugify(name)}"
            add_node(cid, f"{name}={value}", "constant")

    # 6. Edges: function calls
    func_names = {f.name for f in understanding.functions}
    for func in understanding.functions:
        fid = f"func-{_slugify(func.name)}"
        # Check if this function's conditions/hw reference other functions
        all_text = " ".join(func.conditions) + " " + " ".join(func.hw_interactions)
        for other in understanding.functions:
            if func.name != other.name and other.name in all_text:
                add_edge(fid, f"func-{_slugify(other.name)}", "calls")

        # Function → Hardware I/O edges
        for hw in func.hw_interactions:
            hw_id = f"io-{_slugify(hw)}"
            add_edge(fid, hw_id, "writes")

        # Function → State variable edges
        for var in understanding.state_variables:
            # Simple heuristic: if state var appears in function conditions
            if any(var in c for c in func.conditions):
                add_edge(fid, f"state-{_slugify(var)}", "reads")

        # Function → Condition edges
        for cond in func.conditions:
            cid = f"cond-{_slugify(cond)}"
            if cid in node_ids:
                add_edge(fid, cid, "evaluates")

            # Condition → Constant edges
            for const_name in understanding.constants:
                if const_name in cond:
                    add_edge(cid, f"const-{_slugify(const_name)}", "references")

    # 7. Condition → Hardware output edges (conditions that control hardware)
    for func in understanding.functions:
        if func.hw_interactions and func.conditions:
            for cond in func.conditions:
                cid = f"cond-{_slugify(cond)}"
                for hw in func.hw_interactions:
                    hw_id = f"io-{_slugify(hw)}"
                    if cid in node_ids and hw_id in node_ids:
                        add_edge(cid, hw_id, "controls")

    return BehaviorGraph(nodes=nodes, edges=edges)
