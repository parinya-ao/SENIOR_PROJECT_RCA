#include <stdint.h>
#include <stdio.h>

enum { LOW = 0, HIGH = 1, INPUT = 0, OUTPUT = 1 };
enum {
  PIN_PA4 = 4,
  PIN_PA5 = 5,
  PIN_PA6 = 6,
  PIN_PA7 = 7,
  PIN_PC0 = 16,
  PIN_PC1 = 17,
  PIN_PC2 = 18,
  PIN_PC3 = 19,
  PIN_PD0 = 24,
  PIN_PD1 = 25,
  PIN_PD2 = 26,
  PIN_PD3 = 27,
  PIN_PD5 = 29,
  PIN_PD6 = 30
};
static uint8_t modes[32] = {};
static uint8_t values[32] = {};
static unsigned elapsed_ms = 0;
static unsigned enabled_at = 0;
static bool enabled = false;
static unsigned unsafe_operations = 0;

void digitalWriteFast(uint8_t pin, uint8_t value) {
  values[pin] = value;
  if (pin == PIN_PA7 && modes[pin] == OUTPUT && value == LOW) {
    enabled = true;
    enabled_at = elapsed_ms;
    if (modes[PIN_PD1] != INPUT) ++unsafe_operations;
  }
}

void pinModeFast(uint8_t pin, uint8_t mode) {
  if ((pin == PIN_PA7 || pin == PIN_PD5 || pin == PIN_PD6) && mode == OUTPUT &&
      values[pin] != HIGH)
    ++unsafe_operations;
  if (pin == PIN_PD0 && mode == OUTPUT &&
      (!enabled || elapsed_ms - enabled_at < 10))
    ++unsafe_operations;
  if (pin == PIN_PD1 && mode == OUTPUT) ++unsafe_operations;
  modes[pin] = mode;
}

void delay(unsigned ms) { elapsed_ms += ms; }

#include "receiver_gpio_under_test.h"

#define CHECK(condition)                                           \
  do {                                                             \
    if (!(condition)) {                                            \
      fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #condition); \
      return 1;                                                    \
    }                                                              \
  } while (0)

int main() {
  InitializeReceiverGpio();
  CHECK(LORA_PIN_CS == PIN_PD0);
  CHECK(LORA_PIN_RST == PIN_PD1);
  CHECK(LORA_PIN_IRQ == PIN_PD3);
  CHECK(LORA_PIN_DIO1 == PIN_PD2);
  CHECK(enabled && modes[PIN_PA7] == OUTPUT && values[PIN_PA7] == LOW);
  CHECK(elapsed_ms - enabled_at >= 10);
  CHECK(modes[PIN_PD0] == OUTPUT && values[PIN_PD0] == HIGH);
  CHECK(modes[PIN_PD1] == INPUT);
  CHECK(modes[PIN_PD2] == INPUT && modes[PIN_PD3] == INPUT);
  CHECK(modes[PIN_PC3] == OUTPUT && values[PIN_PC3] == HIGH);
  CHECK(modes[PIN_PA6] == OUTPUT && values[PIN_PA6] == HIGH);
  CHECK(modes[PIN_PA5] == OUTPUT && values[PIN_PA5] == HIGH);
  CHECK(modes[PIN_PA4] == INPUT);
  CHECK(modes[PIN_PD5] == OUTPUT && values[PIN_PD5] == HIGH);
  CHECK(modes[PIN_PD6] == OUTPUT && values[PIN_PD6] == HIGH);
  CHECK(unsafe_operations == 0);
  puts(
      "PASS Receiver GPIO mapping, active-low power, POR and chip-select "
      "ordering");
}
