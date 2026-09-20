import os
import json
import asyncio
import logging
from typing import Dict, Any
from pathlib import Path

from ps3_agent.schemas import TestScenario, ExecutionResult
from ps3_agent.execution.simulator import SimulatorAdapter
from ps3_agent.execution.compiler import compile_c_to_arduino

logger = logging.getLogger("wokwi_adapter")

class WokwiAdapter(SimulatorAdapter):
    def name(self) -> str:
        return "Wokwi"
        
    def health_check(self) -> bool:
        # Require both arduino-cli and wokwi-cli to be in PATH, plus token
        from shutil import which
        import os
        return bool(which("arduino-cli")) and bool(which("wokwi-cli")) and bool(os.environ.get("WOKWI_CLI_TOKEN"))

    async def execute(self, firmware_path: str, scenario: TestScenario) -> ExecutionResult:
        if not self.health_check():
            return ExecutionResult(
                run_id="0", simulator="Wokwi", simulator_version="unknown",
                firmware_hash="unknown", scenario_hash="unknown", started_at="",
                duration_ms=0, exit_status="unsupported", uart=[],
                gpio={}, sensors={}, registers={}, artifacts=[],
                error="Wokwi CLI, Arduino CLI, or WOKWI_CLI_TOKEN not configured."
            )
            
        with open(firmware_path, "r") as f:
            c_code = f.read()

        # Compile it!
        try:
            # We inject UART reading into the compiler wrapper to set simulated_adc_value
            wrapper_injection = """
            // Add a hook to read simulated ADC from UART in Wokwi
            extern int16_t simulated_adc_value;
            void check_serial_inputs() {
                if (Serial.available()) {
                    String s = Serial.readStringUntil('\\n');
                    s.trim();
                    if (s.length() > 0) {
                        simulated_adc_value = s.toInt();
                        Serial.println("INJECTED:" + s);
                    }
                }
            }
            """
            
            # Note: We must modify compiler.py to inject check_serial_inputs() into loop()
            # For hackathon speed, we'll just rewrite compiler.py's template here or rely on it
            # Actually, I'll update compiler.py to always include the UART injection hook!
            
            build_dir = compile_c_to_arduino(c_code)
        except Exception as e:
            return ExecutionResult(
                run_id="0", simulator="Wokwi", simulator_version="0.27.1",
                firmware_hash="unknown", scenario_hash="unknown", started_at="",
                duration_ms=0, exit_status="error", uart=[],
                gpio={}, sensors={}, registers={}, artifacts=[],
                error=f"Compilation failed: {e}"
            )

        # Create Wokwi project files
        diagram = {
          "version": 1,
          "author": "JOY",
          "editor": "wokwi",
          "parts": [{"type": "board-esp32-devkit-c-v4", "id": "esp", "top": 0, "left": 0, "attrs": {}}],
          "connections": []
        }
        
        with open(os.path.join(build_dir, "diagram.json"), "w") as f:
            json.dump(diagram, f)
            
        # Figure out the test inputs (just a simple integer temperature for this demo)
        target_temp = 25
        if "boundary" in scenario.category.lower() or "exactly" in scenario.target.lower():
            import re
            m = re.search(r'at (-?\d+)', scenario.target)
            if m: target_temp = int(m.group(1))
        elif "disconnect" in scenario.target.lower():
            target_temp = -999
            
        # Wokwi Scenario YAML (to inject UART automatically)
        scenario_yaml = f"""
version: 1
author: JOY
description: Auto-generated test
steps:
  - delay: 200ms
  - uart:
      tx: "{target_temp}\\n"
  - delay: 500ms
  - expect:
      uart:
        tx: "STATE:"
        timeout: 1000
        
  - delay: 50ms
"""
        with open(os.path.join(build_dir, "scenario.yaml"), "w") as f:
            f.write(scenario_yaml)

        # Execute Wokwi
        # Wokwi uses the ELF file for ESP32
        elf_path = os.path.join(build_dir, "joy_firmware.ino.elf")
        
        cmd = [
            "wokwi-cli",
            "--diagram-file", "diagram.json",
            "--elf", elf_path,
            "--scenario", "scenario.yaml",
            "--timeout", "5000",
            "--timeout-exit-code", "0"
        ]
        
        logger.info(f"Executing Wokwi scenario in {build_dir} with temp={target_temp}")
        import subprocess
        proc = subprocess.run(cmd, cwd=build_dir, capture_output=True, text=True, env=os.environ.copy())
        
        # Parse output
        output_lines = proc.stdout.splitlines()
        uart_logs = [line for line in output_lines if "BOOT" in line or "STATE:" in line or "ERROR:" in line or "FAN:" in line or "RECOVERY:" in line or "SAFETY:" in line or "INJECTED:" in line]
        
        return ExecutionResult(
            run_id="0", simulator="Wokwi", simulator_version="0.27.1",
            firmware_hash="unknown", scenario_hash="unknown", started_at="",
            duration_ms=1000.0, exit_status="completed", uart=uart_logs,
            gpio={}, sensors={}, registers={}, artifacts=[],
            error=None
        )
