import re
with open("ps3_agent/execution/compiler.py", "r") as f:
    code = f.read()

injection = """
extern int16_t simulated_adc_value;
void setup() {
"""

code = code.replace("void setup() {", injection)

loop_injection = """void loop() {
    if (Serial.available()) {
        String s = Serial.readStringUntil('\\n');
        s.trim();
        if (s.length() > 0) {
            simulated_adc_value = s.toInt();
            Serial.print("INJECTED:");
            Serial.println(simulated_adc_value);
        }
    }
    firmware_tick();
"""

code = code.replace("void loop() {\n    firmware_tick();", loop_injection)

with open("ps3_agent/execution/compiler.py", "w") as f:
    f.write(code)
