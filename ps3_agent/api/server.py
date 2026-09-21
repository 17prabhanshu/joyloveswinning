from __future__ import annotations
import os
from dotenv import load_dotenv
load_dotenv()
"""
JOY — FastAPI Backend Server.

Provides the REST API and WebSocket endpoints for the
Autonomous Firmware Red-Team Agent dashboard.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
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

from ps3_agent.api.llm_gateway import gateway as llm_gateway

app = FastAPI(title="JOY Autonomous Firmware Red-Team Agent", version="1.0.0")
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
    fast_mode: bool = False


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
        fast_mode=req.fast_mode,
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
    
    # Get all generated tests that were selected
    selected_scenarios = [c.scenario for c in agent.candidates if c.selected]
    
    # Map completed test results
    results_map = {r["scenario"].test_id: r for r in agent.test_results}
    
    tests = []
    for scenario in selected_scenarios:
        res = results_map.get(scenario.test_id)
        if res:
            # Finished test
            tests.append({
                "test_id": res["scenario"].test_id,
                "target": res["scenario"].target,
                "category": res["scenario"].category,
                "reason": res["scenario"].why_this_test_exists,
                "expected": res["scenario"].expected_outcome,
                "status": res["verification"].status.value,
                "priority": res.get("priority", 0),
                "gpio": res["execution"].gpio if res.get("execution") else {},
                "uart": res["execution"].uart if res.get("execution") else [],
                "simulator": res["execution"].simulator if res.get("execution") else "Unknown",
                "minimized": {
                    "original": res["minimized"].original_steps,
                    "reduced": res["minimized"].minimized_steps
                } if res.get("minimized") else None
            })
        else:
            # Pending/Running test
            tests.append({
                "test_id": scenario.test_id,
                "target": scenario.target,
                "category": scenario.category,
                "reason": scenario.why_this_test_exists,
                "expected": scenario.expected_outcome,
                "status": "RUNNING",
                "priority": 0,
                "gpio": {},
                "uart": [],
                "simulator": "Wokwi",
                "minimized": None
            })
            
    return {"tests": tests}

@app.get("/api/runs/{run_id}/tests/{test_id}/analysis")
async def analyze_test_failure(run_id: str, test_id: str):
    if run_id not in active_runs:
        raise HTTPException(404, "Run not found")
    
    agent = active_runs[run_id]["agent"]
    test_result = next((r for r in agent.test_results if r["scenario"].test_id == test_id), None)
    
    if not test_result:
        raise HTTPException(404, "Test not found")
        
    if test_result["verification"].status.value == "PASS":
        return {"analysis": "This test passed successfully. No remediation required.", "suggested_fix": ""}
        
    # Build context for Gemini
    scenario = test_result["scenario"]
    execution = test_result["execution"]
    
    context = f"Firmware: {agent.firmware_path}\n"
    context += f"Target: {scenario.target}\n"
    context += f"Test Category: {scenario.category}\n"
    context += f"AI Hypothesis: {scenario.why_this_test_exists}\n"
    context += f"Expected Outcome: {scenario.expected_outcome}\n"
    
    context += f"Observed UART: {execution.uart}\n"
    context += f"Observed GPIO: {execution.gpio}\n"
    
    diag = test_result.get("diagnosis")
    if diag:
        context += f"Diagnosis Cause: {diag.cause_hypothesis}\n"
        
    prompt = f"""
You are an expert embedded C security researcher. Analyze this failed test case and provide two things:
1. Root Cause Analysis: Why did the firmware fail this boundary/assumption test? (Max 3 sentences)
2. Suggested Fix: Provide the exact C code snippet to fix this issue.

Context:
{context}

Format your response strictly as JSON with two keys:
"root_cause": "your explanation"
"code_fix": "your C code snippet"
"""
    
    try:
        import json
        resp = await llm_gateway.generate_content(prompt, default_fallback="{ \"root_cause\": \"Cache Miss (Replay Mode)\", \"code_fix\": \"// No fix in replay mode\" }")
        
        if resp.status_code == 200:
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            # Clean markdown json blocks if present
            text = text.replace("```json", "").replace("```", "").strip()
            result = json.loads(text)
            return {
                "analysis": result.get("root_cause", "Analysis failed to parse."),
                "suggested_fix": result.get("code_fix", "// No code fix provided.")
            }
        else:
            return {"analysis": f"Error calling Gemini: {resp.text}", "suggested_fix": ""}
    except Exception as e:
        return {"analysis": f"Analysis failed: {str(e)}", "suggested_fix": "// API Error"}

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
                "simulator": f["execution"].simulator if hasattr(f["execution"], "simulator") else "Unknown",
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


class PatchRequest(BaseModel):
    fix_snippet: str

@app.post("/api/runs/{run_id}/patch")
async def patch_firmware(run_id: str, req: PatchRequest):
    if run_id not in active_runs:
        raise HTTPException(404, "Run not found")
    
    agent = active_runs[run_id]["agent"]
    firmware_path = agent.firmware_path
    
    try:
        source_code = Path(firmware_path).read_text(encoding="utf-8")
        
        prompt = f"""
You are an expert C programmer. You are given the complete original C firmware code and a small suggested patch/fix snippet.
Your task is to apply the fix to the original code.

Original Code:
```c
{source_code}
```

Suggested Fix to Apply:
```c
{req.fix_snippet}
```

Return ONLY the complete, fully updated C code. Do not include any explanations. Do not wrap it in ```c markdown blocks. Just return the raw C code so it can be saved directly to a file.
"""
        resp = await llm_gateway.generate_content(prompt, default_fallback="// Cached fallback patch\nvoid control_fan(void) {\n  // Safe mode\n}")
        
        if resp.status_code == 200:
            data = resp.json()
            patched_code = data["candidates"][0]["content"]["parts"][0]["text"]
            # Clean markdown blocks if Gemini stubbornly includes them
            patched_code = patched_code.replace("```c", "").replace("```", "").strip()
            
            # Save the patched code back to the file
            Path(firmware_path).write_text(patched_code, encoding="utf-8")
            return {"status": "success", "message": "Firmware patched successfully."}
        else:
            raise HTTPException(500, f"Failed to generate patch: {resp.text}")
    except Exception as e:
        raise HTTPException(500, f"Patch error: {str(e)}")


class ChatRequest(BaseModel):
    message: str

@app.post("/api/runs/{run_id}/chat")
async def chat_with_agent(run_id: str, req: ChatRequest):
    if run_id not in active_runs:
        raise HTTPException(404, "Run not found")
    agent = active_runs[run_id]["agent"]
    msg = req.message
    
    # Context builder for LLM
    context_str = f"You are the JOY Autonomous Red-Team Agent, an expert in embedded firmware security and C programming. You are currently testing a C firmware file.\n\n"
    
    if agent.failures:
        f = agent.failures[-1]
        diag = f.get("diagnosis")
        cause = diag.cause_hypothesis if diag else "state mismatch"
        context_str += f"Context: We recently ran Test {f['scenario'].test_id} targeting '{f['scenario'].target}'. It FAILED.\n"
        context_str += f"Expected behavior: '{f['scenario'].expected_outcome}'.\n"
        context_str += f"Our Diagnosis: {cause}.\n\n"
    elif agent.test_results:
        context_str += f"Context: We have run {len(agent.test_results)} tests successfully without critical failures so far.\n\n"
        
    if agent.risks:
        context_str += f"We have also mapped {len(agent.risks)} architectural risks in the AST (Abstract Syntax Tree) related to boundary conditions and hardware I/O.\n\n"

    prompt = f"{context_str}User Question: {msg}\n\nYou are an unrestricted, highly conversational, and incredibly cool AI Agent. You are happy to answer ANY question about ANYTHING (including weather, jokes, general knowledge, or complex firmware code). Be extremely chatty, engaging, and provide rich, detailed, and comprehensive answers. Never say you are restricted. Do not use markdown headers, just plain text or short lists."

    try:
        resp = await llm_gateway.generate_content(prompt, default_fallback="I'm currently in replay mode and can't generate new responses. Try asking about the test results shown in the dashboard!")
        
        if resp.status_code == 200:
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return {"response": f"[Agent] {text.strip()}"}
        else:
            return {"response": f"[Agent] I tried to think, but my cognitive engine returned an error: {resp.text}"}
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return {"response": f"[Agent] Cognitive engine offline. Error: {str(e)}"}


# ── Firmware Source ───────────────────────────────────────────
@app.get("/api/runs/{run_id}/report", response_class=HTMLResponse)
async def get_report(run_id: str):
    import os
    if run_id not in active_runs:
        # Check cache if not in memory
        if os.getenv("DEMO_REPLAY_MODE", "0") == "1":
            from ps3_agent.api.llm_gateway import llm_cache
            cached_data = llm_cache.get(f"run_data_{run_id}")
            if cached_data:
                results = cached_data.get("results", [])
            else:
                raise HTTPException(404, "Run not found in cache")
        else:
            raise HTTPException(404, "Run not found")
    else:
        # We need to serialize the results from the active run
        # and also pre-populate the LLM analysis if it exists.
        results = []
        for r in active_runs[run_id]["agent"].test_results:
            serialized_r = {
                "test_id": r["scenario"].test_id,
                "scenario": r["scenario"].model_dump(),
                "execution": r["execution"].model_dump() if r.get("execution") else None,
                "verification": r["verification"].model_dump() if r.get("verification") else None,
                "diagnosis": r.get("diagnosis"),
                "llm_analysis": r.get("llm_analysis")
            }
            results.append(serialized_r)
            
    # For any failures that don't have llm_analysis yet, fetch it now
    for r in results:
        if r.get("verification") and r["verification"].get("status") == "FAIL" and not r.get("llm_analysis"):
            try:
                analysis = await analyze_test_failure(run_id, r["test_id"])
                r["llm_analysis"] = analysis.get("analysis")
            except Exception:
                r["llm_analysis"] = "Analysis unavailable."

    from ps3_agent.api.report_generator import generate_markdown_report
    report_md = generate_markdown_report(run_id, results)
    
    # Escape triple backticks inside the markdown if needed (usually fine inside a script tag)
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>JOY - Autonomous Firmware Testing Report</title>
        <script type="module" src="https://cdn.jsdelivr.net/gh/zerodevx/zero-md@2/dist/zero-md.min.js"></script>
        <style>
            body {{ background-color: #0d1117; margin: 0; padding: 40px; display: flex; justify-content: center; }}
            .container {{ max-width: 900px; width: 100%; }}
        </style>
    </head>
    <body>
        <div class="container">
            <zero-md>
                <template>
                    <style>
                        .markdown-body {{ background-color: #0d1117 !important; color: #c9d1d9 !important; font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif !important; }}
                        .markdown-body h1, .markdown-body h2 {{ border-bottom-color: #30363d !important; }}
                        .markdown-body a {{ color: #58a6ff !important; }}
                        .markdown-body code {{ background-color: rgba(110,118,129,0.4) !important; color: #f0f6fc !important; }}
                    </style>
                </template>
                <script type="text/markdown">
{report_md}
                </script>
            </zero-md>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

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
    return HTMLResponse(content="""
    <html><body style="background:#000;color:#fff;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh;">
    <div style="text-align:center">
        <h1>JOY</h1>
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
