"""
Adaptive Planner — Core autonomy module that decides what to do next.
"""
from __future__ import annotations

from typing import Optional

from ps3_agent.schemas import AgentDecision, AgentMemory, RiskFinding, VerificationResult

def select_next_test(memory: AgentMemory, risks: list[RiskFinding], previous_result: Optional[VerificationResult] = None) -> AgentDecision:
    reasons: list[str] = []
    target = "Highest priority unexplored risk"
    expected_info: list[str] = []
    
    if previous_result and previous_result.status.value == "FAIL":
        reasons.append(f"Previous test {previous_result.test_id} failed.")
        reasons.append("Need to probe related behavior to map fault boundary.")
        target = f"Follow-up exploration around {previous_result.test_id}"
        expected_info.append("Determine if failure extends to adjacent states.")
        expected_info.append("Check if failure occurs with different parameters.")
    else:
        if previous_result:
            reasons.append(f"Previous test {previous_result.test_id} passed.")
        reasons.append("Moving to next highest-priority unexplored area.")
        expected_info.append("Establish baseline behavior for unexplored risk.")
        
    return AgentDecision(
        decision="EXECUTE_NEXT_CANDIDATE",
        target=target,
        reason=reasons,
        expected_information=expected_info,
        previous_result=previous_result.test_id if previous_result else None
    )
