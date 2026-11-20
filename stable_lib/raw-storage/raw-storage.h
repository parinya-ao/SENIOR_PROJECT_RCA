/**
 * @file
 * Utility class declaration for raw access to SD card
 *
 * @author Chaiporn Jaikaeo <chaiporn.j@ku.ac.th>
 *
 */
#ifndef SENIOR_PROJECT_RCA_STABLE_LIB_RAW_STORAGE_RAW_STORAGE_H_
#define SENIOR_PROJECT_RCA_STABLE_LIB_RAW_STORAGE_RAW_STORAGE_H_

#include <SD.h>
#include <SPI.h>
#include <stdint.h>

#ifdef DEBUG_RAW
#include "debug.h"
#include "printf.h"
#define RAW_DEBUG_PRINT DEBUG_PRINT
#define RAW_DEBUG_PRINTLN DEBUG_PRINTLN
#define RAW_DEBUG_PRINTF DEBUG_PRINTF
#else
#define RAW_DEBUG_PRINT(x)
#define RAW_DEBUG_PRINTLN(x)
#define RAW_DEBUG_PRINTF(...)
#endif

#define BLOCK_POSITION(bytepos) (bytepos / 512)
#define BLOCK_OFFSET(bytepos) (bytepos % 512)
#define RAW_INVALID_VALUE 0xFFFFFFFFFFFFFFFF

class RawStorage {
 public:
  // Borrows `card`; it must remain alive while this object is used.
  RawStorage(Sd2Card& card) : _card(card) { _cached_pos = RAW_INVALID_VALUE; }
  // Reads `len` bytes at an absolute byte offset. `data` must provide `len`
  // writable bytes and the range must be within the card. Uses one 512-byte
  // cache; current Sd2Card read errors are not propagated by this wrapper.
  bool read(uint64_t offset, uint8_t* data, uint16_t len);
  // Writes `len` bytes at an absolute byte offset. `data` must provide `len`
  // readable bytes and the range must be within the card. Partial-block writes
  // preserve the other bytes through the cache; low-level errors are not
  // returned.
  bool write(uint64_t offset, const uint8_t* data, uint16_t len);

 private:
  Sd2Card& _card;
  uint64_t _cached_pos;
  uint8_t _cached_block[512];

  void _cache_read(uint64_t pos);
  void _cache_write(uint64_t pos);
};

#endif  // SENIOR_PROJECT_RCA_STABLE_LIB_RAW_STORAGE_RAW_STORAGE_H_
