from typing import List, Any
from .models import TestScenario, Category, TestInput

class StateTransitionGenerator:
    def __init__(self, behavior_graph: Any):
        self.behavior_graph = behavior_graph

    def generate(self) -> List[TestScenario]:
        scenarios = []
        test_id_counter = 1

        def create_scenario(states: List[str], desc: str) -> TestScenario:
            nonlocal test_id_counter
            scenario = TestScenario(
                test_id=f"STT_{test_id_counter:03d}",
                category=Category.STATE_TRANSITION,
                target_function="state_machine",
                description=desc,
                inputs=[TestInput(name="transition_sequence", value=states, type="sequence")],
                expected_outputs=[{"type": "uart", "target": "console", "value": "STATE", "condition": "contains"}],
                reason="State transition verification",
                priority=6
            )
            test_id_counter += 1
            return scenario

        # Pairwise transitions
        scenarios.append(create_scenario(["OFF", "LOW"], "Transition OFF->LOW"))
        scenarios.append(create_scenario(["LOW", "HIGH"], "Transition LOW->HIGH"))
        scenarios.append(create_scenario(["HIGH", "LOW"], "Transition HIGH->LOW"))
        scenarios.append(create_scenario(["HIGH", "OFF"], "Transition HIGH->OFF"))

        # Rapid transitions
        scenarios.append(create_scenario(["HIGH", "LOW", "HIGH"], "Rapid transition HIGH->LOW->HIGH"))

        return scenarios
