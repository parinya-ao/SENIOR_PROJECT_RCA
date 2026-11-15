#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <Arduino.h>
#include "lora.h"
namespace fake_radio { State state; }
namespace fake_spi { State state; }
SPIClass SPI;
uint32_t host_ms;
void delay(unsigned ms) { host_ms += ms; }
void* operator new(size_t size) { return malloc(size); }
extern "C" bool updi_uart_enabled() { return false; }
extern "C" void updi_uart_tx(uint8_t) {}

int main() {
    SPI.reset();
    LoRa radio;
    assert(radio.init(0));
    assert((fake_radio::state.op_mode & 8)==0);
    uint8_t bytes[] = {8, 1, 'a'};
    assert(radio.send(1, bytes, sizeof bytes) == 0);
    // A stale callback is not physical TxDone for the active transaction.
    fake_radio::state.sent_action();
    assert(!radio.send_done());
    fake_radio::state.irq_flags = 8;
    assert(radio.send_done());
    assert(radio.last_irq()==8);
    assert(radio.send_done());
    assert(fake_radio::state.finish_transmits == 1);
    assert(fake_radio::state.receive_starts == 2);
    assert(radio.send(1, bytes, sizeof bytes) == 0);
    host_ms += 3001;
    assert(!radio.send_done());
    assert(radio.last_error() != 0);
    assert(fake_radio::state.finish_transmits == 1);
    // Timeout recovery leaves a usable radio without reset/reinitialization.
    assert(radio.send(1, bytes, sizeof bytes) == 0);
    fake_radio::state.irq_flags = 8;
    assert(radio.send_done());
    Address src, dst;
    uint8_t id, flags, len, out[4] = {0x55};
    fake_radio::state.rx_size = 0;
    fake_radio::state.irq_flags = 0x40;
    assert(radio.available());
    assert(radio.recv(&src, &dst, &id, &flags, out, &len, sizeof out) != 0);
    assert(len == 0 && out[0] == 0x55);
    fake_radio::state.read_data_status = 0;
    fake_radio::state.rx_size = 6;
    fake_radio::state.irq_flags = 0x60;
    assert(radio.recv(&src, &dst, &id, &flags, out, &len, sizeof out) != 0);
    assert(len == 0 && out[0] == 0x55);
    fake_radio::state.rx_size = 9;
    fake_radio::state.irq_flags = 0x40;
    assert(radio.recv(&src, &dst, &id, &flags, out, &len, sizeof out) != 0);
    assert(len == 0 && out[0] == 0x55);
    fake_radio::state.rx_size = 6;
    fake_radio::state.read_data_status = -7;
    fake_radio::state.irq_flags = 0x60;
    assert(radio.recv(&src, &dst, &id, &flags, out, &len, sizeof out) != 0);
    assert(len == 0 && out[0] == 0x55);
    puts("PASS HAL stale IRQ, exact cleanup, timeout recovery, RX bounds/CRC");
}
