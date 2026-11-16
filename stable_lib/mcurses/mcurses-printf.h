#ifndef __MCURSES_PRINTF_H__
#define __MCURSES_PRINTF_H__

void mc_vprintf(const char *fmt, va_list args);
void mc_printf(char *fmt, ... );
void mc_printf(const __FlashStringHelper *fmt, ... );

#endif
