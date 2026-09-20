with open("ps3_agent/execution/wokwi_adapter.py", "r") as f:
    code = f.read()

code = code.replace(
    'class WokwiAdapter:\n',
    'class WokwiAdapter:\n    name = "Wokwi"\n'
)

with open("ps3_agent/execution/wokwi_adapter.py", "w") as f:
    f.write(code)
