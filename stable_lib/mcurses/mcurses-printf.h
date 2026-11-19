#ifndef __MCURSES_PRINTF_H__
#define __MCURSES_PRINTF_H__

// Formats into a fixed 250-byte stack buffer and appends it to the active
// mcurses window. Output may be truncated; no heap storage is used.
// `fmt` and every value referenced by `args` must remain valid for this call.
void mc_vprintf(const char* fmt, va_list args);
// Variadic wrapper around mc_vprintf(); output follows the same fixed-buffer
// and truncation behavior.
void mc_printf(char* fmt, ...);
// Flash-string overload for Arduino's __FlashStringHelper format strings.
void mc_printf(const __FlashStringHelper* fmt, ...);

#endif
