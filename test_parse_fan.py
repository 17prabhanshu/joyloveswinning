import sys
sys.path.insert(0, "src")
from firmware_agent.analyzer.parser import FirmwareParser
parser = FirmwareParser()
model = parser.parse_file("firmware/demos/fan_controller.c")
for f in model.functions:
    print(f"Function: {f.name}")
    for c in f.conditions:
        print(f"  Condition: {c}")
