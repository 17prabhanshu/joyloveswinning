from typing import Any, List
import datetime
from .models import TestSuite, TestScenario, Category
from .boundary import BoundaryTestGenerator
from .fault import FaultInjectionGenerator
from .state import StateTransitionGenerator
from .z3_gen import Z3BoundaryGenerator

class TestGenerator:
    def __init__(self, firmware_model: Any, behavior_graph: Any):
        self.firmware_model = firmware_model
        self.behavior_graph = behavior_graph
        self.boundary_gen = BoundaryTestGenerator(behavior_graph)
        self.fault_gen = FaultInjectionGenerator(behavior_graph)
        self.state_gen = StateTransitionGenerator(behavior_graph)
        self.z3_gen = Z3BoundaryGenerator(behavior_graph)

    def generate_all(self, firmware_path: str = "unknown") -> TestSuite:
        all_scenarios: List[TestScenario] = []
        
        # Call sub-generators
        all_scenarios.extend(self.boundary_gen.generate())
        all_scenarios.extend(self.fault_gen.generate())
        all_scenarios.extend(self.state_gen.generate())
        all_scenarios.extend(self.z3_gen.generate())

        # Deduplicate tests
        unique_scenarios = self._deduplicate(all_scenarios)
        
        # Prioritize tests
        sorted_scenarios = self._prioritize(unique_scenarios)

        # Assign final test IDs to ensure uniqueness after deduplication
        for i, scenario in enumerate(sorted_scenarios, 1):
            scenario.test_id = f"TS_{i:04d}"

        return TestSuite(
            scenarios=sorted_scenarios,
            firmware_path=firmware_path,
            generated_at=datetime.datetime.now().isoformat(),
            generator="MainTestGenerator"
        )

    def _deduplicate(self, scenarios: List[TestScenario]) -> List[TestScenario]:
        seen = set()
        unique = []
        for s in scenarios:
            # Create a simple hashable signature based on category, inputs and description
            inputs_sig = tuple((i.name, str(i.value)) for i in s.inputs)
            sig = (s.category, s.description, inputs_sig)
            if sig not in seen:
                seen.add(sig)
                unique.append(s)
        return unique

    def _prioritize(self, scenarios: List[TestScenario]) -> List[TestScenario]:
        def get_priority_score(scenario: TestScenario) -> int:
            cat_score = {
                Category.BOUNDARY: 40,
                Category.FAULT_INJECTION: 30,
                Category.STATE_TRANSITION: 20,
                Category.NORMAL: 10
            }
            return cat_score.get(scenario.category, 0) + scenario.priority
            
        return sorted(scenarios, key=get_priority_score, reverse=True)
