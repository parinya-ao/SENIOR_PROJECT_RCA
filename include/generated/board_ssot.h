#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
  uint8_t cs, rst, irq, dio1;
} arq_board;
extern const arq_board board_ssot;
void board_ssot_init(void);
#ifdef __cplusplus
}
#endif
#if defined(LORA_ROLE_SENDER)
#define ARQ_SPI_ROUTE SPI1_SWAP_DEFAULT
#elif defined(LORA_ROLE_RECEIVER)
#define ARQ_SPI_ROUTE SPI1_SWAP_DEFAULT
#else
#error "ARQ requires one role"
#endif
