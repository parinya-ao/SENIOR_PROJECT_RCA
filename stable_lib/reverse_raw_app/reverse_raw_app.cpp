// Runs one reverse-direction raw observation; never retries an accepted
// command.

#include "reverse_raw_app.h"

#include <Arduino.h>
#include <RadioLib.h>
#include <SPI.h>
#include <arq_diagnostics.h>
#include <stdio.h>
#include <string.h>
#include <updi_uart.h>

#include "application_config.h"
#include "generated/arq_config.h"
#include "generated/board_ssot.h"

// Radio wiring belongs to the generated physical board, independent of DATA
// direction.
namespace reverse_raw_app {

static Module module(board_ssot.cs, board_ssot.irq, board_ssot.rst,
                     board_ssot.dio1, SPI,
                     SPISettings(ARQ_SPI_HZ, MSBFIRST, SPI_MODE0));
static SX1276 radio(&module);
// Configuration-owned raw bytes; the terminator is excluded from all RF
// comparisons.
static constexpr auto& kPayload = application_config::raw::kPayload;
static constexpr size_t kPayloadBytes = sizeof(kPayload) - 1;
// One-shot latches are foreground-only and are never reset by repeated
// commands.
static bool ready, active, used, attached;
// Millisecond origin bounds the single observation; matches is diagnostic only.
static uint32_t started, matches;
// Retains IRQ evidence before driver operations clear it.
static uint16_t observed_flags;
static uint8_t packet_events;
// Independent raw grammar; overflow discards through newline before recovery.
static char input_line[5 + 2 * kPayloadBytes + 1];
static uint8_t input_length;
static bool input_overflow;
// Captures register readback in the host auditor's existing address order.
static void RecordConfiguration(const char* name) {
  static const uint8_t addresses[] = {
      0x42, 0x01, 0x06, 0x07, 0x08, 0x09, 0x4d, 0x1d, 0x1e, 0x26, 0x20, 0x21,
      0x39, 0x33, 0x3b, 0x11, 0x40, 0x41, 0x0c, 0x31, 0x37, 0x24, 0x4b};
  char* out = arq::diagnostics::AcquireLine();
  if (!out) return;
  int n = snprintf(
      out, arq::diagnostics::kLineCapacity,
      "A t=%lu e=%s s=0 bytes=", static_cast<unsigned long>(millis()), name);
  const char hex[] = "0123456789ABCDEF";
  for (uint8_t address : addresses) {
    uint8_t v = module.SPIreadRegister(address);
    out[n++] = hex[v >> 4];
    out[n++] = hex[v & 15];
  }
  out[n++] = '\n';
  out[n] = 0;
}
// Retries the low byte if the high byte changes during a non-atomic SPI read.
static uint16_t ReadStableCounter(uint8_t address) {
  uint8_t high = module.SPIreadRegister(address),
          low = module.SPIreadRegister(address + 1);
  uint8_t again = module.SPIreadRegister(address);
  if (high != again) low = module.SPIreadRegister(address + 1);
  return (static_cast<uint16_t>(again) << 8) | low;
}
// Captures PHY counters before RX restoration can reset their observation
// window.
static void RecordObservation(const char* name, uint16_t flags) {
  uint16_t headers = ReadStableCounter(0x14), packets = ReadStableCounter(0x16);
  uint8_t mode = module.SPIreadRegister(1), stat = module.SPIreadRegister(0x18),
          hop = module.SPIreadRegister(0x1c);
  char* out = arq::diagnostics::AcquireLine();
  if (out)
    snprintf(out, arq::diagnostics::kLineCapacity,
             "A t=%lu e=%s s=0 rc=0 flags=%u headers=%u packets=%u mode=%u "
             "stat=%u hop=%u seen=%u overflow=%lu\n",
             static_cast<unsigned long>(millis()), name, flags, headers,
             packets, mode, stat, hop, observed_flags,
             static_cast<unsigned long>(arq::diagnostics::OverflowCount()));
}
// Queues one scalar observation; a full queue drops diagnostics only.
static void RecordEvent(const char* name, int16_t rc, uint16_t flags = 0) {
  char* out = arq::diagnostics::AcquireLine();
  if (out)
    snprintf(out, arq::diagnostics::kLineCapacity,
             "A t=%lu e=%s s=0 rc=%d flags=%u overflow=%lu\n",
             static_cast<unsigned long>(millis()), name, rc, flags,
             static_cast<unsigned long>(arq::diagnostics::OverflowCount()));
}
// Stops the observation in standby and records driver failure without retrying.
static void ParkRadio() {
  int16_t rc = radio.standby();
  active = false;
  if (rc) ready = false;
  RecordEvent("RAW_STANDBY", rc);
}
// Emits identity and readback without starting an RF operation.
static void ReportStatus() {
  char* out = arq::diagnostics::AcquireLine();
  if (out)
    snprintf(out, arq::diagnostics::kLineCapacity,
             "A t=%lu e=IDENTITY s=0 build=%s config=%s\n",
             static_cast<unsigned long>(millis()), LORA_BUILD_ID,
             ARQ_CONFIG_HASH);
  RecordEvent("RAW_STATUS", ready ? 0 : -1);
  RecordConfiguration("RAW_CONFIG");
}
// Matches only the existing uppercase SEND spelling for the configured raw
// bytes.
static bool IsPayloadCommand(const char* text) {
  if (strncmp(text, "SEND ", 5) || strlen(text + 5) != 2 * kPayloadBytes)
    return false;
  constexpr char kHexDigits[] = "0123456789ABCDEF";
  for (size_t i = 0; i < kPayloadBytes; ++i) {
    const uint8_t value = static_cast<uint8_t>(kPayload[i]);
    if (text[5 + 2 * i] != kHexDigits[value >> 4] ||
        text[6 + 2 * i] != kHexDigits[value & 15])
      return false;
  }
  return true;
}
// Starts at most one role-specific operation; status and stop remain available.
static void ExecuteCommand(const char* text) {
  if (!strcmp(text, "STATUS")) {
    ReportStatus();
    return;
  }
  if (!strcmp(text, "X")) {
    used = true;
    ParkRadio();
    return;
  }
  if (!ready || active || used) {
    RecordEvent("RAW_REJECT", -1);
    return;
  }
#if defined(LORA_ROLE_RECEIVER)
  if (!IsPayloadCommand(text)) {
    RecordEvent("RAW_REJECT", -1);
    return;
  }
  RecordConfiguration("RAW_TX_PRE");
  used = true;
  int16_t rc = radio.startTransmit(reinterpret_cast<const uint8_t*>(kPayload),
                                   kPayloadBytes);
  active = !rc;
  started = millis();
  RecordEvent("RAW_TX", rc, kPayloadBytes);
  RecordConfiguration("RAW_TX_STATE");
  if (rc) {
    radio.finishTransmit();
    ParkRadio();
  }
#else
  if (strcmp(text, "RX")) {
    RecordEvent("RAW_REJECT", -1);
    return;
  }
  used = true;
  int16_t rc = radio.startReceive();
  active = !rc;
  started = millis();
  if (!rc) {
    RecordConfiguration("RAW_RX_ACTIVE");
    RecordObservation("RAW_RX_READY", radio.getIRQFlags());
  } else
    RecordEvent("RAW_RX_READY", rc);
  if (rc) ParkRadio();
#endif
}
// Accumulates one line and rejects overflowed commands at their newline.
static void FeedCommandByte(char c) {
  if (c == '\r') return;
  if (c == '\n') {
    input_line[input_length] = 0;
    if (input_overflow)
      RecordEvent("RAW_REJECT", -1);
    else
      ExecuteCommand(input_line);
    input_length = 0;
    input_overflow = false;
    return;
  }
  if (input_length >= sizeof(input_line) - 1) {
    input_overflow = true;
    return;
  }
  input_line[input_length++] = c;
}
// Initializes generated wiring and PHY, then parks until an explicit command.
void Initialize() {
  board_ssot_init();
  delay(application_config::startup::kRadioSettleMs);
  if (!SPI.swap(ARQ_SPI_ROUTE)) return;
  SPI.begin();
  radio.reset();
  int16_t rc = radio.begin(ARQ_FREQUENCY_HZ / 1000000.0f, ARQ_BANDWIDTH_KHZ,
                           ARQ_SPREADING_FACTOR, ARQ_CODING_RATE, ARQ_SYNC_WORD,
                           ARQ_TX_POWER_DBM, ARQ_PREAMBLE_SYMBOLS, 0);
  // RadioLib leaves the reset-default LF bank selected; clear only bit 3 for
  // 915 MHz.
  if (!rc) rc = module.SPIsetRegValue(RADIOLIB_SX127X_REG_OP_MODE, 0, 3, 3);
  if (!rc) rc = radio.setOutputPower(ARQ_TX_POWER_DBM, false);
  if (!rc) rc = radio.explicitHeader();
  if (!rc) rc = radio.setCRC(ARQ_CRC_ENABLED);
  if (!rc) rc = radio.invertIQ(ARQ_IQ_INVERTED);
  if (!rc) rc = radio.standby();
  ready = !rc;
}
// Services commands and one-shot IRQ/deadline handling before nonblocking
// logging.
void Poll() {
  if (updi_uart_enabled() && !attached) ReportStatus();
  attached = updi_uart_enabled();
  if (updi_uart_rx_poll()) FeedCommandByte(updi_uart_rx());
  if (active) {
    uint16_t flags = radio.getIRQFlags();
    observed_flags |= flags;
#if defined(LORA_ROLE_RECEIVER)
    bool done = flags & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_TX_DONE;
    if (done || millis() - started >= ARQ_TX_MS) {
      int16_t rc = radio.finishTransmit();
      RecordEvent(done ? "RAW_TX_DONE" : "RAW_TX_TIMEOUT", rc, flags);
      ParkRadio();
    }
#else
    if (module.SPIreadRegister(1) % 8 != 5) {
      RecordEvent("RAW_RADIO_ERROR", -1, flags);
      ParkRadio();
    }
    if (active && (flags & 0x10) && !(observed_flags & 0x100)) {
      observed_flags |= 0x100;
      RecordObservation("RAW_VALID_HEADER", flags);
    }
    if (active && (flags & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_RX_DONE)) {
      RecordObservation("RAW_RX_DONE", flags);
      ++packet_events;
      int16_t rc = radio.standby();
      size_t length = radio.getPacketLength();
      uint8_t bytes[32] = {0};
      if (!rc) rc = radio.readData(bytes, sizeof bytes);
      bool valid =
          !rc && !(flags & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_PAYLOAD_CRC_ERROR) &&
          length == kPayloadBytes && !memcmp(bytes, kPayload, kPayloadBytes);
      if (valid) ++matches;
      char* out = arq::diagnostics::AcquireLine();
      if (out) {
        int n =
            snprintf(out, arq::diagnostics::kLineCapacity,
                     "A t=%lu e=RAW_RX s=0 rc=%d flags=%u len=%u match=%u "
                     "rssi=%d snr=%d bytes=",
                     static_cast<unsigned long>(millis()), rc, flags,
                     static_cast<unsigned>(length), valid,
                     (int)(radio.getRSSI() * 100), (int)(radio.getSNR() * 100));
        const char hex[] = "0123456789ABCDEF";
        for (size_t i = 0; i < length && i < sizeof bytes; i++) {
          out[n++] = hex[bytes[i] >> 4];
          out[n++] = hex[bytes[i] & 15];
        }
        out[n++] = '\n';
        out[n] = 0;
      }
      if (valid ||
          packet_events >= application_config::raw::kPacketEventLimit ||
          (rc && rc != RADIOLIB_ERR_CRC_MISMATCH))
        ParkRadio();
      else {
        rc = radio.startReceive();
        if (rc) {
          ready = false;
          ParkRadio();
        }
      }
    }
    if (active &&
        millis() - started >= application_config::raw::kReceiveTimeoutMs) {
      RecordObservation("RAW_RX_TIMEOUT", flags);
      ParkRadio();
    }
#endif
  }
  arq::diagnostics::FlushByte();
}

}  // namespace reverse_raw_app
