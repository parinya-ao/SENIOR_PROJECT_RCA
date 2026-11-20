#ifndef SENIOR_PROJECT_RCA_SRC_SENDER_RELIABLE_H_
#define SENIOR_PROJECT_RCA_SRC_SENDER_RELIABLE_H_

// Declares the feature-owned reliable DATA/ACK application lifecycle.
namespace reliable_app {

/// @brief Initializes role-specific pins, radio, transport, and diagnostics.
/// @post Performs hardware setup once during the selected app's startup.
void Initialize();
/// @brief Advances one nonblocking foreground transport and command step.
/// @post Does not wait for radio completion or host input.
void Poll();

}  // namespace reliable_app

#endif  // SENIOR_PROJECT_RCA_SRC_SENDER_RELIABLE_H_
