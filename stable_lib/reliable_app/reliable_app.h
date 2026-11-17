#ifndef SENIOR_PROJECT_RCA_STABLE_LIB_RELIABLE_APP_RELIABLE_APP_H_
#define SENIOR_PROJECT_RCA_STABLE_LIB_RELIABLE_APP_RELIABLE_APP_H_

// Declares the feature-owned reliable DATA/ACK application lifecycle.
namespace reliable_app {

// Initializes role-specific pins, radio, transport, and diagnostic state.
void Initialize();
// Advances one nonblocking foreground transport and command step.
void Poll();

}  // namespace reliable_app

#endif  // SENIOR_PROJECT_RCA_STABLE_LIB_RELIABLE_APP_RELIABLE_APP_H_
