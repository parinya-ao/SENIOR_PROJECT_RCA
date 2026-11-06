#ifndef ESPCOMM_H
#define ESPCOMM_H

#include <Arduino.h>

extern volatile uint8_t rx_buf[32];
extern volatile uint8_t rx_len;
extern volatile uint8_t tx_buf[32];
extern volatile uint8_t tx_len;
extern int16_t receive_message;

///////////////////////////////////////////////////////////////////////////
// Query whether the latest I2C command has been processed.
// Next request returns a single byte; 1 means the board is ready for request
// or next command
#define I2C_CMD_IS_READY 0x00

///////////////////////////////////////////////////////////////////////////
// Read result from previous data-reading command.
// By sending this command, the master needs to ensure the previous command
// has been processed via I2C_CMD_IS_READY
#define I2C_CMD_READ_RESULT 0x01

///////////////////////////////////////////////////////////////////////////
// Query for ring buffer's length.
// Once this command is ready, the I2C_CMD_READ_RESULT will return 16-bit
// unsigned int representing the length of the ring buffer
#define I2C_CMD_QUERY_BUFFER_LEN 0x02

///////////////////////////////////////////////////////////////////////////
// Request first chunk of data for specified length from ring buffer.
// The length is an 8-bit unsigned int with the maximum of 32.
// Once this command is ready, the I2C_CMD_READ_RESULT will return a chunk of
// data with the specified length
#define I2C_CMD_REQUEST_DATA 0x03

///////////////////////////////////////////////////////////////////////////
// Configure LoRa subsystem with the following:
// +------+------+----------+------------+
// | addr | freq | tx_power | long_range |
// +------+------+----------+------------+
//  uint8   float    int8        uint8
//    1       4        1           1
#define I2C_CMD_CONFIG_LORA 0x04

///////////////////////////////////////////////////////////////////////////
// Start receiving and processing LoRa packets
#define I2C_CMD_START_LORA 0x05

///////////////////////////////////////////////////////////////////////////
// Stop receiving and processing LoRa packets
#define I2C_CMD_STOP_LORA 0x06

///////////////////////////////////////////////////////////////////////////
// Read temperature measured by AVR128DA28
// Once this command is ready, the I2C_CMD_READ_RESULT will return 16-bit
// signed int representing the temperature in degrees celsius
#define I2C_CMD_READ_TEMPERATURE 0x07

void espcomm_setup();

#endif
