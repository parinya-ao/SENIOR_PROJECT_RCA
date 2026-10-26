#include <avr/io.h>

// AVR DA names for the same registers used by upstream (0x001e/0x001f).
#define GPIOR2 GPR_GPR2
#define GPIOR3 GPR_GPR3
#include "../../external/upditerm/updi_uart.c"
