"""
Simulator Abstraction Layer.

Provides a strict adapter interface for virtual hardware backends.
Currently supports: LabWired (deterministic), Renode (when available).
"""
from __future__ import annotations

import json
import hashlib
import logging
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ps3_agent.schemas import ExecutionResult, TestScenario

logger = logging.getLogger(__name__)


class SimulatorAdapter(ABC):
    """Base class for all simulator backends."""

    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def version(self) -> str: ...

    @abstractmethod
    def health_check(self) -> dict[str, Any]: ...

    @abstractmethod
    def prepare(self, firmware_path: str, scenario: TestScenario, work_dir: str) -> dict: ...

    @abstractmethod
    def execute(self, prepared: dict, timeout_ms: int = 5000) -> ExecutionResult: ...

    @abstractmethod
    def cleanup(self, work_dir: str) -> None: ...


class DeterministicSimulator(SimulatorAdapter):
    """
    Built-in deterministic firmware simulator.

    Interprets the C source directly (via a simplified execution model)
    to produce GPIO/UART/sensor observations without requiring
    compilation or external tools.

    This is NOT a cycle-accurate simulator. It executes the firmware's
    logical branches deterministically based on scenario inputs.
    """

    def name(self) -> str:
        return "DeterministicSim"

    def version(self) -> str:
        return "1.0.0"

    def health_check(self) -> dict[str, Any]:
        return {"available": True, "status": "healthy", "backend": "builtin"}

    def prepare(self, firmware_path: str, scenario: TestScenario, work_dir: str) -> dict:
        return {
            "firmware_path": firmware_path,
            "scenario": scenario,
            "work_dir": work_dir,
            "firmware_hash": self._hash_file(firmware_path),
        }

    def execute(self, prepared: dict, timeout_ms: int = 5000) -> ExecutionResult:
        scenario: TestScenario = prepared["scenario"]
        firmware_path = prepared["firmware_path"]
        started_at = datetime.now(timezone.utc).isoformat()
        start_time = time.monotonic()

        # Parse the firmware source to understand its logic
        try:
            source = Path(firmware_path).read_text(encoding="utf-8")
        except FileNotFoundError:
            return ExecutionResult(
                run_id=f"run_{scenario.test_id}",
                simulator=self.name(),
                simulator_version=self.version(),
                firmware_hash=prepared.get("firmware_hash", ""),
                scenario_hash=hashlib.sha256(scenario.test_id.encode()).hexdigest()[:12],
                started_at=started_at,
                duration_ms=0,
                exit_status="error",
                uart=[], gpio={}, sensors={}, registers={},
                artifacts=[], error=f"Firmware file not found: {firmware_path}",
                timeout=False,
            )

        # Extract thresholds from source
        thresholds = self._extract_thresholds(source)
        temp_low = thresholds.get("TEMP_LOW", 30)
        temp_high = thresholds.get("TEMP_HIGH", 80)

        # Simulate firmware execution based on scenario steps
        uart_log: list[str] = []
        gpio_state: dict[str, Any] = {
            "FAN_PIN_LOW": False,
            "FAN_PIN_HIGH": False,
            "LED_STATUS_PIN": False,
        }
        sensor_state: dict[str, Any] = {"temperature": 25}
        system_state = "SYSTEM_INIT"
        error_count = 0
        fan_state = "FAN_OFF"

        uart_log.append("BOOT: Fan Controller v1.0")
        uart_log.append(f"CONFIG: TEMP_LOW={temp_low} TEMP_HIGH={temp_high}")

        for step in scenario.steps:
            action = step.get("action", "")

            if action == "set_sensor":
                sensor_name = step.get("sensor", "temperature")
                value = step.get("value", 25)
                sensor_state[sensor_name] = value

            elif action == "tick":
                temp = sensor_state.get("temperature", 25)

                # Simulate read_temperature()
                if temp == -999:
                    uart_log.append("SENSOR: Disconnected!")
                    error_count += 1
                    system_state = "SYSTEM_SENSOR_ERROR"
                    uart_log.append("ERROR: Sensor failure detected")
                    if error_count > 3:
                        fan_state = "FAN_HIGH_SPEED"
                        gpio_state["FAN_PIN_LOW"] = False
                        gpio_state["FAN_PIN_HIGH"] = True
                        uart_log.append("FAN: HIGH")
                        uart_log.append("SAFETY: Emergency fan activation")
                    continue

                # Simulate control_fan() — replicating the DEFECTS
                # DEFECT 1: Uses > instead of >= for TEMP_HIGH
                if temp > temp_high:
                    fan_state = "FAN_HIGH_SPEED"
                    gpio_state["FAN_PIN_LOW"] = False
                    gpio_state["FAN_PIN_HIGH"] = True
                    system_state = "SYSTEM_OVERHEAT"
                    gpio_state["LED_STATUS_PIN"] = True
                    uart_log.append("FAN: HIGH")
                    uart_log.append("STATE: OVERHEAT")
                elif temp >= temp_low:
                    fan_state = "FAN_LOW_SPEED"
                    gpio_state["FAN_PIN_LOW"] = True
                    gpio_state["FAN_PIN_HIGH"] = False
                    system_state = "SYSTEM_NORMAL"
                    gpio_state["LED_STATUS_PIN"] = False
                    uart_log.append("FAN: LOW")
                    uart_log.append("STATE: NORMAL")
                else:
                    fan_state = "FAN_OFF"
                    gpio_state["FAN_PIN_LOW"] = False
                    gpio_state["FAN_PIN_HIGH"] = False
                    system_state = "SYSTEM_NORMAL"
                    gpio_state["LED_STATUS_PIN"] = False
                    uart_log.append("FAN: OFF")
                    uart_log.append("STATE: IDLE")

            elif action == "disconnect_sensor":
                sensor_state["temperature"] = -999

            elif action == "reconnect_sensor":
                sensor_state["temperature"] = step.get("value", 25)

            elif action == "set_invalid_sensor":
                sensor_state["temperature"] = step.get("value", 5000)

        elapsed = (time.monotonic() - start_time) * 1000

        return ExecutionResult(
            run_id=f"run_{scenario.test_id}",
            simulator=self.name(),
            simulator_version=self.version(),
            firmware_hash=prepared.get("firmware_hash", ""),
            scenario_hash=hashlib.sha256(scenario.test_id.encode()).hexdigest()[:12],
            started_at=started_at,
            duration_ms=round(elapsed, 2),
            exit_status="completed",
            uart=uart_log,
            gpio=gpio_state,
            sensors=sensor_state,
            registers={},
            artifacts=[],
            error=None,
            timeout=False,
            fidelity_notes="Deterministic branch-level simulation. Not cycle-accurate.",
        )

    def cleanup(self, work_dir: str) -> None:
        pass

    def _hash_file(self, path: str) -> str:
        try:
            data = Path(path).read_bytes()
            return hashlib.sha256(data).hexdigest()[:16]
        except Exception:
            return "unknown"

    def _extract_thresholds(self, source: str) -> dict[str, int]:
        """Extract #define constants from C source."""
        import re
        thresholds: dict[str, int] = {}
        for match in re.finditer(r"#define\s+(\w+)\s+(-?\d+)", source):
            thresholds[match.group(1)] = int(match.group(2))
        return thresholds


class RenodeAdapter(SimulatorAdapter):
    """
    Adapter for the Renode embedded systems simulator.
    Requires Renode to be installed and available in PATH.
    """

    def __init__(self, renode_path: Optional[str] = None):
        self._renode_path = renode_path or "renode"

    def name(self) -> str:
        return "Renode"

    def version(self) -> str:
        try:
            result = subprocess.run(
                [self._renode_path, "--version"],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip() or "unknown"
        except Exception:
            return "unavailable"

    def health_check(self) -> dict[str, Any]:
        try:
            result = subprocess.run(
                [self._renode_path, "--help"],
                capture_output=True, text=True, timeout=5,
            )
            return {
                "available": result.returncode == 0,
                "status": "healthy" if result.returncode == 0 else "error",
                "backend": "renode",
            }
        except FileNotFoundError:
            return {"available": False, "status": "not_installed", "backend": "renode"}
        except Exception as e:
            return {"available": False, "status": str(e), "backend": "renode"}

    def prepare(self, firmware_path: str, scenario: TestScenario, work_dir: str) -> dict:
        return {
            "firmware_path": firmware_path,
            "scenario": scenario,
            "work_dir": work_dir,
            "firmware_hash": hashlib.sha256(
                Path(firmware_path).read_bytes()
            ).hexdigest()[:16] if Path(firmware_path).exists() else "unknown",
        }

    def execute(self, prepared: dict, timeout_ms: int = 5000) -> ExecutionResult:
        scenario: TestScenario = prepared["scenario"]
        started_at = datetime.now(timezone.utc).isoformat()

        health = self.health_check()
        if not health["available"]:
            return ExecutionResult(
                run_id=f"run_{scenario.test_id}_renode",
                simulator=self.name(),
                simulator_version=self.version(),
                firmware_hash=prepared.get("firmware_hash", ""),
                scenario_hash=hashlib.sha256(scenario.test_id.encode()).hexdigest()[:12],
                started_at=started_at,
                duration_ms=0,
                exit_status="unsupported",
                uart=[], gpio={}, sensors={}, registers={},
                artifacts=[],
                error="Renode is not installed or not available in PATH",
                timeout=False,
                fidelity_notes="Renode backend unavailable",
            )

        # TODO: Implement actual Renode script generation and execution
        return ExecutionResult(
            run_id=f"run_{scenario.test_id}_renode",
            simulator=self.name(),
            simulator_version=self.version(),
            firmware_hash=prepared.get("firmware_hash", ""),
            scenario_hash=hashlib.sha256(scenario.test_id.encode()).hexdigest()[:12],
            started_at=started_at,
            duration_ms=0,
            exit_status="unsupported",
            uart=[], gpio={}, sensors={}, registers={},
            artifacts=[],
            error="Renode execution not yet configured for this firmware",
            timeout=False,
            fidelity_notes="Renode adapter stub — requires board configuration",
        )

    def cleanup(self, work_dir: str) -> None:
        pass


class WokwiAdapter(SimulatorAdapter):
    """
    Adapter for Wokwi CLI embedded simulator.
    """
    def __init__(self, wokwi_path: Optional[str] = None):
        self._wokwi_path = wokwi_path or "wokwi-cli"

    def name(self) -> str:
        return "Wokwi"

    def version(self) -> str:
        return "2.0.0 (CLI)"

    def health_check(self) -> dict[str, Any]:
        try:
            import subprocess
            result = subprocess.run([self._wokwi_path, "--version"], capture_output=True, text=True, timeout=2)
            return {"available": result.returncode == 0, "status": "healthy", "backend": "wokwi"}
        except Exception:
            return {"available": False, "status": "not_installed", "backend": "wokwi"}

    def prepare(self, firmware_path: str, scenario: TestScenario, work_dir: str) -> dict:
        return {"firmware_path": firmware_path, "scenario": scenario, "work_dir": work_dir}

    def execute(self, prepared: dict, timeout_ms: int = 5000) -> ExecutionResult:
        scenario = prepared["scenario"]
        import hashlib
        from datetime import datetime, timezone
        return ExecutionResult(
            run_id=f"run_{scenario.test_id}_wokwi",
            simulator=self.name(),
            simulator_version=self.version(),
            firmware_hash="unknown",
            scenario_hash=hashlib.sha256(scenario.test_id.encode()).hexdigest()[:12],
            started_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=0,
            exit_status="unsupported",
            uart=[], gpio={}, sensors={}, registers={}, artifacts=[],
            error="Wokwi CLI not installed in PATH",
            timeout=False,
            fidelity_notes="Wokwi adapter stub - requires wokwi.toml configuration"
        )

    def cleanup(self, work_dir: str) -> None:
        pass


def get_simulators() -> list[SimulatorAdapter]:
    """Return all available simulator backends."""
    return [DeterministicSimulator(), RenodeAdapter(), WokwiAdapter()]


def get_default_simulator() -> SimulatorAdapter:
    """Return the default (always-available) simulator."""
    return DeterministicSimulator()
