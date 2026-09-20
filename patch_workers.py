with open("ps3_agent/core/loop.py", "r") as f:
    code = f.read()

code = code.replace("ThreadPoolExecutor(max_workers=8)", "ThreadPoolExecutor(max_workers=30)")

with open("ps3_agent/core/loop.py", "w") as f:
    f.write(code)
