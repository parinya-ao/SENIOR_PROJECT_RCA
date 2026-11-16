#pragma once
inline bool updi_uart_enabled() { return monitor; }
inline bool updi_uart_rx_poll() { return input_pending; }
inline uint8_t updi_uart_rx() { input_pending = false; return input; }
