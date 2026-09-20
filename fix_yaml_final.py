import re
with open("ps3_agent/execution/wokwi_adapter.py", "r") as f:
    code = f.read()

# Replace the messy string generation with a clean list join
new_code = r"""        lines = [
            "version: 1",
            "author: JOY",
            "name: 'PS3 Test Scenario'",
            "steps:",
            "  - delay: 100ms",
            f"  - write-serial: '{target_temp}\\r\\n'",
            "  - delay: 1000ms",
            "  - wait-serial: 'STATE:'",
            ""
        ]
        scenario_yaml = "\n".join(lines)
"""

code = re.sub(r'        scenario_yaml = f"""\nversion: 1.*?wait-serial: "STATE:"\n"""\n', new_code, code, flags=re.DOTALL)

with open("ps3_agent/execution/wokwi_adapter.py", "w") as f:
    f.write(code)
