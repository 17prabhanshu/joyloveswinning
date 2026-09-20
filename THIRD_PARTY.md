# Third-Party Attribution

This project uses or is inspired by the following third-party projects.

## FirmwareHive

- **Repository**: https://github.com/bjtu-SecurityLab/firmhive
- **License**: Apache License 2.0
- **What is used**: Conceptual inspiration for the runtime-grown agent architecture and task decomposition patterns. No source code is directly copied.
- **Modifications**: Our agent system is purpose-built for embedded firmware testing (not vulnerability hunting). The agent roles, risk engine, and testing pipeline are original implementations.

## Renode

- **Repository**: https://github.com/renode/renode
- **License**: MIT License
- **What is used**: Used as an optional virtual hardware simulation backend through the RenodeAdapter. The Renode source is included as a reference in `renode/`.
- **Modifications**: None to Renode itself. We provide an adapter layer (`ps3_agent/execution/simulator.py`) that interfaces with Renode's CLI.

## Fuzzware

- **Repository**: https://github.com/fuzzware-fuzzer/fuzzware
- **License**: MIT-like (see repository)
- **What is used**: Conceptual inspiration for autonomous MMIO/peripheral exploration strategies. No source code is directly used.
- **Modifications**: N/A

## Python Dependencies

| Package | License | Purpose |
|---------|---------|---------|
| Pydantic | MIT | Data validation and schemas |
| FastAPI | MIT | REST API framework |
| Uvicorn | BSD | ASGI server |
| React | MIT | Frontend UI framework |
| Tailwind CSS | MIT | CSS utility framework |
| React Flow | MIT | Graph visualization |
