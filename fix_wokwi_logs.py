import re
with open("ps3_agent/execution/wokwi_adapter.py", "r") as f:
    code = f.read()

injection = """        proc = subprocess.run(cmd, cwd=build_dir, capture_output=True, text=True, env=os.environ.copy())
        
        # Log to file so Antigravity can read it
        with open("/tmp/wokwi_last_run.log", "w") as log_f:
            log_f.write("=== CMD ===\\n" + " ".join(cmd) + "\\n")
            log_f.write("=== STDOUT ===\\n" + proc.stdout + "\\n")
            log_f.write("=== STDERR ===\\n" + proc.stderr + "\\n")
        """
code = code.replace("proc = subprocess.run(cmd, cwd=build_dir, capture_output=True, text=True, env=os.environ.copy())", injection)

with open("ps3_agent/execution/wokwi_adapter.py", "w") as f:
    f.write(code)

with open("ps3_agent/execution/compiler.py", "r") as f:
    code = f.read()

injection2 = """result = subprocess.run(cmd, capture_output=True, text=True)
    with open("/tmp/arduino_last_run.log", "w") as log_f:
        log_f.write("=== CMD ===\\n" + " ".join(cmd) + "\\n")
        log_f.write("=== STDOUT ===\\n" + result.stdout + "\\n")
        log_f.write("=== STDERR ===\\n" + result.stderr + "\\n")
    """
code = code.replace("result = subprocess.run(cmd, capture_output=True, text=True)", injection2)

with open("ps3_agent/execution/compiler.py", "w") as f:
    f.write(code)
