# Autonomous Firmware Red-Team Agent

An autonomous firmware red-team agent that actively searches for unexpected embedded behavior in virtual hardware.

> **We don't just generate tests. We decide what is worth testing next.**

## Problem

Embedded firmware is difficult to test because behavior depends on code, hardware, state, timing, and unexpected inputs. Traditional testing requires engineers to manually write test cases, set up hardware, and investigate failures.

## Solution

Our agent autonomously explores firmware behavior in virtual hardware using a closed-loop architecture:

```
Analyze → Model → Hunt → Plan → Execute → Verify → Diagnose → Learn → Repeat
```

The most important architectural principle:

> **AI proposes. Tools execute. Deterministic verification decides. Evidence supports every conclusion.**

The LLM/agent is **never** the final authority for PASS/FAIL.

## Architecture

```
┌─────────────────┐
│   FIRMWARE C     │
└────────┬────────┘
         ▼
┌─────────────────┐     ┌─────────────────┐
│  CODE READER    │────▶│  BEHAVIOR GRAPH  │
│  (AST Parser)   │     │  (States, I/O)   │
└────────┬────────┘     └────────┬────────┘
         ▼                       ▼
┌─────────────────────────────────────────┐
│            RISK ENGINE                   │
│  Boundary · Assumption · State · Fault  │
│  Timing · Combination · Counterexample  │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────┐     ┌─────────────────┐
│ ADAPTIVE PLANNER│────▶│ SCENARIO ENGINE  │
│ "What next?"    │     │ Test generation  │
└────────┬────────┘     └────────┬────────┘
         ▼                       ▼
┌─────────────────────────────────────────┐
│         SIMULATOR ADAPTER                │
│  ┌──────────┐    ┌──────────┐           │
│  │Determin. │    │  Renode  │           │
│  │Simulator │    │ Backend  │           │
│  └──────────┘    └──────────┘           │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────┐
│   VERIFIER      │──── PASS / FAIL / ERROR
│ (Deterministic) │
└────────┬────────┘
         ▼ (on FAIL)
┌─────────────────┐     ┌─────────────────┐
│  DIAGNOSER      │────▶│   MINIMIZER     │
│  Root cause     │     │  Delta-debug    │
└────────┬────────┘     └────────┬────────┘
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│  REGRESSION     │     │ ADAPTIVE NEXT   │
│  Memory         │     │ "What now?"     │
└─────────────────┘     └────────┬────────┘
                                 │
                                 └──▶ LOOP
```

## Quick Start

```bash
# Install
pip install -e .

# Check system health
ps3-agent doctor

# Run the demo (buggy fan controller firmware)
ps3-agent demo

# Start the web UI
ps3-agent ui
# Then open http://localhost:8080

# Analyze firmware without running tests
ps3-agent analyze path/to/firmware.c
```

## Demo

The demo uses a temperature-controlled fan firmware (`fixtures/firmware/fan_controller.c`) with 5 intentional defects:

1. **Boundary Off-by-One**: `if (temperature > 80)` should be `>=`
2. **Missing Sensor Guard**: Disconnected sensor returns -999, treated as cold
3. **No Range Validation**: Out-of-range values (5000°C) accepted
4. **No Debounce**: Rapid fan state changes cause back-EMF
5. **Unsafe Recovery**: First reading after reconnect is blindly trusted

The agent discovers these autonomously through systematic risk hunting and adaptive test selection.

## Key Features

- **Boundary Hunter**: Finds threshold conditions and tests exact boundaries
- **Assumption Hunter**: Discovers implicit assumptions (sensor always valid, etc.)
- **State Hunter**: Tests state sequences and transition edge cases
- **Fault Injector**: Sensor disconnect, invalid values, out-of-range
- **Adaptive Planner**: Uses previous results to select the next test
- **Deterministic Verifier**: Hardware evidence decides PASS/FAIL, never the LLM
- **Failure Diagnosis**: Maps failures to source code lines
- **Delta-Debugging Minimizer**: Reduces failing scenarios to minimal reproducers
- **Regression Memory**: Automatically creates regression tests from failures

## Third-Party Attribution

See [THIRD_PARTY.md](THIRD_PARTY.md) for full attribution.

- **FirmwareHive** (Apache 2.0) — Conceptual inspiration for agent architecture
- **Renode** (MIT) — Virtual hardware simulation backend
- **Fuzzware** — Conceptual inspiration for MMIO exploration

## License

Apache 2.0
