#pragma once

#include <SD.h>

/**************************************************************************
 * Partition ID on SD card for storing data
 */
#ifndef STORAGE_PARTITION_ID
#define STORAGE_PARTITION_ID   0x33
#endif

/**************************************************************************
 * Partition ID on SD card for storing logs
 */
#ifndef LOG_PARTITION_ID
#define LOG_PARTITION_ID  0x34
#endif


void get_data_and_log_partitions(
    Sd2Card& card,
    uint8_t*  config_part_idx,
    uint32_t* data_start, 
    uint32_t* data_size, 
    uint32_t* log_start, 
    uint32_t* log_size);

bool open_file_in_root(SdFile& file, SdVolume& volume, const char* filename, uint8_t oflag);
char* read_line(SdFile& file);
