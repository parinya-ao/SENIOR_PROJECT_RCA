#include "sd-utils.h"

#define PARTITION_ID_FAT16 0x06
#define PARTITION_ID_FAT16_LBA 0x0E

/**************************
 * Find configuration, data, and log partitions on an SD card.
 *
 * If found, start sector and the number of sectors of each partition are
 * returned via the specified pointers.
 */
void get_data_and_log_partitions(Sd2Card& card, uint8_t* config_part_idx,
                                 uint32_t* data_start, uint32_t* data_size,
                                 uint32_t* log_start, uint32_t* log_size) {
  mbr_t mbr;

  *config_part_idx = *data_start = *data_size = *log_start = *log_size = 0;
  card.readBlock(0, (uint8_t*)&mbr);

  if (mbr.mbrSig0 != 0x55 && mbr.mbrSig1 != 0xAA) {
    return;
  }

  for (uint8_t i = 0; i < 4; i++) {
    if (*config_part_idx == 0 &&
        ((mbr.part[i].type == PARTITION_ID_FAT16) ||
         (mbr.part[i].type == PARTITION_ID_FAT16_LBA))) {
      if (config_part_idx != nullptr) *config_part_idx = i + 1;
    }
    if (*data_start == 0 && mbr.part[i].type == STORAGE_PARTITION_ID) {
      if (data_start != nullptr) *data_start = mbr.part[i].firstSector;
      if (data_size != nullptr) *data_size = mbr.part[i].totalSectors;
    }
    if (*log_start == 0 && mbr.part[i].type == LOG_PARTITION_ID) {
      if (log_start != nullptr) *log_start = mbr.part[i].firstSector;
      if (log_size != nullptr) *log_size = mbr.part[i].totalSectors;
    }
  }
}

/*********************************************************
 * Open specified file located in the root folder of the specified volume
 */
bool open_file_in_root(SdFile& file, SdVolume& volume, const char* filename,
                       uint8_t oflag) {
  SdFile root;
  if (!root.openRoot(volume)) {
    return false;
  }

  if (!file.open(&root, filename, oflag)) {
    root.close();
    return false;
  }

  root.close();
  return true;
}

/*****************************************************
 * Read one line from the specified open file on SD
 */
char* read_line(SdFile& file) {
  static char buf[128];
  uint8_t pos = 0;

  while (true) {
    int c = file.read();
    if (c == -1)
      if (pos == 0)
        return NULL;
      else
        break;
    if (c == '\n' || c == '\r') break;
    if (pos < sizeof(buf) - 1U) {
      buf[pos++] = static_cast<char>(c);
    }
    // Continue to the delimiter after filling the buffer so the next call
    // starts at the next record instead of parsing the tail of this line.
  }
  buf[pos] = '\0';
  return buf;
}
