/* Compiled with avr-gcc -mmcu=avr128da28, not hand-encoded jump bytes. */
#include <avr/io.h>
#include "handoff_config.h"

.section .text
.global _start
.type _start, @function
_start:
    cli
    clr r1
    /* IVSEL=0 selects APPCODE vectors. No stack or C runtime is needed here. */
    ldi r16, CCP_IOREG_VALUE
    out _SFR_IO_ADDR(CPU_CCP), r16
    sts CPUINT_CTRLA, r1
    ldi r30, lo8(APP_START)
    ldi r31, hi8(APP_START)
    lpm r16, Z+
    cpi r16, RESET_BYTE_0
    brne parked
    lpm r16, Z+
    cpi r16, RESET_BYTE_1
    brne parked
    lpm r16, Z+
    cpi r16, RESET_BYTE_2
    brne parked
    lpm r16, Z
    cpi r16, RESET_BYTE_3
    brne parked
    /* GNU AVR assembler takes this symbol in bytes and encodes word PC units. */
    jmp APP_START
parked:
    cli
    rjmp parked
.size _start, .-_start
