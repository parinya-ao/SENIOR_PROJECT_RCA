#ifndef SENIOR_PROJECT_RCA_STABLE_LIB_LEGACY_RECEIVER_LEGACY_RECEIVER_H_
#define SENIOR_PROJECT_RCA_STABLE_LIB_LEGACY_RECEIVER_LEGACY_RECEIVER_H_

// Declares the legacy Tracker Receiver lifecycle for compatibility builds.
namespace legacy_receiver {

// Configures the legacy receiver hardware and protocol state once at startup.
void Initialize();
// Processes one nonblocking foreground slice of the receiver application.
void Poll();

}  // namespace legacy_receiver

#endif  // SENIOR_PROJECT_RCA_STABLE_LIB_LEGACY_RECEIVER_LEGACY_RECEIVER_H_
