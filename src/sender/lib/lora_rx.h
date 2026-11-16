#ifndef LORA_RX_H
#define LORA_RX_H

#include "../../../stable_lib/lora/lora.h"

void lora_rx_setup();
void lora_rx_init_lora(Address my_addr);
void lora_rx_reject_config();
void lora_rx_start_lora();
void lora_rx_stop_lora();
void lora_rx_hello_boot();

#endif
