// No repository-wide license is declared; existing rights are unchanged.

// Runs bounded raw radio bring-up; this is independent of the ARQ wire
// protocol.

#include <Arduino.h>
#include <RadioLib.h>
#include <SPI.h>
#include <string.h>
#include <updi_uart.h>

#include "application_config.h"
#include "generated/arq_config.h"
#include "generated/lora_shared_config.h"
#include "generated/radio_915_config.h"
#if defined(LORA_ROLE_RECEIVER)
#include "generated/lora_receiver_board.h"
#endif

// Raw diagnostic bytes are configuration-owned; exclude their NUL on air.
static constexpr auto& kPayload = application_config::raw::kPayload;
static constexpr size_t kPayloadBytes = sizeof(kPayload) - 1;
// Static library objects retain wiring; no driver begin occurs before setup.
static Module module(LORA_PIN_CS, LORA_PIN_IRQ, LORA_PIN_RST, LORA_PIN_DIO1,
                     SPI, SPISettings(ARQ_SPI_HZ, MSBFIRST, SPI_MODE0));
static SX1276 radio(&module);
// Indexed startup observations are retained for a later attached monitor.
static const char* const kStartupStages[] = {
    "BOOT",        "GPIO_INIT",          "RADIO_POWER_ENABLE", "SPI1_INIT",
    "RADIO_RESET", "RADIO_VERSION_READ", "RADIO_INIT",         "RX_READY"};
static int16_t stage_status[8];
static uint8_t stage_count,
    versions[application_config::startup::kVersionProbeAttempts], version_count,
    reset_flags;
// Foreground lifecycle flags distinguish radio readiness from host attachment.
static bool ready, attached, stopped, transmitting;
// Observation counters and modulo-millisecond origins never drive packet
// validity.
static uint32_t attempts, received, matches, crc_errors, tx_started,
    last_attempt;
// Batch deadline bounds diagnostics even if the host disconnects mid-line.
static uint32_t log_started;
static bool log_ok;

// Starts a bounded diagnostic batch; these names match the existing debug API.
void debug_init() {
  log_started = millis();
  log_ok = updi_uart_enabled();
}

// Sends text only while per-byte and batch deadlines allow; never waits
// forever.
void debug_write(const char* text) {
  for (; *text && log_ok; ++text) {
    const uint32_t started = millis();
    while (_SFR_MEM8(0x0f19) && updi_uart_enabled() &&
           millis() - started < application_config::raw::kLogByteTimeoutMs &&
           millis() - log_started <
               application_config::raw::kLogBatchTimeoutMs) {
    }
    if (!updi_uart_enabled() || _SFR_MEM8(0x0f19) ||
        millis() - log_started >= application_config::raw::kLogBatchTimeoutMs) {
      log_ok = false;
      return;
    }
    _SFR_MEM8(0x0f18) = *text;
  }
}

// Formats a signed decimal value in a fixed local buffer.
void debug_write_int(int32_t value) {
  char text[12];
  ltoa(value, text, 10);
  debug_write(text);
}

// Emits exactly two uppercase hexadecimal digits.
void debug_write_hex(uint8_t value) {
  const char digits[] = "0123456789ABCDEF";
  char text[] = {digits[value >> 4], digits[value & 15], 0};
  debug_write(text);
}

// Emits the existing two-decimal representation without heavy float printf
// support.
void debug_write_float(float value) {
  int32_t scaled =
      static_cast<int32_t>(value * 100 + (value < 0 ? -0.5f : 0.5f));
  if (scaled < 0) {
    debug_write("-");
    scaled = -scaled;
  }
  debug_write_int(scaled / 100);
  debug_write(".");
  if (scaled % 100 < 10) debug_write("0");
  debug_write_int(scaled % 100);
}

// Starts a role-prefixed batch without altering captured radio state.
static void StartLogLine(const char* event) {
  debug_init();
#if defined(LORA_ROLE_RECEIVER)
  debug_write("[MVP RECEIVER] ");
#else
  debug_write("[MVP SENDER] ");
#endif
  debug_write(event);
}

// Appends a named signed field to the current diagnostic batch.
static void WriteLogField(const char* name, int32_t value) {
  debug_write(name);
  debug_write_int(value);
}

// Retains the next startup result in the fixed stage order listed above.
static void RecordStartupStage(int16_t status) {
  stage_status[stage_count++] = status;
}

// DxCore has already saved RSTFR in GPR0 before clearing it in .init3.
void onPreMain() { _PROTECTED_WRITE(CPUINT.CTRLA, 0); }

// Sequences board isolation, SPI, register probes and the existing PHY.
void setup() {
  reset_flags = GPR_GPR0;
  RecordStartupStage(0);
#if defined(LORA_ROLE_RECEIVER)
  digitalWrite(LORA_PIN_ENABLE, !LORA_POWER_ACTIVE_LEVEL);
  pinMode(LORA_PIN_ENABLE, OUTPUT);
  digitalWrite(LORA_PIN_GPS_ENABLE, HIGH);
  pinMode(LORA_PIN_GPS_ENABLE, OUTPUT);
  digitalWrite(LORA_PIN_SD_ENABLE, HIGH);
  pinMode(LORA_PIN_SD_ENABLE, OUTPUT);
  digitalWrite(LORA_PIN_SD_CS, HIGH);
  pinMode(LORA_PIN_SD_CS, OUTPUT);
  pinMode(LORA_PIN_SD_DETECT, INPUT);
#endif
  pinMode(LORA_PIN_RST, INPUT);
  pinMode(LORA_PIN_IRQ, INPUT);
  pinMode(LORA_PIN_DIO1, INPUT);
  RecordStartupStage(0);
#if defined(LORA_ROLE_RECEIVER)
  digitalWrite(LORA_PIN_ENABLE, LORA_POWER_ACTIVE_LEVEL);
#endif
  delay(application_config::startup::kRadioSettleMs);
  RecordStartupStage(0);
  digitalWrite(LORA_PIN_CS, HIGH);
  pinMode(LORA_PIN_CS, OUTPUT);
  if (!SPI.swap(LORA_SPI_ROUTE)) {
    RecordStartupStage(-1);
    return;
  }
  SPI.begin();
  RecordStartupStage(0);
  radio.reset();
  RecordStartupStage(0);
  bool supported = false;
  for (uint8_t i = 0; i < application_config::startup::kVersionProbeAttempts;
       ++i) {
    SPI.beginTransaction(SPISettings(ARQ_SPI_HZ, MSBFIRST, SPI_MODE0));
    digitalWrite(LORA_PIN_CS, LOW);
    SPI.transfer(0x42);
    uint8_t version = SPI.transfer(0);
    digitalWrite(LORA_PIN_CS, HIGH);
    SPI.endTransaction();
    versions[version_count++] = version;
    supported = version == RADIOLIB_SX1278_CHIP_VERSION ||
                version == RADIOLIB_SX1278_CHIP_VERSION_ALT ||
                version == RADIOLIB_SX1278_CHIP_VERSION_RFM9X;
    if (supported) break;
    delay(application_config::startup::kRadioSettleMs);
  }
  RecordStartupStage(supported ? 0 : RADIOLIB_ERR_CHIP_NOT_FOUND);
  if (!supported) return;
  int16_t status = radio.begin(HELLO_RF_FREQUENCY_MHZ, HELLO_RF_BANDWIDTH_KHZ,
                               HELLO_RF_SPREADING_FACTOR, HELLO_RF_CODING_RATE,
                               HELLO_RF_SYNC_WORD, HELLO_RF_TX_POWER_DBM,
                               HELLO_RF_PREAMBLE_SYMBOLS, 0);
  if (!status) status = radio.setOutputPower(HELLO_RF_TX_POWER_DBM, false);
  if (!status) status = radio.explicitHeader();
  if (!status) status = radio.setCRC(HELLO_RF_CRC_ENABLED);
  if (!status) status = radio.invertIQ(HELLO_RF_IQ_INVERTED);
  RecordStartupStage(status);
  if (status) return;
#if defined(LORA_ROLE_RECEIVER)
  status = radio.startReceive();
  RecordStartupStage(status);
#endif
  ready = status == RADIOLIB_ERR_NONE;
  last_attempt = millis() - application_config::raw::kTransmitIntervalMs;
}

// Replays captured startup evidence and current counters for an attached
// reader.
static void ReportStartup() {
  for (uint8_t i = 0; i < stage_count; ++i) {
    StartLogLine(kStartupStages[i]);
    WriteLogField(" rc=", stage_status[i]);
    if (i == 0) {
      debug_write(" reset_flags=0x");
      debug_write_hex(reset_flags);
    }
    debug_write("\n");
  }
  for (uint8_t i = 0; i < version_count; ++i) {
    StartLogLine("REG_VERSION");
    WriteLogField(" try=", i + 1);
    debug_write(" value=0x");
    debug_write_hex(versions[i]);
    debug_write("\n");
  }
  StartLogLine(
      "PROFILE 915MHz BW125 SF7 CR4/5 SYNC=0x12 PREAMBLE=8 EXPLICIT CRC "
      "NORMAL_IQ PA_BOOST=2dBm\n");
  StartLogLine("COUNTERS");
  WriteLogField(" tx=", attempts);
  WriteLogField(" rx=", received);
  WriteLogField(" match=", matches);
  WriteLogField(" crc_errors=", crc_errors);
  debug_write("\n");
}

// Advances one raw RX or bounded TX step; only the explicit stop command stops
// tests.
void loop() {
  bool enabled = updi_uart_enabled();
  if (enabled && !attached) ReportStartup();
  attached = enabled;
  if (updi_uart_rx_poll() && updi_uart_rx() == 'X') {
    stopped = true;
    StartLogLine("STOP");
    WriteLogField(" tx=", attempts);
    debug_write("\n");
  }
  if (!ready) {
    delay(1);
    return;
  }
#if defined(LORA_ROLE_RECEIVER)
  const uint16_t irq = radio.getIRQFlags();
  if (!(irq & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_RX_DONE)) {
    delay(1);
    return;
  }
  int16_t status = radio.standby();
  if (status) {
    ready = false;
    StartLogLine("RX_STANDBY");
    WriteLogField(" rc=", status);
    debug_write("\n");
    return;
  }
  const size_t length = radio.getPacketLength();
  uint8_t bytes[32] = {};
  const size_t captured = length < sizeof(bytes) ? length : sizeof(bytes);
  // RadioLib len=0 means read the whole FIFO; use capacity even for empty
  // packets.
  status = radio.readData(bytes, sizeof(bytes));
  const float rssi = radio.getRSSI(), snr = radio.getSNR();
  ++received;
  if (status == RADIOLIB_ERR_CRC_MISMATCH) ++crc_errors;
  const bool match =
      status == RADIOLIB_ERR_NONE &&
      !(irq & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_PAYLOAD_CRC_ERROR) &&
      length == kPayloadBytes && memcmp(bytes, kPayload, kPayloadBytes) == 0;
  if (match) ++matches;
  const int16_t restart = radio.startReceive();
  ready = restart == RADIOLIB_ERR_NONE;
  StartLogLine("RX");
  WriteLogField(" count=", received);
  WriteLogField(" len=", length);
  WriteLogField(" rc=", status);
  WriteLogField(" irq=", irq);
  WriteLogField(" restart=", restart);
  WriteLogField(" match=", matches);
  WriteLogField(" crc_errors=", crc_errors);
  debug_write(" rssi=");
  debug_write_float(rssi);
  debug_write(" snr=");
  debug_write_float(snr);
  debug_write(match ? " PASS bytes=" : " REJECT bytes=");
  for (size_t i = 0; i < captured; ++i) debug_write_hex(bytes[i]);
  debug_write("\n");
#else
  if (transmitting) {
    const uint16_t irq = radio.getIRQFlags();
    const bool done = irq & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_TX_DONE;
    if (!done && millis() - tx_started < LORA_TX_TIMEOUT_MS) {
      delay(1);
      return;
    }
    const int16_t cleanup = radio.finishTransmit();
    transmitting = false;
    if (cleanup) ready = false;
    StartLogLine(done ? "TX_DONE" : "TX_TIMEOUT");
    WriteLogField(" attempt=", attempts);
    WriteLogField(" cleanup=", cleanup);
    WriteLogField(" irq=", irq);
    debug_write("\n");
    return;
  }
  if (stopped ||
      millis() - last_attempt < application_config::raw::kTransmitIntervalMs) {
    delay(1);
    return;
  }
  last_attempt = millis();
  ++attempts;
  const int16_t status = radio.startTransmit(
      reinterpret_cast<const uint8_t*>(kPayload), kPayloadBytes);
  tx_started = millis();
  transmitting = status == RADIOLIB_ERR_NONE;
  const int16_t cleanup = status ? radio.finishTransmit() : 0;
  if (cleanup) ready = false;
  StartLogLine("TX_START");
  WriteLogField(" attempt=", attempts);
  WriteLogField(" len=", kPayloadBytes);
  WriteLogField(" rc=", status);
  WriteLogField(" cleanup=", cleanup);
  debug_write("\n");
#endif
}
