#ifndef SENIOR_PROJECT_RCA_SRC_APP_APPLICATION_H_
#define SENIOR_PROJECT_RCA_SRC_APP_APPLICATION_H_

// Composition-root hooks called by the Arduino entry points for the selected
// LORA_APP_* implementation.
namespace firmware_app {

/// @brief Initializes the application selected by the active LORA_APP_* define.
/// @post Runs during Arduino setup and performs role-specific startup work.
void Initialize();

/// @brief Advances the selected application once from the foreground loop.
/// @post Performs one bounded scheduler or application poll.
void Poll();

/// @brief Applies role-specific interrupt routing before Arduino setup.
/// @post Preserves the selected board's early interrupt workaround.
void PreMain();

}  // namespace firmware_app

#endif  // SENIOR_PROJECT_RCA_SRC_APP_APPLICATION_H_
