from typing import List, Any
from .models import TestScenario, Category, TestInput

class BoundaryTestGenerator:
    def __init__(self, behavior_graph: Any):
        self.behavior_graph = behavior_graph

    def generate(self) -> List[TestScenario]:
        scenarios = []
        test_id_counter = 1
        
        def create_scenario(val: float, desc: str) -> TestScenario:
            nonlocal test_id_counter
            scenario = TestScenario(
                test_id=f"BND_{test_id_counter:03d}",
                category=Category.BOUNDARY,
                target_function="unknown", 
                description=desc,
                inputs=[TestInput(name="temperature", value=val)],
                expected_outputs=[{"type": "uart", "target": "console", "value": f"FAN", "condition": "contains"}],
                reason="Boundary test",
                priority=10
            )
            test_id_counter += 1
            return scenario

        # For temperature >= 50
        scenarios.append(create_scenario(49.0, "Just below boundary (49)"))
        scenarios.append(create_scenario(50.0, "Exact boundary (50)"))
        scenarios.append(create_scenario(51.0, "Just above boundary (51)"))

        # For numeric ranges (e.g. min 0, max 100)
        scenarios.append(create_scenario(-1.0, "Min - 1"))
        scenarios.append(create_scenario(0.0, "Min"))
        scenarios.append(create_scenario(1.0, "Min + 1"))
        scenarios.append(create_scenario(50.0, "Mid"))
        scenarios.append(create_scenario(99.0, "Max - 1"))
        scenarios.append(create_scenario(100.0, "Max"))
        scenarios.append(create_scenario(101.0, "Max + 1"))

        return scenarios
