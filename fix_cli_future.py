with open("ps3_agent/cli.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "from __future__ import annotations" in line:
        new_lines.append(line)
        new_lines.append("from dotenv import load_dotenv\nload_dotenv()\n")
    elif line.startswith("from dotenv import load_dotenv") or line.startswith("load_dotenv()"):
        continue
    else:
        new_lines.append(line)

with open("ps3_agent/cli.py", "w") as f:
    f.writelines(new_lines)
