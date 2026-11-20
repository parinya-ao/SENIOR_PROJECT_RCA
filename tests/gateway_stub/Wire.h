// Supplies only the Wire calls used by the real gateway command task.
#ifndef SENIOR_PROJECT_RCA_TESTS_GATEWAY_STUB_WIRE_H_
#define SENIOR_PROJECT_RCA_TESTS_GATEWAY_STUB_WIRE_H_
#include <Arduino.h>
#include <stddef.h>
#include <stdint.h>
inline int digitalRead(uint8_t) { return 0; }
struct WireStub {
  uint8_t input[32]{};
  uint8_t offset = 0;
  int read() { return input[offset++]; }
  void write(uint8_t) {}
  void write(const char*, size_t) {}
  void end() {}
  void begin(uint8_t) {}
  void onReceive(void (*)(int)) {}
  void onRequest(void (*)()) {}
};
inline WireStub Wire;
#endif  // SENIOR_PROJECT_RCA_TESTS_GATEWAY_STUB_WIRE_H_
