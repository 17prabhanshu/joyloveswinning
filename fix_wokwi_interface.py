with open("ps3_agent/execution/wokwi_adapter.py", "r") as f:
    code = f.read()

import re

# Add prepare and cleanup
prepare_cleanup = """
    def prepare(self, firmware_path: str, scenario: TestScenario, work_dir: str) -> dict:
        import hashlib
        from pathlib import Path
        return {
            "firmware_path": firmware_path,
            "scenario": scenario,
            "work_dir": work_dir,
            "firmware_hash": hashlib.sha256(Path(firmware_path).read_bytes()).hexdigest()[:16] if Path(firmware_path).exists() else "unknown",
            "c_code": Path(firmware_path).read_text() if Path(firmware_path).exists() else ""
        }

    def cleanup(self, work_dir: str) -> None:
        pass
"""

# Fix execute signature
code = code.replace(
    'def execute(self, firmware_hash: str, scenario: TestScenario, c_code: str) -> ExecutionResult:',
    'def execute(self, prepared: dict, timeout_ms: int = 5000) -> ExecutionResult:\n        firmware_hash = prepared.get("firmware_hash", "unknown")\n        scenario = prepared["scenario"]\n        c_code = prepared.get("c_code", "")'
)

# Insert prepare and cleanup before execute
code = code.replace('    def execute(', prepare_cleanup + '\n    def execute(')

with open("ps3_agent/execution/wokwi_adapter.py", "w") as f:
    f.write(code)
