#include <stdint.h>
#include <stdbool.h>

#define PUMP_PIN 4
#define HEATER_PIN 3

int16_t simulated_adc_value = 0;

void GPIO_Write(uint8_t pin, bool value) {}
void UART_Print(const char* msg) {}

int16_t read_sensor() {
    return simulated_adc_value;
}

void firmware_tick(void) {
    int16_t sensor = read_sensor();
    if (sensor > 500) {
        GPIO_Write(PUMP_PIN, true);
        UART_Print("STATE:BREWING\n");
    } else {
        GPIO_Write(PUMP_PIN, false);
        UART_Print("STATE:IDLE\n");
    }
}
