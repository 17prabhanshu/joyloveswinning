with open("ps3_agent/api/server.py", "r") as f:
    lines = f.readlines()

future_idx = -1
for i, line in enumerate(lines):
    if "from __future__ import annotations" in line:
        future_idx = i
        break

if future_idx > 0:
    # move it to the top
    future_line = lines.pop(future_idx)
    lines.insert(0, future_line)

with open("ps3_agent/api/server.py", "w") as f:
    f.writelines(lines)
