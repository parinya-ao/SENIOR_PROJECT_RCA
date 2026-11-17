#ifndef SENIOR_PROJECT_RCA_SRC_APP_APPLICATION_H_
#define SENIOR_PROJECT_RCA_SRC_APP_APPLICATION_H_

// Composition-root hooks called by the Arduino entry points for the selected
// LORA_APP_* implementation.
namespace firmware_app {

// Initializes the single application selected by the active LORA_APP_* define.
// Runs during Arduino setup and owns role-specific startup side effects.
void Initialize();

// Advances the selected application once from the foreground Arduino loop.
void Poll();

// Applies the role-specific early interrupt-routing workaround before setup.
void PreMain();

}  // namespace firmware_app

#endif  // SENIOR_PROJECT_RCA_SRC_APP_APPLICATION_H_
