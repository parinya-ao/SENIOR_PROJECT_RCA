#include <Wire.h>

#include "io.h"
#include "debug.h"
#include "iw/core/byte_codec.h"
#include "iw/tracker/radio/packets.h"

using namespace iw::tracker::radio;

#include "main.h" 
#include "espcomm.h"
#include "lora_rx.h"


#define A0  PIN_PA7
#define A1  PIN_PA6
#define BASE_ADDRESS 0x20

#define I2C_RESET_INTERVAL 60000

struct LoraConfig {
    uint8_t addr;
    float   freq;
    int8_t  tx_power;
    uint8_t long_range;
} __attribute__((packed));

// I2C callbacks expose volatile buffers. Decode the application-local schema
// explicitly while keeping little-endian conversion in iw_core.
static void DecodeLoraConfig(const volatile uint8_t* input, LoraConfig* config) {
    config->addr = input[0];
    uint8_t frequency_bytes[4] = {input[1], input[2], input[3], input[4]};
    uint32_t frequency_bits = iw::core::LoadLittleEndian32(frequency_bytes);
    memcpy(&config->freq, &frequency_bits, sizeof(config->freq));
    config->tx_power = static_cast<int8_t>(input[5]);
    config->long_range = input[6];
}

static void StoreI2c16(volatile uint8_t* destination, uint16_t value) {
    uint8_t bytes[2];
    iw::core::StoreLittleEndian16(bytes, value);
    destination[0] = bytes[0];
    destination[1] = bytes[1];
}

uint8_t i2c_address;
volatile uint8_t rx_buf[32];
volatile uint8_t rx_len = 0;
volatile uint8_t tx_buf[32];
volatile uint8_t tx_len = 0;
volatile uint8_t last_cmd = 0;
volatile bool is_ready = true;
LoraConfig config;
extern int16_t current_temperature;

// read data from master
void onReceive(int byteCount) {
    rx_len = byteCount;
    if (rx_len) {
        for (uint8_t i = 0; i<rx_len; i++) {
            rx_buf[i] = Wire.read();
        }
        last_cmd = rx_buf[0];
        if ( (last_cmd != I2C_CMD_IS_READY) &&
             (last_cmd != I2C_CMD_READ_RESULT)) {
            // normal commands other than 'ready check' and 'read result'
            // require some time to process; is_ready flag is used to indicate
            // whether the processing is done
            is_ready = false;
        }
    }
}

// send data to master
void onRequest() {
    if (last_cmd == I2C_CMD_IS_READY) {
        Wire.write(is_ready);
    }
    else if ((last_cmd == I2C_CMD_READ_RESULT) && tx_len) {
        Wire.write((char*)tx_buf, tx_len);
    }
    else {
        Wire.write(0xFF);
    }
}

// recieve data from lora tracker and write to buffer
//class Task1: public virtual Task {
//  private:
//    uint32_t _ts;
//  public:
//    virtual const char* GetName() {
//      return "Task1";
//    }
//  
//    virtual TASK(Run()) {
//      TASK_BEGIN();
//      report.quality = rand() % 101;
//      ringbuf.WriteByte(0x12);             // type of report
//      ringbuf.WriteByte(sizeof(report));   // data
//      ringbuf.Write(report);               // write to struct
//      TASK_END();
//    }
//  
//  } task1;

// read data from buffer and send to esp32
class TaskI2CManager: public virtual Task {
private:
    // int quality = 0;
    uint32_t _ts;
    uint8_t _cmd;
public:
    virtual const char* GetName() {
        return "I2CManager";
    }
  
    virtual TASK(Run()) {
        TASK_BEGIN();
        for (;;) {
            TASK_WAIT_UNTIL(rx_len != 0);
            LED1_ON();
            _cmd = rx_buf[0];
            DEBUG_TS("%s Command = %d\r\n", GetName(), _cmd);
            rx_len = 0;   // clear flag

            // prepare data
            if (_cmd == I2C_CMD_QUERY_BUFFER_LEN) {
                tx_len = 2;
                uint16_t length = ringbuf.Used();
                DEBUG_TS("%s Ringbuf length = %d\r\n", GetName(), length);
                StoreI2c16(tx_buf, length);
            }
            else if (_cmd == I2C_CMD_REQUEST_DATA) {
                uint8_t length = rx_buf[1];
                DEBUG_TS("%s Requesting %d bytes\r\n", GetName(), length);
                if (length > 32) {
                    tx_len = 0;  // invalid request
                }
                else {
                    tx_len = length;
                ringbuf.Read((void*)tx_buf, tx_len);
                if (ringbuf.Empty()) {
                        digitalWriteFast(PIN_INT, LOW);
                    }
                }
            }
            else if (_cmd == I2C_CMD_CONFIG_LORA) {
                DecodeLoraConfig(rx_buf + 1, &config);
                DEBUG_TS(
                    "%s Config LoRa: "
                    "addr=%" PRIu8 ","
                    "freq=%" PRIu16 ".%02" PRIu16 ","
                    "tx_power=%" PRId8 ","
                    "long_range=%" PRIu8 "\r\n",
                    GetName(),
                    config.addr,
                    (uint16_t)config.freq,
                    (uint16_t)(((uint32_t)(config.freq*100)) % 100),
                    config.tx_power,
                    config.long_range);
                lora_rx_init_lora(config.addr, config.freq, config.tx_power, config.long_range);
            }
            else if (_cmd == I2C_CMD_START_LORA) {
                DEBUG_TS("%s LoRa started\r\n", GetName());
                lora_rx_start_lora();
            }
            else if (_cmd == I2C_CMD_STOP_LORA) {
                DEBUG_TS("%s LoRa stopped\r\n", GetName());
                lora_rx_stop_lora();
            }
            else if (_cmd == I2C_CMD_READ_TEMPERATURE) {
                DEBUG_TS("%s Read temperature\r\n", GetName());
                tx_len = 2;
                DEBUG_TS("%s Current temperature = %d\r\n", GetName(), current_temperature);
                StoreI2c16(tx_buf, static_cast<uint16_t>(current_temperature));
            }

            is_ready = true;
            LED1_OFF();
        }
        TASK_END();
    } 
} taskI2CManager;

/***********************************************
 * TODO investigate why this is needed
 */
class TaskI2CReset: public virtual Task {
private:
    uint32_t _ts;
public:
    virtual const char* GetName() {
        return "I2CReset";
    }

    virtual TASK(Run()) {
        TASK_BEGIN();
        for (;;) {
            Wire.end();
            TASK_DELAY(50, _ts);
            Wire.begin(i2c_address);
            DEBUG_TS("I2C begin: %X\r\n", i2c_address);
            TASK_DELAY(I2C_RESET_INTERVAL, _ts);
        }
        TASK_END();
    }

} taskI2CReset;

/***********************************************
 * 
 */
void espcomm_setup() {
    pinMode(A0, INPUT);
    pinMode(A1, INPUT);

    uint8_t a0 = digitalRead(A0);
    uint8_t a1 = digitalRead(A1);
    i2c_address = 0x20 | (a1 << 1) | a0;
    DEBUG_TS("address = %d  %d%d\r\n", i2c_address, a1, a0);

    scheduler.Add(&taskI2CManager);
    //scheduler.Add(&taskI2CReset);

    Wire.onReceive(onReceive);
    Wire.onRequest(onRequest);
    int slave_address = i2c_address;
    Wire.begin(i2c_address);
}
