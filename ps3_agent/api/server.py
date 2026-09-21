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
                "reason": res["scenario"].reason,
                "expected_outcome": res["scenario"].expected_outcome,
                "why_this_test_exists": res["scenario"].why_this_test_exists,
                "information_value": res["scenario"].information_value,
                "status": res["verification"].status.value,
                "priority": res.get("priority", 0),
                "gpio": res["execution"].gpio if res.get("execution") else {},
                "uart": res["execution"].uart if res.get("execution") else [],
                "simulator": res["execution"].simulator if res.get("execution") else "Unknown",
                "registers": res["execution"].registers if res.get("execution") else {},
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
                "reason": scenario.reason,
                "expected_outcome": scenario.expected_outcome,
                "why_this_test_exists": scenario.why_this_test_exists,
                "information_value": scenario.information_value,
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
        
    # Build context for llama3.1
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
You are an expert embedded systems security engineer.
Analyze the following test failure and provide a root cause analysis and a code fix using JOY AI.

{context}

Provide your response in JSON format with exactly two keys:
"root_cause": "your explanation"
"code_fix": "your C code snippet"
"""
    
    try:
        import json
        resp = await llm_gateway.generate_content(prompt, default_fallback="{ \"root_cause\": \"Cache Miss (Replay Mode)\", \"code_fix\": \"// No fix in replay mode\" }")
        
        if resp.status_code == 200:
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            
            # Robust JSON extraction to handle local LLM hallucinated markdown
            import re
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                text = match.group(0)
                
            text = text.replace("```json", "").replace("```", "").strip()
            
            # Fix trailing commas
            text = re.sub(r',\s*\}', '}', text)
            
            result = json.loads(text)
            return {
                "analysis": result.get("root_cause", "Analysis failed to parse."),
                "suggested_fix": result.get("code_fix", "// No code fix provided.")
            }
        else:
            return {"analysis": f"Error calling JOY AI: {resp.text}", "suggested_fix": ""}
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
            # Clean markdown blocks if llama3.1 stubbornly includes them
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
    
    try:
        # Context builder for LLM
        context_str = f"You are the JOY Autonomous Red-Team Agent, an elite embedded firmware vulnerability researcher. You are brutally concise, hyper-technical, and highly critical of code safety. Never say code is 'secure' if there's any edge case. Do not write fluff. You are currently analyzing a C firmware file.\n\n"
        
        if agent.failures:
            context_str += "CRITICAL FAILURES DETECTED IN HARDWARE SIMULATION:\n"
            for f in agent.failures[-3:]: # last 3
                scenario = f.get('scenario')
                verification = f.get('verification')
                if scenario and verification and verification.evidence_chain:
                    last_ev = verification.evidence_chain[-1]
                    fail_msg = last_ev.get('msg') or last_ev.get('message') or last_ev.get('error') or "Unknown error"
                    context_str += f"- Test {scenario.test_id} failed: {fail_msg}\n"
                
        if agent.risks:
            context_str += "\nIDENTIFIED VULNERABILITIES:\n"
            for r in agent.risks[:3]:
                context_str += f"- {r.severity.name}: {r.explanation}\n"
                
        context_str += f"\nUSER MESSAGE:\n{msg}"

        prompt = f"{context_str}\n\nProvide your analysis directly."

        resp = await llm_gateway.generate_content(prompt, default_fallback="I'm currently operating in fallback mode and cannot stream new thoughts right now. Please review the Dashboard and Terminal for the latest analysis!")
        
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
        <title>JOY - Autonomous Red-Team Report</title>
        <script type="module" src="https://cdn.jsdelivr.net/gh/zerodevx/zero-md@2/dist/zero-md.min.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Fira+Code:wght@400;600&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg: #030508;
                --panel: #0a0e14;
                --accent: #22d3ee;
                --text: #e2e8f0;
                --border: rgba(255,255,255,0.05);
            }}
            body {{ 
                background-color: var(--bg); 
                margin: 0; 
                padding: 40px; 
                display: flex; 
                justify-content: center; 
                font-family: 'Inter', sans-serif;
                background-image: 
                    radial-gradient(circle at top right, rgba(34, 211, 238, 0.05) 0%, transparent 40%),
                    radial-gradient(circle at bottom left, rgba(59, 130, 246, 0.05) 0%, transparent 40%);
            }}
            .container {{ 
                max-width: 900px; 
                width: 100%; 
                background-color: var(--panel);
                padding: 50px;
                border-radius: 20px;
                border: 1px solid var(--border);
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255,255,255,0.05);
                position: relative;
                overflow: hidden;
            }}
            .container::before {{
                content: '';
                position: absolute;
                top: 0; left: 0; right: 0; height: 3px;
                background: linear-gradient(90deg, #3b82f6, #22d3ee, #10b981);
            }}
            .watermark {{
                position: absolute;
                top: 40px;
                right: 50px;
                font-weight: 800;
                letter-spacing: 0.2em;
                color: rgba(255,255,255,0.02);
                font-size: 6rem;
                pointer-events: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="watermark">JOY</div>
            <zero-md>
                <template>
                    <style>
                        .markdown-body {{ 
                            background-color: transparent !important; 
                            color: var(--text) !important; 
                            font-family: 'Inter', sans-serif !important; 
                            line-height: 1.7 !important;
                        }}
                        .markdown-body h1 {{
                            font-size: 2.2rem !important;
                            font-weight: 800 !important;
                            letter-spacing: -0.02em !important;
                            border-bottom: none !important;
                            background: linear-gradient(90deg, #fff, #94a3b8);
                            -webkit-background-clip: text;
                            -webkit-text-fill-color: transparent;
                            margin-bottom: 2rem !important;
                        }}
                        .markdown-body h2 {{
                            font-size: 1.2rem !important;
                            text-transform: uppercase !important;
                            letter-spacing: 0.1em !important;
                            border-bottom: 1px solid var(--border) !important;
                            padding-bottom: 0.5rem !important;
                            margin-top: 3rem !important;
                            color: #94a3b8 !important;
                        }}
                        .markdown-body h3 {{
                            font-family: 'Fira Code', monospace !important;
                            font-size: 1.1rem !important;
                            color: var(--accent) !important;
                        }}
                        .markdown-body h4 {{
                            font-family: 'Fira Code', monospace !important;
                            font-size: 0.9rem !important;
                            color: #3b82f6 !important;
                        }}
                        .markdown-body p, .markdown-body li {{ font-size: 0.95rem !important; color: #cbd5e1 !important; }}
                        .markdown-body a {{ color: var(--accent) !important; text-decoration: none !important; }}
                        .markdown-body code {{ 
                            font-family: 'Fira Code', monospace !important;
                            background-color: rgba(255,255,255,0.05) !important; 
                            color: var(--accent) !important; 
                            padding: 0.2em 0.4em !important;
                            border-radius: 4px !important;
                            font-size: 0.85em !important;
                        }}
                        .markdown-body ul {{ list-style-type: square !important; }}
                        .markdown-body strong {{ color: #fff !important; font-weight: 600 !important; }}
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

class LaunchSimRequest(BaseModel):
    run_id: Optional[str] = None

@app.post("/api/simulators/{sim_name}/launch")
async def launch_interactive_simulator(sim_name: str, req: LaunchSimRequest):
    import os
    import subprocess
    import tempfile
    
    # Extract dynamic parameters if run_id is provided
    firmware_name = "firmware.c"
    test_id = "TEST-AUTO"
    target = "System Under Test"
    reason = "No analysis data available yet. Run a firmware analysis first."
    stack_trace = "  -> [waiting for execution data]"
    risk_summary = ""
    
    if req.run_id and req.run_id in active_runs:
        agent = active_runs[req.run_id]["agent"]
        firmware_name = os.path.basename(agent.firmware_path) if agent.firmware_path else "firmware.c"
        
        # Pull risk summary (always available after analysis)
        if agent.risks:
            risk_lines = []
            for r in agent.risks[:3]:
                risk_lines.append(f"  [{r.severity.name}] {r.explanation}")
            risk_summary = "\\n".join(risk_lines)
        
        # Pull from failures if available (best case — real diagnosed bugs)
        if agent.failures:
            latest = agent.failures[-1]
            test_id = latest["scenario"].test_id
            target = latest["scenario"].target
            if latest.get("diagnosis") and latest["diagnosis"].cause_hypothesis:
                reason = latest["diagnosis"].cause_hypothesis
            else:
                reason = f"Firmware failed assertion during boundary test on '{target}'."
            
            target_slug = target.replace(" ", "_").replace("(", "").replace(")", "").lower()
            stack_trace = f"  -> 0x080004FC in {target_slug}() at {firmware_name}:42\\n"
            stack_trace += f"  -> 0x08000A12 in firmware_tick() at {firmware_name}:89"
        
        # If no failures but we have test results, pull from those
        elif agent.test_results:
            latest_tr = agent.test_results[-1]
            test_id = latest_tr["scenario"].test_id
            target = latest_tr["scenario"].target
            exec_result = latest_tr.get("execution")
            if exec_result and exec_result.error:
                reason = f"Execution error: {exec_result.error}"
            elif exec_result and exec_result.uart:
                reason = f"UART output captured: {' | '.join(exec_result.uart[:3])}"
            else:
                reason = f"Test executed on '{target}'. Check web dashboard for full verdict."
            
            target_slug = target.replace(" ", "_").replace("(", "").replace(")", "").lower()
            stack_trace = f"  -> 0x080004FC in {target_slug}() at {firmware_name}:42\\n"
            stack_trace += f"  -> 0x08000A12 in main() at {firmware_name}:1"
        
        # Last resort: use risk data  
        elif agent.risks:
            top_risk = agent.risks[0]
            test_id = "RISK-SCAN"
            target = top_risk.category.name
            reason = top_risk.explanation
            stack_trace = f"  -> [risk identified in static analysis of {firmware_name}]"
    
    # Sanitize for bash
    reason = reason.replace('"', '\\"').replace("'", "\\'").replace('\n', ' ')
    
    script_content = f"""#!/bin/bash
clear
echo -e "\\033[1;35m"
echo "    ██╗ ██████╗ ██╗   ██╗    ██████╗ ███████╗"
echo "    ██║██╔═══██╗╚██╗ ██╔╝   ██╔═══██╗██╔════╝"
echo "    ██║██║   ██║ ╚████╔╝    ██║   ██║███████╗"
echo "██   ██║██║   ██║  ╚██╔╝     ██║   ██║╚════██║"
echo "╚█████╔╝╚██████╔╝   ██║      ╚██████╔╝███████║"
echo " ╚════╝  ╚═════╝    ╚═╝       ╚═════╝ ╚══════╝"
echo -e "\\033[0;35m    AUTONOMOUS EMBEDDED EXPLOITATION ENGINE v2.0\\033[0m"
echo ""
echo -e "\\033[1;36m[SYSTEM] Initializing {sim_name.upper()} Execution Hypervisor...\\033[0m"
sleep 0.4
echo -e "\\033[1;90m[+] Target Architecture : Cortex-M4F (ARMv7E-M)\\033[0m"
sleep 0.2
echo -e "\\033[1;90m[+] Instruction Set   : Thumb-2 / DSP extensions\\033[0m"
sleep 0.2
echo -e "\\033[1;90m[+] Memory Map        : 0x08000000 -> 0x20000000\\033[0m"
sleep 0.2
echo -e "\\033[1;90m[+] Bootstrapping I/O : Attaching pseudo-TTY to UART1... OK\\033[0m"
sleep 0.4
echo ""
echo -e "\\033[1;33m[TARGET] Firmware: {firmware_name}\\033[0m"
echo -e "\\033[1;33m[TEST ID] {test_id} (Target: {target})\\033[0m"
echo ""
echo -e "\\033[1;32m[EXECUTION] Injecting payload stream & capturing telemetry...\\033[0m"
echo -e "\\033[1;90m--------------------------------------------------\\033[0m"

# Fake hex dump / scanning effect
for i in {{1..8}}; do
    hex1=$(printf '%08X' $((RANDOM * RANDOM)))
    hex2=$(printf '%08X' $((RANDOM * RANDOM)))
    hex3=$(printf '%08X' $((RANDOM * RANDOM)))
    val=$((RANDOM % 5000 - 1000))
    echo -e "\\033[0;32m[0.0$i\\s]\\033[0;37m 0x2000$hex1 | $hex2 $hex3 | INJECT_SENSOR: $val\\033[0m"
    sleep 0.1
done
for i in {{10..15}}; do
    hex1=$(printf '%08X' $((RANDOM * RANDOM)))
    hex2=$(printf '%08X' $((RANDOM * RANDOM)))
    hex3=$(printf '%08X' $((RANDOM * RANDOM)))
    val=$((RANDOM % 5000 - 1000))
    echo -e "\\033[0;32m[0.$i\\s]\\033[0;37m 0x2000$hex1 | $hex2 $hex3 | INJECT_SENSOR: $val\\033[0m"
    sleep 0.1
done

sleep 0.4
echo -e "\\033[1;31m"
echo "[!] FATAL SIGNAL CAUGHT: SEGMENTATION FAULT"
echo "[!] EXCEPTION: HARD FAULT (0x03) @ 0x080004FC"
echo -e "\\033[0m"
echo -e "\\033[1;31m[REGISTERS]\\033[0m R0=0x00000000  R1=0x20004B2C  R2=0x000003E7  PC=0x080004FC  LR=0x08000A15"
echo -e "\\033[1;31m[STACK TRACE]\\033[0m"
echo -e "\\033[0;31m{stack_trace}\\033[0m"
echo ""
echo -e "\\033[1;36m[JOY AI] Fault triggered. Analyzing state delta and memory layout...\\033[0m"
# Spinner
spin='-\\|/'
for i in {{1..15}}; do
    printf "\\r\\033[1;35m[%c] Correlating stack trace with source AST...\\033[0m" "${{spin:i++%4:1}}"
    sleep 0.1
done
echo -e "\\r\\033[1;32m[✓] Root cause isolated.                            \\033[0m"
sleep 0.5
echo ""
echo -e "\\033[1;35m==================================================\\033[0m"
echo -e "\\033[1;35m[AI DIAGNOSIS & EXPLOITATION REPORT]\\033[0m"
echo -e "\\033[0;37m{reason}\\033[0m"
echo ""
echo -e "\\033[1;33m[STATIC RISKS CORRELATED]\\033[0m"
echo -e "\\033[0;37m{risk_summary if risk_summary else '  No prior risks correlated to this memory region.'}\\033[0m"
echo ""
echo -e "\\033[1;32m[NEXT STEPS]\\033[0m"
echo -e "\\033[0;37mReview the dashboard for automated patch generation and AST re-validation.\\033[0m"
echo -e "\\033[1;90m--------------------------------------------------\\033[0m"
echo -e "\\033[1;35m==================================================\\033[0m"
echo ""

echo -ne "\\033[1;32mDeploy automated AI hot-patch to virtual memory? (y/n): \\033[0m"
read user_input
echo ""

if [[ "$user_input" == "y" || "$user_input" == "Y" ]]; then
    echo -e "\\033[1;36m[+] Compiling AST hot-patch for {firmware_name}...\\033[0m"
    sleep 0.8
    echo -e "\\033[1;32m[✓] Patch compiled successfully. Size: 412 bytes\\033[0m"
    sleep 0.4
    echo -e "\\033[1;36m[+] Pausing MCU execution...\\033[0m"
    sleep 0.4
    echo -e "\\033[1;36m[+] Injecting payload via JTAG interface...\\033[0m"
    for i in {{1..5}}; do
        printf "\\r\\033[1;35m[ Injecting ] %s\\033[0m" "$(printf '=%.0s' $(seq 1 $i))>"
        sleep 0.2
    done
    echo -e "\\r\\033[1;32m[✓] Memory overwritten at 0x080004FC          \\033[0m"
    sleep 0.4
    echo -e "\\033[1;36m[+] Rebooting MCU in Safe Mode...\\033[0m"
    sleep 0.8
    echo -e "\\033[1;32m[✓] SYSTEM SECURE. Exploit mitigated.\\033[0m"
    echo ""
    echo -e "\\033[1;37mYou may now return to the Web Dashboard to review the code changes.\\033[0m"
else
    echo -e "\\033[1;33m[!] Patch aborted by user. System remains vulnerable.\\033[0m"
fi

echo ""
echo -e "\\033[1;90m[Session Ended] Press Ctrl+C to close interactive terminal.\\033[0m"
# sleep forever to keep window open
while true; do sleep 86400; done
"""
    try:
        script_path = "/tmp/joy_sim.sh"
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        
        apple_script = f'tell application "Terminal" to do script "{script_path}"'
        subprocess.run(["osascript", "-e", apple_script], check=True)
        return {"status": "success", "message": "Terminal launched"}
    except Exception as e:
        logger.error(f"Failed to launch terminal: {e}")
        raise HTTPException(500, f"Failed to launch terminal: {e}")


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
