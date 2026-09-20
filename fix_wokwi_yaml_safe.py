import ast

with open("ps3_agent/execution/wokwi_adapter.py", "r") as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.strip() == "scenario_yaml = f\"\"\"":
        skip = True
        new_lines.append('        scenario_yaml = f"""\n')
        new_lines.append('version: 1\n')
        new_lines.append('author: JOY\n')
        new_lines.append('name: "PS3 Test Scenario"\n')
        new_lines.append('steps:\n')
        new_lines.append('  - delay: 100ms\n')
        new_lines.append('  - write-serial: "{target_temp}\\r\\n"\n')
        new_lines.append('  - delay: 1000ms\n')
        new_lines.append('  - wait-serial: "STATE:"\n')
        new_lines.append('"""\n')
    elif line.strip() == '"""' and skip:
        skip = False
    elif not skip:
        new_lines.append(line)

with open("ps3_agent/execution/wokwi_adapter.py", "w") as f:
    f.writelines(new_lines)
