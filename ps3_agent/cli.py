#!/usr/bin/env python3
"""
ps3-agent CLI — Command-line interface for the Autonomous Firmware Red-Team Agent.
"""
from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()

import argparse
import hashlib
import json
import logging
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def cmd_doctor(args):
    """Check system health and dependencies."""
    print("=" * 60)
    print("  PS3 AGENT — SYSTEM DIAGNOSTICS")
    print("=" * 60)
    checks = []

    # Python
    v = sys.version_info
    ok = v >= (3, 10)
    checks.append(("Python >= 3.10", ok, f"{v.major}.{v.minor}.{v.micro}"))

    # Core deps
    for mod in ["pydantic", "fastapi", "uvicorn"]:
        try:
            __import__(mod)
            checks.append((mod, True, "installed"))
        except ImportError:
            checks.append((mod, False, "MISSING — pip install " + mod))

    # Renode
    renode_path = shutil.which("renode")
    checks.append(("Renode simulator", bool(renode_path), renode_path or "Not in PATH"))

    # Frontend
    frontend_dist = PROJECT_ROOT / "frontend" / "dist" / "index.html"
    checks.append(("Frontend build", frontend_dist.exists(),
                    str(frontend_dist) if frontend_dist.exists() else "Run: cd frontend && npm run build"))

    # Fixtures
    fixture = PROJECT_ROOT / "fixtures" / "firmware" / "fan_controller.c"
    checks.append(("Demo firmware", fixture.exists(), str(fixture)))

    print()
    all_ok = True
    for name, ok, detail in checks:
        icon = "✅" if ok else "❌"
        print(f"  {icon}  {name:<25} {detail}")
        if not ok:
            all_ok = False

    print()
    if all_ok:
        print("  All checks passed. Ready to run.")
    else:
        print("  Some checks failed. Fix issues above before running.")
    print()


def cmd_demo(args):
    """Run the demo with the built-in buggy fan controller firmware."""
    print()
    print("=" * 60)
    print("  AUTONOMOUS FIRMWARE RED-TEAM AGENT — DEMO")
    print("=" * 60)
    print()

    firmware_path = str(PROJECT_ROOT / "fixtures" / "firmware" / "fan_controller.c")

    from ps3_agent.schemas import FirmwareProject
    from ps3_agent.core.loop import AgentLoop

    project = FirmwareProject(
        id=f"demo_{uuid.uuid4().hex[:6]}",
        name="fan_controller",
        source_files=[firmware_path],
        firmware_hash=hashlib.sha256(
            Path(firmware_path).read_bytes()
        ).hexdigest()[:16],
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    def on_event(event):
        ts = event.timestamp.split("T")[1][:8] if "T" in event.timestamp else ""
        agent = event.agent
        icon = {
            "CODE_READER": "📖",
            "MODELER": "🧩",
            "RISK_ENGINE": "⚠️ ",
            "BOUNDARY_HUNTER": "🎯",
            "ASSUMPTION_HUNTER": "💡",
            "STATE_HUNTER": "🔄",
            "FAULT_HUNTER": "💥",
            "TIMING_HUNTER": "⏱️ ",
            "SCENARIO_ENGINE": "🧪",
            "PLANNER": "🤖",
            "EXECUTOR": "▶️ ",
            "VERIFIER": "✅" if event.status == "PASS" else "❌",
            "DIAGNOSER": "🔎",
            "MINIMIZER": "🔬",
            "REGRESSION": "📌",
            "ADAPTIVE_AGENT": "🧠",
            "AGENT": "🚀",
        }.get(agent, "  ")
        print(f"  {ts}  {icon}  [{agent}]  {event.reason}")

    agent = AgentLoop(
        project=project,
        firmware_path=firmware_path,
        max_tests=args.max_tests if hasattr(args, "max_tests") else 20,
        on_event=on_event,
    )

    print(f"  Firmware: {firmware_path}")
    print(f"  Run ID:   {agent.run_id}")
    print()
    print("─" * 60)
    print()

    summary = agent.run()

    print()
    print("─" * 60)
    print()
    print(f"  RESULTS")
    print(f"  {'─' * 40}")
    print(f"  Total Tests:     {summary.total_tests}")
    print(f"  Passed:          {summary.passed}")
    print(f"  Failed:          {summary.failed}")
    print(f"  Errors:          {summary.errors}")
    print(f"  Risks Found:     {summary.risks_found}")
    print(f"  Risks Explored:  {summary.risks_explored}")
    print(f"  Regressions:     {summary.regressions_created}")
    print(f"  Stopping:        {summary.stopping_reason}")
    print()


def cmd_ui(args):
    """Start the web UI."""
    port = args.port if hasattr(args, "port") else 8080
    print(f"\n  Starting PS3 Agent UI on http://localhost:{port}\n")
    from ps3_agent.api.server import app
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def cmd_analyze(args):
    """Analyze firmware without running tests."""
    firmware = args.firmware
    if not Path(firmware).exists():
        print(f"  ❌ File not found: {firmware}")
        return

    from ps3_agent.schemas import FirmwareProject
    from ps3_agent.firmware.analyzer import analyze_firmware
    from ps3_agent.behavior.graph_builder import build_behavior_graph
    from ps3_agent.risk.engine import assess_risks

    project = FirmwareProject(
        id="analyze", name=Path(firmware).stem,
        source_files=[firmware], firmware_hash="",
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    understanding = analyze_firmware(project)
    graph = build_behavior_graph(understanding)
    risks = assess_risks(understanding, graph)

    print(f"\n  📖 Firmware Analysis: {firmware}")
    print(f"  {'─' * 40}")
    print(f"  Functions:     {len(understanding.functions)}")
    print(f"  Conditions:    {len(understanding.conditions)}")
    print(f"  I/O Points:    {len(understanding.io_points)}")
    print(f"  State Vars:    {len(understanding.state_variables)}")
    print(f"  Graph Nodes:   {len(graph.nodes)}")
    print(f"  Graph Edges:   {len(graph.edges)}")
    print(f"  Risks Found:   {len(risks)}")
    print()
    for r in risks:
        icon = {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟡"}.get(r.severity.value, "⚪")
        print(f"  {icon} [{r.category.value}] {r.explanation}")
    print()


def main():
    parser = argparse.ArgumentParser(
        prog="ps3-agent",
        description="Autonomous Firmware Red-Team Agent",
    )
    sub = parser.add_subparsers(dest="command")

    # doctor
    sub.add_parser("doctor", help="Check system health")

    # demo
    p_demo = sub.add_parser("demo", help="Run the demo")
    p_demo.add_argument("--max-tests", type=int, default=20)

    # ui
    p_ui = sub.add_parser("ui", help="Start web UI")
    p_ui.add_argument("--port", type=int, default=8080)

    # analyze
    p_analyze = sub.add_parser("analyze", help="Analyze firmware")
    p_analyze.add_argument("firmware", help="Path to firmware source")

    # report
    sub.add_parser("report", help="Generate report from last run")

    args = parser.parse_args()

    if args.command == "doctor":
        cmd_doctor(args)
    elif args.command == "demo":
        cmd_demo(args)
    elif args.command == "ui":
        cmd_ui(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
