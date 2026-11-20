// Supplies controllable host-monitor flags and bytes to the raw-MVP app.
#ifndef SENIOR_PROJECT_RCA_TESTS_RAW_MVP_STUB_UPDI_UART_H_
#define SENIOR_PROJECT_RCA_TESTS_RAW_MVP_STUB_UPDI_UART_H_

inline bool updi_uart_enabled() { return monitor; }
inline bool updi_uart_rx_poll() { return input_pending; }
inline uint8_t updi_uart_rx() {
  input_pending = false;
  return input;
}

#endif  // SENIOR_PROJECT_RCA_TESTS_RAW_MVP_STUB_UPDI_UART_H_
