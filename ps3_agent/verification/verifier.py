"""
Deterministic Verifier — Decides PASS/FAIL based purely on hardware evidence.
The LLM is explicitly excluded from the decision loop here.
"""
from __future__ import annotations

import logging
from typing import Any

from ps3_agent.schemas import (
    Assertion,
    AssertionProvenance,
    ExecutionResult,
    TestScenario,
    VerificationResult,
    VerificationStatus,
)

logger = logging.getLogger(__name__)


def check_uart_contains(uart_output: list[str], expected: str) -> tuple[bool, str]:
    combined_output = "\n".join(uart_output)
    if expected in combined_output:
        return True, f"Found expected string: '{expected}'"
    return False, f"String '{expected}' not found in UART output"


def check_gpio_equals(gpio_state: dict[str, Any], pin: str, expected: bool) -> tuple[bool, str]:
    if pin not in gpio_state:
        return False, f"Pin '{pin}' not found in GPIO state"
    actual = gpio_state[pin]
    if actual == expected:
        return True, f"Pin '{pin}' matches expected state {expected}"
    return False, f"Pin '{pin}' is {actual}, expected {expected}"


def check_sensor_range(sensors: dict[str, Any], sensor_id: str, min_val: float, max_val: float) -> tuple[bool, str]:
    if sensor_id not in sensors:
        return False, f"Sensor '{sensor_id}' not found"
    actual = sensors[sensor_id]
    if min_val <= actual <= max_val:
        return True, f"Sensor '{sensor_id}' value {actual} in range [{min_val}, {max_val}]"
    return False, f"Sensor '{sensor_id}' value {actual} out of range [{min_val}, {max_val}]"


def verify(scenario: TestScenario, execution: ExecutionResult) -> VerificationResult:
    if execution.error:
        return VerificationResult(
            test_id=scenario.test_id,
            status=VerificationStatus.ERROR,
            assertions=[],
            evidence_chain=[{"error": execution.error}]
        )
        
    if execution.timeout:
        return VerificationResult(
            test_id=scenario.test_id,
            status=VerificationStatus.TIMEOUT,
            assertions=[],
            evidence_chain=[{"error": "Execution timed out"}]
        )

    assertions: list[Assertion] = []
    evidence_chain: list[dict[str, Any]] = []
    all_passed = True

    for i, step in enumerate(scenario.steps):
        action = step.get("action", "")
        
        if action == "assert_gpio":
            pin = step.get("pin", "")
            expected = step.get("expected", False)
            passed, msg = check_gpio_equals(execution.gpio, pin, expected)
            
            verdict = VerificationStatus.PASS if passed else VerificationStatus.FAIL
            assertion = Assertion(
                type="GPIO_STATE",
                expected=expected,
                observed=execution.gpio.get(pin),
                provenance=AssertionProvenance.EXPLICIT_TEST,
                verdict=verdict,
                evidence=msg
            )
            assertions.append(assertion)
            evidence_chain.append({"step": i, "action": action, "msg": msg, "passed": passed})
            if not passed:
                all_passed = False
                
        elif action == "assert_uart":
            expected = step.get("expected", "")
            passed, msg = check_uart_contains(execution.uart, expected)
            
            verdict = VerificationStatus.PASS if passed else VerificationStatus.FAIL
            assertion = Assertion(
                type="UART_OUTPUT",
                expected=expected,
                observed=None,
                provenance=AssertionProvenance.EXPLICIT_TEST,
                verdict=verdict,
                evidence=msg
            )
            assertions.append(assertion)
            evidence_chain.append({"step": i, "action": action, "msg": msg, "passed": passed})
            if not passed:
                all_passed = False
                
        elif action == "assert_sensor":
            sensor_id = step.get("sensor", "")
            min_val = step.get("min_val", 0)
            max_val = step.get("max_val", 0)
            passed, msg = check_sensor_range(execution.sensors, sensor_id, min_val, max_val)
            
            verdict = VerificationStatus.PASS if passed else VerificationStatus.FAIL
            assertion = Assertion(
                type="SENSOR_RANGE",
                expected=f"[{min_val}, {max_val}]",
                observed=execution.sensors.get(sensor_id),
                provenance=AssertionProvenance.EXPLICIT_TEST,
                verdict=verdict,
                evidence=msg
            )
            assertions.append(assertion)
            evidence_chain.append({"step": i, "action": action, "msg": msg, "passed": passed})
            if not passed:
                all_passed = False

    # If no assertions, it's considered PASS (just an exploration test)
    if not assertions:
        status = VerificationStatus.PASS
        evidence_chain.append({"msg": "No assertions in scenario, exploration completed."})
    else:
        status = VerificationStatus.PASS if all_passed else VerificationStatus.FAIL
        
    return VerificationResult(
        test_id=scenario.test_id,
        status=status,
        assertions=assertions,
        evidence_chain=evidence_chain
    )
