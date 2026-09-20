# Repository Inventory

## Tree (Depth 3)
```
.
├── README.md
├── UPSTREAM.md
├── artifacts
│   ├── raw
│   ├── regression
│   ├── reports
│   ├── results
│   └── traces
├── demo_artifacts
│   ├── report.html
│   └── report.json
├── docs
│   ├── ARCHITECTURE_AUDIT.md
│   └── audit
├── firmware
│   ├── demos
│   ├── examples
│   └── fixtures
├── logs
├── ps3
│   ├── __init__.py
│   ├── agent
│   ├── analyzer
│   ├── cli.py
│   ├── coverage
│   ├── diagnosis
│   ├── execution
│   ├── generators
│   ├── observation
│   ├── planner
│   ├── regression
│   ├── reporting
│   ├── simulator
│   ├── test_analyzer.py
│   └── verification
├── pyproject.toml
├── pytest.ini
├── schemas
│   └── trace.v1.json
├── scripts
│   └── verify_no_fakes.py
└── tests
    ├── integration
    ├── ps3
    ├── regression
    └── unit
```

## File Counts by Extension
- `py`: 36
- `txt`: 5
- `json`: 3
- `md`: 3
- `toml`: 1
- `html`: 1
- `c`: 1
- `ini`: 1

## Largest Source Files
1. `ps3/analyzer/parser.py`: 433 lines
2. `ps3/verification/verifier.py`: 378 lines
3. `ps3/simulator/labwired.py`: 326 lines

## Modules
- `ps3.analyzer`: Statically parses C source code into behavior graphs.
- `ps3.generators`: Deterministically proposes boundary/fault test scenarios.
- `ps3.simulator`: Orchestrates LabWired CLI execution and collects artifacts.
- `ps3.verification`: Strictly evaluates simulation results against expectations.
- `ps3.diagnosis`: Traces verification failures back to source code locations.
- `ps3.reporting`: Generates HTML/JSON telemetry and UI.
- `ps3.agent`: Coordinates the analysis, generation, execution, and diagnosis loop.
- `ps3.coverage`: Tracks functional and edge-case execution logic.
- `ps3.regression`: Saves scenarios that fail for minimization and replay.

## Confirm or Deny
- **Test suite**: CONFIRMED (`tests/` exists, running `pytest`).
- **CI configuration**: DENIED (No GitHub Actions, GitLab CI, or Travis configs present).
- **Agent loop module**: CONFIRMED (`ps3/agent/loop.py`).
- **Dockerfile**: DENIED (No `Dockerfile` exists).
- **Environment configuration mechanism**: DENIED (No `.env` handling, purely CLI args).
