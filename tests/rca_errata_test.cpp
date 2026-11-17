// Characterization only: compile real installed driver with both existing
// options.
#define main characterized_driver_main
#include "radiolib_hal_test.cpp"
#undef main
int main() {
  Bus bus(9);
  Module module(&bus, 1, 2, 3, 4);
  SX1276 radio(&module);
  assert(radio.begin(915, 125, 7, 5, 0x12, 2, 8, 0) == 0);
  bus.regs[0x31] = 0xc3;
  bus.regs[0x2f] = 0x20;
  assert(radio.startReceive() == 0);
#if RADIOLIB_FIX_ERRATA_SX127X
  assert(bus.regs[0x31] == 0x43 && bus.regs[0x2f] == 0x40 &&
         bus.regs[0x30] == 0);
#else
  assert(bus.regs[0x31] == 0xc3 && bus.regs[0x2f] == 0x20);
#endif
  assert(bus.regs[6] == 0xe4 && bus.regs[7] == 0xc0 && bus.regs[8] == 0 &&
         bus.regs[1] == 0x8d);
  puts(
      "real driver errata option: modeled RX registers verified; no RF "
      "inference");
}
