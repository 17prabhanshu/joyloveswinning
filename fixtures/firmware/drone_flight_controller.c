#include <stdint.h>
#include <stdbool.h>
#include <math.h>

// --- Hardware Abstraction Layer (HAL) Mocks ---
extern float read_gyro_pitch();
extern float read_gyro_roll();
extern float read_barometer_alt();
extern float read_battery_voltage();
extern void pwm_write_motor(uint8_t motor_id, uint16_t throttle);
extern void led_set_status(uint8_t color);

// --- Constants & Thresholds ---
#define BATTERY_MIN_VOLTAGE 10.5f     // 3S LiPo Minimum safe voltage
#define MAX_PITCH_ANGLE 45.0f         // Maximum safe pitch in degrees
#define MAX_ROLL_ANGLE 45.0f          // Maximum safe roll in degrees
#define FAILSAFE_THROTTLE 1100        // Throttle value to descend slowly
#define MIN_ARMING_VOLTAGE 11.4f      // Cannot arm if battery is low

// --- System State ---
typedef enum {
    STATE_DISARMED,
    STATE_ARMED,
    STATE_FLYING,
    STATE_FAILSAFE,
    STATE_CRASH_MODE
} SystemState;

SystemState current_state = STATE_DISARMED;
float current_pitch = 0.0f;
float current_roll = 0.0f;
float current_alt = 0.0f;
float current_vbat = 12.6f;

// --- PID Controller State ---
float error_pitch = 0.0f;
float integral_pitch = 0.0f;
float Kp = 1.2f;
float Ki = 0.05f;

// ====================================================================
// CORE FLIGHT LOGIC
// ====================================================================

/**
 * Update all sensor readings
 */
void update_sensors() {
    current_pitch = read_gyro_pitch();
    current_roll = read_gyro_roll();
    current_alt = read_barometer_alt();
    current_vbat = read_battery_voltage();
}

/**
 * Arming sequence. Should only allow arming if sensors are calibrated
 * and battery is healthy.
 */
bool arm_drone() {
    if (current_state != STATE_DISARMED) {
        return false;
    }

    // Safety checks
    if (current_vbat < MIN_ARMING_VOLTAGE) {
        led_set_status(0); // Red LED
        return false;
    }

    if (current_pitch > 10.0f || current_roll > 10.0f) {
        // Drone is not level, dangerous to arm
        return false;
    }

    current_state = STATE_ARMED;
    led_set_status(1); // Green LED
    return true;
}

/**
 * Emergency Disarm
 */
void disarm_drone() {
    current_state = STATE_DISARMED;
    pwm_write_motor(1, 0);
    pwm_write_motor(2, 0);
    pwm_write_motor(3, 0);
    pwm_write_motor(4, 0);
}

/**
 * Main Flight Control Loop (Runs at 1kHz)
 */
void flight_loop(float target_pitch, float target_throttle) {
    update_sensors();

    // 1. Critical Failure Detection (CRASH MODE)
    // BUG INTRODUCED: The absolute value is not checked for negative angles,
    // so if the drone flips upside down (-180 degrees), this logic fails to trigger.
    if (current_pitch > MAX_PITCH_ANGLE || current_roll > MAX_ROLL_ANGLE) {
        current_state = STATE_CRASH_MODE;
    }

    // 2. Battery Failsafe Detection
    if (current_vbat <= BATTERY_MIN_VOLTAGE) {
        if (current_state == STATE_FLYING) {
            current_state = STATE_FAILSAFE;
        }
    }

    // 3. State Machine Execution
    switch (current_state) {
        case STATE_DISARMED:
            // Motors must remain off
            pwm_write_motor(1, 0);
            pwm_write_motor(2, 0);
            pwm_write_motor(3, 0);
            pwm_write_motor(4, 0);
            break;

        case STATE_ARMED:
            // Motors idle spinning
            pwm_write_motor(1, 1000);
            pwm_write_motor(2, 1000);
            pwm_write_motor(3, 1000);
            pwm_write_motor(4, 1000);
            if (target_throttle > 1050) {
                current_state = STATE_FLYING;
            }
            break;

        case STATE_FLYING: {
            // Basic PID calculation for pitch
            error_pitch = target_pitch - current_pitch;
            integral_pitch += error_pitch;
            
            // BUG INTRODUCED: Integral windup is not capped.
            // If flying forward for a long time, integral_pitch grows infinitely.
            
            float pid_output = (Kp * error_pitch) + (Ki * integral_pitch);

            // Mix throttle and PID
            uint16_t m1 = target_throttle + pid_output;
            uint16_t m2 = target_throttle - pid_output;

            pwm_write_motor(1, m1);
            pwm_write_motor(2, m2);
            break;
        }

        case STATE_FAILSAFE:
            // Auto-descend slowly
            pwm_write_motor(1, FAILSAFE_THROTTLE);
            pwm_write_motor(2, FAILSAFE_THROTTLE);
            pwm_write_motor(3, FAILSAFE_THROTTLE);
            pwm_write_motor(4, FAILSAFE_THROTTLE);
            
            // If we've reached the ground (alt < 1.0m), disarm
            if (current_alt < 1.0f) {
                disarm_drone();
            }
            break;

        case STATE_CRASH_MODE:
            // Immediately cut all power to prevent motor burnout or injury
            disarm_drone();
            break;
    }
}
