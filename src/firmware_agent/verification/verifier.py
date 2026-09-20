"""
Deterministic verification engine.

This is where PASS/FAIL decisions are made. The LLM NEVER overrides
results from this engine. Verification compares EXPECTED vs OBSERVED
based on actual simulator evidence.

Key principle: AI proposes → Tools execute → Deterministic verification decides.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from firmware_agent.simulator.base import SimulationResult


class VerificationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIP = "skip"


class AssertionCheck(BaseModel):
    """A single assertion check result with evidence."""
    assertion_type: str
    description: str
    expected: Any
    observed: Any
    passed: bool
    evidence: str = ""

    @property
    def status(self) -> VerificationStatus:
        return VerificationStatus.PASS if self.passed else VerificationStatus.FAIL


class VerificationResult(BaseModel):
    """Complete verification result for a single test execution.

    This is the authoritative PASS/FAIL record. Every field is derived
    from deterministic comparison of expected vs observed behavior.
    """
    test_id: str
    status: VerificationStatus
    assertions: list[AssertionCheck] = Field(default_factory=list)
    expected_summary: dict[str, Any] = Field(default_factory=dict)
    observed_summary: dict[str, Any] = Field(default_factory=dict)
    uart_output: str = ""
    gpio_evidence: dict[str, Any] = Field(default_factory=dict)
    simulation_status: str = ""
    stop_reason: str = ""
    steps_executed: int = 0
    cycles: int = 0
    failure_reason: str = ""
    evidence_chain: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw_simulation: dict[str, Any] = Field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == VerificationStatus.PASS

    @property
    def failed(self) -> bool:
        return self.status == VerificationStatus.FAIL

    def add_evidence(self, category: str, detail: str, data: Any = None) -> None:
        """Add an evidence entry to the chain."""
        self.evidence_chain.append({
            "category": category,
            "detail": detail,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


class Verifier:
    """Deterministic verification engine.

    Compares expected behavior (from test scenarios) against observed
    behavior (from simulation results) using deterministic assertion logic.

    The LLM is NEVER involved in making PASS/FAIL decisions.
    """

    def verify(
        self,
        test_id: str,
        expected: dict[str, Any],
        simulation: SimulationResult,
    ) -> VerificationResult:
        """Verify a test by comparing expected vs observed behavior.

        Args:
            test_id: Unique test identifier
            expected: Expected behavior from test scenario
            simulation: Actual simulation result from LabWired

        Returns:
            VerificationResult with deterministic PASS/FAIL
        """
        result = VerificationResult(
            test_id=test_id,
            status=VerificationStatus.PASS,  # Assume pass, fail on first assertion
            uart_output=simulation.uart_output,
            simulation_status=simulation.status,
            stop_reason=simulation.stop_reason,
            steps_executed=simulation.steps_executed,
            cycles=simulation.cycles,
            expected_summary=expected,
            observed_summary={
                "uart": simulation.uart_output[:500],
                "status": simulation.status,
                "stop_reason": simulation.stop_reason,
                "gpio": simulation.gpio_state,
            },
            raw_simulation=simulation.raw_result,
        )

        # Check if simulation itself errored or failed native assertions
        if simulation.errored:
            result.status = VerificationStatus.ERROR
            result.failure_reason = f"Simulation error: {simulation.stop_reason}"
            result.add_evidence("simulation", "Simulation ended with error",
                                {"stop_reason": simulation.stop_reason,
                                 "details": simulation.stop_reason_details})
            return result
            
        if simulation.status == "fail":
            # LabWired's native assertions failed
            result.status = VerificationStatus.FAIL
            failed_asserts = [a for a in simulation.assertions if not a.passed]
            result.failure_reason = f"LabWired native assertions failed: {len(failed_asserts)}"
            for lw_a in simulation.assertions:
                check = AssertionCheck(
                    assertion_type="labwired_native",
                    description=str(lw_a.assertion),
                    expected=lw_a.assertion,
                    observed="Evaluated by LabWired",
                    passed=lw_a.passed
                )
                result.assertions.append(check)
                result.add_evidence("labwired_assertion", f"{'PASS' if lw_a.passed else 'FAIL'}: {lw_a.assertion}", {})
            return result

        # Run all expected assertions
        assertions_to_check = expected.get("assertions", [])
        for assertion_spec in assertions_to_check:
            check = self._evaluate_assertion(assertion_spec, simulation)
            result.assertions.append(check)
            result.add_evidence(
                "assertion",
                f"{check.assertion_type}: {'PASS' if check.passed else 'FAIL'}",
                {"expected": check.expected, "observed": check.observed},
            )

        # Check expected UART content
        expected_uart = expected.get("uart_contains", [])
        if isinstance(expected_uart, str):
            expected_uart = [expected_uart]
        for pattern in expected_uart:
            check = self._check_uart_contains(pattern, simulation.uart_output)
            result.assertions.append(check)
            result.add_evidence("uart", f"uart_contains '{pattern}': "
                                f"{'PASS' if check.passed else 'FAIL'}")

        # Check UART must NOT contain
        not_expected_uart = expected.get("uart_not_contains", [])
        if isinstance(not_expected_uart, str):
            not_expected_uart = [not_expected_uart]
        for pattern in not_expected_uart:
            check = self._check_uart_not_contains(pattern, simulation.uart_output)
            result.assertions.append(check)
            result.add_evidence("uart", f"uart_not_contains '{pattern}': "
                                f"{'PASS' if check.passed else 'FAIL'}")

        # Check UART regex
        expected_regex = expected.get("uart_regex", [])
        if isinstance(expected_regex, str):
            expected_regex = [expected_regex]
        for pattern in expected_regex:
            check = self._check_uart_regex(pattern, simulation.uart_output)
            result.assertions.append(check)
            result.add_evidence("uart", f"uart_regex '{pattern}': "
                                f"{'PASS' if check.passed else 'FAIL'}")

        # Check expected stop reason
        expected_stop = expected.get("expected_stop_reason")
        if expected_stop:
            check = self._check_stop_reason(expected_stop, simulation.stop_reason)
            result.assertions.append(check)
            result.add_evidence("stop_reason",
                                f"Expected '{expected_stop}', got '{simulation.stop_reason}'")

        # Check GPIO expectations
        expected_gpio = expected.get("gpio", {})
        for pin_name, expected_value in expected_gpio.items():
            check = self._check_gpio(pin_name, expected_value, simulation.gpio_state)
            result.assertions.append(check)
            result.add_evidence("gpio", f"GPIO {pin_name}: "
                                f"{'PASS' if check.passed else 'FAIL'}")

        # Check simulation exit status expectation
        expected_status = expected.get("simulation_status")
        if expected_status:
            check = self._check_simulation_status(expected_status, simulation.status)
            result.assertions.append(check)

        # Determine overall result
        if any(not a.passed for a in result.assertions):
            result.status = VerificationStatus.FAIL
            failed = [a for a in result.assertions if not a.passed]
            reasons = [f"{a.assertion_type}: expected={a.expected}, observed={a.observed}"
                       for a in failed[:5]]
            result.failure_reason = "; ".join(reasons)

        return result

    def verify_from_labwired_result(
        self,
        test_id: str,
        simulation: SimulationResult,
    ) -> VerificationResult:
        """Verify using LabWired's own assertion results.

        When the test script already contains assertions, LabWired evaluates
        them deterministically. We build our VerificationResult from its results.
        """
        result = VerificationResult(
            test_id=test_id,
            status=VerificationStatus.PASS,
            uart_output=simulation.uart_output,
            simulation_status=simulation.status,
            stop_reason=simulation.stop_reason,
            steps_executed=simulation.steps_executed,
            cycles=simulation.cycles,
            raw_simulation=simulation.raw_result,
        )

        for lw_assertion in simulation.assertions:
            check = AssertionCheck(
                assertion_type=self._assertion_type(lw_assertion.assertion),
                description=str(lw_assertion.assertion),
                expected=lw_assertion.assertion,
                observed="(evaluated by LabWired)",
                passed=lw_assertion.passed,
                evidence=f"LabWired assertion: {lw_assertion.assertion}",
            )
            result.assertions.append(check)
            result.add_evidence("labwired_assertion",
                                f"{'PASS' if check.passed else 'FAIL'}: {lw_assertion.assertion}")

        if simulation.status == "fail" or any(not a.passed for a in result.assertions):
            result.status = VerificationStatus.FAIL
            failed = [a for a in result.assertions if not a.passed]
            result.failure_reason = f"LabWired reported {len(failed)} failed assertion(s)"
        elif simulation.status == "error":
            result.status = VerificationStatus.ERROR
            result.failure_reason = f"Simulation error: {simulation.stop_reason}"

        return result

    # ── Assertion evaluators ──────────────────────────────────────────

    def _check_uart_contains(self, pattern: str, uart: str) -> AssertionCheck:
        found = pattern in uart
        return AssertionCheck(
            assertion_type="uart_contains",
            description=f"UART output contains '{pattern}'",
            expected=pattern,
            observed=uart[:200] if not found else f"...{pattern}...",
            passed=found,
            evidence=f"Full UART: {uart[:500]}",
        )

    def _check_uart_not_contains(self, pattern: str, uart: str) -> AssertionCheck:
        found = pattern in uart
        return AssertionCheck(
            assertion_type="uart_not_contains",
            description=f"UART output must NOT contain '{pattern}'",
            expected=f"NOT '{pattern}'",
            observed="FOUND" if found else "NOT FOUND",
            passed=not found,
            evidence=f"Full UART: {uart[:500]}",
        )

    def _check_uart_regex(self, pattern: str, uart: str) -> AssertionCheck:
        try:
            match = re.search(pattern, uart, re.MULTILINE)
            return AssertionCheck(
                assertion_type="uart_regex",
                description=f"UART matches regex '{pattern}'",
                expected=pattern,
                observed=match.group(0) if match else "NO MATCH",
                passed=match is not None,
                evidence=f"Full UART: {uart[:500]}",
            )
        except re.error as e:
            return AssertionCheck(
                assertion_type="uart_regex",
                description=f"UART regex '{pattern}' (INVALID REGEX)",
                expected=pattern,
                observed=f"REGEX ERROR: {e}",
                passed=False,
            )

    def _check_stop_reason(self, expected: str, actual: str) -> AssertionCheck:
        return AssertionCheck(
            assertion_type="stop_reason",
            description=f"Stop reason is '{expected}'",
            expected=expected,
            observed=actual,
            passed=expected == actual,
        )

    def _check_gpio(
        self, pin: str, expected: Any, gpio_state: dict[str, Any]
    ) -> AssertionCheck:
        observed = gpio_state.get(pin, "UNKNOWN")
        return AssertionCheck(
            assertion_type="gpio_equals",
            description=f"GPIO {pin} equals {expected}",
            expected=expected,
            observed=observed,
            passed=str(observed) == str(expected),
            evidence=f"Full GPIO state: {gpio_state}",
        )

    def _check_simulation_status(self, expected: str, actual: str) -> AssertionCheck:
        return AssertionCheck(
            assertion_type="simulation_status",
            description=f"Simulation status is '{expected}'",
            expected=expected,
            observed=actual,
            passed=expected == actual,
        )

    def _evaluate_assertion(
        self, spec: dict[str, Any], sim: SimulationResult
    ) -> AssertionCheck:
        """Evaluate a generic assertion specification."""
        if "uart_contains" in spec:
            return self._check_uart_contains(spec["uart_contains"], sim.uart_output)
        if "uart_not_contains" in spec:
            return self._check_uart_not_contains(spec["uart_not_contains"], sim.uart_output)
        if "uart_regex" in spec:
            return self._check_uart_regex(spec["uart_regex"], sim.uart_output)
        if "expected_stop_reason" in spec:
            return self._check_stop_reason(spec["expected_stop_reason"], sim.stop_reason)
        if "gpio_equals" in spec:
            gpio = spec["gpio_equals"]
            return self._check_gpio(
                gpio.get("pin", ""), gpio.get("value"), sim.gpio_state
            )

        return AssertionCheck(
            assertion_type="unknown",
            description=f"Unknown assertion type: {spec}",
            expected=spec,
            observed="NOT EVALUATED",
            passed=False,
        )

    @staticmethod
    def _assertion_type(assertion: dict[str, Any]) -> str:
        """Extract the type name from an assertion dict."""
        for key in ["uart_contains", "uart_regex", "expected_stop_reason",
                     "uart_not_contains", "gpio_equals", "memory_value",
                     "rtt_contains"]:
            if key in assertion:
                return key
        return "unknown"
