#pragma once

// Adapted from https://playground.arduino.cc/Main/Printf

// Writes formatted text to `stream` using a fixed MAX_PRINTF_RESULT_LENGTH
// buffer (default 250 bytes); long output may be truncated. The caller owns the
// Stream and must supply a valid format string and matching arguments.
void printf(Stream& stream, const char* fmt, ...);
// Arduino flash-string format overload; uses the same bounded output contract.
void printf(Stream& stream, const __FlashStringHelper* fmt, ...);
// Returns a pointer to static storage overwritten by the next call; copy it if
// the text must outlive this conversion. No allocation occurs.
char* ui64toa(uint64_t v);
