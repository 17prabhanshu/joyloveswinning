"""
Regression Memory — Tracks knowledge across tests and delta-debugs failures.
"""
from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from ps3_agent.schemas import (
    AgentMemory,
    DiagnosisResult,
    MinimizedFailure,
    RegressionTest,
    TestScenario,
    VerificationResult,
)


class RegressionMemory:
    def __init__(self):
        self.regressions: list[RegressionTest] = []
        self.agent_memory = AgentMemory(
            discovered_risks=[],
            explored_states=[],
            covered_branches=[],
            failures=[],
            regressions=[],
            simulator_disagreements=[],
            assumptions=[],
            previous_results=[],
            useful_patterns=[]
        )

    def record_result(self, test_id: str, scenario: TestScenario, verification: VerificationResult, execution_result: Any):
        if verification.status.value == "FAIL":
            if test_id not in self.agent_memory.failures:
                self.agent_memory.failures.append(test_id)
                
        self.agent_memory.previous_results.append({
            "test_id": test_id,
            "status": verification.status.value
        })

    def minimize_failure(self, scenario: TestScenario, execute_fn: Callable[[TestScenario], VerificationResult]) -> MinimizedFailure:
        """Delta-debugging algorithm to find the minimal steps to reproduce a failure."""
        original_steps = len(scenario.steps)
        current_scenario = copy.deepcopy(scenario)
        minimization_log = ["Starting delta-debugging..."]
        
        # Don't minimize if there's only 1 step
        if original_steps <= 1:
            return MinimizedFailure(
                original_steps=original_steps,
                minimized_steps=original_steps,
                original_scenario=scenario,
                minimized_scenario=current_scenario,
                minimization_log=["Scenario too small to minimize."]
            )
            
        i = 0
        while i < len(current_scenario.steps):
            test_scenario = copy.deepcopy(current_scenario)
            removed = test_scenario.steps.pop(i)
            action = removed.get("action", "unknown")
            
            # Re-execute after removal
            result = execute_fn(test_scenario)
            
            if result.status.value == "FAIL":
                # If it still fails, the step is unnecessary. Keep it removed.
                current_scenario = test_scenario
                minimization_log.append(f"Removed unnecessary step: {action}")
            else:
                # If it passes, the step is required to trigger the failure. Restore it.
                minimization_log.append(f"Kept required step: {action}")
                i += 1
                
        return MinimizedFailure(
            original_steps=original_steps,
            minimized_steps=len(current_scenario.steps),
            original_scenario=scenario,
            minimized_scenario=current_scenario,
            minimization_log=minimization_log
        )

    def create_regression(self, scenario: TestScenario, verification: VerificationResult, diagnosis: DiagnosisResult, firmware_hash: str, simulator: str) -> RegressionTest:
        reg_id = f"REG-{uuid.uuid4().hex[:6].upper()}"
        
        observed_failure = "Unknown"
        if verification.assertions:
            for a in verification.assertions:
                if a.verdict.value == "FAIL":
                    observed_failure = f"{a.type}: {a.evidence}"
                    break
        
        test = RegressionTest(
            regression_id=reg_id,
            firmware_hash=firmware_hash,
            scenario=scenario,
            expected_behavior=scenario.expected_outcome,
            observed_failure=observed_failure,
            source_location=diagnosis.source_location,
            created_at=datetime.now(timezone.utc).isoformat(),
            simulator=simulator,
            minimized_reproducer=None,
            confirmed=True
        )
        self.regressions.append(test)
        self.agent_memory.regressions.append(reg_id)
        return test

    def get_memory(self) -> AgentMemory:
        return self.agent_memory
