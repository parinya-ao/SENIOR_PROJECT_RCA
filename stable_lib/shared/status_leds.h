// Nonblocking status indicators shared by Gateway and Tracker firmware.

#ifndef SENIOR_PROJECT_RCA_SRC_SHARED_STATUS_LEDS_H_
#define SENIOR_PROJECT_RCA_SRC_SHARED_STATUS_LEDS_H_

#include <Arduino.h>
#include <stdint.h>

namespace status_leds {

class Controller {
 public:
  Controller(uint8_t led1_pin, uint8_t led2_pin, uint8_t led_on_level,
             uint8_t led_off_level, uint32_t led1_interval_ms,
             uint32_t tx_interval_ms)
      : led1_pin_(led1_pin),
        led2_pin_(led2_pin),
        led_on_level_(led_on_level),
        led_off_level_(led_off_level),
        led1_interval_ms_(led1_interval_ms),
        tx_interval_ms_(tx_interval_ms) {}

  void Begin(uint32_t now) {
    digitalWrite(led1_pin_, led_off_level_);
    digitalWrite(led2_pin_, led_off_level_);
    pinMode(led1_pin_, OUTPUT);
    pinMode(led2_pin_, OUTPUT);
    last_led1_toggle_ = now;
    led1_on_ = false;
    tx_active_ = false;
    tx_led_on_ = false;
  }

  void Poll(uint32_t now, bool transmitting) {
    if (now - last_led1_toggle_ >= led1_interval_ms_) {
      last_led1_toggle_ = now;
      led1_on_ = !led1_on_;
      digitalWrite(led1_pin_, led1_on_ ? led_on_level_ : led_off_level_);
    }

    if (!transmitting) {
      if (tx_active_) digitalWrite(led2_pin_, led_off_level_);
      tx_active_ = false;
      tx_led_on_ = false;
      return;
    }

    if (!tx_active_) {
      tx_active_ = true;
      tx_led_on_ = true;
      last_tx_toggle_ = now;
      digitalWrite(led2_pin_, led_on_level_);
    } else if (now - last_tx_toggle_ >= tx_interval_ms_) {
      last_tx_toggle_ = now;
      tx_led_on_ = !tx_led_on_;
      digitalWrite(led2_pin_, tx_led_on_ ? led_on_level_ : led_off_level_);
    }
  }

 private:
  uint8_t led1_pin_;
  uint8_t led2_pin_;
  uint8_t led_on_level_;
  uint8_t led_off_level_;
  uint32_t led1_interval_ms_;
  uint32_t tx_interval_ms_;
  uint32_t last_led1_toggle_ = 0;
  uint32_t last_tx_toggle_ = 0;
  bool led1_on_ = false;
  bool tx_active_ = false;
  bool tx_led_on_ = false;
};

}  // namespace status_leds

#endif  // SENIOR_PROJECT_RCA_SRC_SHARED_STATUS_LEDS_H_
