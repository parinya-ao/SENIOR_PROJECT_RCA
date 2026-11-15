/** 
 * @file
 * Utility class declaration for raw access to SD card
 *
 * @author Chaiporn Jaikaeo <chaiporn.j@ku.ac.th>
 *
 */
#pragma once

#include <stdint.h>
#include <SPI.h>
#include <SD.h>

#ifdef DEBUG_RAW
#include "printf.h"
#include "debug.h"
#define RAW_DEBUG_PRINT   DEBUG_PRINT
#define RAW_DEBUG_PRINTLN DEBUG_PRINTLN
#define RAW_DEBUG_PRINTF  DEBUG_PRINTF
#else
#define RAW_DEBUG_PRINT(x)
#define RAW_DEBUG_PRINTLN(x)
#define RAW_DEBUG_PRINTF(...)
#endif

#define BLOCK_POSITION(bytepos)  (bytepos/512)
#define BLOCK_OFFSET(bytepos)    (bytepos%512)
#define RAW_INVALID_VALUE        0xFFFFFFFFFFFFFFFF

class RawStorage {
    public:
        RawStorage(Sd2Card& card):_card(card) { _cached_pos = RAW_INVALID_VALUE; }
        bool read(uint64_t offset, uint8_t* data, uint16_t len);
        bool write(uint64_t offset, const uint8_t* data, uint16_t len);

    private:
        Sd2Card& _card;
        uint64_t _cached_pos;
        uint8_t _cached_block[512];

        void _cache_read(uint64_t pos);
        void _cache_write(uint64_t pos);
};
