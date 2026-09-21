import os
import re
import tempfile
import subprocess
import hashlib
import logging

logger = logging.getLogger("native_compiler")


def _find_matching_brace(code: str, start: int) -> int:
    """Find the index of the closing brace that matches the opening brace at `start`."""
    depth = 0
    i = start
    while i < len(code):
        if code[i] == '{':
            depth += 1
        elif code[i] == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _replace_sensor_functions(c_code: str) -> str:
    """
    Find functions whose names suggest sensor reading (Read_*, Get_*, Sense_*, etc.)
    and replace their ENTIRE body (brace-matched) to return simulated_adc_value.
    """
    pattern = re.compile(
        r'((?:uint(?:8|16|32)_t|int(?:8|16|32)?_t|int|unsigned\s+int|short|long)\s+'
        r'((?:read|get|sense|sample|measure|fetch|acquire)[_a-zA-Z0-9]*)\s*'
        r'\([^)]*\))\s*\{',
        re.IGNORECASE
    )
    
    offset = 0
    result = c_code
    for m in pattern.finditer(c_code):
        brace_open = m.end() - 1 + offset
        brace_close = _find_matching_brace(result, brace_open)
        if brace_close == -1:
            continue
        
        fn_name = m.group(2)
        return_type = m.group(1).split()[0]
        
        new_body = (
            f'{{\n'
            f'    extern int16_t simulated_adc_value;\n'
            f'    printf("SENSOR:{fn_name}=%d\\n", simulated_adc_value);\n'
            f'    fflush(stdout);\n'
            f'    return ({return_type}) simulated_adc_value;\n'
            f'}}'
        )
        
        old_len = brace_close - brace_open + 1
        result = result[:brace_open] + new_body + result[brace_close + 1:]
        offset += len(new_body) - old_len
    
    return result


def _replace_infinite_loops(c_code: str) -> str:
    """Replace while(1)/while(true)/for(;;) with single-pass if(1)."""
    c_code = re.sub(r'\bwhile\s*\(\s*1\s*\)', 'if (1) /* single-pass */', c_code)
    c_code = re.sub(r'\bwhile\s*\(\s*true\s*\)', 'if (1) /* single-pass */', c_code, flags=re.IGNORECASE)
    c_code = re.sub(r'\bfor\s*\(\s*;\s*;\s*\)', 'if (1) /* single-pass */', c_code)
    return c_code


def _inject_branch_traces(c_code: str) -> str:
    """Inject printf tracing into if/else branches and switch/case blocks."""
    
    # Trace if/else-if conditions
    def _trace_if(m):
        cond = m.group(1).replace('"', '\\"').replace('\n', ' ').strip()
        if len(cond) > 60:
            cond = cond[:57] + "..."
        return f'{m.group(0)}\n        printf("BRANCH:{cond}\\n"); fflush(stdout);'
    
    c_code = re.sub(r'(?:else\s+)?if\s*\(([^)]+)\)\s*\{', _trace_if, c_code)
    
    # Trace else blocks
    def _trace_else(m):
        return f'{m.group(0)}\n        printf("BRANCH:else\\n"); fflush(stdout);'
    c_code = re.sub(r'\belse\s*\{', _trace_else, c_code)
    
    # Trace switch case labels
    def _trace_case(m):
        val = m.group(1).strip()
        return f'{m.group(0)}\n            printf("CASE:{val}\\n"); fflush(stdout);'
    c_code = re.sub(r'\bcase\s+([^:]+):', _trace_case, c_code)
    
    # Trace default
    def _trace_default(m):
        return f'{m.group(0)}\n            printf("CASE:default\\n"); fflush(stdout);'
    c_code = re.sub(r'\bdefault\s*:', _trace_default, c_code)
    
    return c_code


def compile_c_native(c_code: str) -> str:
    """
    Compile arbitrary C firmware code into a native executable for deterministic testing.
    
    Strategy:
    1. Detect all symbols the firmware defines
    2. Auto-instrument: replace sensor reads, kill infinite loops, inject branch traces
    3. Rename main() to _user_main(), create firmware_tick() that calls it
    4. Provide GPIO/UART stubs and a test harness main()
    """

    # --- 1. Detect what the user's firmware already defines ---
    has_gpio_write = bool(re.search(r'\bvoid\s+GPIO_Write\s*\(', c_code))
    has_uart_print = bool(re.search(r'\bvoid\s+UART_Print\s*\(', c_code))
    has_simulated_adc = bool(re.search(r'\bsimulated_adc_value\b', c_code))
    has_firmware_tick = bool(re.search(r'\bvoid\s+firmware_tick\s*\(', c_code))
    has_main = bool(re.search(r'\bint\s+main\s*\(', c_code))

    # --- 2. Remove #include <stdint.h> etc. from user code (we provide them) ---
    c_code = re.sub(r'#include\s*<std(int|bool|io|lib)\.h>', '/* \\g<0> - provided by harness */', c_code)

    # --- 3. Remove ALL definitions of simulated_adc_value from user code ---
    # We define it in the header, so any user definition must be removed entirely
    if has_simulated_adc:
        # Remove: static int16_t simulated_adc_value = XX;
        c_code = re.sub(r'static\s+int16_t\s+simulated_adc_value\s*=\s*[^;]+;', 
                         '/* simulated_adc_value: provided by harness */', c_code)
        # Remove: int16_t simulated_adc_value = XX;
        c_code = re.sub(r'(?<!/\* )int16_t\s+simulated_adc_value\s*=\s*[^;]+;', 
                         '/* simulated_adc_value: provided by harness */', c_code)
        # Remove: int16_t simulated_adc_value; (no initializer)
        c_code = re.sub(r'int16_t\s+simulated_adc_value\s*;', 
                         '/* simulated_adc_value: provided by harness */', c_code)

    # --- 4. Auto-instrument: replace sensor functions, kill loops, add traces ---
    c_code = _replace_sensor_functions(c_code)
    c_code = _replace_infinite_loops(c_code)
    c_code = _inject_branch_traces(c_code)

    # --- 5. Rename GPIO_Write/UART_Print in user code so our stubs take priority ---
    if has_gpio_write:
        # Rename definition
        c_code = re.sub(r'\bvoid\s+(GPIO_Write)\s*\(', 'void _fw_GPIO_Write(', c_code)
        # Rename calls to _fw_ version — actually DON'T, we want calls to hit our stub
    if has_uart_print:
        c_code = re.sub(r'\bvoid\s+(UART_Print)\s*\(', 'void _fw_UART_Print(', c_code)

    # --- 6. Handle main() and firmware_tick() ---
    #    If user has firmware_tick: rename it to _user_firmware_tick, create wrapper
    #    If user has main: rename to _user_main, create firmware_tick that calls it
    if has_firmware_tick:
        c_code = re.sub(r'\bvoid\s+firmware_tick\s*\(\s*void\s*\)', 'void _user_firmware_tick(void)', c_code)
        c_code = re.sub(r'\bvoid\s+firmware_tick\s*\(\s*\)', 'void _user_firmware_tick(void)', c_code)
    
    if has_main:
        c_code = re.sub(r'\bint\s+main\s*\(\s*void\s*\)', 'void _user_main(void)', c_code)
        c_code = re.sub(r'\bint\s+main\s*\(\s*\)', 'void _user_main(void)', c_code)

    # --- 7. Build the header ---
    wrapper_header = """
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <stdint.h>

// Global sensor variable — test harness writes, firmware reads
int16_t simulated_adc_value = 0;

// Forward declarations for hardware stubs
void GPIO_Write(uint8_t pin, bool value);
void UART_Print(const char* msg);

// Forward declarations for user entry points and test harness wrappers
void _user_firmware_tick(void);
void _user_main(void);
void firmware_tick(void);
"""

    # --- 8. Build the footer ---
    wrapper_footer = "\n// === JOY OS Native Test Harness ===\n"

    # GPIO stub — captures all GPIO changes
    wrapper_footer += """
void GPIO_Write(uint8_t pin, bool value) {
    printf("GPIO[%d]=%d\\n", pin, value);
    fflush(stdout);
}
"""

    # UART stub — captures all UART output
    wrapper_footer += """
void UART_Print(const char* msg) {
    printf("%s", msg);
    fflush(stdout);
}
"""

    # Create firmware_tick() that calls the appropriate user entry point
    if has_firmware_tick and has_main:
        wrapper_footer += """
void firmware_tick(void) {
    _user_firmware_tick();
}
"""
    elif has_firmware_tick:
        wrapper_footer += """
void firmware_tick(void) {
    _user_firmware_tick();
}
"""
    elif has_main:
        wrapper_footer += """
void firmware_tick(void) {
    _user_main();
}
"""
    else:
        wrapper_footer += """
void firmware_tick(void) {
    // No user entry point found
    printf("WARN: No firmware_tick or main found\\n");
    fflush(stdout);
}
"""

    # Test harness main
    wrapper_footer += """
int main() {
    char line[256];
    
    printf("BOOT: JOY OS Native Execution Engine\\n");
    fflush(stdout);
    
    while (fgets(line, sizeof(line), stdin)) {
        simulated_adc_value = atoi(line);
        printf("INJECTED:%d\\n", simulated_adc_value);
        fflush(stdout);
        
        firmware_tick();
        
        printf("TICK_DONE\\n");
        fflush(stdout);
    }
    return 0;
}
"""

    full_code = wrapper_header + "\n" + c_code + "\n" + wrapper_footer

    code_hash = hashlib.sha256(full_code.encode()).hexdigest()[:16]
    build_dir = os.path.join(tempfile.gettempdir(), f"native_build_{code_hash}")
    os.makedirs(build_dir, exist_ok=True)

    source_path = os.path.join(build_dir, "firmware.c")
    exec_path = os.path.join(build_dir, "firmware.out")

    if os.path.exists(exec_path):
        return exec_path

    with open(source_path, "w") as f:
        f.write(full_code)

    # Write debug copy
    with open("/tmp/joy_native_debug.c", "w") as dbg:
        dbg.write(full_code)

    # Compile with relaxed warnings for instrumented code
    cmd = ["gcc", "-O0", "-g", 
           "-Wno-attributes", "-Wno-return-type",
           "-Wno-implicit-function-declaration",
           "-Wno-int-conversion",
           source_path, "-o", exec_path]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"Native compilation failed: {result.stderr}")
        raise RuntimeError("Native compilation failed")

    return exec_path
