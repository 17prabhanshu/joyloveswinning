with open("ps3_agent/execution/wokwi_adapter.py", "r") as f:
    code = f.read()

bad = "firmware_path = prepared['firmware_path']\\n        scenario = prepared['scenario']\\n        if not self.health_check():"
good = "firmware_path = prepared['firmware_path']\n        scenario = prepared['scenario']\n        if not self.health_check():"

code = code.replace(bad, good)

with open("ps3_agent/execution/wokwi_adapter.py", "w") as f:
    f.write(code)
