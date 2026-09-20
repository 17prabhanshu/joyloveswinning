"""
PS3 Agent — FastAPI Backend Server.

Provides the REST API and WebSocket endpoints for the
Autonomous Firmware Red-Team Agent dashboard.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ps3_agent.schemas import (
    AgentEvent,
    FirmwareProject,
    RunSummary,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

# ── App ───────────────────────────────────────────────────────
app = FastAPI(title="PS3 Autonomous Firmware Red-Team Agent", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = PROJECT_ROOT / "fixtures" / "firmware"
FRONTEND_DIR = PROJECT_ROOT / "frontend" / "dist"

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")

# ── State ─────────────────────────────────────────────────────
active_runs: dict[str, dict[str, Any]] = {}
ws_connections: dict[str, list[WebSocket]] = {}


# ── Models ────────────────────────────────────────────────────
class CreateRunRequest(BaseModel):
    firmware_path: Optional[str] = None
    code: Optional[str] = None
    max_tests: int = 30


# ── Health ────────────────────────────────────────────────────
@app.get("/health")
async def health():
    from ps3_agent.execution.simulator import get_simulators
    sims = []
    for s in get_simulators():
        h = s.health_check()
        sims.append({"name": s.name(), "version": s.version(), **h})
    return {
        "status": "healthy",
        "version": "1.0.0",
        "simulators": sims,
        "active_runs": len(active_runs),
    }


# ── Runs ──────────────────────────────────────────────────────
@app.post("/api/runs")
async def create_run(req: CreateRunRequest, background_tasks: BackgroundTasks):
    firmware_path = req.firmware_path or str(FIXTURES_DIR / "fan_controller.c")

    if req.code and req.code.strip():
        # If user pasted code, create a temp file for it
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".c", delete=False, mode="w")
        tmp.write(req.code)
        tmp.close()
        firmware_path = tmp.name

    if not Path(firmware_path).exists():
        raise HTTPException(404, f"Firmware not found: {firmware_path}")

    project = FirmwareProject(
        id=f"proj_{uuid.uuid4().hex[:8]}",
        name=Path(firmware_path).stem,
        source_files=[firmware_path],
        firmware_hash="",
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    from ps3_agent.core.loop import AgentLoop

    run_events: list[AgentEvent] = []

    def on_event(event: AgentEvent):
        run_events.append(event)
        run_id = event.run_id
        # Broadcast to WebSocket clients
        if run_id in ws_connections:
            for ws in ws_connections[run_id]:
                try:
                    asyncio.get_event_loop().create_task(
                        ws.send_json(event.model_dump(mode="json"))
                    )
                except Exception:
                    pass

    agent = AgentLoop(
        project=project,
        firmware_path=firmware_path,
        max_tests=req.max_tests,
        on_event=on_event,
    )

    run_id = agent.run_id
    active_runs[run_id] = {
        "agent": agent,
        "events": run_events,
        "status": "starting",
        "summary": None,
    }

    def run_agent():
        try:
            active_runs[run_id]["status"] = "running"
            summary = agent.run()
            active_runs[run_id]["status"] = "completed"
            active_runs[run_id]["summary"] = summary
        except Exception as e:
            logger.exception("Agent run failed")
            active_runs[run_id]["status"] = "error"
            active_runs[run_id]["error"] = str(e)

    background_tasks.add_task(run_agent)

    return {"run_id": run_id, "status": "started"}


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    if run_id not in active_runs:
        raise HTTPException(404, "Run not found")
    run = active_runs[run_id]
    agent = run["agent"]

    summary_data = None
    if run.get("summary"):
        summary_data = run["summary"].model_dump(mode="json")

    return {
        "run_id": run_id,
        "status": run["status"],
        "summary": summary_data,
        "total_events": len(run["events"]),
        "total_tests": len(agent.test_results),
        "total_risks": len(agent.risks),
        "total_failures": len(agent.failures),
        "total_regressions": len(agent.regressions),
        "stopping_reason": agent.stopping_reason,
    }


@app.get("/api/runs/{run_id}/events")
async def get_run_events(run_id: str):
    if run_id not in active_runs:
        raise HTTPException(404, "Run not found")
    events = active_runs[run_id]["events"]
    return {"events": [e.model_dump(mode="json") for e in events]}


@app.get("/api/runs/{run_id}/risks")
async def get_run_risks(run_id: str):
    if run_id not in active_runs:
        raise HTTPException(404, "Run not found")
    agent = active_runs[run_id]["agent"]
    return {"risks": [r.model_dump(mode="json") for r in agent.risks]}


@app.get("/api/runs/{run_id}/tests")
async def get_run_tests(run_id: str):
    if run_id not in active_runs:
        raise HTTPException(404, "Run not found")
    agent = active_runs[run_id]["agent"]
    tests = []
    for r in agent.test_results:
        tests.append({
            "test_id": r["scenario"].test_id,
            "target": r["scenario"].target,
            "category": r["scenario"].category,
            "reason": r["scenario"].why_this_test_exists,
            "expected": r["scenario"].expected_outcome,
            "status": r["verification"].status.value,
            "priority": r.get("priority", 0),
            "gpio": r["execution"].gpio if r.get("execution") else {},
            "uart": r["execution"].uart if r.get("execution") else [],
        })
    return {"tests": tests}


@app.get("/api/runs/{run_id}/behavior")
async def get_run_behavior(run_id: str):
    if run_id not in active_runs:
        raise HTTPException(404, "Run not found")
    agent = active_runs[run_id]["agent"]
    if not agent.behavior_graph:
        return {"nodes": [], "edges": []}
    return {
        "nodes": [n.model_dump(mode="json") for n in agent.behavior_graph.nodes],
        "edges": [e.model_dump(mode="json") for e in agent.behavior_graph.edges],
    }


@app.get("/api/runs/{run_id}/failures")
async def get_run_failures(run_id: str):
    if run_id not in active_runs:
        raise HTTPException(404, "Run not found")
    agent = active_runs[run_id]["agent"]
    failures = []
    for f in agent.failures:
        entry: dict[str, Any] = {
            "test_id": f["scenario"].test_id,
            "scenario": f["scenario"].model_dump(mode="json"),
            "verification": f["verification"].model_dump(mode="json"),
            "execution": {
                "uart": f["execution"].uart,
                "gpio": f["execution"].gpio,
            },
        }
        if f.get("diagnosis"):
            entry["diagnosis"] = f["diagnosis"].model_dump(mode="json")
        if f.get("minimized"):
            entry["minimized"] = f["minimized"].model_dump(mode="json")
        if f.get("regression"):
            entry["regression"] = f["regression"].model_dump(mode="json")
        failures.append(entry)
    return {"failures": failures}


@app.get("/api/runs/{run_id}/regressions")
async def get_run_regressions(run_id: str):
    if run_id not in active_runs:
        raise HTTPException(404, "Run not found")
    agent = active_runs[run_id]["agent"]
    return {"regressions": [r.model_dump(mode="json") for r in agent.regressions]}


@app.post("/api/runs/{run_id}/pause")
async def pause_run(run_id: str):
    if run_id not in active_runs:
        raise HTTPException(404, "Run not found")
    # TODO: Implement pause via threading event
    return {"status": "pause_requested"}


@app.post("/api/runs/{run_id}/stop")
async def stop_run(run_id: str):
    if run_id not in active_runs:
        raise HTTPException(404, "Run not found")
    # TODO: Implement stop via threading event
    return {"status": "stop_requested"}


class ChatRequest(BaseModel):
    message: str

@app.post("/api/runs/{run_id}/chat")
async def chat_with_agent(run_id: str, req: ChatRequest):
    if run_id not in active_runs:
        raise HTTPException(404, "Run not found")
    agent = active_runs[run_id]["agent"]
    msg = req.message
    
    # Context builder for LLM
    context_str = f"You are the PS3 Autonomous Red-Team Agent. You are testing a C firmware.\n"
    if agent.failures:
        f = agent.failures[-1]
        context_str += f"Most recent failure: Test {f['scenario'].test_id} failed. Expected: {f['scenario'].expected_outcome}.\n"
    if agent.risks:
        context_str += f"Found {len(agent.risks)} risks, including boundary conditions on hardware I/O.\n"
    
    # Try Ollama integration (Qwen/Llama)
    try:
        import httpx
        import json
        async with httpx.AsyncClient() as client:
            # Check models
            models_res = await client.get("http://localhost:11434/api/tags", timeout=1.0)
            if models_res.status_code == 200:
                models = models_res.json().get("models", [])
                if models:
                    model_name = models[0]["name"] # Use first available model (often qwen or llama)
                    
                    # Generate response
                    prompt = f"{context_str}\nUser Question: {msg}\nAnswer concisely and technically as the testing agent:"
                    payload = {"model": model_name, "prompt": prompt, "stream": False}
                    chat_res = await client.post("http://localhost:11434/api/generate", json=payload, timeout=10.0)
                    if chat_res.status_code == 200:
                        return {"response": f"[{model_name}] " + chat_res.json().get("response", "").strip()}
    except Exception:
        pass # Fallback to heuristic

    # --- Heuristic Fallback ---
    msg_lower = msg.lower()
    if "fail" in msg_lower or "error" in msg_lower or "bug" in msg_lower:
        if not agent.failures:
            return {"response": "I haven't encountered any test failures yet. All simulated boundaries are holding up so far."}
        f = agent.failures[-1]
        diag = f.get("diagnosis")
        cause = diag.cause_hypothesis if diag else "state mismatch"
        loc = f" around {diag.source_location}" if diag and getattr(diag, 'source_location', None) else ""
        return {"response": f"Looking at {f['scenario'].test_id}, testing '{f['scenario'].target}'. Expected: '{f['scenario'].expected_outcome}'. However, {cause}{loc}."}
        
    if "risk" in msg_lower or "vulnerabilit" in msg_lower:
        if not agent.risks:
            return {"response": "I am currently building the AST. No risks mapped yet."}
        return {"response": f"I found {len(agent.risks)} architectural risks. I flagged them because triggering these thresholds directly alters hardware state."}
            
    if "code" in msg_lower or "logic" in msg_lower:
        files = ", ".join(Path(f).name for f in agent.project.source_files)
        return {"response": f"I parsed {files}, extracted the control flow graph, and identified MMIO. I use this to generate failure scenarios."}

    return {"response": f"I am monitoring execution. I ran {len(agent.test_results)} tests and found {len(agent.failures)} anomalies. (Note: Install Ollama locally for deep LLM chat)."}


# ── Firmware Source ───────────────────────────────────────────
@app.get("/api/runs/{run_id}/report")
async def generate_report(run_id: str):
    if run_id not in active_runs:
        raise HTTPException(404, "Run not found")
    agent = active_runs[run_id]["agent"]
    
    html = f"""
    <html>
    <head>
        <title>PS3 Agent - Autonomous Firmware Testing Report</title>
        <style>
            body {{ font-family: system-ui, sans-serif; background: #0a0a0a; color: #fff; padding: 40px; }}
            h1 {{ color: #3b82f6; }}
            .card {{ background: #111; padding: 20px; border: 1px solid #333; border-radius: 8px; margin-bottom: 20px; }}
            .pass {{ color: #10b981; font-weight: bold; }}
            .fail {{ color: #ef4444; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>Autonomous Red-Team Execution Report</h1>
        <div class="card">
            <h2>Summary</h2>
            <p>Target Firmware: {agent.firmware_path}</p>
            <p>Total Tests Run: {len(agent.test_results)}</p>
            <p>Failures Found: <span class="fail">{len(agent.failures)}</span></p>
            <p>Risks Mapped: {len(agent.risks)}</p>
        </div>
        <div class="card">
            <h2>Critical Failures & Regressions</h2>
            {"".join(f"<p><b>Test {f['scenario'].test_id}</b>: {f['scenario'].target} - <span class='fail'>FAILED</span><br/>Reason: {f.get('diagnosis', {}).get('cause_hypothesis', 'State mismatch')}</p>" for f in agent.failures) if agent.failures else "<p>No critical failures detected.</p>"}
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/api/firmware/{run_id}")
async def get_firmware_source(run_id: str):
    if run_id not in active_runs:
        raise HTTPException(404, "Run not found")
    agent = active_runs[run_id]["agent"]
    sources = {}
    for f in agent.project.source_files:
        p = Path(f)
        if p.exists():
            sources[p.name] = p.read_text(encoding="utf-8", errors="replace")
    return {"files": sources}


# ── Simulator Status ──────────────────────────────────────────
@app.get("/api/simulators")
async def get_simulators():
    from ps3_agent.execution.simulator import get_simulators as _get_sims
    sims = []
    for s in _get_sims():
        h = s.health_check()
        sims.append({"name": s.name(), "version": s.version(), **h})
    return {"simulators": sims}


# ── WebSocket ─────────────────────────────────────────────────
@app.websocket("/ws/runs/{run_id}")
async def websocket_events(websocket: WebSocket, run_id: str):
    await websocket.accept()
    if run_id not in ws_connections:
        ws_connections[run_id] = []
    ws_connections[run_id].append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_connections[run_id].remove(websocket)


# ── Frontend ──────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return HTMLResponse(content=index.read_text(encoding="utf-8"))
    return HTMLResponse("""
    <html><body style="background:#000;color:#fff;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh;">
    <div style="text-align:center">
        <h1>PS3 Agent</h1>
        <p>Frontend not built. Run: cd frontend && npm install && npm run build</p>
        <p>API available at <a href="/health" style="color:#0070f3">/health</a></p>
    </div>
    </body></html>
    """)


# ── Main ──────────────────────────────────────────────────────
def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")


if __name__ == "__main__":
    main()
