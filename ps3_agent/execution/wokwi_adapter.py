import os
import re
import json
import time
import hashlib
import subprocess
import logging
from pathlib import Path
from typing import Any

from ps3_agent.schemas import ExecutionResult, TestScenario
from ps3_agent.execution.compiler import compile_c_to_arduino

logger = logging.getLogger("wokwi_adapter")

WOKWI_CLI_PATH = "/Users/prabhanshushekhar/.wokwi/bin/wokwi-cli"


class WokwiAdapter:
    """Adapter that executes firmware headlessly on Wokwi via wokwi-cli."""

    def name(self) -> str:
        return "Wokwi"

    def version(self) -> str:
        return "0.27.1"

    def health_check(self) -> dict[str, Any]:
        """Check if wokwi-cli is available and token is set."""
        token = os.environ.get("WOKWI_CLI_TOKEN", "")
        cli_exists = os.path.isfile(WOKWI_CLI_PATH)
        healthy = bool(token) and cli_exists
        return {
            "available": healthy,
            "status": "healthy" if healthy else "unhealthy",
            "backend": "wokwi",
        }

    def prepare(self, firmware_path: str, scenario: TestScenario, work_dir: str) -> dict:
        return {
            "firmware_path": firmware_path,
            "scenario": scenario,
            "work_dir": work_dir,
            "firmware_hash": hashlib.sha256(
                Path(firmware_path).read_bytes()
            ).hexdigest()[:16] if Path(firmware_path).exists() else "unknown",
            "c_code": Path(firmware_path).read_text() if Path(firmware_path).exists() else "",
        }

    def cleanup(self, work_dir: str) -> None:
        pass

    def execute(self, prepared: dict, timeout_ms: int = 15000) -> ExecutionResult:
        firmware_hash = prepared.get("firmware_hash", "unknown")
        scenario: TestScenario = prepared["scenario"]
        c_code = prepared.get("c_code", "")
        started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        t0 = time.monotonic()

        # --- 1. Compile ---
        try:
            build_dir = compile_c_to_arduino(c_code)
        except Exception as e:
            return self._error_result(firmware_hash, scenario, started_at, 0, f"Compilation failed: {e}")

        # --- 2. Generate diagram.json (correct board type!) ---
        diagram = {
            "version": 1,
            "author": "JOY",
            "editor": "wokwi",
            "parts": [
                {"type": "wokwi-arduino-uno", "id": "uno", "top": 0, "left": 0, "attrs": {}}
            ],
            "connections": [],
        }
        with open(os.path.join(build_dir, "diagram.json"), "w") as f:
            json.dump(diagram, f)

        # --- 3. Parse target temperature from scenario steps ---
        # The actual test value is in the scenario steps, not in scenario.target
        # (which contains source location strings like "control_fan()")
        target_temp = 25
        for step in scenario.steps:
            action = step.get("action", "")
            if action == "set_sensor" and step.get("sensor") == "temperature":
                target_temp = step.get("value", 25)
                break
            elif action == "disconnect_sensor":
                target_temp = -999
                break
            elif action == "set_invalid_sensor":
                target_temp = step.get("value", 5000)
                break
        
        logger.info(f"Parsed target_temp={target_temp} from scenario steps for {scenario.test_id}")

        # --- 4. Generate scenario.yaml ---
        # wait-serial / write-serial are the correct Wokwi scenario keys.
        # We wait for BOOT first (confirms firmware actually started), then inject temp.
        scenario_lines = [
            "version: 1",
            "name: 'PS3 Test Scenario'",
            "steps:",
            "  - wait-serial: 'BOOT:'",
            f"  - write-serial: '{target_temp}\\n'",
            "  - wait-serial: 'STATE:'",
        ]
        scenario_yaml = "\n".join(scenario_lines) + "\n"
        with open(os.path.join(build_dir, "scenario.yaml"), "w") as f:
            f.write(scenario_yaml)

        # --- 5. Run wokwi-cli ---
        elf_path = os.path.join(build_dir, "joy_firmware.ino.elf")
        cmd = [
            WOKWI_CLI_PATH,
            "--diagram-file", "diagram.json",
            "--elf", elf_path,
            "--scenario", "scenario.yaml",
            "--timeout", str(timeout_ms),
            "--timeout-exit-code", "1",
        ]

        logger.info(f"Executing Wokwi scenario in {build_dir} with temp={target_temp}")
        proc = subprocess.run(cmd, cwd=build_dir, capture_output=True, text=True, env=os.environ.copy())
        elapsed_ms = round((time.monotonic() - t0) * 1000, 1)

        # --- 6. Log raw output ---
        with open("/tmp/wokwi_last_run.log", "w") as log_f:
            log_f.write(f"=== CMD ===\n{' '.join(cmd)}\n")
            log_f.write(f"=== STDOUT ===\n{proc.stdout}\n")
            log_f.write(f"=== STDERR ===\n{proc.stderr}\n")

        # --- 7. Parse serial output ---
        output_lines = proc.stdout.splitlines()
        uart_logs = []
        gpio_state = {}
        for line in output_lines:
            stripped = line.strip()
            # Skip Wokwi CLI meta-lines
            if stripped.startswith("[") or stripped.startswith("Wokwi CLI") or stripped.startswith("Connected") or stripped.startswith("Starting"):
                continue
            # Capture firmware serial output
            if any(kw in stripped for kw in ("BOOT", "CONFIG", "STATE:", "FAN:", "ERROR:", "RECOVERY:", "SAFETY:", "INJECTED:", "SENSOR:")):
                uart_logs.append(stripped)
            # Parse GPIO state from FAN lines
            if "FAN: HIGH" in stripped:
                gpio_state["FAN_PIN_HIGH"] = True
                gpio_state["FAN_PIN_LOW"] = False
            elif "FAN: LOW" in stripped:
                gpio_state["FAN_PIN_HIGH"] = False
                gpio_state["FAN_PIN_LOW"] = True
            elif "FAN: OFF" in stripped:
                gpio_state["FAN_PIN_HIGH"] = False
                gpio_state["FAN_PIN_LOW"] = False
            if "STATE: OVERHEAT" in stripped:
                gpio_state["LED_STATUS_PIN"] = True
            elif "STATE: NORMAL" in stripped or "STATE: IDLE" in stripped:
                gpio_state["LED_STATUS_PIN"] = False

        # --- 8. Determine exit status ---
        if proc.returncode != 0:
            stderr = proc.stderr.strip()
            # Distinguish Wokwi execution errors from test failures
            if "Timeout" in stderr or "did not finish" in stderr:
                # Timeout can mean the firmware never printed STATE: — could be a real bug or a wiring issue
                if not uart_logs:
                    # No serial output at all = execution infrastructure error
                    return self._error_result(firmware_hash, scenario, started_at, elapsed_ms,
                                              f"Wokwi execution error: no serial output. Stderr: {stderr}")
                else:
                    # Got some output but timed out waiting for STATE: — may be a real firmware issue
                    exit_status = "completed"
                    error_msg = None
            elif "Invalid scenario" in stderr or "YAML" in stderr or "Error:" in stderr:
                return self._error_result(firmware_hash, scenario, started_at, elapsed_ms,
                                          f"Wokwi scenario error: {stderr}")
            else:
                return self._error_result(firmware_hash, scenario, started_at, elapsed_ms,
                                          f"Wokwi CLI error (rc={proc.returncode}): {stderr}")
        else:
            exit_status = "completed"
            error_msg = None

        return ExecutionResult(
            run_id=f"run_{scenario.test_id}_wokwi",
            simulator="Wokwi",
            simulator_version="0.27.1",
            firmware_hash=firmware_hash,
            scenario_hash=hashlib.sha256(scenario.test_id.encode()).hexdigest()[:12],
            started_at=started_at,
            duration_ms=elapsed_ms,
            exit_status=exit_status,
            uart=uart_logs,
            gpio=gpio_state,
            sensors={"temperature": target_temp},
            registers={},
            artifacts=[],
            error=error_msg,
        )

    def _error_result(self, fw_hash: str, scenario: TestScenario, started_at: str, elapsed_ms: float, error: str) -> ExecutionResult:
        """Return an ExecutionResult with exit_status='error' — NOT 'completed'.
        This ensures the verifier/diagnoser treats it as an infrastructure failure,
        not a firmware test failure."""
        return ExecutionResult(
            run_id=f"run_{scenario.test_id}_wokwi",
            simulator="Wokwi",
            simulator_version="0.27.1",
            firmware_hash=fw_hash,
            scenario_hash=hashlib.sha256(scenario.test_id.encode()).hexdigest()[:12],
            started_at=started_at,
            duration_ms=elapsed_ms,
            exit_status="error",
            uart=[],
            gpio={},
            sensors={},
            registers={},
            artifacts=[],
            error=error,
        )
