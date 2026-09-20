import re

with open("ps3_agent/execution/compiler.py", "r") as f:
    code = f.read()

code = code.replace('fqbn: str = "esp32:esp32:esp32"', 'fqbn: str = "arduino:avr:uno"')
code = code.replace('BOOT: Fan Controller v1.0 (Arduino Wrapper)', 'BOOT: Fan Controller v1.0 (Arduino Uno Wrapper)')

with open("ps3_agent/execution/compiler.py", "w") as f:
    f.write(code)


with open("ps3_agent/execution/wokwi_adapter.py", "r") as f:
    code = f.read()

code = code.replace('"board-esp32-devkit-c-v4"', '"board-arduino-uno"')
code = code.replace('"esp"', '"uno"')

with open("ps3_agent/execution/wokwi_adapter.py", "w") as f:
    f.write(code)
