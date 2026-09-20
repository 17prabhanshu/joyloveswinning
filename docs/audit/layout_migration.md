# Package Layout Migration

- **Previous Layout**: The package root was `ps3/`.
- **Current Layout**: The package root is `src/firmware_agent/`.
- **Migration**: All imports were migrated from `ps3.*` to `firmware_agent.*` via a bulk `sed` replacement across all Python source files. The `pyproject.toml` `[tool.setuptools.packages.find]` `where` directive was updated from `["."]` to `["src"]`.
- **Verification**: `pytest -v` passes 9/9 tests post-migration. No residual `from ps3.` or `import ps3.` references exist in the `src/` tree (confirmed via `grep -r "from ps3\.\|import ps3\." src/` returning empty).
