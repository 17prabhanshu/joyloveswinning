"""
Execution runner that connects the test scenarios to the simulator and verifier.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from firmware_agent.generators.models import TestScenario, TestSuite
from firmware_agent.simulator.base import HardwareConfig, SimulationResult, SimulatorAdapter
from firmware_agent.verification.assertions import AssertionEngine
from firmware_agent.verification.verifier import VerificationResult, Verifier

logger = logging.getLogger(__name__)


class TestExecutionResult(BaseModel):
    test_id: str
    scenario: dict[str, Any]
    simulation_result: dict[str, Any]
    verification_result: dict[str, Any]
    diagnosis: dict[str, Any] | None = None
    duration_seconds: float
    timestamp: str

    @property
    def passed(self) -> bool:
        return self.verification_result.get("status") == "pass"


class TestRunner:
    """Orchestrates test execution by bridging generators, simulator, and verifier."""

    def __init__(self, simulator: SimulatorAdapter, verifier: Verifier, localizer=None):
        self.simulator = simulator
        self.verifier = verifier
        self.localizer = localizer

    def run_test(
        self,
        scenario: TestScenario,
        firmware_path: str,
        base_hardware_config: HardwareConfig,
    ) -> TestExecutionResult:
        """Run a single test scenario."""
        logger.info(f"Running test {scenario.test_id}...")
        start_time = time.time()

        # Build assertions from scenario expectations
        expected_outputs = [e.model_dump() for e in scenario.expected_outputs]
        expected_dict = AssertionEngine.build_expected(expected_outputs)
        lw_assertions = AssertionEngine.build_labwired_assertions(expected_outputs)

        # Clone config and inject test-specific inputs/assertions
        config = base_hardware_config.model_copy(deep=True)
        config.firmware_path = firmware_path
        if lw_assertions:
            config.assertions.extend(lw_assertions)

        # Build UART injections from scenario inputs
        # For simplicity, if input type is 'uart', we send it over UART
        for inp in scenario.inputs:
            if inp.type == "uart":
                config.uart_injections.append({
                    "port": "uart0",  # or default port
                    "payload": str(inp.value)
                })
            # Other inputs (like sensors) might need custom handling depending on the simulator
        
        # Execute simulation
        sim_result = self.simulator.execute_test(firmware_path, config)
        
        # Verify
        ver_result = self.verifier.verify(scenario.test_id, expected_dict, sim_result)
        
        # Diagnose if failed
        diagnosis_dict = None
        if not ver_result.passed and self.localizer:
            try:
                # Localizer takes verification result and firmware model (if available)
                diagnosis = self.localizer.diagnose(ver_result, None)
                if diagnosis:
                    diagnosis_dict = diagnosis.model_dump()
            except Exception as e:
                logger.error(f"Failed to diagnose test {scenario.test_id}: {e}")

        duration = time.time() - start_time
        
        return TestExecutionResult(
            test_id=scenario.test_id,
            scenario=scenario.model_dump(),
            simulation_result=sim_result.model_dump(),
            verification_result=ver_result.model_dump(),
            diagnosis=diagnosis_dict,
            duration_seconds=duration,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def run_suite(
        self,
        suite: TestSuite,
        firmware_path: str,
        base_hardware_config: HardwareConfig,
    ) -> list[TestExecutionResult]:
        """Run an entire test suite."""
        results = []
        for scenario in suite.scenarios:
            result = self.run_test(scenario, firmware_path, base_hardware_config)
            results.append(result)
        return results
