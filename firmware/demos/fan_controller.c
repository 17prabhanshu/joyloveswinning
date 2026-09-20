#include <stdint.h>
void _start(void);
__attribute__((section(".vectors")))
const void* vectors[] = {
    (void*)0x20005000, // Initial SP
    (void*)_start,      // Reset Handler
};
#include <stdbool.h>
int _strcmp(const char* s1, const char* s2) {
    while (*s1 && (*s1 == *s2)) {
        s1++;
        s2++;
    }
    return *(const unsigned char*)s1 - *(const unsigned char*)s2;
}

// Hardware registers for STM32F103
#define RCC_APB2ENR   (*(volatile uint32_t *)0x40021018)
#define GPIOC_ODR     (*(volatile uint32_t *)0x4001100C)
#define USART1_DR     (*(volatile uint32_t *)0x40013804)

// PC13 is pin 13
#define FAN_PIN 13
#define HIGH 1
#define LOW 0
#define OFF 0
#define MEDIUM 1 // using 1 for simplicity

void GPIO_Write(int pin, int state) {
    if (state) {
        GPIOC_ODR |= (1 << pin);
    } else {
        GPIOC_ODR &= ~(1 << pin);
    }
}

void uart_print(const char* msg) {
    while (*msg) {
        USART1_DR = *msg++;
    }
}

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
    if (_strcmp(cmd, "STATUS") == 0) {
        uart_print("STATUS OK\n");
    } else {
        uart_print("ERROR: Invalid command\n");
    }
#endif
}

#define GPIOC_CRH     (*(volatile uint32_t *)0x40011004)

int main() {
    // Enable GPIOC (bit 4) and USART1 (bit 14) clocks
    RCC_APB2ENR |= (1 << 4) | (1 << 14);

    // Configure PC13 as output push-pull, 2MHz (bits 23:20 = 0010 = 2)
    GPIOC_CRH &= ~(0xF << 20);
    GPIOC_CRH |= (0x2 << 20);

    uart_print("INIT OK\n");
    
    // Temperature sweep scenario
    int temperatures[] = {20, 35, 50, 30, SENSOR_DISCONNECTED_VAL};
    for (int i = 0; i < 5; i++) {
        update_fan(temperatures[i]);
    }
    
    while(1) {}
    return 0;
}

// Minimal startup
void _start(void) {
    // Initialize stack pointer to end of 20K RAM (STM32F103C8)
    __asm__ volatile("ldr sp, =0x20005000");
    main();
    while(1);
}
