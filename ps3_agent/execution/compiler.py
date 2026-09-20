import os
import shutil
import tempfile
import subprocess
import logging
import re
from pathlib import Path

logger = logging.getLogger("compiler")

def compile_c_to_arduino(c_code: str, fqbn: str = "arduino:avr:uno") -> str:
    temp_dir = tempfile.mkdtemp(prefix="ps3_build_")
    sketch_dir = os.path.join(temp_dir, "joy_firmware")
    os.makedirs(sketch_dir)
    
    # 1. Replace the mock bodies with Arduino bodies using a simple string replacement
    # We just replace the entire function bodies safely.
    c_code = re.sub(r'void GPIO_Write\(uint8_t pin, bool value\) \{[^\}]+\}', 'void GPIO_Write(uint8_t pin, bool value) { pinMode(pin, OUTPUT); digitalWrite(pin, value ? HIGH : LOW); }', c_code)
    c_code = re.sub(r'void UART_Print\(const char\* msg\) \{[^\}]+\}', 'void UART_Print(const char* msg) { Serial.print(msg); }', c_code)
    
    # 2. Rename original main so it doesn't run and block Arduino
    c_code = c_code.replace("int main(void)", "int disabled_main(void)")
    
    # 3. Remove 'static' from simulated_adc_value so our injected loop() can write to it
    c_code = c_code.replace("static int16_t simulated_adc_value", "int16_t simulated_adc_value")
    
    # 4. Add Arduino wrapper at the end
    sketch_code = "#include <Arduino.h>\n" + c_code + """
void setup() {
    Serial.begin(115200);
    delay(100);
    UART_Print("BOOT: Fan Controller v1.0 (Arduino Uno Wrapper)\\n");
    UART_Print("CONFIG: TEMP_LOW=30 TEMP_HIGH=80\\n");
}

void loop() {
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
    delay(10);
}
"""
    sketch_path = os.path.join(sketch_dir, "joy_firmware.ino")
    with open(sketch_path, "w") as f:
        f.write(sketch_code)
        
    logger.info(f"Compiling Arduino sketch in {sketch_dir}...")
    
    cmd = [
        "arduino-cli", "compile",
        "--fqbn", fqbn,
        "--output-dir", sketch_dir,
        sketch_dir
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    with open("/tmp/arduino_last_run.log", "w") as log_f:
        log_f.write("=== CMD ===\n" + " ".join(cmd) + "\n")
        log_f.write("=== STDOUT ===\n" + result.stdout + "\n")
        log_f.write("=== STDERR ===\n" + result.stderr + "\n")
        
    if result.returncode != 0:
        logger.error(f"Compilation failed:\n{result.stderr}\n{result.stdout}")
        raise RuntimeError("Failed to compile Arduino firmware via arduino-cli.")
        
    return sketch_dir
