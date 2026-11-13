#pragma once
#include <Arduino.h>
#include <updi_uart.h>
#include <stdio.h>
#include <string.h>

struct LogSlot { char text[192]; };
static LogSlot log_slots[16];
static uint8_t log_head,log_tail,log_count,log_offset;
static uint32_t log_overflow;
static char* log_slot() {
    if(log_count==16){++log_overflow;return NULL;}
    char* out=log_slots[log_tail].text;
    log_tail=(log_tail+1)%16;++log_count;return out;
}
static void log_flush() {
    // The UPDI ready byte is a mailbox; never wait for a disconnected reader.
    if(!log_count || !updi_uart_enabled() || _SFR_MEM8(0x0f19))return;
    const char c=log_slots[log_head].text[log_offset++];
    _SFR_MEM8(0x0f18)=c;
    if(!log_slots[log_head].text[log_offset]){
        log_offset=0;log_head=(log_head+1)%16;--log_count;
    }
}
