// Coordinates the gateway radio task using the existing stable LoRa driver.

#ifndef SENIOR_PROJECT_RCA_SRC_SENDER_LIB_LORA_RX_H_
#define SENIOR_PROJECT_RCA_SRC_SENDER_LIB_LORA_RX_H_

#include <lora.h>

// Registers the static foreground radio task with the application scheduler.
void RegisterRadioTask();
// Selects SPI once and arms the configured PHY for this local address.
// Failure leaves the radio task unready; does not transmit DATA.
void InitializeRadio(Address my_addr);
// Cancels requested work and parks the radio after invalid host configuration.
void RejectRadioConfiguration();
// Requests one foreground reliable transfer; repeated starts while busy do
// nothing.
void StartRadioTransaction();
// Cancels queued work and parks the transport; does not reset sequence history.
void StopRadio();
// Requests the configured hello transfer only in an explicit Hello test build.
void StartHelloTestIfEnabled();
// Reports only active DATA/ACK/NACK radio transmission, not ACK waiting.
bool IsRadioTransmitting();

#endif  // SENIOR_PROJECT_RCA_SRC_SENDER_LIB_LORA_RX_H_
