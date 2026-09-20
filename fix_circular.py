with open("ps3_agent/execution/simulator.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith("from ps3_agent.execution.wokwi_adapter import WokwiAdapter"):
        continue
    new_lines.append(line)

with open("ps3_agent/execution/simulator.py", "w") as f:
    f.writelines(new_lines)

# Now add it inside get_simulators
code = "".join(new_lines)
code = code.replace("def get_simulators() -> list[SimulatorAdapter]:", "def get_simulators() -> list[SimulatorAdapter]:\n    from ps3_agent.execution.wokwi_adapter import WokwiAdapter")

with open("ps3_agent/execution/simulator.py", "w") as f:
    f.write(code)
