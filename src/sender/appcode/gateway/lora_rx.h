// Coordinates the gateway radio task using the existing stable LoRa driver.

#ifndef SENIOR_PROJECT_RCA_SRC_SENDER_LIB_LORA_RX_H_
#define SENIOR_PROJECT_RCA_SRC_SENDER_LIB_LORA_RX_H_

#include <lora.h>

/// @brief Registers the static foreground radio task with the scheduler.
/// @post The task is available for subsequent scheduler polls.
void RegisterRadioTask();
/// @brief Selects SPI and arms the configured PHY for this local address.
/// @param my_addr Local wire address.
/// @post Failure leaves the radio task unready; no DATA is transmitted.
void InitializeRadio(Address my_addr);
/// @brief Cancels queued work and parks the radio after invalid host settings.
void RejectRadioConfiguration();
/// @brief Requests one foreground reliable transfer.
/// @post Repeated starts while the transport is busy do nothing.
void StartRadioTransaction();
/// @brief Cancels queued work and parks the transport.
/// @post Existing sequence history is preserved.
void StopRadio();
/// @brief Requests the hello transfer in an explicit Hello test build.
/// @post Other builds do not queue an application transmission.
void StartHelloTestIfEnabled();
/// @brief Reports whether a DATA, ACK, or NACK transmission is active.
/// @return False while merely waiting for an ACK.
bool IsRadioTransmitting();

// Poll the bounded production UPDI radio console.
void PollRadioConsole();
// True while the bench owns radio commands instead of I2C.
bool IsRadioBenchActive();

#endif  // SENIOR_PROJECT_RCA_SRC_SENDER_LIB_LORA_RX_H_
