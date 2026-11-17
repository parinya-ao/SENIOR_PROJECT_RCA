// Minimal SD API double for host tests of the first-party sd-utils helpers.
#ifndef SENIOR_PROJECT_RCA_TESTS_SD_STUB_SD_H_
#define SENIOR_PROJECT_RCA_TESTS_SD_STUB_SD_H_

#include <stddef.h>
#include <stdint.h>

struct SdPartition {
  uint8_t type = 0;
  uint32_t firstSector = 0;
  uint32_t totalSectors = 0;
};

struct mbr_t {
  uint8_t mbrSig0 = 0;
  uint8_t mbrSig1 = 0;
  SdPartition part[4]{};
};

class Sd2Card {
 public:
  bool readBlock(uint32_t, uint8_t*) { return true; }
};

class SdVolume {};

class SdFile {
 public:
  bool openRoot(SdVolume&) { return true; }
  bool open(SdFile*, const char*, uint8_t) { return true; }
  void close() {}

  void SetInput(const char* data, size_t length) {
    data_ = data;
    length_ = length;
    position_ = 0;
  }

  int read() {
    if (position_ == length_) return -1;
    return static_cast<unsigned char>(data_[position_++]);
  }

 private:
  const char* data_ = nullptr;
  size_t length_ = 0;
  size_t position_ = 0;
};

#endif  // SENIOR_PROJECT_RCA_TESTS_SD_STUB_SD_H_
