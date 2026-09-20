with open("ps3_agent/execution/wokwi_adapter.py", "r") as f:
    code = f.read()

code = code.replace(
    'class WokwiAdapter:\n    name = "Wokwi"\n',
    'class WokwiAdapter:\n    def name(self) -> str:\n        return "Wokwi"\n\n    def version(self) -> str:\n        return "0.27.1"\n'
)
# Wait, let me check if there was just `class WokwiAdapter:\n` without the `name = "Wokwi"`
import re
code = re.sub(r'class WokwiAdapter:(\n\s+name = "Wokwi")?\n', 'class WokwiAdapter:\n    def name(self) -> str:\n        return "Wokwi"\n\n    def version(self) -> str:\n        return "0.27.1"\n\n', code)

with open("ps3_agent/execution/wokwi_adapter.py", "w") as f:
    f.write(code)
