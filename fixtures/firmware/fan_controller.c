/**
 * fan_controller.c - Temperature-Controlled Fan System
 * 
 * Intentionally contains several embedded defects for the
 * autonomous red-team agent to discover:
 * 
 * DEFECT 1 (Line ~47): Boundary off-by-one
 *   if (temperature > TEMP_HIGH) — should be >=
 *   At exactly 80°C the fan stays OFF.
 * 
 * DEFECT 2 (Line ~62): Missing sensor disconnect guard
 *   read_temperature() can return SENSOR_DISCONNECTED (-999)
 *   but control_fan() does not check for it, treating -999 as cold.
 * 
 * DEFECT 3 (Line ~72): No range validation
 *   Out-of-range values (e.g. 5000°C) are accepted without clamping.
 * 
 * DEFECT 4 (Line ~89): No debounce on rapid state transitions
 *   Rapid HIGH→LOW→HIGH can cause back-EMF on inductive fan motor.
 * 
 * DEFECT 5 (Line ~35): Recovery assumes sensor reconnects cleanly
 *   After a disconnect, system transitions directly to normal mode
 *   without re-validating the first reading.
 */

#include <stdint.h>
#include <stdbool.h>

/* --- Configuration --- */
#define TEMP_LOW        30
#define TEMP_HIGH       80
#define SENSOR_DISCONNECTED  -999
#define SENSOR_MAX      150
#define FAN_PIN_LOW     0x01
#define FAN_PIN_HIGH    0x02
#define LED_STATUS_PIN  0x04

/* --- Hardware Abstraction --- */
typedef enum {
    FAN_OFF = 0,
    FAN_LOW_SPEED,
    FAN_HIGH_SPEED
} FanState;

typedef enum {
    SYSTEM_INIT = 0,
    SYSTEM_NORMAL,
    SYSTEM_OVERHEAT,
    SYSTEM_SENSOR_ERROR,
    SYSTEM_RECOVERY
} SystemState;

/* --- Global State --- */
static FanState    current_fan_state   = FAN_OFF;
static SystemState system_state        = SYSTEM_INIT;
static int16_t     last_valid_temp     = 25;
static uint32_t    error_count         = 0;
static bool        led_status          = false;

/* --- Simulated Hardware I/O --- */
static int16_t simulated_adc_value = 25;

void GPIO_Write(uint8_t pin, bool value) {
    /* Hardware GPIO write — observed by simulator */
    (void)pin;
    (void)value;
}

void UART_Print(const char* msg) {
    /* Hardware UART transmit — captured by simulator */
    (void)msg;
}

/* --- Sensor Interface --- */
int16_t read_temperature(void) {
    /* 
     * Reads ADC and converts to temperature in °C.
     * Returns SENSOR_DISCONNECTED if ADC times out.
     */
    int16_t raw = simulated_adc_value;
    
    if (raw == SENSOR_DISCONNECTED) {
        UART_Print("SENSOR: Disconnected!\n");
        return SENSOR_DISCONNECTED;
    }
    
    /* DEFECT 3: No range validation here.
     * Values like 5000 pass through unchecked. */
    return raw;
}

/* --- Fan Control --- */
void set_fan_state(FanState new_state) {
    /* DEFECT 4: No debounce delay between transitions.
     * Rapid HIGH→OFF→HIGH causes back-EMF spike. */
    current_fan_state = new_state;
    
    switch (new_state) {
        case FAN_OFF:
            GPIO_Write(FAN_PIN_LOW, false);
            GPIO_Write(FAN_PIN_HIGH, false);
            UART_Print("FAN: OFF\n");
            break;
        case FAN_LOW_SPEED:
            GPIO_Write(FAN_PIN_LOW, true);
            GPIO_Write(FAN_PIN_HIGH, false);
            UART_Print("FAN: LOW\n");
            break;
        case FAN_HIGH_SPEED:
            GPIO_Write(FAN_PIN_LOW, false);
            GPIO_Write(FAN_PIN_HIGH, true);
            UART_Print("FAN: HIGH\n");
            break;
    }
}

/* --- Main Control Logic --- */
void control_fan(int16_t temperature) {
    /* DEFECT 2: Does not check for SENSOR_DISCONNECTED.
     * -999 < TEMP_LOW, so fan turns OFF during potential overheat. */
    
    /* DEFECT 1: Uses > instead of >=.
     * At exactly TEMP_HIGH (80), fan stays in LOW instead of HIGH. */
    if (temperature > TEMP_HIGH) {
        set_fan_state(FAN_HIGH_SPEED);
        system_state = SYSTEM_OVERHEAT;
        GPIO_Write(LED_STATUS_PIN, true);
        UART_Print("STATE: OVERHEAT\n");
    } else if (temperature >= TEMP_LOW) {
        set_fan_state(FAN_LOW_SPEED);
        system_state = SYSTEM_NORMAL;
        GPIO_Write(LED_STATUS_PIN, false);
        UART_Print("STATE: NORMAL\n");
    } else {
        set_fan_state(FAN_OFF);
        system_state = SYSTEM_NORMAL;
        GPIO_Write(LED_STATUS_PIN, false);
        UART_Print("STATE: IDLE\n");
    }
}

/* --- Error Recovery --- */
void handle_sensor_error(void) {
    error_count++;
    system_state = SYSTEM_SENSOR_ERROR;
    UART_Print("ERROR: Sensor failure detected\n");
    
    /* Maintain last known fan state for safety */
    if (error_count > 3) {
        set_fan_state(FAN_HIGH_SPEED);
        UART_Print("SAFETY: Emergency fan activation\n");
    }
}

/* DEFECT 5: Recovery does not re-validate first reading */
void attempt_recovery(void) {
    int16_t temp = read_temperature();
    
    /* Blindly trusts first reading after disconnect */
    if (temp != SENSOR_DISCONNECTED) {
        system_state = SYSTEM_RECOVERY;
        error_count = 0;
        control_fan(temp);
        UART_Print("RECOVERY: Sensor reconnected\n");
    }
}

/* --- Main Loop (single iteration) --- */
void firmware_tick(void) {
    int16_t temp = read_temperature();
    
    if (temp == SENSOR_DISCONNECTED) {
        handle_sensor_error();
        return;
    }
    
    /* Normal operation */
    last_valid_temp = temp;
    control_fan(temp);
    
    /* Toggle status LED */
    led_status = !led_status;
    GPIO_Write(LED_STATUS_PIN, led_status);
}

/* --- Entry Point --- */
int main(void) {
    UART_Print("BOOT: Fan Controller v1.0\n");
    UART_Print("CONFIG: TEMP_LOW=30 TEMP_HIGH=80\n");
    
    system_state = SYSTEM_INIT;
    set_fan_state(FAN_OFF);
    
    /* Main loop */
    while (1) {
        firmware_tick();
    }
    
    return 0;
}
