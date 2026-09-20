with open("ps3_agent/api/llm_gateway.py", "r") as f:
    code = f.read()

bad = """        async with self.semaphore:
        # Replay Mode Safety Net"""

good = """        async with self.semaphore:
            # Replay Mode Safety Net"""

code = code.replace("async with self.semaphore:\n        # Replay", "async with self.semaphore:\n            # Replay")

with open("ps3_agent/api/llm_gateway.py", "w") as f:
    f.write(code)
