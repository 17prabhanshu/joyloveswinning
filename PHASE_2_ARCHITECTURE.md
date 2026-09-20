# Phase 2 (Hackathon-Realistic, v2): JOY Extension Plan

**Context for implementer (Antigravity):** Renode and Wokwi support are **named requirements in the hackathon problem statement**, not optional polish — treat them as graded scope, not nice-to-haves. Physical ESP32/Arduino hardware is a bonus tier only, attempted after the required scope is demo-stable. Every phase below must leave the system in a fully demoable state on its own — do not start a later phase until the current phase's exit criteria pass.

**Do not touch, regardless of phase:**
- The existing `SimulatorAdapter` interface contract — `AgentLoop` must not need to know whether it's talking to Renode, Wokwi, physical hardware, or the deterministic mock.
- The `DeterministicSimulator` fallback path — it stays as the last-resort safety net if every real execution target fails.

---

## Phase A — LLM Gateway & Rate-Limit Resilience
**Priority: highest. Do this first. Do it fully.**

### Goal
Never visibly fail or stall mid-demo due to Gemini 429/503 errors, regardless of what else ships in later phases.

### Files

**CREATE `ps3_agent/api/llm_gateway.py`**
- `LLMGateway` class wrapping all Gemini calls.
- `diskcache`-based response cache, keyed by `hash(prompt + model)`.
- 429-specific backoff with jitter, respecting `retry-after` where present.
- Concurrency cap via `asyncio.Semaphore` (max 2–3 in-flight Gemini calls).
- Fallback chain: `gemini-3.6-flash` → `gemini-1.5-flash` → `gemini-2.0-flash-exp` → cached "safe default".

**MODIFY `ps3_agent/api/server.py`**
- Route all Gemini calls through `LLMGateway`. Remove any remaining direct `httpx` calls to the Gemini endpoint.

**Demo safety net:**
- Add a `--replay-mode` flag serving pre-recorded LLM responses for the known `fan_controller.c` run.

---

## Phase B — Wokwi Headless Execution
**Priority: second. Start once Phase A passes. This is required scope.**

### Goal
Real Wokwi simulation execution — no USB/driver dependency, more demo-reliable than physical hardware, and directly satisfies the problem statement.

### Files

**CREATE `ps3_agent/execution/wokwi_adapter.py`**
- Wraps the `wokwi-cli` headless simulation runner.
- Generates a `diagram.json` describing the board and wiring.
- Compiles `fan_controller.c` to a binary/hex the Wokwi simulator can load (via `arduino-cli` or `platformio`).
- Launches `wokwi-cli` against the diagram + binary, injects test stimulus, and scrapes serial/UART output.

**MODIFY `ps3_agent/execution/simulator.py`**
- Replace the current Wokwi stub with real dispatch to `WokwiAdapter`.

---

## Phase C — Renode Scripted Execution
**Priority: third. Start once Phase B passes. Also required scope.**

### Goal
Real Renode emulation — scriptable via `.resc` monitor files, directly satisfies the problem statement's second named tool.

### Files

**CREATE `ps3_agent/execution/compiler.py`**
- Shared compilation wrapper for both Phase B and C.

**CREATE `ps3_agent/execution/renode_adapter.py`**
- Generates a `.resc` script targeting a standard Renode platform description.
- Boots Renode headless, loads the compiled `.elf`, injects test stimulus, and reads back register/UART state.

**MODIFY `ps3_agent/execution/simulator.py`**
- Replace the current Renode stub with real dispatch to `RenodeAdapter`.

---

## Phase D — Physical ESP32/Arduino (Bonus Tier)
**Priority: fourth. Only attempt if Phases A–C are demo-stable with real time remaining.**

### Goal
A literal physical board flashing/crashing/patching live.

### Files

**CREATE `ps3_agent/execution/physical_adapter.py`**
- Uses `esptool.py` or `arduino-cli upload` to flash the binary compiled in Phase C's `compiler.py`.
- Uses `pyserial` to inject stimulus and read UART output.

**MODIFY `ps3_agent/execution/simulator.py`**
- Add adapter-selection logic: detect a connected board via `pyserial.tools.list_ports`.

---

## Phase E — Persistent State
**Priority: fifth. Only if A–C (and ideally D) are done with time remaining.**
- **CREATE** `ps3_agent/db/models.py` — SQLite + SQLAlchemy models.
- **MODIFY** `ps3_agent/api/server.py` — swap `active_runs` dict for DB-backed reads/writes.

---

## Phase F — RAG on Past Patches
**Priority: lowest. Only if everything above is done and rehearsed with days to spare.**
- `ps3_agent/memory/rag_engine.py` (NEW) — local vector store (ChromaDB/FAISS) of crash signature → successful patch.

---

## Ground Rules Summary

1. **Renode and Wokwi are required scope.** Physical hardware is purely optional.
2. Every phase must leave `main` in a demoable state at all times.
3. Preserve the `SimulatorAdapter` interface contract exactly across all phases.
4. Fallback order at runtime: Physical (if connected) → Renode → Wokwi → DeterministicSimulator. Each degrades gracefully.
5. If forced to cut under time pressure: **Phase F → Phase E → Phase D**. Do not cut B or C.
