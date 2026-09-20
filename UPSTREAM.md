# Upstream Attribution

## Source Project
- **Project**: LabWired Core
- **Repository**: https://github.com/w1ne/labwired-core
- **Revision**: 11dc7896 (main branch)
- **License**: MIT
- **Copyright**: Copyright (C) 2026 Andrii Shylenko

## What We Use
This project uses the LabWired Core simulator as the firmware execution backend.
The LabWired CLI binary (`labwired`) executes real firmware ELF images against
modeled silicon (CPU, buses, peripherals, sensors, displays) and provides
deterministic UART/GPIO/register/state observation.

We invoke LabWired via:
1. **CLI** (`labwired test --script ...`) for test execution
2. **Python SDK** (`labwired.Sim`) for programmatic simulation control

## PS3 Modifications
Our PS3 (Black Box Hackathon Problem Statement 3) layer is **additive**:
- Firmware static analysis and behavior graph extraction
- AI-powered autonomous test planning
- Automated test scenario generation (boundary, fault, state, timing)
- Deterministic verification engine above LabWired results
- Failure diagnosis and root-cause localization
- Automatic regression test generation
- Coverage-guided adaptive testing loop
- Z3-based constraint solving for boundary values
- HTML/JSON reporting

None of these modifications alter the LabWired Core simulator engine.
