import os
import shutil
import tempfile
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("compiler")

def compile_c_to_arduino(c_code: str, fqbn: str = "esp32:esp32:esp32") -> str:
    """
    Wraps generic C firmware into an Arduino sketch and compiles it using arduino-cli.
    Returns the absolute path to the compiled .bin/.elf directory.
    """
    # Disable original main so we can let Arduino's setup()/loop() handle execution
    # and provide the mock implementations for UART/GPIO
    c_code = c_code.replace("int main(void)", "int disabled_main(void)")
    
    sketch_code = """#include <Arduino.h>

// Forward declarations
void firmware_tick(void);
extern void control_fan(int16_t temperature);

// Mock the hardware writes directly to Arduino functions
void GPIO_Write(uint8_t pin, bool value) {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, value ? HIGH : LOW);
}

void UART_Print(const char* msg) {
    Serial.print(msg);
}

""" + c_code + """


extern int16_t simulated_adc_value;
void setup() {

    Serial.begin(115200);
    // Wokwi ESP32 serial needs a moment sometimes
    delay(100);
    UART_Print("BOOT: Fan Controller v1.0 (Arduino Wrapper)\\n");
    UART_Print("CONFIG: TEMP_LOW=30 TEMP_HIGH=80\\n");
}

void loop() {
    if (Serial.available()) {
        String s = Serial.readStringUntil('\n');
        s.trim();
        if (s.length() > 0) {
            simulated_adc_value = s.toInt();
            Serial.print("INJECTED:");
            Serial.println(simulated_adc_value);
        }
    }
    firmware_tick();

    delay(10); // Don't starve FreeRTOS watchdog
}
"""
    
    temp_dir = tempfile.mkdtemp(prefix="ps3_build_")
    sketch_dir = os.path.join(temp_dir, "joy_firmware")
    os.makedirs(sketch_dir)
    
    sketch_path = os.path.join(sketch_dir, "joy_firmware.ino")
    with open(sketch_path, "w") as f:
        f.write(sketch_code)
        
    logger.info(f"Compiling ESP32 sketch in {sketch_dir}...")
    
    cmd = [
        "arduino-cli", "compile",
        "--fqbn", fqbn,
        "--output-dir", sketch_dir,
        sketch_dir
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Compilation failed:\\n{result.stderr}\\n{result.stdout}")
        raise RuntimeError("Failed to compile ESP32 firmware via arduino-cli.")
        
    return sketch_dir
