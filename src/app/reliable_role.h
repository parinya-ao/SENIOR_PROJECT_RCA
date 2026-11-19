#ifndef SENIOR_PROJECT_RCA_SRC_APP_RELIABLE_ROLE_H_
#define SENIOR_PROJECT_RCA_SRC_APP_RELIABLE_ROLE_H_

#include <features/reliable_transfer/reliable_transport.h>
#include <lora.h>

#include "hello_config.h"

namespace reliable_app {

extern LoRa lora;
extern reliable::Transport<LoRa> transport;
extern bool radio_ready;
extern const char kRole[];
extern const char kFirmware[];
void InitializeRoleGpio();
void PollRoleLeds(uint32_t now, bool transmitting);

#if !HELLO_RF_DIAGNOSTIC_ONLY
extern const char kReadyEvent[];
void RecordTransportEvent(void*, const char* event, uint8_t type,
                          uint8_t sequence, int16_t error);
bool AcceptData(void*, uint8_t sequence, const uint8_t* data, uint8_t length);
bool ArmRadio();
bool ArmRole();
void ReportRoleReadyAtStartup();
void PollRoleRadio(uint32_t now);
bool RoleCommandPending();
void ResetRoleTransaction();
void HandleRoleCommand(char command);
#endif

}  // namespace reliable_app

#endif  // SENIOR_PROJECT_RCA_SRC_APP_RELIABLE_ROLE_H_
