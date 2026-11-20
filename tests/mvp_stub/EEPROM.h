// Byte-backed EEPROM test double that records writes made by the MVP app.
#ifndef SENIOR_PROJECT_RCA_TESTS_MVP_STUB_EEPROM_H_
#define SENIOR_PROJECT_RCA_TESTS_MVP_STUB_EEPROM_H_

#include <cstring>

struct EepromSpy {
  unsigned reads = 0;
  unsigned writes = 0;
  template <typename T>
  T& get(int, T& value) {
    ++reads;
    std::memset(&value, 0xff, sizeof(value));
    return value;
  }
  template <typename T>
  const T& put(int, const T& value) {
    ++writes;
    return value;
  }
};
extern EepromSpy EEPROM;

#endif  // SENIOR_PROJECT_RCA_TESTS_MVP_STUB_EEPROM_H_
