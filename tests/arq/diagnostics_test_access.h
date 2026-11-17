// Test-only inspection after diagnostics.cpp is included in the host harness.
#ifndef SENIOR_PROJECT_RCA_TESTS_ARQ_DIAGNOSTICS_TEST_ACCESS_H_
#define SENIOR_PROJECT_RCA_TESTS_ARQ_DIAGNOSTICS_TEST_ACCESS_H_

inline void ResetLog() {
  arq::diagnostics::head = arq::diagnostics::tail = 0;
  arq::diagnostics::count = arq::diagnostics::offset = 0;
  arq::diagnostics::overflow = 0;
}

inline const char* QueuedLogLine(uint8_t index) {
  return arq::diagnostics::lines[(arq::diagnostics::head + index) %
                                 application_config::logging::kSlotCount];
}
#endif  // SENIOR_PROJECT_RCA_TESTS_ARQ_DIAGNOSTICS_TEST_ACCESS_H_
