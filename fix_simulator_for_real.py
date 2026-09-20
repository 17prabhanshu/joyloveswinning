import re

with open("ps3_agent/execution/simulator.py", "r") as f:
    code = f.read()

# Use regex to strip WokwiAdapter class entirely
code = re.sub(r'class WokwiAdapter.*?def cleanup.*?pass', '', code, flags=re.DOTALL)

# Now add the import if it's not there
if "from ps3_agent.execution.wokwi_adapter import WokwiAdapter" not in code:
    code = "from ps3_agent.execution.wokwi_adapter import WokwiAdapter\n" + code

with open("ps3_agent/execution/simulator.py", "w") as f:
    f.write(code)
