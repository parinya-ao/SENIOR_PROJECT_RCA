#ifndef SENIOR_PROJECT_RCA_STABLE_LIB_LEGACY_SENDER_LEGACY_SENDER_H_
#define SENIOR_PROJECT_RCA_STABLE_LIB_LEGACY_SENDER_LEGACY_SENDER_H_

// Declares the legacy Gateway Sender lifecycle for compatibility builds.
namespace legacy_sender {

// Configures the legacy sender hardware and protocol state once at startup.
void Initialize();
// Processes one nonblocking foreground slice of the sender application.
void Poll();

}  // namespace legacy_sender

#endif  // SENIOR_PROJECT_RCA_STABLE_LIB_LEGACY_SENDER_LEGACY_SENDER_H_
