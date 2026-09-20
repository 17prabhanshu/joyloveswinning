# Phase 2: Enterprise Architecture Implementation Plan

This document outlines the exact technical roadmap to transition the JOY framework from a hackathon prototype into a production-grade, model-agnostic, Hardware-in-the-Loop (HIL) security testing platform.

---

## 1. The Model-Agnostic LLM Gateway
**Goal:** Eliminate dependency on a single AI provider, prevent rate-limiting, and introduce zero-cost semantic caching.

### New Architecture
We will replace direct `httpx` calls with a unified `LLMGateway` class utilizing `litellm` (or a custom OpenAI-compatible router).

### Files to Modify / Create
- **CREATE** `ps3_agent/api/llm_gateway.py`
  - Defines `LLMGateway` class.
  - Implements `hash(prompt)` for SQLite caching.
  - Implements a Round-Robin API key queue.
- **MODIFY** `ps3_agent/api/server.py`
  - Remove all hardcoded `gemini-3.6-flash` calls.
  - Import and instantiate `LLMGateway`.
- **MODIFY** `requirements.txt` / `pyproject.toml`
  - Add `litellm` (for universal LLM routing).
  - Add `diskcache` (for lightning-fast prompt caching).

### Execution Flow
1. Agent requests a payload generation.
2. `LLMGateway` checks the local cache. If a hit, return instantly (0ms).
3. If a miss, Gateway tries Provider A (e.g., Groq Llama 3.1 70B).
4. If Provider A hits a 429/503, Gateway intercepts and silently reroutes to Provider B (Gemini).
5. If Provider B fails, Gateway reroutes to Local Ollama.
6. Response is cached and returned to the agent.

---

## 2. True Hardware-in-the-Loop (HIL) Execution
**Goal:** Move away from the Python `DeterministicSimulator` and execute actual cross-compiled binaries on physical boards (ESP32/Arduino) and real virtual emulators (Renode/Wokwi).

### New Architecture
Introduce a dynamic compilation pipeline and physical serial adapters.

### Files to Modify / Create
- **CREATE** `ps3_agent/execution/compiler.py`
  - Wraps the `platformio` CLI.
  - Automatically generates `platformio.ini` based on the target board.
  - Compiles `fan_controller.c` into `firmware.bin` or `firmware.elf`.
- **CREATE** `ps3_agent/execution/physical_adapter.py`
  - Uses `esptool.py` to flash the `.bin` to a connected USB board.
  - Uses `pyserial` to open the COM port, inject inputs, and read UART crash logs.
- **MODIFY** `ps3_agent/execution/simulator.py`
  - Update `RenodeAdapter` and `WokwiAdapter` to execute the actual compiled `.elf` files via background subprocesses, rather than returning "unsupported".
  
### Execution Flow
1. LLM synthesizes a new test scenario.
2. `compiler.py` compiles the C code into binary.
3. The orchestrator checks if a physical board is connected via USB.
4. **If Yes:** `physical_adapter.py` flashes the board and monitors the Serial output.
5. **If No:** `RenodeAdapter` boots a virtual Cortex-M4, loads the `.elf`, and reads virtual registers.
6. Execution results are parsed and fed back to the LLM for diagnosis.

---

## 3. Persistent State & RAG (Retrieval-Augmented Generation)
**Goal:** Prevent data loss on server restarts and allow the AI to learn from its past successful patches.

### New Architecture
Replace in-memory Python dictionaries (`active_runs`) with an SQLite database and a vector-based knowledge graph.

### Files to Modify / Create
- **CREATE** `ps3_agent/db/models.py`
  - SQLAlchemy ORM models for `Run`, `Event`, `Risk`, and `Patch`.
- **CREATE** `ps3_agent/memory/rag_engine.py`
  - Uses a lightweight local vector store (e.g., `ChromaDB` or `FAISS`) to store successful patches.
- **MODIFY** `ps3_agent/api/server.py`
  - Mount the database connection on startup.
  - Refactor all `/api/runs` endpoints to query SQLite instead of RAM.

### Execution Flow
1. Agent detects a Boundary Off-by-One crash.
2. Agent queries `rag_engine.py`: *"Have I seen this crash signature before?"*
3. RAG engine retrieves a previously successful patch from the database.
4. Agent uses the historical patch as context to generate a highly accurate fix on the first try.
5. All telemetry is written to SQLite for persistent dashboard viewing.

---

## 4. Implementation Phasing

**Phase 2.1: Robustness (Week 1)**
- Implement `LLMGateway`.
- Integrate caching and Open-Source model fallbacks (Groq/Llama3).
- Migrate from in-memory state to SQLite.

**Phase 2.2: Execution Reality (Week 2)**
- Implement `compiler.py` (PlatformIO integration).
- Build the `physical_adapter.py` (PySerial/USB).
- Connect Wokwi CLI for headless virtual execution.

**Phase 2.3: Intelligence (Week 3)**
- Implement `rag_engine.py`.
- Embed historical test results.
- Refine the LLM prompts to utilize the RAG context.
