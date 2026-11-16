// No repository-wide license is declared; existing rights are unchanged.

// Declares the gateway Wire mailbox and its fixed external command codes.

#ifndef SENIOR_PROJECT_RCA_SRC_SENDER_LIB_ESPCOMM_H_
#define SENIOR_PROJECT_RCA_SRC_SENDER_LIB_ESPCOMM_H_

#include <Arduino.h>

// Query whether the latest I2C command has been processed.
// Next request returns a single byte; 1 means the board is ready for request
// or next command
inline constexpr uint8_t kI2cIsReady = 0x00;

// Read result from previous data-reading command.
// By sending this command, the master needs to ensure the previous command
// has been processed via I2C_CMD_IS_READY
inline constexpr uint8_t kI2cReadResult = 0x01;

// Query for ring buffer's length.
// Once this command is ready, the I2C_CMD_READ_RESULT will return 16-bit
// unsigned int representing the length of the ring buffer
inline constexpr uint8_t kI2cQueryBufferLen = 0x02;

// Request first chunk of data for specified length from ring buffer.
// The length is an 8-bit unsigned int with the maximum of 32.
// Once this command is ready, the I2C_CMD_READ_RESULT will return a chunk of
// data with the specified length
inline constexpr uint8_t kI2cRequestData = 0x03;

// Validates the legacy eight-byte radio command, including its command byte.
// Only the generated frequency/power/range are accepted; config cannot retune
// PHY.
// +------+------+----------+------------+
// | addr | freq | tx_power | long_range |
// +------+------+----------+------------+
//  uint8   float    int8        uint8
//    1       4        1           1
inline constexpr uint8_t kI2cConfigLora = 0x04;

// Start receiving and processing LoRa packets
inline constexpr uint8_t kI2cStartLora = 0x05;

// Stop receiving and processing LoRa packets
inline constexpr uint8_t kI2cStopLora = 0x06;

// Read temperature measured by AVR128DA28
// Once this command is ready, the I2C_CMD_READ_RESULT will return 16-bit
// signed int representing the temperature in degrees celsius
inline constexpr uint8_t kI2cReadTemperature = 0x07;

// Reads hardware address straps, registers callbacks and schedules command
// work. Call once from setup after GPIO initialization; callbacks never run
// radio work.
void InitializeEspCommunication();

#endif  // SENIOR_PROJECT_RCA_SRC_SENDER_LIB_ESPCOMM_H_
