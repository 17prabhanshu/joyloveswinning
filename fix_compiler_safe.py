import re
with open("ps3_agent/execution/compiler.py", "r") as f:
    code = f.read()

code = code.replace("    # Disable original main\n so we can", "    # Disable original main so we can")

with open("ps3_agent/execution/compiler.py", "w") as f:
    f.write(code)
