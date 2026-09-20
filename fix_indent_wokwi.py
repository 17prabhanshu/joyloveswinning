with open("ps3_agent/execution/wokwi_adapter.py", "r") as f:
    code = f.read()

code = code.replace("        import subprocess\n                proc =", "        import subprocess\n        proc =")

with open("ps3_agent/execution/wokwi_adapter.py", "w") as f:
    f.write(code)
