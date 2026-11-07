// HOST SIMULATION ONLY. Runs one real firmware role per native process.
#include <Arduino.h>
#include <EEPROM.h>
#include <RadioLib.h>
#include <cstdio>
#include <cstdlib>
#include <deque>
#include <iostream>
#include <string>

namespace fake_radio { State state{}; }
namespace fake_spi { State state{}; }
SPIClass SPI;
EepromSpy EEPROM;
uint32_t host_ms = 0;
static std::deque<uint8_t> console_input;

extern "C" bool updi_uart_enabled() { return true; }
extern "C" bool updi_uart_rx_poll() { return !console_input.empty(); }
extern "C" uint8_t updi_uart_rx() {
    const auto byte = console_input.front();
    console_input.pop_front();
    return byte;
}
extern "C" void updi_uart_tx(uint8_t byte) {
    static bool line_start = true;
    if (line_start) std::cout << "[HOST_SIMULATION] ";
    std::cout << static_cast<char>(byte);
    line_start = byte == '\n';
}

void delay(unsigned ms) {
    host_ms += ms;
    // Simulate the external radio's TX-done interrupt, never protocol decisions.
    if (fake_radio::state.tx_data && fake_radio::state.sent_action) {
        fake_radio::state.sent_action();
    }
}

#ifdef LORA_RECEIVER_BOARD
#include "../src/receiver/main.cpp"
static void step() { loop(); }
static const char* state_name() { return armed_session ? "RX_READY" : "WAIT_SESSION"; }
#else
#include "../src/sender/lib/lora_rx.cpp"
iw::core::RingBuffer<4096> ringbuf;
TaskScheduler scheduler;
static void step() { scheduler.Loop(); }
static const char* state_name() {
    using lora_hello::State;
    switch (test_campaign.state()) {
        case State::TEST_IDLE: return "TEST_IDLE";
        case State::TEST_ARMED: return "TEST_ARMED";
        case State::TEST_RUNNING: return "TEST_RUNNING";
        case State::TEST_COMPLETED: return "TEST_COMPLETED";
        case State::TEST_FAILED: return "TEST_FAILED";
    }
    return "UNKNOWN";
}
#endif

static void pump() {
    static int reported_tx = 0;
    for (unsigned i = 0; i < 20; ++i) {
        step();
        delay(1);
        if (fake_radio::state.transmit_starts != reported_tx) {
            std::cout << "HOST_FRAME ";
            for (unsigned j = 0; j < fake_radio::state.tx_size; ++j) {
                std::printf("%02X", fake_radio::state.tx_data[j]);
            }
            std::cout << '\n';
            reported_tx = fake_radio::state.transmit_starts;
        }
    }
    std::cout << "HOST_READY\n" << std::flush;
}

int main() {
    SPI.reset();
    fake_radio::state.airtime_us = 50000;  // Synthetic timing; no RF measurement.
#ifdef LORA_RECEIVER_BOARD
    setup();
#else
    lora_rx_setup();
    lora_rx_hello_boot();
#endif
    pump();
    std::string command;
    while (std::getline(std::cin, command)) {
        if (command == "STATUS") {
            std::cout << "HOST_STATUS {\"state\":\"" << state_name()
                      << "\",\"tx\":" << fake_radio::state.transmit_starts
                      << ",\"eeprom_reads\":" << EEPROM.reads
                      << ",\"eeprom_writes\":" << EEPROM.writes << "}\n";
        } else if (command.compare(0, 3, "RX ") == 0) {
            const std::string hex = command.substr(3);
            if (hex.size() % 2 || hex.size() / 2 > 255) return 2;
            fake_radio::state.rx_size = hex.size() / 2;
            for (size_t i = 0; i < fake_radio::state.rx_size; ++i) {
                fake_radio::state.rx_data[i] =
                    static_cast<uint8_t>(std::stoul(hex.substr(i * 2, 2), nullptr, 16));
            }
            if (fake_radio::state.received_action) fake_radio::state.received_action();
        } else if (command.compare(0, 5, "TICK ") == 0) {
            host_ms += std::stoul(command.substr(5));
        } else if (command == "START") {
#ifndef LORA_RECEIVER_BOARD
            lora_rx_start_lora();
#endif
        } else {
            for (const auto byte : command) console_input.push_back(byte);
        }
        pump();
    }
    return 0;
}
