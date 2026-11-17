#ifndef SENIOR_PROJECT_RCA_STABLE_LIB_SD_UTILS_SD_UTILS_H_
#define SENIOR_PROJECT_RCA_STABLE_LIB_SD_UTILS_SD_UTILS_H_

// Finds the Tracker's data/config/log partitions and reads small root files.
#include <SD.h>

/**************************************************************************
 * Partition ID on SD card for storing data
 */
#ifndef STORAGE_PARTITION_ID
#define STORAGE_PARTITION_ID 0x33
#endif

/**************************************************************************
 * Partition ID on SD card for storing logs
 */
#ifndef LOG_PARTITION_ID
#define LOG_PARTITION_ID 0x34
#endif

// Sets every output to zero, then reports the config partition index (1..4)
// and data/log starts and sizes in 512-byte sectors. All pointers and `card`
// must be non-null; zero outputs indicate a missing partition or invalid MBR.
void get_data_and_log_partitions(Sd2Card& card, uint8_t* config_part_idx,
                                 uint32_t* data_start, uint32_t* data_size,
                                 uint32_t* log_start, uint32_t* log_size);

// Opens the NUL-terminated `filename` in the volume root. `file` and `volume`
// must be valid; on success `file` remains open after the root handle closes.
// Returns false if either open fails.
bool open_file_in_root(SdFile& file, SdVolume& volume, const char* filename,
                       uint8_t oflag);
// Reads an open-file line, stopping at the first CR or LF byte. Returns nullptr
// at EOF before any bytes; otherwise returns shared storage overwritten by the
// next call. Stores 127 bytes and drains any excess through the delimiter so
// the next call begins at the next line.
char* read_line(SdFile& file);

#endif  // SENIOR_PROJECT_RCA_STABLE_LIB_SD_UTILS_SD_UTILS_H_
