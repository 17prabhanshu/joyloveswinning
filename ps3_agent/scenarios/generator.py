"""
Scenario Generator — Generates targeted test scenarios based on risk findings.
"""
from __future__ import annotations

import re
import uuid
from typing import Any

from ps3_agent.schemas import (
    AgentMemory,
    FirmwareUnderstanding,
    RiskFinding,
    TestCandidate,
    TestScenario,
)

def _test_id() -> str:
    return f"TEST-{uuid.uuid4().hex[:6].upper()}"

def generate_scenarios(risks: list[RiskFinding], understanding: FirmwareUnderstanding, memory: AgentMemory) -> list[TestScenario]:
    scenarios: list[TestScenario] = []
    
    for i, risk in enumerate(risks):
        if risk.category.value == "BOUNDARY":
            # Extract numeric value from explanation or contributing_factors
            text_to_search = risk.explanation
            if not text_to_search and risk.contributing_factors:
                text_to_search = " ".join(risk.contributing_factors)
            
            val_match = re.search(r'\d+', text_to_search or "80")
            val = int(val_match.group()) if val_match else 80
            
            for test_val in [val - 1, val, val + 1]:
                scenario = TestScenario(
                    test_id=_test_id(),
                    target=risk.source_location or "Unknown",
                    category="BOUNDARY",
                    reason=f"Boundary test around {test_val}",
                    expected_outcome="System handles boundary correctly without faulting.",
                    steps=[
                        {"action": "set_sensor", "sensor": "temperature", "value": test_val},
                        {"action": "tick"},
                        {"action": "assert_gpio", "pin": "FAN_PIN_HIGH", "expected": test_val >= 80}
                    ],
                    priority=0.9 if risk.severity.value == "HIGH" else 0.5,
                    why_this_test_exists=f"Risk {risk.risk_id} indicates potential boundary failure at {val}. Testing exactly at {test_val}.",
                    information_value=f"Confirms if off-by-one error exists at {test_val}."
                )
                scenarios.append(scenario)
                
        elif risk.category.value == "ASSUMPTION":
            scenario = TestScenario(
                test_id=_test_id(),
                target=risk.source_location or "Unknown",
                category="ASSUMPTION",
                reason="Assumption violation",
                expected_outcome="System enters safe state or logs error.",
                steps=[
                    {"action": "disconnect_sensor", "sensor": "temperature"},
                    {"action": "tick"},
                    {"action": "assert_gpio", "pin": "FAN_PIN_HIGH", "expected": True}
                ],
                priority=0.8,
                why_this_test_exists=f"Testing assumption violation for risk {risk.risk_id}. Disconnecting sensor.",
                information_value="Validates fail-safe behavior when input assumption is broken."
            )
            scenarios.append(scenario)
            
            # Adding one for extreme value
            scenario2 = TestScenario(
                test_id=_test_id(),
                target=risk.source_location or "Unknown",
                category="ASSUMPTION",
                reason="Invalid sensor value",
                expected_outcome="System handles out of bounds value safely.",
                steps=[
                    {"action": "set_invalid_sensor", "sensor": "temperature", "value": 5000},
                    {"action": "tick"}
                ],
                priority=0.7,
                why_this_test_exists=f"Testing assumption violation for risk {risk.risk_id}. Injecting out of range data.",
                information_value="Validates range checks."
            )
            scenarios.append(scenario2)
            
        elif risk.category.value == "STATE":
            scenario = TestScenario(
                test_id=_test_id(),
                target=risk.source_location or "Unknown",
                category="STATE",
                reason="Multi-step state transition",
                expected_outcome="System recovers successfully without using stale data.",
                steps=[
                    {"action": "set_sensor", "sensor": "temperature", "value": 100},
                    {"action": "tick"}, # enters overheat
                    {"action": "disconnect_sensor", "sensor": "temperature"},
                    {"action": "tick"}, # enters sensor error
                    {"action": "reconnect_sensor", "sensor": "temperature", "value": 25},
                    {"action": "tick"}, # attempts recovery
                    {"action": "assert_gpio", "pin": "FAN_PIN_HIGH", "expected": False} # should evaluate as cold now
                ],
                priority=0.7,
                why_this_test_exists=f"Testing state sequence resilience for risk {risk.risk_id}.",
                information_value="Tests complex state transition and recovery path."
            )
            scenarios.append(scenario)
            
        elif risk.category.value == "FAULT":
            scenario = TestScenario(
                test_id=_test_id(),
                target=risk.source_location or "Unknown",
                category="FAULT",
                reason="Fault injection",
                expected_outcome="System detects fault and recovers or halts safely.",
                steps=[
                    {"action": "disconnect_sensor", "sensor": "temperature"},
                    {"action": "tick"},
                    {"action": "tick"},
                    {"action": "tick"},
                    {"action": "tick"} # should trigger emergency fan activation
                ],
                priority=0.8,
                why_this_test_exists=f"Testing fault resilience for risk {risk.risk_id}.",
                information_value="Tests persistent fault handling."
            )
            scenarios.append(scenario)
            
        elif risk.category.value == "TIMING":
            scenario = TestScenario(
                test_id=_test_id(),
                target=risk.source_location or "Unknown",
                category="TIMING",
                reason="Rapid timing sequence",
                expected_outcome="System manages rapid events without race condition.",
                steps=[
                    {"action": "set_sensor", "sensor": "temperature", "value": 100},
                    {"action": "tick"},
                    {"action": "set_sensor", "sensor": "temperature", "value": 20},
                    {"action": "tick"},
                    {"action": "set_sensor", "sensor": "temperature", "value": 100},
                    {"action": "tick"}
                ],
                priority=0.6,
                why_this_test_exists=f"Testing timing constraints for risk {risk.risk_id}.",
                information_value="Tests for back-EMF or debounce logic."
            )
            scenarios.append(scenario)
            
    return scenarios


def rank_candidates(scenarios: list[TestScenario], memory: AgentMemory) -> list[TestCandidate]:
    candidates: list[TestCandidate] = []
    
    past_scenario_hashes = set()
    # If memory tracked hashes, we'd use them. Simplified for now.
    
    for scenario in scenarios:
        risk_score = scenario.priority
        
        # Novelty is higher if the behavior hasn't been explored
        novelty_score = 1.0 
        
        redundancy_score = 0.0
        
        value_score = (risk_score * novelty_score) - redundancy_score
        
        candidates.append(TestCandidate(
            scenario=scenario,
            risk_score=risk_score,
            novelty_score=novelty_score,
            value_score=value_score,
            redundancy_score=redundancy_score,
            selected=False
        ))
        
    # Sort by value_score descending
    candidates.sort(key=lambda c: c.value_score, reverse=True)
    
    # Select top tests
    for c in candidates[:20]:
        c.selected = True
        
    return candidates
