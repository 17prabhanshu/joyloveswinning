with open("ps3_agent/execution/compiler.py", "r") as f:
    code = f.read()

code = code.replace('f.write("#include <Arduino.h>\n" + c_code)', 'f.write("#include <Arduino.h>\\n" + c_code)')

with open("ps3_agent/execution/compiler.py", "w") as f:
    f.write(code)
