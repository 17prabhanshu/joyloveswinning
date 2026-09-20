"""
Assertion engine for building expected behavior specifications.

Converts test scenarios into assertion dictionaries that the Verifier
can evaluate against simulation evidence.
"""
from __future__ import annotations

from typing import Any


class AssertionEngine:
    """Builds assertion specifications from test scenario expectations."""

    @staticmethod
    def build_expected(
        expected_outputs: list[dict[str, Any]],
        extra_uart: list[str] | None = None,
        extra_uart_not: list[str] | None = None,
        expected_stop_reason: str | None = None,
        expected_status: str | None = None,
    ) -> dict[str, Any]:
        """Build an expected-behavior dict for the Verifier.

        Args:
            expected_outputs: list of {type, target, value, condition}
            extra_uart: UART strings that must appear
            extra_uart_not: UART strings that must NOT appear
            expected_stop_reason: expected simulation stop reason
            expected_status: expected simulation status
        """
        expected: dict[str, Any] = {}
        assertions: list[dict[str, Any]] = []
        gpio_checks: dict[str, Any] = {}
        uart_contains: list[str] = list(extra_uart or [])
        uart_not_contains: list[str] = list(extra_uart_not or [])

        for out in expected_outputs:
            out_type = out.get("type", "")
            target = out.get("target", "")
            value = out.get("value")

            if out_type == "gpio":
                gpio_checks[target] = value
            elif out_type == "uart":
                if out.get("condition") == "not_contains":
                    uart_not_contains.append(str(value))
                else:
                    uart_contains.append(str(value))
            elif out_type == "uart_regex":
                assertions.append({"uart_regex": str(value)})
            elif out_type == "stop_reason":
                expected_stop_reason = str(value)
            elif out_type == "memory":
                assertions.append({
                    "memory_value": {
                        "address": target,
                        "expected_value": value,
                    }
                })

        if uart_contains:
            expected["uart_contains"] = uart_contains
        if uart_not_contains:
            expected["uart_not_contains"] = uart_not_contains
        if gpio_checks:
            expected["gpio"] = gpio_checks
        if expected_stop_reason:
            expected["expected_stop_reason"] = expected_stop_reason
        if expected_status:
            expected["simulation_status"] = expected_status
        if assertions:
            expected["assertions"] = assertions

        return expected

    @staticmethod
    def build_labwired_assertions(
        expected_outputs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build LabWired-native assertion list for test YAML scripts.

        These go into the test script's `assertions:` field and are
        evaluated by LabWired's own deterministic assertion engine.
        """
        lw_assertions: list[dict[str, Any]] = []

        for out in expected_outputs:
            out_type = out.get("type", "")
            value = out.get("value")

            if out_type == "uart":
                condition = out.get("condition", "contains")
                if condition == "contains":
                    lw_assertions.append({"uart_contains": str(value)})
                elif condition == "regex":
                    lw_assertions.append({"uart_regex": str(value)})
            elif out_type == "uart_regex":
                lw_assertions.append({"uart_regex": str(value)})
            elif out_type == "stop_reason":
                lw_assertions.append({"expected_stop_reason": str(value)})

        return lw_assertions
