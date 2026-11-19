// Formats bounded printf-style text into the active mcurses screen buffer.
#include <Stream.h>
#include <stdarg.h>

#include "mcurses.h"

#ifndef MAX_PRINTF_RESULT_LENGTH
#define MAX_PRINTF_RESULT_LENGTH 250
#endif

void mc_vprintf(const char* fmt, va_list args) {
  char buf[MAX_PRINTF_RESULT_LENGTH];
  vsnprintf(buf, MAX_PRINTF_RESULT_LENGTH, fmt, args);
  addstr(buf);
}

void mc_printf(char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  mc_vprintf(fmt, args);
  va_end(args);
}

void mc_printf(const __FlashStringHelper* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  mc_vprintf((const char*)fmt, args);
  va_end(args);
}
