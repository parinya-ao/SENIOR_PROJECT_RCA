#pragma once

#include <Arduino.h>
#include <avr/wdt.h>
#include <stddef.h>
#include <stdint.h>

#include "application_config.h"
#include "generated/lora_shared_config.h"
#include "generated/radio_915_config.h"

namespace GatewaySSOT {

struct Pins {
    static constexpr uint8_t LED1 = PIN_PA5;
    static constexpr uint8_t LED2 = PIN_PA4;
    static constexpr uint8_t LED_ON_LEVEL = LOW;
    static constexpr uint8_t LED_OFF_LEVEL = HIGH;
    static constexpr uint8_t ANALOG_IN_0 = PIN_PA7;
    static constexpr uint8_t ANALOG_IN_1 = PIN_PA6;
    static constexpr uint8_t DEBUG_RX = PIN_PA1;
    static constexpr uint8_t DEBUG_TX = PIN_PA0;
    static constexpr uint8_t HOST_INT = PIN_PD1;
    static constexpr uint8_t LORA_CS = LORA_PIN_CS;
    static constexpr uint8_t LORA_RST = LORA_PIN_RST;
    static constexpr uint8_t LORA_IRQ = LORA_PIN_IRQ;
    static constexpr uint8_t LORA_DIO1 = LORA_PIN_DIO1;
};

struct Comm {
    static constexpr uint32_t DEBUG_BAUD_RATE = application_config::gateway::kUartBaud;
    static constexpr bool ENABLE_I2C_WIRE = true;
    static constexpr uint8_t I2C_ADDRESS_BASE = 0x20;
    static constexpr uint8_t GATEWAY_DEFAULT_ADDR = LORA_SENDER_ADDRESS;
    static constexpr uint8_t GATEWAY_ANYCAST_ADDR = 0xFF;
    static constexpr uint8_t AIR_CONFIG_NODE_ADDR = 0xFE;
    static constexpr uint8_t I2C_ADDRESS_STRAP_SHIFT = 1;
};

struct Memory {
    static constexpr size_t SHARED_RINGBUF_BYTES =
        application_config::gateway::kResultBufferBytes;
    static constexpr size_t I2C_MAILBOX_BYTES = 32;
    static_assert((SHARED_RINGBUF_BYTES & (SHARED_RINGBUF_BYTES - 1)) == 0,
                  "SHARED_RINGBUF_BYTES must be a power of two.");
};

struct AdcTemp {
    static constexpr uint8_t VREF_SETTING = VREF_REFSEL_2V048_gc;
    static constexpr uint8_t PRESCALER_SETTING = ADC_PRESC_DIV4_gc;
    static constexpr uint8_t MUX_TEMP_CHANNEL = ADC_MUXPOS_TEMPSENSE_gc;
    static constexpr uint8_t INIT_DELAY_SETTING = ADC_INITDLY_DLY32_gc;
    static constexpr uint8_t CTRLA_ENABLE_12BIT =
        ADC_ENABLE_bm | ADC_RESSEL_12BIT_gc;

    static constexpr uint8_t TEMP_SAMPLE_CYCLES = 50;
    static constexpr uint16_t ADC_MAX_COUNTS = 4096;
    static constexpr uint32_t ROUNDING_OFFSET = 0x0800UL;
    static constexpr uint8_t FIXED_POINT_SHIFT = 12;
    static constexpr int16_t KELVIN_TO_CELSIUS = 273;
    static constexpr uint32_t TEMP_READ_INTERVAL_MS = 1000;
};

struct Tasks {
    static constexpr bool ENABLE_HEARTBEAT_TASK = false;
    static constexpr const char* HEARTBEAT_NAME = "Heartbeat";
    static constexpr uint32_t HEARTBEAT_ON_MS = 50;
    static constexpr uint32_t HEARTBEAT_OFF_MS = 1950;
    static constexpr uint32_t HEARTBEAT_PERIOD_MS =
        HEARTBEAT_ON_MS + HEARTBEAT_OFF_MS;
    static constexpr uint32_t LED1_TOGGLE_INTERVAL_MS = 1000;
    static constexpr uint32_t LORA_TX_LED_TOGGLE_INTERVAL_MS = 100;
    static constexpr uint32_t I2C_RESET_SETTLE_MS = 50;

    static_assert(HEARTBEAT_PERIOD_MS == 2000,
                  "Heartbeat cycle must remain 2000 ms.");
};

// Example wiring retained only for the excluded SX1262 experiment in
// src/sender/main.cpp. It is not the Gateway RFM95/98 board pin map.
struct ExcludedSx1262Experiment {
    static constexpr uint8_t NSS_PIN = 10;
    static constexpr uint8_t DIO1_PIN = 2;
    static constexpr uint8_t RESET_PIN = 3;
    static constexpr uint8_t BUSY_PIN = 9;
    static constexpr uint8_t PACKET_COUNT = 3;
    static constexpr uint8_t PACKET_BYTES = 5;
    static constexpr uint32_t ERROR_RETRY_DELAY_MS = 1000;
    static constexpr uint32_t PACKET_GAP_MS = 500;
    static constexpr uint32_t POST_SEND_DELAY_MS = 1000;
};

struct System {
    static constexpr bool ENABLE_ESPCOMM = true;
    static constexpr bool ENABLE_LORA_RX = true;
    static constexpr bool ENABLE_WATCHDOG = true;
    static constexpr uint8_t WDT_TIMEOUT_PERIOD = WDT_PERIOD_2KCLK_gc;
};

} // namespace GatewaySSOT
