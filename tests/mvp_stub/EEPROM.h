#pragma once
#include <cstring>

struct EepromSpy {
    unsigned reads = 0;
    unsigned writes = 0;
    template <typename T> T& get(int, T& value) {
        ++reads;
        std::memset(&value, 0xff, sizeof(value));
        return value;
    }
    template <typename T> const T& put(int, const T& value) {
        ++writes;
        return value;
    }
};
extern EepromSpy EEPROM;
