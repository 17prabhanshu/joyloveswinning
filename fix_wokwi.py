import re
with open("ps3_agent/execution/wokwi_adapter.py", "r") as f:
    code = f.read()

bad = """            # We inject UART reading into the compiler wrapper to set simulated_adc_value
            # Note: We must modify compiler.py to inject check_serial_inputs() into loop()
            # For hackathon speed, we'll just rewrite compiler.py's template here or rely on it
            # Actually, I'll update compiler.py to always include the UART injection hook!"""
code = code.replace(bad, "")

with open("ps3_agent/execution/wokwi_adapter.py", "w") as f:
    f.write(code)
