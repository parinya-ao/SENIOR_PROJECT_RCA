#include <avr/io.h>
#include "handoff_config.h"

_Static_assert(CCP_IOREG_VALUE == CCP_IOREG_gc, "wrong CCP unlock key");
_Static_assert(_SFR_MEM_ADDR(CPU_CCP) == 0x34, "unexpected CCP register");
_Static_assert(_SFR_MEM_ADDR(CPUINT_CTRLA) == 0x110, "unexpected CPUINT register");
_Static_assert(MAPPED_PROGMEM_PAGE_SIZE == 512, "unexpected Flash page size");
_Static_assert(APP_START == 44 * 512, "Receiver BOOTSIZE/address mismatch");
