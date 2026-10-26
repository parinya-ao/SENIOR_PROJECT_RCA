#include <stdint.h>
#include <avr/io.h>

#include "updi_uart.h"

#define UART_FLAGS _SFR_MEM8(0x001E)
#define UART_RX    _SFR_MEM8(0x001F)

#define FLAG_ENABLE 0x01
#define FLAG_RX     0x02

#define SYSCFG_OCDM  _SFR_MEM8(0x0F18)
#define SYSCFG_OCDMS _SFR_MEM8(0x0F19)

_Bool updi_uart_enabled(void) {
    return (UART_FLAGS & FLAG_ENABLE) != 0;
}

void updi_uart_tx(uint8_t byte) {
    while (UART_FLAGS & FLAG_ENABLE) {
        if (!SYSCFG_OCDMS) {
            SYSCFG_OCDM = byte;
            break;
        }
    }
}

_Bool updi_uart_rx_poll(void) {
    return (UART_FLAGS & FLAG_RX) != 0;
}

uint8_t updi_uart_rx(void) {
    while (!(UART_FLAGS & FLAG_RX)) {
    }

    uint8_t byte = UART_RX;
    UART_FLAGS &= (uint8_t)~FLAG_RX;

    return byte;
}
