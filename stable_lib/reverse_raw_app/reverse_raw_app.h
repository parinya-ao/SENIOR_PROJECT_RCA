#ifndef SENIOR_PROJECT_RCA_STABLE_LIB_REVERSE_RAW_APP_REVERSE_RAW_APP_H_
#define SENIOR_PROJECT_RCA_STABLE_LIB_REVERSE_RAW_APP_REVERSE_RAW_APP_H_

// Declares the reverse-direction raw observation lifecycle for diagnostics.
namespace reverse_raw_app {

// Initializes the selected role without sending a packet.
void Initialize();
// Processes one foreground command or receive observation; no automatic retry.
void Poll();

}  // namespace reverse_raw_app

#endif  // SENIOR_PROJECT_RCA_STABLE_LIB_REVERSE_RAW_APP_REVERSE_RAW_APP_H_
