"""
PS3 Firmware Agent — Local Web Server (FastAPI)

Serves the dashboard, 3D viewer, board designer, and run APIs.
Start with: firmware-agent serve
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="PS3 Firmware Agent", version="1.0.0")

# ---------- paths ----------
PROJECT_ROOT = Path(os.environ.get("PS3_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
TRACES_DIR = PROJECT_ROOT / "artifacts" / "traces"
BOARDS_DIR = PROJECT_ROOT / "hardware" / "boards"
VIEWER_PATH = PROJECT_ROOT / "src" / "firmware_agent" / "reporting" / "viewer" / "rig_view.html"
SCHEMAS_DIR = PROJECT_ROOT / "schemas"


def _get_capabilities(chip: str):
    """Return SimulatorCapabilities for a chip, importing locally to avoid circular deps."""
    import sys
    src_dir = str(PROJECT_ROOT / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    from firmware_agent.simulator.labwired import LabWiredAdapter
    return LabWiredAdapter().capabilities(chip)


# ---------- API: Runs ----------

@app.get("/api/runs")
def list_runs():
    """List all available trace runs."""
    runs = []
    if not TRACES_DIR.exists():
        return runs
    for run_dir in sorted(TRACES_DIR.iterdir()):
        if not run_dir.is_dir():
            continue
        trace_path = run_dir / "trace.json"
        if not trace_path.exists():
            continue
        try:
            trace = json.loads(trace_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        runs.append({
            "run_id": run_dir.name,
            "verdict": trace.get("verdict", "UNAVAILABLE"),
            "chip": trace.get("board", {}).get("chip", "unknown"),
            "duration_ns": trace.get("duration_ns", 0),
            "timestamp": datetime.fromtimestamp(trace_path.stat().st_mtime).isoformat(),
            "trace_file": str(trace_path),
        })
    return runs


@app.get("/api/runs/{run_id}/trace.json")
def get_trace(run_id: str):
    """Serve the raw trace.v1.json for a run."""
    trace_path = TRACES_DIR / run_id / "trace.json"
    if not trace_path.exists():
        raise HTTPException(404, f"No trace found for run_id={run_id}")
    return JSONResponse(json.loads(trace_path.read_text()))


# ---------- API: Boards ----------

@app.get("/api/boards")
def list_boards():
    """List all board descriptors, annotated with simulator capability info."""
    boards = []
    if not BOARDS_DIR.exists():
        return boards
    for board_file in sorted(BOARDS_DIR.glob("*.json")):
        try:
            board = json.loads(board_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        chip = board.get("chip", "")
        cap = _get_capabilities(chip)
        boards.append({
            "file": board_file.name,
            "board": board,
            "simulator": {
                "chip": cap.chip,
                "available": cap.available,
                "error": cap.error,
                "supported_pins_count": len(cap.supported_pins),
            }
        })
    return boards


@app.get("/api/boards/{chip}")
def get_board(chip: str):
    """Return a single board descriptor + live capability info."""
    board_path = BOARDS_DIR / f"{chip}.json"
    if board_path.exists():
        board = json.loads(board_path.read_text())
    else:
        board = None
    cap = _get_capabilities(chip)
    return {
        "board": board,
        "simulator": {
            "chip": cap.chip,
            "available": cap.available,
            "error": cap.error,
            "supported_pins": cap.supported_pins,
            "can_observe_gpio": cap.can_observe_gpio,
            "can_observe_uart": cap.can_observe_uart,
        }
    }


@app.post("/api/boards")
async def create_board(request: Request):
    """Accept a new board descriptor JSON, validate against schema and capabilities."""
    try:
        board = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON body")

    # Required fields
    chip = board.get("chip")
    if not chip:
        raise HTTPException(400, "Missing required field: 'chip'")
    if "peripherals" not in board:
        raise HTTPException(400, "Missing required field: 'peripherals'")

    # Validate pins against simulator capabilities
    cap = _get_capabilities(chip)
    if cap.available and cap.supported_pins:
        for periph in board.get("peripherals", []):
            for pin in periph.get("pins", []):
                if pin not in cap.supported_pins and pin not in ["TX", "RX"]:
                    raise HTTPException(
                        422,
                        f"Pin '{pin}' on peripheral '{periph.get('id', '?')}' "
                        f"is not recognized by the simulator for chip '{chip}'. "
                        f"Valid pins: {cap.supported_pins[:10]}..."
                    )

    # Set metadata
    board.setdefault("created_by", "user")
    board.setdefault("board_name", f"Custom {chip} board")

    # Determine filename
    board_name = board.get("board_name", chip).replace(" ", "_").lower()
    filename = f"{board_name}.json"
    out_path = BOARDS_DIR / filename
    BOARDS_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(board, indent=2))

    return {"status": "saved", "path": str(out_path), "board": board}


# ---------- Pages ----------

@app.get("/view/{run_id}", response_class=HTMLResponse)
def view_run(run_id: str):
    """Serve the 3D viewer, configured to fetch trace from API."""
    trace_path = TRACES_DIR / run_id / "trace.json"
    if not trace_path.exists():
        raise HTTPException(404, f"No trace found for run_id={run_id}")
    if not VIEWER_PATH.exists():
        raise HTTPException(500, "rig_view.html not found")
    html = VIEWER_PATH.read_text()
    # Inject a query-string redirect: the viewer reads ?trace-url= at boot
    # We replace the <html> tag with one that sets the URL param via JS
    inject = f"""<script>
    if (!window.location.search.includes('trace-url')) {{
        const sep = window.location.search ? '&' : '?';
        window.history.replaceState(null, '', window.location.pathname + sep + 'trace-url=/api/runs/{run_id}/trace.json');
    }}
    </script>"""
    html = html.replace("</head>", f"{inject}\n</head>")
    return HTMLResponse(html)


@app.get("/compare/{run_a}/{run_b}", response_class=HTMLResponse)
def compare_runs(run_a: str, run_b: str):
    """Serve the 3D viewer in comparison mode."""
    for rid in [run_a, run_b]:
        if not (TRACES_DIR / rid / "trace.json").exists():
            raise HTTPException(404, f"No trace found for run_id={rid}")
    if not VIEWER_PATH.exists():
        raise HTTPException(500, "rig_view.html not found")
    html = VIEWER_PATH.read_text()
    inject = f"""<script>
    if (!window.location.search.includes('compare-url-a')) {{
        const sep = window.location.search ? '&' : '?';
        window.history.replaceState(null, '', window.location.pathname + sep +
            'compare-url-a=/api/runs/{run_a}/trace.json&compare-url-b=/api/runs/{run_b}/trace.json');
    }}
    </script>"""
    html = html.replace("</head>", f"{inject}\n</head>")
    return HTMLResponse(html)


# ---------- Dashboard ----------

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PS3 Firmware Agent — Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --pcb-black: #0b0f0d;
    --pcb-panel: #10201a;
    --pcb-panel-2: #142620;
    --copper: #b8733b;
    --copper-dim: #6f4728;
    --phosphor: #ffb000;
    --phosphor-dim: #6b4b0a;
    --silk: #e9ede7;
    --silk-dim: #6f7a73;
    --sig-red: #ff4f3e;
    --sig-green: #4ade80;
    --hair: rgba(233,237,231,0.14);
    --radius: 3px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body {
    height: 100%; background: var(--pcb-black); color: var(--silk);
    font-family: 'IBM Plex Mono', monospace; overflow-x: hidden;
  }

  /* Calibration-mark frame */
  .cal-frame {
    position: relative; border: 1px solid var(--hair); margin: 12px;
    padding: 20px 24px;
  }
  .cal-frame::before, .cal-frame::after {
    content: ''; position: absolute; width: 16px; height: 16px;
    border-color: var(--copper); border-style: solid;
  }
  .cal-frame::before { top: -1px; left: -1px; border-width: 2px 0 0 2px; }
  .cal-frame::after  { bottom: -1px; right: -1px; border-width: 0 2px 2px 0; }

  h1 {
    font-family: 'Big Shoulders Display', sans-serif; font-weight: 800;
    font-size: 28px; letter-spacing: 2px; text-transform: uppercase;
    color: var(--phosphor); margin-bottom: 4px;
  }
  .subtitle { color: var(--silk-dim); font-size: 11px; margin-bottom: 20px; }

  /* Sections */
  .section-title {
    font-family: 'Big Shoulders Display', sans-serif; font-weight: 700;
    font-size: 16px; letter-spacing: 1.5px; text-transform: uppercase;
    color: var(--copper); margin: 24px 0 12px; padding-bottom: 4px;
    border-bottom: 1px solid var(--copper-dim);
  }

  /* Run list */
  .run-table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .run-table th {
    text-align: left; padding: 6px 10px; color: var(--silk-dim);
    border-bottom: 1px solid var(--hair); font-weight: 500;
    font-family: 'Big Shoulders Display', sans-serif;
    text-transform: uppercase; letter-spacing: 1px; font-size: 11px;
  }
  .run-table td { padding: 8px 10px; border-bottom: 1px solid var(--hair); }
  .run-table tr:hover { background: var(--pcb-panel); }
  .verdict-pass { color: var(--sig-green); font-weight: 600; }
  .verdict-fail { color: var(--sig-red); font-weight: 600; }
  .verdict-unavailable { color: var(--silk-dim); }
  a { color: var(--phosphor); text-decoration: none; }
  a:hover { text-decoration: underline; }

  /* Board cards */
  .board-card {
    border: 1px solid var(--hair); padding: 12px 16px; margin-bottom: 8px;
    position: relative;
  }
  .board-card::before {
    content: ''; position: absolute; top: -1px; left: -1px;
    width: 10px; height: 10px; border-top: 2px solid var(--copper);
    border-left: 2px solid var(--copper);
  }
  .board-card .chip-name {
    font-family: 'Big Shoulders Display', sans-serif; font-weight: 700;
    font-size: 14px; color: var(--phosphor); text-transform: uppercase;
  }
  .board-card .periph-count { color: var(--silk-dim); font-size: 11px; }
  .board-card .sim-status { font-size: 11px; margin-top: 4px; }
  .sim-ok { color: var(--sig-green); }
  .sim-err { color: var(--sig-red); }

  /* Circuit trace animation */
  .trace-line {
    stroke: var(--copper-dim); stroke-width: 2; fill: none;
  }
  .trace-pulse {
    fill: var(--phosphor); filter: drop-shadow(0 0 4px var(--phosphor));
  }
  .led-indicator { transition: fill 0.3s, filter 0.3s; }
  .led-off { fill: #1a1a1a; filter: none; }
  .led-on  { fill: var(--sig-green); filter: drop-shadow(0 0 6px var(--sig-green)); }

  /* Transport bar */
  .transport {
    position: fixed; bottom: 0; left: 0; right: 0; height: 40px;
    background: var(--pcb-panel); border-top: 1px solid var(--copper-dim);
    display: flex; align-items: center; padding: 0 20px;
    font-size: 11px; color: var(--silk-dim); z-index: 100;
  }
  .transport .status-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--sig-green); margin-right: 8px;
    box-shadow: 0 0 4px var(--sig-green);
  }
</style>
</head>
<body>
<div class="cal-frame">
  <h1>PS3 Firmware Agent</h1>
  <div class="subtitle">AUTONOMOUS EMBEDDED FIRMWARE TESTING PLATFORM</div>

  <!-- Circuit Trace Animation -->
  <svg id="circuit-anim" width="100%" height="50" viewBox="0 0 800 50" style="margin-bottom:16px;">
    <path class="trace-line" d="M 0,25 L 200,25 L 220,10 L 280,10 L 300,25 L 500,25 L 520,40 L 580,40 L 600,25 L 780,25" />
    <circle class="trace-pulse" id="pulse-dot" cx="0" cy="25" r="4" opacity="0" />
    <circle class="led-indicator led-off" id="led-1" cx="300" cy="25" r="6" />
    <circle class="led-indicator led-off" id="led-2" cx="600" cy="25" r="6" />
  </svg>

  <div class="section-title">Test Runs</div>
  <table class="run-table">
    <thead><tr><th>Run ID</th><th>Verdict</th><th>Chip</th><th>Duration</th><th>Timestamp</th><th>Actions</th></tr></thead>
    <tbody id="run-list"><tr><td colspan="6" style="color:var(--silk-dim);">Loading...</td></tr></tbody>
  </table>

  <div class="section-title">Board Descriptors</div>
  <div id="board-list"><div style="color:var(--silk-dim);">Loading...</div></div>
</div>

<div class="transport">
  <div class="status-dot"></div>
  <span>SERVER ONLINE</span>
  <span style="margin-left:auto;" id="clock"></span>
</div>

<script>
// Clock
setInterval(() => {
  document.getElementById('clock').textContent = new Date().toLocaleTimeString('en-US', {hour12:false});
}, 1000);

// Load runs
fetch('/api/runs').then(r=>r.json()).then(runs => {
  const tbody = document.getElementById('run-list');
  if (!runs.length) { tbody.innerHTML = '<tr><td colspan="6" style="color:var(--silk-dim);">No runs found in artifacts/traces/</td></tr>'; return; }
  tbody.innerHTML = runs.map(r => {
    const vc = r.verdict === 'PASS' ? 'verdict-pass' : r.verdict === 'FAIL' ? 'verdict-fail' : 'verdict-unavailable';
    const dur = (r.duration_ns / 1e6).toFixed(2) + ' ms';
    const ts = new Date(r.timestamp).toLocaleString();
    return `<tr>
      <td><code>${r.run_id}</code></td>
      <td class="${vc}">${r.verdict}</td>
      <td>${r.chip}</td>
      <td>${dur}</td>
      <td>${ts}</td>
      <td><a href="/view/${r.run_id}">VIEW</a></td>
    </tr>`;
  }).join('');

  // If there are 2+ runs, add compare links
  if (runs.length >= 2) {
    const last = runs[runs.length-1];
    const first = runs[0];
    tbody.innerHTML += `<tr><td colspan="6" style="padding-top:12px;">
      <a href="/compare/${first.run_id}/${last.run_id}">⟷ COMPARE ${first.run_id} vs ${last.run_id}</a>
    </td></tr>`;
  }

  // Drive the circuit animation from the first run's trace data
  animateCircuit(runs[0]);
});

// Load boards
fetch('/api/boards').then(r=>r.json()).then(boards => {
  const el = document.getElementById('board-list');
  if (!boards.length) { el.innerHTML = '<div style="color:var(--silk-dim);">No board descriptors in hardware/boards/</div>'; return; }
  el.innerHTML = boards.map(b => {
    const periph_count = (b.board.peripherals || []).length;
    const sim = b.simulator.available
      ? `<span class="sim-ok">✓ SIMULATOR AVAILABLE (${b.simulator.supported_pins_count} pins)</span>`
      : `<span class="sim-err">✗ ${b.simulator.error || 'No simulator backing'}</span>`;
    const created = b.board.created_by === 'user' ? ' [USER]' : '';
    return `<div class="board-card">
      <div class="chip-name">${b.board.chip}${created}</div>
      <div class="periph-count">${periph_count} peripheral(s) · ${b.board.package || 'unknown package'}</div>
      <div class="sim-status">${sim}</div>
    </div>`;
  }).join('');
});

// Circuit animation — driven by real run data, idle when no run selected
function animateCircuit(run) {
  const pulse = document.getElementById('pulse-dot');
  const led1 = document.getElementById('led-1');
  const led2 = document.getElementById('led-2');
  const path = document.querySelector('.trace-line');
  if (!run || !path) return;

  // Fetch actual trace to get real gpio timestamps
  fetch(`/api/runs/${run.run_id}/trace.json`).then(r=>r.json()).then(trace => {
    const gpio = trace.channels?.gpio || [];
    if (!gpio.length) return; // No data → idle

    const duration = trace.duration_ns || 1;
    const totalAnimMs = 4000; // 4 second animation cycle

    // Find first HIGH transition
    const firstHigh = gpio.find(g => g.value === 1);
    const firstHighPct = firstHigh ? firstHigh.t_ns / duration : 1;

    // Animate the pulse dot along the SVG path
    const pathLen = path.getTotalLength();
    let start = null;
    function step(ts) {
      if (!start) start = ts;
      const elapsed = (ts - start) % totalAnimMs;
      const pct = elapsed / totalAnimMs;
      const pt = path.getPointAtLength(pct * pathLen);
      pulse.setAttribute('cx', pt.x);
      pulse.setAttribute('cy', pt.y);
      pulse.setAttribute('opacity', '1');

      // Light up LEDs at the correct proportion of the trace
      led1.className.baseVal = 'led-indicator ' + (pct >= firstHighPct * 0.5 ? 'led-on' : 'led-off');
      led2.className.baseVal = 'led-indicator ' + (pct >= firstHighPct ? 'led-on' : 'led-off');

      requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }).catch(() => {}); // Silently stay idle if fetch fails
}
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard():
    """Serve the main dashboard."""
    return HTMLResponse(DASHBOARD_HTML)
