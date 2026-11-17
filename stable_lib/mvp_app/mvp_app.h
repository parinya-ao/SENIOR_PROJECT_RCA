#ifndef SENIOR_PROJECT_RCA_STABLE_LIB_MVP_APP_MVP_APP_H_
#define SENIOR_PROJECT_RCA_STABLE_LIB_MVP_APP_MVP_APP_H_

// Declares the raw radio bring-up application's Arduino lifecycle hooks.
namespace mvp_app {

// Initializes the selected role and its diagnostic radio state.
void Initialize();
// Advances one foreground command, radio, or logging step without blocking.
void Poll();

}  // namespace mvp_app

#endif  // SENIOR_PROJECT_RCA_STABLE_LIB_MVP_APP_MVP_APP_H_
