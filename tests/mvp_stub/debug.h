// Discards debug output in native tests so radio state is tested without UART.
#ifndef SENIOR_PROJECT_RCA_TESTS_MVP_STUB_DEBUG_H_
#define SENIOR_PROJECT_RCA_TESTS_MVP_STUB_DEBUG_H_

template <typename... Args>
inline void host_debug(const char*, const Args&...) {}
#define DEBUG_TS(...) host_debug(__VA_ARGS__)

#endif  // SENIOR_PROJECT_RCA_TESTS_MVP_STUB_DEBUG_H_
