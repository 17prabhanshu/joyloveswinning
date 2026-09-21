with open("ps3_agent/core/loop.py", "r") as f:
    code = f.read()

# Default to DeterministicSimulator, only use Wokwi when fast_mode is explicitly False
old = """        if self.fast_mode:
            simulator = DeterministicSimulator()
        else:
            simulator = get_default_simulator()"""

new = """        if not self.fast_mode:
            simulator = get_default_simulator()
        else:
            simulator = DeterministicSimulator()"""

# Actually, let's just flip it - fast_mode=True means Wokwi, default is Deterministic
# No wait, the user wants default to be FAST. Let me just swap the default.

with open("ps3_agent/core/loop.py", "w") as f:
    f.write(code)
