import re
with open("ps3_agent/execution/wokwi_adapter.py", "r") as f:
    code = f.read()

# Add path fix
path_fix = """import os
os.environ["PATH"] += os.pathsep + os.path.expanduser("~/bin") + os.pathsep + "/opt/homebrew/bin"
"""
code = path_fix + code

# Replace subprocess.run with asyncio
old_run = """        import subprocess
        proc = subprocess.run(cmd, cwd=build_dir, capture_output=True, text=True, env=os.environ.copy())
        
        # Log to file so Antigravity can read it
        with open("/tmp/wokwi_last_run.log", "w") as log_f:
            log_f.write("=== CMD ===\\n" + " ".join(cmd) + "\\n")
            log_f.write("=== STDOUT ===\\n" + proc.stdout + "\\n")
            log_f.write("=== STDERR ===\\n" + proc.stderr + "\\n")"""

new_run = """        # Use asyncio so we don't block the FastAPI event loop for 5 seconds
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=build_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy()
        )
        stdout, stderr = await proc.communicate()
        stdout_str = stdout.decode('utf-8')
        stderr_str = stderr.decode('utf-8')
        
        with open("/tmp/wokwi_last_run.log", "w") as log_f:
            log_f.write("=== CMD ===\\n" + " ".join(cmd) + "\\n")
            log_f.write("=== STDOUT ===\\n" + stdout_str + "\\n")
            log_f.write("=== STDERR ===\\n" + stderr_str + "\\n")
        
        # Override proc.stdout for downstream logic
        class FakeProc:
            def __init__(self, s):
                self.stdout = s
        proc = FakeProc(stdout_str)"""

code = code.replace(old_run, new_run)

with open("ps3_agent/execution/wokwi_adapter.py", "w") as f:
    f.write(code)
