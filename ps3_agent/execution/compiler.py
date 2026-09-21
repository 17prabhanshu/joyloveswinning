import os
import re
import shutil
import tempfile
import subprocess
import logging
import hashlib
import threading
from pathlib import Path

logger = logging.getLogger("compiler")

_compile_lock = threading.Lock()

def compile_c_to_arduino(c_code: str, fqbn: str = "arduino:avr:uno") -> str:
    """
    Compile arbitrary C firmware code into an Arduino ELF for Wokwi execution.
    Dynamically detects which symbols the firmware already defines and only
    injects the missing stubs to avoid redefinition errors.
    """
    CACHE_VERSION = "v3"
    code_hash = hashlib.sha256((c_code + CACHE_VERSION).encode()).hexdigest()[:16]
    sketch_dir = os.path.join(tempfile.gettempdir(), f"ps3_build_{code_hash}")

    with _compile_lock:
        elf_path = os.path.join(sketch_dir, "joy_firmware", "joy_firmware.ino.elf")
        if os.path.exists(elf_path):
            logger.info(f"Using cached Arduino build in {sketch_dir}...")
            return os.path.join(sketch_dir, "joy_firmware")

        os.makedirs(os.path.join(sketch_dir, "joy_firmware"), exist_ok=True)
        sketch_dir = os.path.join(sketch_dir, "joy_firmware")

    # --- 1. Detect what the user's firmware already defines ---
    has_gpio_write = bool(re.search(r'\bvoid\s+GPIO_Write\s*\(', c_code))
    has_uart_print = bool(re.search(r'\bvoid\s+UART_Print\s*\(', c_code))
    has_simulated_adc = bool(re.search(r'\bsimulated_adc_value\b', c_code))
    has_firmware_tick = bool(re.search(r'\bvoid\s+firmware_tick\s*\(', c_code))
    has_main = bool(re.search(r'\bint\s+main\s*\(', c_code))

    # --- 2. Rename the user's main() so Arduino's setup()/loop() takes over ---
    if has_main:
        c_code = re.sub(r'\bint\s+main\s*\(\s*void\s*\)', 'int disabled_main(void)', c_code)
        c_code = re.sub(r'\bint\s+main\s*\(\s*\)', 'int disabled_main()', c_code)

    # --- 3. If the firmware defines GPIO_Write/UART_Print with bodies, replace
    #    the bodies with Arduino-native implementations ---
    if has_gpio_write:
        c_code = re.sub(
            r'void GPIO_Write\(uint8_t pin, bool value\)\s*\{[^}]*\}',
            'void GPIO_Write(uint8_t pin, bool value) { pinMode(pin, OUTPUT); digitalWrite(pin, value ? HIGH : LOW); }',
            c_code
        )
    if has_uart_print:
        c_code = re.sub(
            r'void UART_Print\(const char\*\s*msg\)\s*\{[^}]*\}',
            'void UART_Print(const char* msg) { Serial.print(msg); }',
            c_code
        )

    # --- 4. Make simulated_adc_value non-static so setup()/loop() can access it ---
    c_code = c_code.replace("static int16_t simulated_adc_value", "int16_t simulated_adc_value")

    # --- 5. Build stub block: only inject what the firmware is missing ---
    stubs = "#include <Arduino.h>\n\n// === JOY OS Auto-Injected Hardware Stubs ===\n"

    if not has_simulated_adc:
        stubs += "int16_t simulated_adc_value = 0;\n"
    if not has_firmware_tick:
        stubs += "void firmware_tick(void) { /* no-op */ }\n"
    if not has_gpio_write:
        stubs += "void GPIO_Write(uint8_t pin, bool value) { pinMode(pin, OUTPUT); digitalWrite(pin, value ? HIGH : LOW); }\n"
    if not has_uart_print:
        stubs += "void UART_Print(const char* msg) { Serial.print(msg); }\n"

    stubs += "\n"

    # --- 6. Build the Arduino wrapper ---
    arduino_wrapper = """
void setup() {
    Serial.begin(115200);
    delay(100);
    Serial.println("BOOT: JOY OS Interactive Simulation Session");
}

void loop() {
    if (Serial.available()) {
        String s = Serial.readStringUntil('\\n');
        s.trim();
        if (s.length() > 0) {
            simulated_adc_value = s.toInt();
            Serial.print("INJECTED:");
            Serial.println(simulated_adc_value);

            firmware_tick();

            Serial.println("TICK_DONE");
        }
    }
    delay(10);
}
"""

    sketch_code = stubs + c_code + "\n" + arduino_wrapper

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
