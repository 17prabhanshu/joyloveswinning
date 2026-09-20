with open("ps3_agent/execution/wokwi_adapter.py", "r") as f:
    code = f.read()

code = code.replace(
    '  - uart:\n      tx:',
    '  - serial:\n      tx:'
)

with open("ps3_agent/execution/wokwi_adapter.py", "w") as f:
    f.write(code)
