// Replaces device sleep with a no-op for deterministic host application tests.
#ifndef SENIOR_PROJECT_RCA_TESTS_MVP_STUB_SLEEP_H_
#define SENIOR_PROJECT_RCA_TESTS_MVP_STUB_SLEEP_H_

#include <stdint.h>
inline void SleepFor(uint32_t) {}

#endif  // SENIOR_PROJECT_RCA_TESTS_MVP_STUB_SLEEP_H_
