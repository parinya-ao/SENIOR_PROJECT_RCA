#pragma once

#include <Stream.h>

#define MAX_NMEA_LENGTH  100

class GNSS {
    public:
        GNSS(Stream& serial);
        void begin(uint32_t baud); 
        void send_raw_command(const char *);
        bool read();
        void reset_buffer(bool flush_serial);
        void disable_nmea_msg(const char *type);
        void enable_nmea_msg(const char *type);

        uint8_t hour, minute, seconds, year, month, day;
        int32_t latitude, longitude; // unit of 1/100000 degrees
        uint8_t fixquality, satellites;

        uint8_t _nmea_buf[MAX_NMEA_LENGTH];
    private:
        void _parse();
        Stream& _serial;
        bool _gga_received, _rmc_received;
        uint8_t _nmea_ptr;
        void _send_message(const char *msg);
};
