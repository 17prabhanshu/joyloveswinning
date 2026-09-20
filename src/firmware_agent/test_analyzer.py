import os
from analyzer import FirmwareParser, BehaviorGraphBuilder, CFGBuilder

test_code = """
#define TEMP_HIGH 50
#define TEMP_LOW 30
void update_fan(int temperature) {
    if (temperature >= TEMP_HIGH) {
        GPIO_Write(FAN_PIN, HIGH);
        uart_print("Fan HIGH");
    } else if (temperature >= TEMP_LOW) {
        GPIO_Write(FAN_PIN, MEDIUM);
    } else {
        GPIO_Write(FAN_PIN, LOW);
    }
}
"""

with open("test_fw.c", "w") as f:
    f.write(test_code)

parser = FirmwareParser()
model = parser.parse_file("test_fw.c")

print(f"Functions found: {[f.name for f in model.functions]}")
print(f"Defines found: {[d.name for d in model.defines]}")
if model.functions:
    func = model.functions[0]
    print(f"Function params: {func.params}")
    print(f"GPIO ops: {func.gpio_ops}")
    print(f"UART ops: {func.uart_ops}")

builder = BehaviorGraphBuilder()
graph = builder.build(model)
print(f"Graph nodes: {len(graph.nodes)}")
print(f"Boundary conditions: {graph.boundary_conditions}")

cfg_builder = CFGBuilder()
if model.functions:
    cfg = cfg_builder.build(model.functions[0])
    print(f"CFG nodes: {len(cfg.nodes)}")
