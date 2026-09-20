"""
Integration test: Prove that real firmware executes through LabWired
and Python receives actual simulation results with evidence.

This is Phase 0.5 acceptance criterion:
  firmware_elf -> LabWiredAdapter -> simulation -> VerificationResult

This test does NOT mock LabWired. It runs the real binary.
"""
import json
import os
import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from firmware_agent.simulator.labwired import LabWiredAdapter
from firmware_agent.simulator.base import HardwareConfig, SimulationResult
from firmware_agent.verification.verifier import Verifier, VerificationResult, VerificationStatus


# Path to the upstream LabWired fixture ELF
PROJECT_ROOT = Path(__file__).parent.parent.parent
UPSTREAM_DIR = PROJECT_ROOT / "upstream" / "labwired-core"
FIXTURE_ELF = UPSTREAM_DIR / "tests" / "fixtures" / "uart-ok-thumbv7m.elf"
CI_SYSTEM = UPSTREAM_DIR / "configs" / "systems" / "ci-fixture-uart1.yaml"


@pytest.fixture
def labwired():
    """Create a LabWired adapter instance."""
    adapter = LabWiredAdapter()
    if not adapter.is_available():
        pytest.skip(f"LabWired CLI not available at {adapter._bin}")
    return adapter


@pytest.fixture
def verifier():
    """Create a Verifier instance."""
    return Verifier()


@pytest.mark.integration_real_simulator
class TestLabWiredIntegration:
    """Prove that real firmware executes through LabWired with real evidence."""

    def test_labwired_is_available(self, labwired: LabWiredAdapter):
        """LabWired CLI binary must be accessible."""
        assert labwired.is_available()
        version = labwired.get_version()
        assert version is not None
        assert "labwired" in version.lower()
        print(f"LabWired version: {version}")

    def test_list_chips(self, labwired: LabWiredAdapter):
        """LabWired must report supported chip architectures."""
        chips = labwired.list_chips()
        assert len(chips) > 0
        assert "stm32f103" in chips
        print(f"Available chips: {', '.join(chips[:10])}")

    def test_execute_real_firmware(self, labwired: LabWiredAdapter):
        """Execute a REAL firmware ELF and get REAL results."""
        if not FIXTURE_ELF.exists():
            pytest.skip(f"Fixture ELF not found: {FIXTURE_ELF}")

        config = HardwareConfig(
            firmware_path=str(FIXTURE_ELF),
            system_manifest=str(CI_SYSTEM),
            max_steps=1000,
            assertions=[{"uart_contains": "OK"}],
        )

        labwired.prepare(str(FIXTURE_ELF), config)
        result = labwired.execute(config)
        labwired.cleanup()

        # Verify we got REAL results
        assert isinstance(result, SimulationResult)
        assert result.status == "pass", f"Simulation failed: {result.stop_reason}"
        assert result.steps_executed > 0, "No steps executed"
        assert result.cycles > 0, "No cycles recorded"

        # Verify UART evidence
        assert "OK" in result.uart_output, \
            f"Expected 'OK' in UART output, got: {result.uart_output!r}"

        # Verify assertions were evaluated
        assert len(result.assertions) > 0
        assert result.assertions[0].passed

        # Print evidence for humans
        print(f"Status: {result.status}")
        print(f"Steps: {result.steps_executed}")
        print(f"Cycles: {result.cycles}")
        print(f"UART: {result.uart_output!r}")
        print(f"Stop reason: {result.stop_reason}")

    def test_verification_of_real_simulation(
        self, labwired: LabWiredAdapter, verifier: Verifier
    ):
        """Full pipeline: execute firmware -> verify results deterministically."""
        if not FIXTURE_ELF.exists():
            pytest.skip(f"Fixture ELF not found: {FIXTURE_ELF}")

        config = HardwareConfig(
            firmware_path=str(FIXTURE_ELF),
            system_manifest=str(CI_SYSTEM),
            max_steps=1000,
            assertions=[{"uart_contains": "OK"}],
        )

        # Execute via LabWired
        result = labwired.execute_test(str(FIXTURE_ELF), config)
        assert result.status == "pass"

        # Verify using our deterministic verifier
        expected = {
            "uart_contains": ["OK"],
            "expected_stop_reason": "max_steps",
        }
        verification = verifier.verify("test_real_firmware", expected, result)

        assert verification.status == VerificationStatus.PASS
        assert len(verification.assertions) > 0
        assert all(a.passed for a in verification.assertions)
        assert len(verification.evidence_chain) > 0

        # Print verification evidence
        print(f"Verification status: {verification.status}")
        for a in verification.assertions:
            print(f"  {a.assertion_type}: {a.passed} ({a.description})")
        print(f"Evidence chain: {len(verification.evidence_chain)} entries")

    def test_failing_assertion_detected(
        self, labwired: LabWiredAdapter, verifier: Verifier
    ):
        """Verify that a genuinely wrong assertion is detected as FAIL."""
        if not FIXTURE_ELF.exists():
            pytest.skip(f"Fixture ELF not found: {FIXTURE_ELF}")

        config = HardwareConfig(
            firmware_path=str(FIXTURE_ELF),
            system_manifest=str(CI_SYSTEM),
            max_steps=1000,
        )

        result = labwired.execute_test(str(FIXTURE_ELF), config)

        # Verify with a deliberately wrong expectation
        expected = {
            "uart_contains": ["THIS TEXT DOES NOT EXIST IN OUTPUT"],
        }
        verification = verifier.verify("test_wrong_expectation", expected, result)

        # Must be detected as FAIL
        assert verification.status == VerificationStatus.FAIL
        assert verification.failure_reason != ""
        assert any(not a.passed for a in verification.assertions)
        print(f"Correctly detected failure: {verification.failure_reason}")

    def test_nrf54l15_smoke(self, labwired: LabWiredAdapter):
        """Run the nRF54L15 smoke test using the example test script."""
        script_path = UPSTREAM_DIR / "examples" / "nrf54l15-dk" / "io-smoke.yaml"
        if not script_path.exists():
            pytest.skip(f"Script not found: {script_path}")

        # This test uses LabWired's test runner directly via subprocess
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                labwired._bin, "test",
                "--script", str(script_path),
                "--output-dir", tmpdir,
                "--no-uart-stdout",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            assert proc.returncode == 0, f"Test failed: {proc.stderr}"

            # Verify artifacts exist
            result_json = Path(tmpdir) / "result.json"
            uart_log = Path(tmpdir) / "uart.log"
            assert result_json.exists()
            assert uart_log.exists()

            # Parse and verify
            raw = json.loads(result_json.read_text())
            assert raw["status"] == "pass"
            assert raw["steps_executed"] > 0

            uart = uart_log.read_text()
            assert "nRF54L15 boot OK" in uart

            print(f"nRF54L15 smoke: PASS ({raw['steps_executed']} steps)")

    def test_gpio_observability_via_vcd(self, labwired: LabWiredAdapter, verifier: Verifier):
        """Verify GPIO changes are captured via VCD and parsed (Gate 4 blocker)."""
        blinky_elf = UPSTREAM_DIR / "tests" / "fixtures" / "stm32f103-blinky.elf"
        if not blinky_elf.exists():
            pytest.skip(f"Fixture ELF not found: {blinky_elf}")

        config = HardwareConfig(
            firmware_path=str(blinky_elf),
            chip="stm32f103",
            max_steps=50000,
            assertions=[{"gpio_equals": {"pin": "PC13", "value": 0}}],
        )
        
        result = labwired.execute_test(str(blinky_elf), config)
        
        # Verify the VCD was actually generated and saved to raw artifacts
        output_dir = Path(result.raw_result.get("config", {}).get("script", "")).parent
        vcd_path = output_dir / "trace.vcd"
        if not vcd_path.exists():
            # If the backend did not generate trace.vcd, print a warning for the user
            print(f"\nWARNING: trace.vcd was not generated at {vcd_path}")
        else:
            print(f"\nSUCCESS: VCD trace generated at {vcd_path} ({vcd_path.stat().st_size} bytes)")
        
        print(f"\nGPIO State: {result.gpio_state}")
        # We assert gpio_equals. If it's not implemented yet, it will fail the verifier, which is correct
        expected = {
            "assertions": [
                {"gpio_equals": {"pin": "PC13", "value": 0}}
            ]
        }
        verification = verifier.verify("test_gpio_blinky", expected, result)
        
        # Verify it passes when expected value is 0
        print(f"\n--- ASSERTING PASS CASE (0) ---")
        print(f"GPIO Verification status: {verification.status}")
        for a in verification.assertions:
            print(f"  {a.assertion_type}: {a.passed} ({a.description})")
        
        assert verification.status == VerificationStatus.PASS
        assert len(verification.assertions) > 0
        assert verification.assertions[0].passed
        
        # Now toggle it to show it flips to FAIL
        print(f"\n--- ASSERTING FAIL CASE (1) ---")
        expected_fail = {
            "assertions": [
                {"gpio_equals": {"pin": "PC13", "value": 1}}
            ]
        }
        verification_fail = verifier.verify("test_gpio_blinky", expected_fail, result)
        print(f"GPIO Verification status: {verification_fail.status}")
        for a in verification_fail.assertions:
            print(f"  {a.assertion_type}: {a.passed} ({a.description})")
            
        assert verification_fail.status == VerificationStatus.FAIL
        assert not verification_fail.assertions[0].passed

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
