import re
with open("ps3_agent/execution/wokwi_adapter.py", "r") as f:
    code = f.read()

# Make health_check load dotenv
old_health = """    def health_check(self) -> bool:
        # Require both arduino-cli and wokwi-cli to be in PATH, plus token
        from shutil import which
        import os
        return bool(which("arduino-cli")) and bool(which("wokwi-cli")) and bool(os.environ.get("WOKWI_CLI_TOKEN"))"""

new_health = """    def health_check(self) -> bool:
        # Require both arduino-cli and wokwi-cli to be in PATH, plus token
        from shutil import which
        import os
        from dotenv import load_dotenv
        load_dotenv()
        return bool(which("arduino-cli")) and bool(which("wokwi-cli")) and bool(os.environ.get("WOKWI_CLI_TOKEN"))"""

code = code.replace(old_health, new_health)

with open("ps3_agent/execution/wokwi_adapter.py", "w") as f:
    f.write(code)
