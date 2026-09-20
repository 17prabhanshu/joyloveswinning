import re

with open("ps3_agent/execution/simulator.py", "r") as f:
    code = f.read()

# Replace WokwiAdapter stub with real import
old_wokwi = """class WokwiAdapter(SimulatorAdapter):
    def name(self) -> str:
        return "Wokwi"
    def health_check(self) -> bool:
        return True
    async def execute(self, firmware_path: str, scenario: TestScenario) -> ExecutionResult:
        return ExecutionResult(
            run_id="0", simulator="Wokwi", simulator_version="0.0.0",
            firmware_hash="unknown", scenario_hash="unknown", started_at="",
            duration_ms=0, exit_status="unsupported", uart=[],
            gpio={}, sensors={}, registers={}, artifacts=[],
            error=None
        )"""

if old_wokwi in code:
    code = code.replace(old_wokwi, "")
    code = "from ps3_agent.execution.wokwi_adapter import WokwiAdapter\n" + code

with open("ps3_agent/execution/simulator.py", "w") as f:
    f.write(code)

