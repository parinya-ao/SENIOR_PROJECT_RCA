// Owns the ARQ raw radio and its board-specific SPI transactions.
#include "radio.h"

#include <Arduino.h>
#include <SPI.h>

#include "arq_config.h"
#include "arq_radio_only.h"
#include "generated/board_ssot.h"

namespace arq::app {

// Radio objects have static lifetime; hardware initialization happens only in
// setup.
static Module module(board_ssot.cs, board_ssot.irq, board_ssot.rst,
                     board_ssot.dio1, SPI,
                     SPISettings(ARQ_SPI_HZ, MSBFIRST, SPI_MODE0));
SX1276 radio(&module);

uint8_t ReadRadioRegister(uint8_t address) {
  SPI.beginTransaction(SPISettings(ARQ_SPI_HZ, MSBFIRST, SPI_MODE0));
  digitalWrite(board_ssot.cs, LOW);
  SPI.transfer(address);
  const uint8_t value = SPI.transfer(0);
  digitalWrite(board_ssot.cs, HIGH);
  SPI.endTransaction();
  return value;
}

int16_t InitializeRadio([[maybe_unused]] bool* sd_blocked, bool* spi_selected) {
#if defined(ARQ_RADIO_ONLY_DIAGNOSTIC) && defined(LORA_ROLE_RECEIVER)
  if (!PrepareTrackerForRadioOnly()) {
    *sd_blocked = true;
    return -1;
  }
#endif
  // Tracker board init keeps EN-LORA low through DATA/ACK; omit the diagnostic
  // flag to restore normal setup.
  board_ssot_init();
  delay(application_config::startup::kRadioSettleMs);
  if (!SPI.swap(ARQ_SPI_ROUTE)) return -1;
  *spi_selected = true;
  SPI.begin();
  radio.reset();
  bool supported = false;
  for (uint8_t i = 0; i < application_config::startup::kVersionProbeAttempts;
       i++) {
    const uint8_t version = ReadRadioRegister(0x42);
    supported = version == RADIOLIB_SX1278_CHIP_VERSION ||
                version == RADIOLIB_SX1278_CHIP_VERSION_ALT ||
                version == RADIOLIB_SX1278_CHIP_VERSION_RFM9X;
    if (supported) break;
    delay(application_config::startup::kRadioSettleMs);
  }
  int16_t rc = supported ? 0 : RADIOLIB_ERR_CHIP_NOT_FOUND;
  if (!rc)
    rc = radio.begin(ARQ_FREQUENCY_HZ / 1000000.0f, ARQ_BANDWIDTH_KHZ,
                     ARQ_SPREADING_FACTOR, ARQ_CODING_RATE, ARQ_SYNC_WORD,
                     ARQ_TX_POWER_DBM, ARQ_PREAMBLE_SYMBOLS, 0);
  // The 915 MHz profile uses the HF bank; clear only bit 3 and preserve mode
  // bits.
  if (!rc) rc = module.SPIsetRegValue(RADIOLIB_SX127X_REG_OP_MODE, 0, 3, 3);
  if (!rc) rc = radio.setOutputPower(ARQ_TX_POWER_DBM, false);
  if (!rc) rc = radio.explicitHeader();
  if (!rc) rc = radio.setCRC(ARQ_CRC_ENABLED);
  if (!rc) rc = radio.invertIQ(ARQ_IQ_INVERTED);
  if (!rc) rc = radio.standby();
  return rc;
}

}  // namespace arq::app
