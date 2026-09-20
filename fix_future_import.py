with open("ps3_agent/execution/simulator.py", "r") as f:
    lines = f.readlines()

new_lines = []
imported = False
for line in lines:
    if "from __future__ import annotations" in line:
        new_lines.append(line)
        new_lines.append("from ps3_agent.execution.wokwi_adapter import WokwiAdapter\n")
        imported = True
    elif line.startswith("from ps3_agent.execution.wokwi_adapter import WokwiAdapter"):
        continue
    else:
        new_lines.append(line)

with open("ps3_agent/execution/simulator.py", "w") as f:
    f.writelines(new_lines)
