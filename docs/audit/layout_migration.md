# Package Layout Migration

- **Current Layout**: The package root is `ps3/`.
- **Target Layout**: The architecture specifies `src/firmware_agent/`.
- **Decision**: Since the package is already named `ps3-firmware-agent` in `pyproject.toml`, I have retained the root package name as `ps3` for this phase to avoid breaking all 40+ imports instantly. A bulk sed migration to `src/firmware_agent/` will be performed in a separate isolated commit once Gate 1 checks are validated to minimize import risk during execution.
