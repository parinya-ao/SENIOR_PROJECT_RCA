// Defers Wire host commands to foreground tasks; callbacks only move bounded
// bytes.

#include "espcomm.h"

#include <Wire.h>

#include "byte_codec.h"
#include "debug.h"
#include "gateway_app.h"
#include "io.h"
#include "lora_config.h"
#include "lora_rx.h"
#include "tracker_radio_packets.h"

namespace {
constexpr uint32_t kI2cResetIntervalMs =
    application_config::gateway::kI2cResetIntervalMs;

// Stores little-endian host results without serializing a native integer
// object.
static void StoreI2c16(volatile uint8_t* destination, uint16_t value) {
  uint8_t bytes[kI2cUint16ResponseBytes];
  iw::core::StoreLittleEndian16(bytes, value);
  destination[0] = bytes[0];
  destination[1] = bytes[1];
}

// Address straps are sampled once before registering Wire callbacks.
uint8_t i2c_address;
// Wire callback writes bounded bytes; foreground consumes only after callback
// return. The host must await IS_READY before submitting another work command.
volatile uint8_t rx_buf[kI2cMaxPayloadLength];
volatile uint8_t rx_len = 0;
// Foreground results are borrowed by Wire request callbacks until replaced.
volatile uint8_t tx_buf[kI2cMaxPayloadLength];
volatile uint8_t tx_len = 0;
// Byte-wide callback/task flags are atomic on AVR; buffers are not general
// locks.
volatile uint8_t last_cmd = 0;
volatile bool is_ready = true;
// Accepted local address; generated PHY parameters cannot be overridden over
// I2C.
LoraConfig config;

// Drains one Wire command into the bounded mailbox; never performs radio I/O.
void HandleReceive(int byte_count) {
  if (byte_count <= 0) {
    rx_len = 0;
    return;
  }
  rx_len = byte_count > sizeof(rx_buf)
               ? static_cast<uint8_t>(sizeof(rx_buf) + 1)
               : static_cast<uint8_t>(byte_count);
  for (int i = 0; i < byte_count; ++i) {
    const uint8_t value = static_cast<uint8_t>(Wire.read());
    if (i < sizeof(rx_buf)) rx_buf[i] = value;
  }
  if (rx_len) {
    last_cmd = rx_buf[kI2cCommandOffset];
    if ((last_cmd != kI2cIsReady) && (last_cmd != kI2cReadResult)) {
      // normal commands other than 'ready check' and 'read result'
      // require some time to process; is_ready flag is used to indicate
      // whether the processing is done
      is_ready = false;
    }
  }
}

// Returns readiness or the prior result; never waits for foreground work.
void HandleRequest() {
  if (last_cmd == kI2cIsReady) {
    Wire.write(is_ready);
  } else if ((last_cmd == kI2cReadResult) && tx_len) {
    // Wire reads this foreground result buffer during its request callback.
    Wire.write(
        reinterpret_cast<const char*>(const_cast<const uint8_t*>(tx_buf)),
        tx_len);
  } else {
    Wire.write(kI2cReadErrorResponse);
  }
}

// Executes host commands in cooperative foreground context, outside Wire
// callbacks.
class I2cCommandTask : public virtual Task {
 private:
  uint8_t command_;
  uint8_t command_length_;

 public:
  virtual const char* GetName() { return "I2CManager"; }

  virtual TASK(Run()) {
    TASK_BEGIN();
    for (;;) {
      TASK_WAIT_UNTIL(rx_len != 0);
      LED1_ON();
      command_ = rx_buf[kI2cCommandOffset];
      // Consuming the mailbox must not erase the decoder's length input.
      command_length_ = rx_len;
      DEBUG_TS("%s Command = %d\r\n", GetName(), command_);
      rx_len = 0;  // clear flag

      // prepare data
      if (command_ == kI2cQueryBufferLen) {
        tx_len = kI2cUint16ResponseBytes;
        uint16_t length = gateway_app::ringbuf.Used();
        DEBUG_TS("%s Ringbuf length = %d\r\n", GetName(), length);
        StoreI2c16(tx_buf, length);
      } else if (command_ == kI2cRequestData) {
        uint8_t length = rx_buf[kI2cRequestDataLengthOffset];
        DEBUG_TS("%s Requesting %d bytes\r\n", GetName(), length);
        if (length > kI2cMaxPayloadLength) {
          tx_len = 0;  // invalid request
        } else {
          tx_len = length;
          // Only foreground writes result bytes; the host waits for the ready
          // latch.
          gateway_app::ringbuf.Read(const_cast<uint8_t*>(tx_buf), tx_len);
          if (gateway_app::ringbuf.Empty()) {
            digitalWriteFast(PIN_INT, LOW);
          }
        }
      } else if (command_ == kI2cConfigLora) {
        if (IsRadioBenchActive()) {
          DEBUG_TS("%s LoRa is reserved by the bench\r\n", GetName());
        } else if (DecodeLoraConfig(rx_buf, command_length_, &config)) {
          DEBUG_TS("%s Config LoRa address=%" PRIu8 "\r\n", GetName(),
                   config.addr);
          InitializeRadio(config.addr);
        } else {
          RejectRadioConfiguration();
        }
      } else if (command_ == kI2cStartLora) {
        DEBUG_TS("%s LoRa started\r\n", GetName());
        if (!IsRadioBenchActive()) StartRadioTransaction();
      } else if (command_ == kI2cStopLora) {
        DEBUG_TS("%s LoRa stopped\r\n", GetName());
        if (!IsRadioBenchActive()) StopRadio();
      } else if (command_ == kI2cReadTemperature) {
        DEBUG_TS("%s Read temperature\r\n", GetName());
        tx_len = kI2cUint16ResponseBytes;
        DEBUG_TS("%s Current temperature = %d\r\n", GetName(),
                 gateway_app::current_temperature);
        StoreI2c16(tx_buf,
                   static_cast<uint16_t>(gateway_app::current_temperature));
      }

      is_ready = true;
      LED1_OFF();
    }
    TASK_END();
  }
} i2c_command_task;

// Retains the disabled legacy bus recovery task; no scheduling behavior is
// changed. Its historical reason is unknown, so it remains available but
// unregistered.
class I2cResetTask : public virtual Task {
 private:
  uint32_t timestamp_ms_;

 public:
  virtual const char* GetName() { return "I2CReset"; }

  virtual TASK(Run()) {
    TASK_BEGIN();
    for (;;) {
      Wire.end();
      TASK_DELAY(GatewaySSOT::Tasks::I2C_RESET_SETTLE_MS, timestamp_ms_);
      Wire.begin(i2c_address);
      DEBUG_TS("I2C begin: %X\r\n", i2c_address);
      TASK_DELAY(kI2cResetIntervalMs, timestamp_ms_);
    }
    TASK_END();
  }

} i2c_reset_task;

}  // namespace

// Registers bounded Wire callbacks after reading the existing address straps.
void InitializeEspCommunication() {
  pinMode(GatewaySSOT::Pins::ANALOG_IN_0, INPUT);
  pinMode(GatewaySSOT::Pins::ANALOG_IN_1, INPUT);

  uint8_t a0 = digitalRead(GatewaySSOT::Pins::ANALOG_IN_0);
  uint8_t a1 = digitalRead(GatewaySSOT::Pins::ANALOG_IN_1);
  i2c_address = GatewaySSOT::Comm::I2C_ADDRESS_BASE |
                (a1 << GatewaySSOT::Comm::I2C_ADDRESS_STRAP_SHIFT) | a0;
  DEBUG_TS("address = %d  %d%d\r\n", i2c_address, a1, a0);

  gateway_app::scheduler.Add(&i2c_command_task);
  // scheduler.Add(&i2c_reset_task);

  Wire.onReceive(HandleReceive);
  Wire.onRequest(HandleRequest);
  Wire.begin(i2c_address);
}
