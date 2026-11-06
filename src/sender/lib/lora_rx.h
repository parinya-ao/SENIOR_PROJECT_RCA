#ifndef LORA_RX_H
#define LORA_RX_H

#include "lora.h"

void lora_rx_setup();
void lora_rx_init_lora(Address my_addr, float freq, int8_t tx_power, uint8_t long_range);
void lora_rx_start_lora();
void lora_rx_stop_lora();
void lora_rx_hello_boot();

#endif
