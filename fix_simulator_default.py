with open("ps3_agent/execution/simulator.py", "r") as f:
    code = f.read()

new_default = """def get_default_simulator() -> SimulatorAdapter:
    \"\"\"Return the first healthy simulator in fallback order: Renode -> Wokwi -> Deterministic\"\"\"
    for sim in get_simulators():
        if sim.name() != "DeterministicSim":
            try:
                # Wokwi Adapter returns a bool, Renode returns a dict. We must handle both.
                health = sim.health_check()
                is_healthy = health if isinstance(health, bool) else health.get("available", False)
                if is_healthy:
                    return sim
            except Exception:
                pass
    return DeterministicSimulator()"""

code = code.replace("def get_default_simulator() -> SimulatorAdapter:\n    \"\"\"Return the default (always-available) simulator.\"\"\"\n    return DeterministicSimulator()", new_default)

with open("ps3_agent/execution/simulator.py", "w") as f:
    f.write(code)
