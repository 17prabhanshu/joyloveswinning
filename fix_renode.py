import re
with open("ps3_agent/execution/simulator.py", "r") as f:
    code = f.read()

# Make renode return false
code = code.replace('return {"available": True, "status": "healthy", "backend": "renode"}', 'return {"available": False, "status": "unhealthy", "backend": "renode"}')

with open("ps3_agent/execution/simulator.py", "w") as f:
    f.write(code)
