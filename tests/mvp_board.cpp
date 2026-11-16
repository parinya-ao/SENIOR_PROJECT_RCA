// HOST SIMULATION ONLY. Runs one real firmware role per native process.
#include <Arduino.h>
#include <RadioLib.h>

#include <cstdio>
#include <cstdlib>
#include <deque>
#include <iostream>
#include <string>

namespace fake_radio {
State state{};
}
namespace fake_spi {
State state{};
}
SPIClass SPI;
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
  if (fake_radio::state.tx_data && fake_radio::state.sent_action &&
      fake_radio::state.transmit_starts > fake_radio::state.finish_transmits) {
    fake_radio::state.irq_flags = 8;
    fake_radio::state.sent_action();
  }
}

#ifdef LORA_ROLE_RECEIVER
#define LORA_APP_LEGACY_RECEIVER 1
#include "../stable_lib/legacy_receiver/legacy_receiver.cpp"
static void step() { legacy_receiver::Poll(); }
static const char* state_name() {
  return radio_ready ? "RX_READY" : "RADIO_INIT_FAILED";
}
#else
#define LORA_APP_GATEWAY 1
#include "../stable_lib/gateway_app/lora_rx.cpp"
namespace gateway_app {
iw::core::RingBuffer<application_config::gateway::kResultBufferBytes> ringbuf;
TaskScheduler scheduler;
}  // namespace gateway_app
static void step() { gateway_app::scheduler.Loop(); }
static const char* state_name() {
  switch (transport.state()) {
    case decltype(transport)::State::kRxWait:
      return "RX_WAIT";
    case decltype(transport)::State::kTxData:
      return "TX_DATA";
    case decltype(transport)::State::kWaitResponse:
      return "WAIT_ACK";
    case decltype(transport)::State::kRetryPending:
      return "RETRY_PENDING";
    case decltype(transport)::State::kTxResponse:
      return "TX_RESPONSE";
    case decltype(transport)::State::kComplete:
      return "COMPLETE";
    case decltype(transport)::State::kFailed:
      return "FAILED";
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
        std::printf("%02X", fake_radio::state.tx_copy[j]);
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
#ifdef LORA_ROLE_RECEIVER
  legacy_receiver::Initialize();
#else
  RegisterRadioTask();
  StartHelloTestIfEnabled();
#endif
  pump();
  std::string command;
  while (std::getline(std::cin, command)) {
    if (command == "STATUS") {
      std::cout << "HOST_STATUS {\"state\":\"" << state_name()
                << "\",\"tx\":" << fake_radio::state.transmit_starts << "}\n";
    } else if (command.compare(0, 3, "RX ") == 0) {
      const std::string hex = command.substr(3);
      if (hex.size() % 2 || hex.size() / 2 > 255) return 2;
      fake_radio::state.rx_size = hex.size() / 2;
      for (size_t i = 0; i < fake_radio::state.rx_size; ++i) {
        fake_radio::state.rx_data[i] =
            static_cast<uint8_t>(std::stoul(hex.substr(i * 2, 2), nullptr, 16));
      }
      fake_radio::state.irq_flags = 0x40;
      if (fake_radio::state.received_action)
        fake_radio::state.received_action();
    } else if (command.compare(0, 5, "TICK ") == 0) {
      host_ms += std::stoul(command.substr(5));
    } else if (command == "START") {
#ifndef LORA_ROLE_RECEIVER
      StartRadioTransaction();
#endif
    } else {
      for (const auto byte : command) console_input.push_back(byte);
    }
    pump();
  }
  return 0;
}
