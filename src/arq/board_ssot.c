// Generated from config/radio_915.toml and config/lora_system.json.
#include <Arduino.h>
#include "generated/board_ssot.h"
#if defined(LORA_ROLE_SENDER)
const arq_board board_ssot = {PIN_PC3, PIN_PD0, PIN_PD2, PIN_PD3};
void board_ssot_init(void) {
 digitalWrite(board_ssot.cs, HIGH);
 pinMode(board_ssot.cs, OUTPUT);
 pinMode(board_ssot.rst, INPUT);
 pinMode(board_ssot.irq, INPUT);
 pinMode(board_ssot.dio1, INPUT);
}
#elif defined(LORA_ROLE_RECEIVER)
const arq_board board_ssot = {PIN_PD0, PIN_PD1, PIN_PD3, PIN_PD2};
void board_ssot_init(void) {
 digitalWrite(PIN_PD5, HIGH);
 pinMode(PIN_PD5, OUTPUT);
 digitalWrite(PIN_PD6, HIGH);
 pinMode(PIN_PD6, OUTPUT);
 digitalWrite(PIN_PC3, HIGH);
 pinMode(PIN_PC3, OUTPUT);
 pinMode(PIN_PA4, INPUT);
 digitalWrite(PIN_PA7, HIGH);
 pinMode(PIN_PA7, OUTPUT);
 digitalWrite(PIN_PA7, 0);
 digitalWrite(board_ssot.cs, HIGH);
 pinMode(board_ssot.cs, OUTPUT);
 pinMode(board_ssot.rst, INPUT);
 pinMode(board_ssot.irq, INPUT);
 pinMode(board_ssot.dio1, INPUT);
}
#endif
