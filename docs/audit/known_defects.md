# Known Defects

- **LabWiredAdapter_Mock**: The identifier `LabWiredAdapter_Mock` was referenced in `src/firmware_agent/cli.py` on line 40 inside the `test` command. The class did not exist, causing a `NameError` whenever `firmware-agent test` was invoked.
- **Reproduction**: `python -m firmware_agent.cli test firmware/demos`
- **Resolution**: This reference has been removed from `cli.py` in accordance with Rule 1.3 (Mock isolation rule). The CLI now uses `LabWiredAdapter` directly.
