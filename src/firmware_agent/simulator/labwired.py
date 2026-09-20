"""
LabWired simulator adapter.

Drives the real LabWired CLI (`labwired test`) to execute firmware ELFs
against modeled MCU hardware. Parses result.json, uart.log, and snapshot.json
to build a SimulationResult with actual evidence.

This adapter does NOT mock or fake LabWired output. It invokes the real
simulator binary and parses its real artifacts.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

import yaml

from firmware_agent.simulator.base import (
    AssertionResult,
    HardwareConfig,
    SimulationResult,
    SimulatorAdapter,
)


class LabWiredAdapter(SimulatorAdapter):
    """Adapter that drives the LabWired Core CLI for firmware execution.

    Uses `labwired test --script <yaml> --output-dir <dir>` to execute
    firmware and collect UART/GPIO/register/state evidence.
    """

    def __init__(
        self,
        labwired_bin: str | None = None,
        config_dir: str | None = None,
        work_dir: str | None = None,
    ):
        # Find LabWired binary
        self._bin = labwired_bin or self._find_labwired()
        # LabWired config directory (chips, systems)
        self._config_dir = config_dir
        # Working directory for temporary scripts/artifacts
        self._work_dir = work_dir or os.path.join(os.getcwd(), "artifacts", "raw")
        os.makedirs(self._work_dir, exist_ok=True)
        self._current_script: Path | None = None
        self._output_dir: Path | None = None

    def capabilities(self, chip: str) -> SimulatorCapabilities:
        """Return simulator capabilities for a chip by parsing its upstream YAML config.

        Searches upstream/labwired-core/configs/chips/ for <chip>.yaml (both
        top-level and onboarding/). Extracts GPIO port peripherals and derives
        pin names from the port naming convention used by LabWired configs.
        """
        from firmware_agent.simulator.base import SimulatorCapabilities
        from pathlib import Path

        chips_dir = Path("upstream/labwired-core/configs/chips")
        # Search top-level first, then onboarding/
        candidates = [
            chips_dir / f"{chip}.yaml",
            chips_dir / "onboarding" / f"{chip}.yaml",
        ]

        chip_yaml_path = None
        for c in candidates:
            if c.exists():
                chip_yaml_path = c
                break

        if chip_yaml_path is None:
            return SimulatorCapabilities(
                chip=chip,
                available=False,
                error=f"No chip config found. Searched: {[str(c) for c in candidates]}",
            )

        try:
            chip_config = yaml.safe_load(chip_yaml_path.read_text())
        except Exception as e:
            return SimulatorCapabilities(
                chip=chip,
                available=False,
                error=f"Failed to parse {chip_yaml_path}: {e}",
            )

        # Derive supported pins from GPIO port peripherals
        pins: list[str] = []
        peripherals = chip_config.get("peripherals", [])
        for periph in peripherals:
            periph_id = periph.get("id", "")
            periph_type = periph.get("type", "")

            # LabWired uses three naming conventions for GPIO ports:
            #   STM32 onboarding: id: gpioPortA, type: stm32f1gpioport → PA0..PA15
            #   STM32 top-level:  id: gpioa,     type: gpio            → PA0..PA15
            #   Nordic-style:     id: gpio0,     type: gpio            → P0.0..P0.N
            if "gpio" in periph_type.lower() or periph_id.lower().startswith("gpio"):
                # Skip GPIOTE (event controller), not a GPIO port
                if "gpiote" in periph_id.lower():
                    continue

                # STM32 convention 1: gpioPortA → port letter A
                if periph_id.lower().startswith("gpioport"):
                    port_letter = periph_id.replace("gpioPort", "").replace("gpioport", "").upper()
                    if len(port_letter) == 1 and port_letter.isalpha():
                        for pin_num in range(16):
                            pins.append(f"P{port_letter}{pin_num}")
                elif periph_id.lower().startswith("gpio"):
                    suffix = periph_id[4:]  # everything after "gpio"
                    # STM32 convention 2: gpioa → port letter A (single alpha suffix)
                    if len(suffix) == 1 and suffix.isalpha():
                        port_letter = suffix.upper()
                        for pin_num in range(16):
                            pins.append(f"P{port_letter}{pin_num}")
                    # Nordic/generic convention: gpio0 → P0.0..P0.N (numeric suffix)
                    elif suffix.isdigit():
                        config_block = periph.get("config", {})
                        ngpios = config_block.get("ngpios", 16) if isinstance(config_block, dict) else 16
                        for pin_num in range(ngpios):
                            pins.append(f"P{suffix}.{pin_num}")

        return SimulatorCapabilities(
            chip=chip,
            available=True,
            can_observe_gpio=True,
            can_observe_uart=True,
            can_observe_registers=True,
            can_inject_faults=["disconnect", "out_of_range"],
            supported_pins=pins,
        )

    def name(self) -> str:
        return "labwired"

    def is_available(self) -> bool:
        """Check if LabWired CLI binary is accessible."""
        try:
            result = subprocess.run(
                [self._bin, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0 and "labwired" in result.stdout.lower()
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False

    def get_version(self) -> str | None:
        """Return LabWired CLI version string."""
        try:
            result = subprocess.run(
                [self._bin, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to get version: {e}")
        return None

    def list_chips(self) -> list[str]:
        """Return the list of supported chip names."""
        try:
            result = subprocess.run(
                [self._bin, "chips"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to list chips: {e}")
        return []

    def prepare(self, firmware_path: str | Path, config: HardwareConfig) -> None:
        """Generate a LabWired test YAML script and output directory."""
        firmware_path = Path(firmware_path).resolve()
        if not firmware_path.exists():
            raise FileNotFoundError(f"Firmware not found: {firmware_path}")

        config.firmware_path = str(firmware_path)
        if config.chip:
            if config.chip.endswith(".yaml") or config.chip.endswith(".yml") or "/" in config.chip:
                config.chip = str(Path(config.chip).resolve())
        if config.system_manifest:
            config.system_manifest = str(Path(config.system_manifest).resolve())

        # Create unique output dir for this run
        run_id = uuid.uuid4().hex[:8]
        self._output_dir = Path(self._work_dir) / f"run_{run_id}"
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Build the test YAML script
        script = self._build_test_script(config)
        self._current_script = self._output_dir / "test_script.yaml"
        self._current_script.write_text(yaml.dump(script, default_flow_style=False))

    def execute(self, config: HardwareConfig) -> SimulationResult:
        """Run LabWired CLI and parse the real results."""
        if self._current_script is None or self._output_dir is None:
            raise RuntimeError("Must call prepare() before execute()")

        cmd = [
            self._bin, "test",
            "--script", str(self._current_script),
            "--output-dir", str(self._output_dir),
            "--no-uart-stdout",
        ]
        # Gate 4: Enable GPIO observability (using native logic analyzer trace)
        for assertion in config.assertions:
            if "gpio_equals" in assertion:
                pin_str = assertion["gpio_equals"].get("pin", "").lower()
                # e.g. PA5 -> gpioa:5
                if len(pin_str) >= 3 and pin_str.startswith("p"):
                    port = pin_str[1]
                    pin = pin_str[2:]
                    cmd.extend(["--watch-gpio", f"gpio{port}:{pin}"])
        
        cmd.extend(config.extra_args)

        import time
        start_time = time.time()
        
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.wall_time_ms / 1000 + 30 if config.wall_time_ms else 60,
                cwd=str(self._output_dir),
            )
            duration = time.time() - start_time
            
            # Gate 1.5 Raw artifact retention
            (self._output_dir / "stdout.txt").write_text(proc.stdout)
            (self._output_dir / "stderr.txt").write_text(proc.stderr)
            run_manifest = {
                "command": cmd,
                "working_dir": str(self._output_dir),
                "resolved_binary": self._bin,
                "exit_code": proc.returncode,
                "duration_s": duration
            }
            (self._output_dir / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2))
            
        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            run_manifest = {
                "command": cmd,
                "working_dir": str(self._output_dir),
                "resolved_binary": self._bin,
                "exit_code": "TIMEOUT",
                "duration_s": duration,
                "error": str(e)
            }
            (self._output_dir / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2))
            
            return SimulationResult(
                status="error",
                stop_reason="wall_time",
                stop_reason_details={"error": "Host process timed out"},
            )

        # Parse LabWired artifacts
        return self._parse_results(proc)

    def cleanup(self) -> None:
        """Remove temporary run artifacts."""
        # Keep work_dir but clean current run
        self._current_script = None
        self._output_dir = None

    def _find_labwired(self) -> str:
        """Locate the labwired binary on the system."""
        # Check common locations
        candidates = [
            "labwired",
            os.path.expanduser("~/.local/bin/labwired"),
            "/usr/local/bin/labwired",
        ]
        for candidate in candidates:
            if shutil.which(candidate):
                return candidate
        # Return default and let is_available() fail gracefully
        return "labwired"

    def _build_test_script(self, config: HardwareConfig) -> dict[str, Any]:
        """Build a LabWired v1.0 test YAML script from HardwareConfig."""
        script: dict[str, Any] = {"schema_version": "1.0"}

        # Inputs
        inputs: dict[str, Any] = {"firmware": config.firmware_path}
        if config.system_manifest:
            inputs["system"] = config.system_manifest
        if config.chip:
            if config.chip.endswith(".yaml") or config.chip.endswith(".yml") or "/" in config.chip:
                inputs["chip"] = os.path.abspath(config.chip)
            else:
                inputs["chip"] = config.chip
        script["inputs"] = inputs

        # Limits
        limits: dict[str, Any] = {"max_steps": config.max_steps}
        if config.max_cycles is not None:
            limits["max_cycles"] = config.max_cycles
        if config.max_uart_bytes is not None:
            limits["max_uart_bytes"] = config.max_uart_bytes
        if config.wall_time_ms is not None:
            limits["wall_time_ms"] = config.wall_time_ms
        if config.no_progress_steps is not None:
            limits["no_progress_steps"] = config.no_progress_steps
        script["limits"] = limits

        # Assertions
        native_assertions = []
        for a in config.assertions:
            if any(k in a for k in ("uart_contains", "uart_not_contains", "uart_regex", "expected_stop_reason")):
                native_assertions.append(a)
        if native_assertions:
            script["assertions"] = native_assertions

        # UART injections (schema 1.2)
        if config.uart_injections:
            script["schema_version"] = "1.2"
            script["uart_injections"] = config.uart_injections

        return script

    def _parse_results(self, proc: subprocess.CompletedProcess) -> SimulationResult:
        """Parse LabWired output artifacts into SimulationResult."""
        if self._output_dir is None:
            return SimulationResult(status="error", stop_reason="config_error")

        result_path = self._output_dir / "result.json"
        uart_path = self._output_dir / "uart.log"
        snapshot_path = self._output_dir / "snapshot.json"

        # Read UART output
        uart_output = ""
        if uart_path.exists():
            uart_output = uart_path.read_text(errors="replace")

        # Read snapshot
        snapshot = {}
        if snapshot_path.exists():
            try:
                snapshot = json.loads(snapshot_path.read_text())
            except json.JSONDecodeError as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to decode snapshot.json: {e}")

        # Parse result.json - the authoritative source
        if result_path.exists():
            try:
                raw = json.loads(result_path.read_text())
                return self._build_result_from_json(raw, uart_output, snapshot)
            except json.JSONDecodeError as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to decode result.json: {e}")

        # Fallback: determine status from exit code
        from firmware_agent.verification.verifier import VerificationStatus
        if proc.returncode == 0:
            status = VerificationStatus.PASS.value
        elif proc.returncode == 1:
            status = VerificationStatus.FAIL.value
        elif proc.returncode == 2:
            status = VerificationStatus.ERROR.value
        elif proc.returncode == 3:
            status = VerificationStatus.ERROR.value
        else:
            status = VerificationStatus.ERROR.value

        return SimulationResult(
            status=status,
            uart_output=uart_output,
            snapshot=snapshot,
            stop_reason_details={
                "exit_code": proc.returncode,
                "stderr": proc.stderr[:2000] if proc.stderr else "",
                "stdout": proc.stdout[:2000] if proc.stdout else "",
            },
        )

    def _build_result_from_json(
        self,
        raw: dict[str, Any],
        uart_output: str,
        snapshot: dict[str, Any],
    ) -> SimulationResult:
        """Build SimulationResult from LabWired's result.json."""
        assertions = []
        for a in raw.get("assertions", []):
            assertions.append(AssertionResult(
                assertion=a.get("assertion", {}),
                passed=a.get("passed", False),
            ))

        # Extract CPU state from snapshot or result
        cpu_state = raw.get("cpu_state", {})
        if not cpu_state and snapshot:
            cpu_state = snapshot.get("cpu", {})

        # Extract GPIO state from logic_edges
        gpio_state = {}
        logic_edges = raw.get("logic_edges", {})
        for channel in logic_edges.get("channels", []):
            port = channel.get("peripheral", "").replace("gpio", "").upper()
            pin = channel.get("pin", "")
            key = f"P{port}{pin}"
            
            # Use final transitioned value, or initial if no transitions
            transitions = channel.get("transitions", [])
            if transitions:
                gpio_state[key] = transitions[-1].get("value")
            else:
                gpio_state[key] = channel.get("initial")
        if snapshot and not gpio_state:
            gpio_state = snapshot.get("gpio", snapshot.get("peripherals", {}))

        return SimulationResult(
            status=raw.get("status", "error"),
            steps_executed=raw.get("steps_executed", 0),
            cycles=raw.get("cycles", 0),
            instructions=raw.get("instructions", 0),
            stop_reason=raw.get("stop_reason", "unknown"),
            stop_reason_details=raw.get("stop_reason_details", {}),
            limits=raw.get("limits", {}),
            assertions=assertions,
            uart_output=uart_output,
            gpio_state=gpio_state,
            cpu_state=cpu_state,
            raw_result=raw,
            firmware_hash=raw.get("firmware_hash", ""),
            snapshot=snapshot,
        )
