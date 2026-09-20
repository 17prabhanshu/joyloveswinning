with open("ps3_agent/execution/simulator.py", "r") as f:
    code = f.read()

target = """    import os
    if os.environ.get("DEMO_REPLAY_MODE", "0") == "1":
        return DeterministicSimulator()
        
    for sim in get_simulators():"""

replacement = """    for sim in get_simulators():"""
code = code.replace(target, replacement)

with open("ps3_agent/execution/simulator.py", "w") as f:
    f.write(code)
