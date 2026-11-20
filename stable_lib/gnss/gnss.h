#ifndef SENIOR_PROJECT_RCA_STABLE_LIB_GNSS_GNSS_H_
#define SENIOR_PROJECT_RCA_STABLE_LIB_GNSS_GNSS_H_

#include <Stream.h>

#define MAX_NMEA_LENGTH 100

// Incrementally parses NMEA GGA/RMC messages from a caller-owned Stream.
// The parser uses fixed storage and must be called from foreground code.
class GNSS {
 public:
  // Borrows `serial`; the caller must keep the Stream alive for this object.
  GNSS(Stream& serial);
  // Legacy declaration retained for source compatibility; this library supplies
  // no definition, so configure the borrowed Stream at its owning call site.
  void begin(uint32_t baud);
  // Writes the supplied NMEA command followed by the Stream's line ending.
  // `cmd` is borrowed for the duration of the call and must be NUL-terminated.
  void send_raw_command(const char*);
  // Consumes at most one available byte. Returns true after valid GGA and RMC
  // data have both been observed; parsed fields remain stored in this object.
  bool read();
  // Clears partial sentence/fix state; drains serial input only when requested.
  void reset_buffer(bool flush_serial);
  // Sends a u-blox PUBX control for a non-null, three-character message type.
  // Invalid lengths are ignored; no command is sent in that case.
  void disable_nmea_msg(const char* type);
  // Enables a non-null, three-character NMEA message type; invalid lengths are
  // ignored.
  void enable_nmea_msg(const char* type);

  // UTC fields from the most recently accepted GGA/RMC sentences. `year` is
  // the two-digit NMEA year field.
  uint8_t hour, minute, seconds, year, month, day;
  // Signed coordinates in 1/10000000 degrees; south/west values are negative.
  int32_t latitude, longitude;
  // NMEA GGA quality code (zero means no valid fix) and satellite count.
  uint8_t fixquality, satellites;

  // Current NMEA sentence storage; contents are overwritten as bytes arrive.
  uint8_t _nmea_buf[MAX_NMEA_LENGTH];

 private:
  void _parse();
  Stream& _serial;
  bool _gga_received, _rmc_received;
  uint8_t _nmea_ptr;
  void _send_message(const char* msg);
};

#endif  // SENIOR_PROJECT_RCA_STABLE_LIB_GNSS_GNSS_H_
