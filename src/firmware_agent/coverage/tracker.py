"""
Coverage tracking.

Tracks which functions, conditions, and boundary values have been tested.
"""
import logging
from typing import List, Set
from pydantic import BaseModel

from firmware_agent.verification.verifier import VerificationResult
from firmware_agent.analyzer.models import FirmwareModel
from firmware_agent.generators.models import TestScenario

logger = logging.getLogger(__name__)


class CoverageSummary(BaseModel):
    functions_total: int
    functions_covered: int
    conditions_total: int
    conditions_covered: int
    boundaries_total: int
    boundaries_covered: int
    transitions_total: int
    transitions_covered: int


class CoverageTracker:
    """Tracks structural and behavioral coverage of tests."""
    
    def __init__(self):
        self.covered_functions: Set[str] = set()
        self.covered_conditions: Set[str] = set()
        self.covered_boundaries: Set[str] = set()
        self.covered_transitions: Set[str] = set()
        
        self.total_functions = 0
        self.total_conditions = 0
        self.total_boundaries = 0
        self.total_transitions = 0
        
        self.model = None
        self.graph = None

    def initialize(self, firmware_model: FirmwareModel, behavior_graph=None) -> None:
        """Initialize the coverage goals from the firmware model."""
        self.model = firmware_model
        self.graph = behavior_graph
        
        if firmware_model:
            self.total_functions = len(firmware_model.functions)
            self.total_conditions = sum(len(f.conditions) for f in firmware_model.functions)
            
        if behavior_graph:
            self.total_boundaries = len(behavior_graph.boundary_conditions) * 3 # min, exact, max
            self.total_transitions = len(behavior_graph.state_transitions)

    def update(self, scenario: TestScenario, verification_result: VerificationResult) -> None:
        """Update coverage based on an executed test scenario."""
        if not verification_result.passed:
            return # Optionally only count passed tests for coverage
            
        # Target function coverage
        if scenario.target_function:
            self.covered_functions.add(scenario.target_function)
            
        # Category-based coverage
        cat = scenario.category
        if cat == "BOUNDARY":
            self.covered_boundaries.add(scenario.test_id)
        elif cat == "STATE_TRANSITION":
            self.covered_transitions.add(scenario.test_id)
            
        # Very rough condition mapping
        if self.model and scenario.target_function:
            for func in self.model.functions:
                if func.name == scenario.target_function:
                    for cond in func.conditions:
                        # Assuming the test hit at least one condition in the target function
                        self.covered_conditions.add(cond)

    def get_uncovered_functions(self) -> List[str]:
        if not self.model: return []
        all_funcs = {f.name for f in self.model.functions}
        return list(all_funcs - self.covered_functions)

    def get_coverage_percentage(self) -> float:
        if self.total_functions == 0:
            return 0.0
        # Simple weighted average
        func_cov = len(self.covered_functions) / self.total_functions
        cond_cov = len(self.covered_conditions) / max(1, self.total_conditions)
        return ((func_cov * 0.7) + (cond_cov * 0.3)) * 100.0

    def get_summary(self) -> CoverageSummary:
        return CoverageSummary(
            functions_total=self.total_functions,
            functions_covered=len(self.covered_functions),
            conditions_total=self.total_conditions,
            conditions_covered=len(self.covered_conditions),
            boundaries_total=self.total_boundaries,
            boundaries_covered=len(self.covered_boundaries),
            transitions_total=self.total_transitions,
            transitions_covered=len(self.covered_transitions)
        )
