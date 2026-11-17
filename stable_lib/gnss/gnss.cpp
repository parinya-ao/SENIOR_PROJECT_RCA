#include "gnss.h"

#include <Arduino.h>
#include <stdint.h>

// Parses NMEA GGA/RMC sentences incrementally from a caller-owned Stream.

/***********************************************
 * Borrowed from Adafruit's GPS library
 */
// Converts one uppercase checksum digit to a nibble; invalid input maps to 0.
static uint8_t parseHex(char c) {
  if (c < '0') return 0;
  if (c <= '9') return c - '0';
  if (c < 'A') return 0;
  if (c <= 'F') return (c - 'A') + 10;
  // if (c > 'F')
  return 0;
}

// Copies one comma-delimited field into caller storage and returns the next
// field pointer. The caller must provide room for the full field and NUL.
static char* extract_field(char* nmea, char* buf) {
  while (*nmea) {
    if (*nmea == ',') {
      nmea++;
      break;
    }
    *buf++ = *nmea++;
  }
  *buf = 0;
  return nmea;
}

/***********************************************
 * Taken from https://gis.stackexchange.com/a/201484
 */
// NMEA checksums are XORs of the short PUBX command body bytes.
static int calculate_checksum(const char* msg) {
  int checksum = 0;
  for (int i = 0; msg[i] && i < 32; i++) checksum ^= (unsigned char)msg[i];

  return checksum;
}

// Borrows `serial`; parser state must be reset before the first read.
GNSS::GNSS(Stream& serial) : _serial(serial) {
  // reset_buffer(true);
}

// Sends a complete caller-formed NMEA command; this method adds only CR/LF.
void GNSS::send_raw_command(const char* cmd) { _serial.println(cmd); }

// Converts NMEA degrees/minutes text to the integer coordinate scale in gnss.h.
static int32_t to_coord(const char* buf) {
  int32_t rawval = (int32_t)(atof(buf) * 100000);
  return (rawval / 10000000) * 10000000 + (rawval % 10000000) * 10 / 6;
}

// Validates the stored sentence checksum, then updates GGA fix or RMC date.
void GNSS::_parse() {
  // checksum check, obtained from Adafruit's GPS library

  // first look if we even have one
  uint16_t slen = strlen((char*)_nmea_buf);
  // DEBUG_PRINT("NMEA: "); DEBUG_PRINTLN((char*)_nmea_buf);
  if (_nmea_buf[slen - 3] == '*') {
    uint16_t sum = parseHex(_nmea_buf[slen - 2]) * 16;
    sum += parseHex(_nmea_buf[slen - 1]);
    // DEBUG_PRINT("NMEA checksum: "); DEBUG_PRINTLN(sum);

    // check checksum
    for (uint8_t i = 1; i < slen - 3; i++) {
      sum ^= _nmea_buf[i];
    }
    if (sum != 0) {
      // bad checksum :(
      // DEBUG_PRINT("Checksum failed: "); DEBUG_PRINTLN(sum);
      return;
    }
  } else {
    return;  // checksum not exist
  }

  char buf[20];
  // Normalize the talker to GP so equivalent GNSS-prefixed GGA/RMC lines match.
  _nmea_buf[2] = 'P';
  char* ptr = (char*)_nmea_buf;
  ptr = extract_field(ptr, buf);
  if (!strcmp(buf, "$GPGGA")) {
    //$GPGGA,050119.000,1350.7864,N,10034.1178,E,1,08,0.96,6.5,M,-27.7,M,,*48

    // time
    ptr = extract_field(ptr, buf);
    uint32_t time = (uint32_t)atof(buf);
    hour = time / 10000;
    minute = (time % 10000) / 100;
    seconds = (time % 100);

    // latitude
    int32_t rawval;
    ptr = extract_field(ptr, buf);
    latitude = to_coord(buf);
    if (*ptr == 'S') latitude = -latitude;
    ptr = extract_field(ptr, buf);

    // longitude
    ptr = extract_field(ptr, buf);
    longitude = to_coord(buf);
    if (*ptr == 'W') longitude = -longitude;
    ptr = extract_field(ptr, buf);

    // fix quality
    ptr = extract_field(ptr, buf);
    fixquality = atoi(buf);

    // num satellites
    ptr = extract_field(ptr, buf);
    satellites = atoi(buf);

    if (fixquality) _gga_received = true;

    // DEBUG_PRINT(hour);
    // DEBUG_PRINT(':');
    // DEBUG_PRINT(minute);
    // DEBUG_PRINT(':');
    // DEBUG_PRINT(seconds);
    // DEBUG_PRINT(' ');
    // DEBUG_PRINT(latitude);
    // DEBUG_PRINT(',');
    // DEBUG_PRINT(longitude);
    // DEBUG_PRINT(' ');
    // DEBUG_PRINT(fixquality);
    // DEBUG_PRINT(',');
    // DEBUG_PRINT(satellites);
    // DEBUG_PRINTLN();
  } else if (!strcmp(buf, "$GPRMC")) {
    //$GPRMC,050119.000,A,1350.7864,N,10034.1178,E,0.70,33.46,310519,,,A*5B
    ptr = extract_field(ptr, buf);
    ptr = extract_field(ptr, buf);
    if (buf[0] == 'A') {
      for (uint8_t i = 0; i < 7; i++) {
        ptr = extract_field(ptr, buf);
      }
      uint32_t date = atol(buf);

      if (date) {
        day = date / 10000;
        month = (date % 10000) / 100;
        year = date % 100;
        _rmc_received = true;
        // DEBUG_PRINT("20");
        // DEBUG_PRINT(year);
        // DEBUG_PRINT('-');
        // DEBUG_PRINT(month);
        // DEBUG_PRINT('-');
        // DEBUG_PRINT(day);
        // DEBUG_PRINTLN();
      }
    }
  }
}

// Consumes at most one stream byte and returns true after valid GGA and RMC
// records have supplied the required fields.
bool GNSS::read() {
  if (_gga_received && _rmc_received) return true;

  if (!_serial.available()) {
    return false;
  }

  char c = _serial.read();
#ifdef DEBUG_GNSS
  Serial.print(c);
#endif

  if (c == '$') {
    // got start of NMEA sentence; start over
    _nmea_ptr = 0;
    _nmea_buf[_nmea_ptr++] = c;
    return false;
  } else if (c == '\n' || c == '\r') {
    // EOL found; terminate and try to parse
    _nmea_buf[_nmea_ptr] = '\0';
    _parse();
    _nmea_ptr = 0;
    return _gga_received && _rmc_received;
  }

  _nmea_buf[_nmea_ptr++] = c;
  if (_nmea_ptr == MAX_NMEA_LENGTH) {  // unusual NMEA length; start over
    _nmea_ptr = 0;
  }

  return false;
}

// Clears partial parser/fix state and optionally drains buffered serial bytes.
void GNSS::reset_buffer(bool flush_serial) {
  _gga_received = false;
  _rmc_received = false;
  _nmea_ptr = 0;
  _nmea_buf[0] = '\0';

  if (flush_serial) {
    // DEBUG_PRINTLN("Start flushing GPS serial.");
    while (_serial.available() > 0) {
      _serial.read();
    }
    // DEBUG_PRINTLN("Flush GPS serial done.");
  }
}

/***********************************************
 * Taken from https://gis.stackexchange.com/a/201484
 */
// Builds a PUBX sentence from a body without `$` or checksum text.
void GNSS::_send_message(const char* msg) {
  char checksum[8];
  snprintf(checksum, sizeof(checksum) - 1, "*%.2X", calculate_checksum(msg));
  _serial.print("$");
  _serial.print(msg);
  _serial.println(checksum);
}

/***********************************************
 * Taken from https://gis.stackexchange.com/a/201484
 */
// Enables/disables one receiver message code; `type` must contain 3 chars.
void GNSS::disable_nmea_msg(const char* type) {
  if (strlen(type) != 3) return;

  char tmp[32];
  snprintf(tmp, sizeof(tmp) - 1, "PUBX,40,%s,0,0,0,0", type);
  _send_message(tmp);
}

/***********************************************
 * Taken from https://gis.stackexchange.com/a/201484
 */
// Enables one receiver message code; invalid type lengths are ignored.
void GNSS::enable_nmea_msg(const char* type) {
  if (strlen(type) != 3) return 0;

  char tmp[32];
  snprintf(tmp, sizeof(tmp) - 1, "PUBX,40,%s,0,1,0,0", type);
  _send_message(tmp);
}
