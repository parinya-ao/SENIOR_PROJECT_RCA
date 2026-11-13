#include <Arduino.h>
#include <SPI.h>
#include <RadioLib.h>
#include <updi_uart.h>
#include <string.h>
#include "generated/radio_915_config.h"
#if defined(LORA_ROLE_RECEIVER)
#include "generated/lora_receiver_board.h"
#endif

static const uint8_t payload[] = {'H','e','l','l','o',' ','W','o','r','l','d'};
static_assert(sizeof(payload) == 11, "raw payload must be exactly eleven bytes");
static Module module(LORA_PIN_CS, LORA_PIN_IRQ, LORA_PIN_RST, LORA_PIN_DIO1,
                     SPI, SPISettings(1000000, MSBFIRST, SPI_MODE0));
static SX1276 radio(&module);
static const char* const stages[] = {"BOOT", "GPIO_INIT", "RADIO_POWER_ENABLE",
    "SPI1_INIT", "RADIO_RESET", "RADIO_VERSION_READ", "RADIO_INIT", "RX_READY"};
static int16_t stage_status[8];
static uint8_t stage_count, versions[3], version_count, reset_flags;
static bool ready, attached, stopped, transmitting;
static uint32_t attempts, received, matches, crc_errors, tx_started, last_attempt;
static uint32_t log_started;
static bool log_ok;

void debug_init() {
    log_started = millis();
    log_ok = updi_uart_enabled();
}

void debug_write(const char* text) {
    for (; *text && log_ok; ++text) {
        const uint32_t started = millis();
        while (_SFR_MEM8(0x0f19) && updi_uart_enabled() &&
               millis() - started < 100 && millis() - log_started < 3000) {}
        if (!updi_uart_enabled() || _SFR_MEM8(0x0f19) || millis() - log_started >= 3000) {
            log_ok = false;
            return;
        }
        _SFR_MEM8(0x0f18) = *text;
    }
}

void debug_write_int(int32_t value) {
    char text[12];
    ltoa(value, text, 10);
    debug_write(text);
}

void debug_write_hex(uint8_t value) {
    const char digits[] = "0123456789ABCDEF";
    char text[] = {digits[value >> 4], digits[value & 15], 0};
    debug_write(text);
}

void debug_write_float(float value) {
    int32_t scaled = static_cast<int32_t>(value * 100 + (value < 0 ? -0.5f : 0.5f));
    if (scaled < 0) { debug_write("-"); scaled = -scaled; }
    debug_write_int(scaled / 100);
    debug_write(".");
    if (scaled % 100 < 10) debug_write("0");
    debug_write_int(scaled % 100);
}

static void line(const char* event) {
    debug_init();
#if defined(LORA_ROLE_RECEIVER)
    debug_write("[MVP RECEIVER] ");
#else
    debug_write("[MVP SENDER] ");
#endif
    debug_write(event);
}

static void field(const char* name, int32_t value) {
    debug_write(name);
    debug_write_int(value);
}

static void stage(int16_t status) { stage_status[stage_count++] = status; }

// DxCore has already saved RSTFR in GPR0 before clearing it in .init3.
void onPreMain() { _PROTECTED_WRITE(CPUINT.CTRLA, 0); }

void setup() {
    reset_flags = GPR_GPR0;
    stage(0);
#if defined(LORA_ROLE_RECEIVER)
    digitalWrite(LORA_PIN_ENABLE, HIGH);
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
    stage(0);
#if defined(LORA_ROLE_RECEIVER)
    digitalWrite(LORA_PIN_ENABLE, LOW);
#endif
    delay(10);
    stage(0);
    digitalWrite(LORA_PIN_CS, HIGH);
    pinMode(LORA_PIN_CS, OUTPUT);
    if (!SPI.swap(LORA_SPI_ROUTE)) { stage(-1); return; }
    SPI.begin();
    stage(0);
    radio.reset();
    stage(0);
    bool supported = false;
    for (uint8_t i = 0; i < 3; ++i) {
        SPI.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE0));
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
        delay(10);
    }
    stage(supported ? 0 : RADIOLIB_ERR_CHIP_NOT_FOUND);
    if (!supported) return;
    int16_t status = radio.begin(915.0f, 125.0f, 7, 5, 0x12, 2, 8, 0);
    if (!status) status = radio.setOutputPower(2, false);
    if (!status) status = radio.explicitHeader();
    if (!status) status = radio.setCRC(true);
    if (!status) status = radio.invertIQ(false);
    stage(status);
    if (status) return;
#if defined(LORA_ROLE_RECEIVER)
    status = radio.startReceive();
    stage(status);
#endif
    ready = status == RADIOLIB_ERR_NONE;
    last_attempt = millis() - 3000;
}

static void startup_log() {
    for (uint8_t i = 0; i < stage_count; ++i) {
        line(stages[i]); field(" rc=", stage_status[i]);
        if (i == 0) { debug_write(" reset_flags=0x"); debug_write_hex(reset_flags); }
        debug_write("\n");
    }
    for (uint8_t i = 0; i < version_count; ++i) {
        line("REG_VERSION"); field(" try=", i + 1);
        debug_write(" value=0x"); debug_write_hex(versions[i]); debug_write("\n");
    }
    line("PROFILE 915MHz BW125 SF7 CR4/5 SYNC=0x12 PREAMBLE=8 EXPLICIT CRC NORMAL_IQ PA_BOOST=2dBm\n");
    line("COUNTERS"); field(" tx=", attempts); field(" rx=", received);
    field(" match=", matches); field(" crc_errors=", crc_errors); debug_write("\n");
}

void loop() {
    bool enabled = updi_uart_enabled();
    if (enabled && !attached) startup_log();
    attached = enabled;
    if (updi_uart_rx_poll() && updi_uart_rx() == 'X') {
        stopped = true;
        line("STOP"); field(" tx=", attempts); debug_write("\n");
    }
    if (!ready) { delay(1); return; }
#if defined(LORA_ROLE_RECEIVER)
    const uint16_t irq = radio.getIRQFlags();
    if (!(irq & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_RX_DONE)) { delay(1); return; }
    int16_t status = radio.standby();
    if (status) { ready = false; line("RX_STANDBY"); field(" rc=", status); debug_write("\n"); return; }
    const size_t length = radio.getPacketLength();
    uint8_t bytes[32] = {};
    const size_t captured = length < sizeof(bytes) ? length : sizeof(bytes);
    // RadioLib len=0 means read the whole FIFO; use capacity even for empty packets.
    status = radio.readData(bytes, sizeof(bytes));
    const float rssi = radio.getRSSI(), snr = radio.getSNR();
    ++received;
    if (status == RADIOLIB_ERR_CRC_MISMATCH) ++crc_errors;
    const bool match = status == RADIOLIB_ERR_NONE &&
        !(irq & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_PAYLOAD_CRC_ERROR) &&
        length == sizeof(payload) && memcmp(bytes, payload, sizeof(payload)) == 0;
    if (match) ++matches;
    const int16_t restart = radio.startReceive();
    ready = restart == RADIOLIB_ERR_NONE;
    line("RX"); field(" count=", received); field(" len=", length);
    field(" rc=", status); field(" irq=", irq); field(" restart=", restart);
    field(" match=", matches); field(" crc_errors=", crc_errors);
    debug_write(" rssi="); debug_write_float(rssi);
    debug_write(" snr="); debug_write_float(snr);
    debug_write(match ? " PASS bytes=" : " REJECT bytes=");
    for (size_t i = 0; i < captured; ++i) debug_write_hex(bytes[i]);
    debug_write("\n");
#else
    if (transmitting) {
        const uint16_t irq = radio.getIRQFlags();
        const bool done = irq & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_TX_DONE;
        if (!done && millis() - tx_started < 3000) { delay(1); return; }
        const int16_t cleanup = radio.finishTransmit();
        transmitting = false;
        if (cleanup) ready = false;
        line(done ? "TX_DONE" : "TX_TIMEOUT"); field(" attempt=", attempts);
        field(" cleanup=", cleanup); field(" irq=", irq); debug_write("\n");
        return;
    }
    if (stopped || millis() - last_attempt < 3000) { delay(1); return; }
    last_attempt = millis();
    ++attempts;
    const int16_t status = radio.startTransmit(payload, sizeof(payload));
    tx_started = millis();
    transmitting = status == RADIOLIB_ERR_NONE;
    const int16_t cleanup = status ? radio.finishTransmit() : 0;
    if (cleanup) ready = false;
    line("TX_START"); field(" attempt=", attempts); field(" len=", sizeof(payload));
    field(" rc=", status); field(" cleanup=", cleanup); debug_write("\n");
#endif
}
