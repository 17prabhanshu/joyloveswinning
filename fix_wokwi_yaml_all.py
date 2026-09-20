import re
with open("ps3_agent/execution/wokwi_adapter.py", "r") as f:
    code = f.read()

# Replace ANY instance of `  - uart:` with `  - serial:`
code = code.replace("  - uart:\\n", "  - serial:\\n")
# Replace any instance of `      uart:` with `      serial:`
code = code.replace("      uart:\\n", "      serial:\\n")

with open("ps3_agent/execution/wokwi_adapter.py", "w") as f:
    f.write(code)
