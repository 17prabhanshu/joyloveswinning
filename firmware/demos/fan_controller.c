#include <stdint.h>
#include <stdbool.h>
#include <string.h>

// Mock definitions for hardware access
#define GPIO_Write(pin, state) 
#define uart_print(msg) 
#define FAN_PIN 1
#define HIGH 1
#define LOW 0
#define OFF 0
#define MEDIUM 1 // using 1 for simplicity

#define TEMP_HIGH 50
#define TEMP_LOW 30
#define SENSOR_DISCONNECTED_VAL -999

int current_fan_state = OFF;

void set_fan_state(int state) {
    current_fan_state = state;
    GPIO_Write(FAN_PIN, state);
    if (state == HIGH) {
        uart_print("FAN: HIGH\n");
    } else if (state == LOW) {
        uart_print("FAN: LOW\n");
    } else {
        uart_print("FAN: OFF\n");
    }
}

void update_fan(int temperature) {
#ifdef DEFECT_SENSOR_DISCONNECT_UNSAFE
    // Defect 2: Does not check for disconnected sensor, treats it as very cold
#else
    if (temperature == SENSOR_DISCONNECTED_VAL) {
        set_fan_state(OFF); // Safe state
        uart_print("ERROR: Sensor disconnected\n");
        return;
    }
#endif

#ifdef DEFECT_OUT_OF_RANGE_ACCEPTED
    // Defect 3: Accepts impossible temperatures without error
#else
    if (temperature > 150 || temperature < -50) {
        uart_print("ERROR: Temperature out of range\n");
        return;
    }
#endif

#ifdef DEFECT_INCLUSIVE_EXCLUSIVE_COMPARISON
    // Defect 1: Exclusive instead of inclusive at upper threshold (>= vs >)
    if (temperature > TEMP_HIGH) {
#else
    if (temperature >= TEMP_HIGH) {
#endif
        set_fan_state(HIGH);
    } else if (temperature >= TEMP_LOW) {
#ifdef DEFECT_RAPID_TRANSITION_STATE
        // Defect 4: Bad intermediate state logic causing incorrect GPIO write
        if (current_fan_state == HIGH) {
            GPIO_Write(FAN_PIN, OFF); // glitch
        }
#endif
        set_fan_state(LOW);
    } else {
        set_fan_state(OFF);
    }
}

void parse_uart_command(const char* cmd) {
#ifdef DEFECT_MALFORMED_UART_CMD
    // Defect 5: Vulnerable to malformed commands (buffer overflow or bad parsing)
    if (cmd[0] == 'S') {
        uart_print("STATUS OK\n");
    }
#else
    if (strcmp(cmd, "STATUS") == 0) {
        uart_print("STATUS OK\n");
    } else {
        uart_print("ERROR: Invalid command\n");
    }
#endif
}

int main() {
    uart_print("INIT OK\n");
    // Main loop would be here
    return 0;
}
