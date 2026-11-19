#ifndef SENIOR_PROJECT_RCA_SRC_APP_ARQ_RADIO_H_
#define SENIOR_PROJECT_RCA_SRC_APP_ARQ_RADIO_H_

#include <RadioLib.h>
#include <stdint.h>

namespace arq::app {

extern SX1276 radio;
uint8_t ReadRadioRegister(uint8_t address);
int16_t InitializeRadio(bool* sd_blocked, bool* spi_selected);

}  // namespace arq::app

#endif  // SENIOR_PROJECT_RCA_SRC_APP_ARQ_RADIO_H_
