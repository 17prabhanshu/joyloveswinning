with open("ps3_agent/execution/wokwi_adapter.py", "r") as f:
    code = f.read()

# Fix the scenario YAML generation
old_scenario_gen = """        # Wokwi Scenario YAML (to inject UART automatically)
        scenario_yaml = f\"\"\"
version: 1
author: JOY
name: "PS3 Test Scenario"
description: Auto-generated test
steps:
  - time: 100ms
  - serial:
      tx: "{target_temp}\\n"
  - time: 1000ms
  - expect:
      serial:
        tx: "STATE:"
        timeout: 1000
        
  - delay: 50ms
\"\"\""""

new_scenario_gen = """        # Wokwi Scenario YAML (to inject UART automatically)
        scenario_yaml = f\"\"\"
version: 1
author: JOY
name: 'PS3 Test Scenario'
steps:
  - delay: 100ms
  - write-serial: '{target_temp}\\n'
  - delay: 1000ms
  - wait-serial: 'STATE:'
\"\"\""""

if old_scenario_gen in code:
    code = code.replace(old_scenario_gen, new_scenario_gen)
else:
    # If the exact string didn't match, let's use regex to replace the scenario_yaml definition
    import re
    code = re.sub(r'scenario_yaml = f"""\nversion: 1.*?delay: 50ms\n"""', new_scenario_gen, code, flags=re.DOTALL)

# Fix the execution result logic
old_return = """        # Parse output
        output_lines = proc.stdout.splitlines()
        uart_logs = [line for line in output_lines if "BOOT" in line or "STATE:" in line or "ERROR:" in line or "FAN:" in line or "RECOVERY:" in line or "SAFETY:" in line or "INJECTED:" in line]
        
        return ExecutionResult(
            run_id="0", simulator="Wokwi", simulator_version="0.27.1",
            firmware_hash="unknown", scenario_hash="unknown", started_at="",
            duration_ms=1000.0, exit_status="completed", uart=uart_logs,
            gpio={}, sensors={}, registers={}, artifacts=[],
            error=None
        )"""

new_return = """        # Parse output
        output_lines = proc.stdout.splitlines()
        uart_logs = [line for line in output_lines if "BOOT" in line or "STATE:" in line or "ERROR:" in line or "FAN:" in line or "RECOVERY:" in line or "SAFETY:" in line or "INJECTED:" in line]
        
        exit_status = "completed"
        error_msg = None
        
        if proc.returncode != 0:
            exit_status = "error"
            error_msg = proc.stderr.strip()
            
        return ExecutionResult(
            run_id="0", simulator="Wokwi", simulator_version="0.27.1",
            firmware_hash="unknown", scenario_hash="unknown", started_at="",
            duration_ms=1000.0, exit_status=exit_status, uart=uart_logs,
            gpio={}, sensors={}, registers={}, artifacts=[],
            error=error_msg
        )"""

if old_return in code:
    code = code.replace(old_return, new_return)
else:
    print("Warning: return block didn't match perfectly. Trying regex.")
    code = re.sub(r'# Parse output.*?error=None\n        \)', new_return, code, flags=re.DOTALL)

with open("ps3_agent/execution/wokwi_adapter.py", "w") as f:
    f.write(code)
