"""
Diagnosis Engine — Investigates failures to find the root cause.
"""
from __future__ import annotations

from ps3_agent.schemas import (
    DiagnosisResult,
    ExecutionResult,
    FirmwareUnderstanding,
    TestScenario,
    VerificationResult,
)

def diagnose_failure(scenario: TestScenario, execution: ExecutionResult, verification: VerificationResult, understanding: FirmwareUnderstanding) -> DiagnosisResult:
    if verification.status.value != "FAIL":
        return DiagnosisResult(
            test_id=scenario.test_id,
            cause_hypothesis="No failure to diagnose",
            confidence=1.0,
            evidence=[],
            is_hypothesis=False
        )

    failed_assertion = None
    for assertion in verification.assertions:
        if assertion.verdict.value == "FAIL":
            failed_assertion = assertion
            break
            
    if not failed_assertion:
        return DiagnosisResult(
            test_id=scenario.test_id,
            cause_hypothesis="Unknown failure, no failed assertion found",
            confidence=0.0,
            evidence=[],
            is_hypothesis=True
        )

    signal = "unknown"
    if failed_assertion.type == "GPIO_STATE":
        # Hack to extract pin name from expected "True" / observed "False"
        # We need the step action to know which pin. We can find it in evidence_chain.
        for e in verification.evidence_chain:
            if not e.get("passed", True) and e.get("action") == "assert_gpio":
                # Find the step
                step_idx = e.get("step", 0)
                if step_idx < len(scenario.steps):
                    signal = scenario.steps[step_idx].get("pin", "unknown")
                break
    elif failed_assertion.type == "UART_OUTPUT":
        signal = "UART"
    elif failed_assertion.type == "SENSOR_RANGE":
        for e in verification.evidence_chain:
            if not e.get("passed", True) and e.get("action") == "assert_sensor":
                step_idx = e.get("step", 0)
                if step_idx < len(scenario.steps):
                    signal = scenario.steps[step_idx].get("sensor", "unknown")
                break

    # Search understanding.functions for functions that write to that signal
    function_name = None
    source_location = None
    relevant_condition = None
    
    for func in understanding.functions:
        if signal in func.hw_interactions or any(signal in hw for hw in func.hw_interactions):
            function_name = func.name
            source_location = f"{func.file}:{func.line}" if func.file else "Unknown"
            if func.conditions:
                relevant_condition = func.conditions[0] # Pick the first for simplicity
            break

    # If it's a boundary test, we can be highly confident about the condition
    confidence = 0.8
    if scenario.category == "BOUNDARY" and relevant_condition:
        confidence = 0.95

    cause_hypothesis = (
        f"Assertion failed for signal {signal}. "
        f"Expected: {failed_assertion.expected}, Observed: {failed_assertion.observed}. "
    )
    
    if function_name:
        cause_hypothesis += f"Likely caused by incorrect logic in {function_name}()."
        if relevant_condition:
            cause_hypothesis += f" Check condition: `{relevant_condition}`"
    
    evidence = [{"message": f"Failed check: {failed_assertion.evidence}"}]
    if source_location:
        evidence.append({"source": source_location})
    
    return DiagnosisResult(
        test_id=scenario.test_id,
        failed_assertion=f"{failed_assertion.type}: {failed_assertion.evidence}",
        hardware_signal=signal,
        function_name=function_name,
        source_location=source_location,
        relevant_condition=relevant_condition,
        cause_hypothesis=cause_hypothesis,
        confidence=confidence,
        evidence=evidence,
        is_hypothesis=True
    )
