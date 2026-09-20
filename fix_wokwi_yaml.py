with open("ps3_agent/execution/wokwi_adapter.py", "r") as f:
    code = f.read()

code = code.replace(
    'yaml_str = f"""version: 1',
    'yaml_str = f"""version: 1\\nname: "PS3 Test Scenario"'
)

with open("ps3_agent/execution/wokwi_adapter.py", "w") as f:
    f.write(code)
