/**
 * @file
 * @brief Logging service on SD card
 *
 * Declarations for logging messages on an SD card.
 *
 * @author Chaiporn Jaikaeo <chaiporn.j@ku.ac.th>
 *
 */
#ifndef SENIOR_PROJECT_RCA_STABLE_LIB_LOGGER_LOGGER_H_
#define SENIOR_PROJECT_RCA_STABLE_LIB_LOGGER_LOGGER_H_

#include <SD.h>
#include <SPI.h>
#include <stdarg.h>
#include <stdint.h>

#include "debug.h"
#include "raw-storage.h"

#ifdef DEBUG_LOGGER
#define LOGGER_DEBUG_PRINT DEBUG_PRINT
#define LOGGER_DEBUG_PRINTLN DEBUG_PRINTLN
#define LOGGER_DEBUG_PRINTF DEBUG_PRINTF
#else
#define LOGGER_DEBUG_PRINT(x)
#define LOGGER_DEBUG_PRINTLN(x)
#define LOGGER_DEBUG_PRINTF(...)
#endif

#define LOGGER_MAGIC_STRING "CATTRACK-LOGGER"
#define LOGGER_MAGIC_LENGTH (sizeof(LOGGER_MAGIC_STRING) - 1)

#define MAX_MSG_LEN 1024

#define LOGGER_INVALID_VALUE 0xFFFFFFFFFFFFFFFF

class Logger {
 public:
  /******************************************************************
   * Construct a logging storage
   *
   * The logger is NOT ready for use until setup() is called
   */
  Logger(Sd2Card& card) : _raw(card) { _cursor = LOGGER_INVALID_VALUE; }

  /******************************************************************
   * Set up logging at `start_block`, with `capacity` measured in 512-byte
   * sectors. `overwrite` resets existing logs; otherwise setup resumes the
   * stored cursor when the magic marker is valid.
   *
   * @return true after setup. Low-level RawStorage card errors are not
   *         propagated by the current implementation.
   */
  bool setup(uint32_t start_block, uint32_t capacity, bool overwrite);

  /******************************************************************
   * Appends `len` bytes from `buf` without adding a terminator. `buf` must
   * remain readable for the call; records are silently skipped when full.
   */
  void writeraw(const char* buf, uint16_t len);

  /******************************************************************
   * Formats into a fixed MAX_MSG_LEN buffer and appends the result; output may
   * be truncated and no heap allocation occurs.
   */
  void printf(const char* fmt, ...);

 private:
  RawStorage _raw;        ///< interface to raw-SD
  uint64_t _start_block;  ///< first block on SD to store logging state
  uint64_t _cursor;       ///< current cursor position from the first block
  uint64_t _capacity;     ///< maximum number of bytes
  void _save_cursor();
  void _load_cursor();
  void _save_magic();
  uint64_t _sd_position() { return (_start_block + 1) * 512 + _cursor; }
};

#ifdef LOGGING
extern Logger logger;
#define LOG_TS(args...)                           \
  do {                                            \
    logger.printf("%s ", get_current_time_str()); \
    logger.printf(args);                          \
    DEBUG_PRINTF("%s ", get_current_time_str());  \
    DEBUG_PRINTF(args);                           \
  } while (0)

#define LOG(args...)     \
  do {                   \
    logger.printf(args); \
    DEBUG_PRINTF(args);  \
  } while (0)
#else
#define LOG_TS(args...)                          \
  do {                                           \
    DEBUG_PRINTF("%s ", get_current_time_str()); \
    DEBUG_PRINTF(args);                          \
  } while (0)
#define LOG(args...)    \
  do {                  \
    DEBUG_PRINTF(args); \
  } while (0)
#endif

#endif  // SENIOR_PROJECT_RCA_STABLE_LIB_LOGGER_LOGGER_H_
