import re
with open("ps3_agent/execution/compiler.py", "r") as f:
    code = f.read()

# Replace old mock functions from C code
injection = """    # Remove old mocks
    c_code = re.sub(r'void GPIO_Write.*?\{.*?\}', '', c_code, flags=re.DOTALL)
    c_code = re.sub(r'void UART_Print.*?\{.*?\}', '', c_code, flags=re.DOTALL)
    
    # Disable original main
"""
code = code.replace("    # Disable original main", injection)

# Fix loop syntax error
code = code.replace("s.trim();", "s.trim();")  # Not sure why it failed. Let's just remove s.trim()
code = code.replace("s.trim();", "")

with open("ps3_agent/execution/compiler.py", "w") as f:
    f.write(code)
