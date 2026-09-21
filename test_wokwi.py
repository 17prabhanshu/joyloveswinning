from ps3_agent.execution.wokwi_adapter import WokwiAdapter
from ps3_agent.schemas import TestScenario
import tempfile
import os

scenario = TestScenario(
    test_id="TEST-123",
    target="test",
    category="BOUNDARY",
    reason="test",
    expected_outcome="test",
    steps=[{"action": "set_sensor", "sensor": "temperature", "value": 81}],
    why_this_test_exists="test",
    information_value="test",
    priority=0.5
)

adapter = WokwiAdapter()
c_file_path = "fixtures/firmware/fan_controller.c"
prepared = adapter.prepare(c_file_path, scenario, "/tmp")
result = adapter.execute(prepared)
print("Exit Status:", result.exit_status)
print("Error:", result.error)
print("UART:", result.uart)
