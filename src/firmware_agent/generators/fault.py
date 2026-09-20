from typing import List, Any
from .models import TestScenario, Category, TestInput

class FaultInjectionGenerator:
    def __init__(self, behavior_graph: Any = None):
        self.behavior_graph = behavior_graph

    def generate(self) -> List[TestScenario]:
        scenarios = []
        test_id_counter = 1

        def create_scenario(name: str, val: Any, desc: str) -> TestScenario:
            nonlocal test_id_counter
            scenario = TestScenario(
                test_id=f"FLT_{test_id_counter:03d}",
                category=Category.FAULT_INJECTION,
                target_function="system",
                description=desc,
                inputs=[TestInput(name=name, value=val)],
                expected_outputs=[{"type": "uart", "target": "console", "value": "ERROR", "condition": "contains"}],
                reason="Fault injection",
                priority=8
            )
            test_id_counter += 1
            return scenario

        # Sensor disconnect scenarios
        scenarios.append(create_scenario("sensor_status", "DISCONNECTED", "Sensor disconnect scenario"))

        # Invalid value scenarios
        scenarios.append(create_scenario("sensor_value", float('nan'), "NaN value scenario"))
        scenarios.append(create_scenario("sensor_value", -9999.9, "Negative invalid value scenario"))
        scenarios.append(create_scenario("sensor_value", float('inf'), "Overflow/large value scenario"))

        # Timeout scenarios
        scenarios.append(create_scenario("comm_timeout", True, "Communication timeout scenario"))

        # Communication failure scenarios
        scenarios.append(create_scenario("comm_status", "FAILURE", "Communication failure scenario"))

        return scenarios
