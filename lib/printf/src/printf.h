#pragma once

// Adapted from https://playground.arduino.cc/Main/Printf

void printf(Stream& stream, const char *fmt, ... );
void printf(Stream& stream, const __FlashStringHelper *fmt, ... );
char* ui64toa(uint64_t v);
