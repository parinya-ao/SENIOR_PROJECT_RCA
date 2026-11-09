#include <stdint.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include <Arduino.h>
#include "lora.h"
#include <RadioLib.h>

namespace fake_radio {
State state;
}

namespace fake_spi {
State state;
}

SPIClass SPI;

static unsigned checks;

#define CHECK(condition) do { \
    ++checks; \
    if (!(condition)) { \
        std::fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #condition); \
        return EXIT_FAILURE; \
    } \
} while (0)

static void reset_radio() {
    std::memset(&fake_radio::state, 0, sizeof(fake_radio::state));
    SPI.reset();
}

static void complete_tx() {
    if (fake_radio::state.sent_action != nullptr) {
        fake_radio::state.sent_action();
    }
}

static void deliver(const uint8_t* bytes, size_t length) {
    fake_radio::state.rx_size = length;
    for (size_t i = 0; i < length; ++i) fake_radio::state.rx_data[i] = bytes[i];
    if (fake_radio::state.received_action != nullptr) {
        fake_radio::state.received_action();
    }
}

int main() {
    CHECK(LoRa::is_supported_chip_version(0x11));
    CHECK(LoRa::is_supported_chip_version(0x12));
    CHECK(LoRa::is_supported_chip_version(0x13));
    CHECK(!LoRa::is_supported_chip_version(0x10));
    CHECK(!LoRa::is_supported_chip_version(0x22));

    reset_radio();
    fake_spi::state.swap_succeeds = false;
    LoRa failed_spi_route;
    CHECK(!failed_spi_route.init(0));
    CHECK(failed_spi_route.last_error() == RADIOLIB_ERR_UNKNOWN);
    CHECK(fake_spi::state.swap_count == 1);
    CHECK(fake_radio::state.begin_calls == 0);

    reset_radio();
    LoRa smoke;
    CHECK(fake_radio::state.module_cs_pin == PIN_PC3);
    CHECK(fake_radio::state.module_irq_pin == PIN_PD2);
    CHECK(fake_radio::state.module_reset_pin == PIN_PD0);
    CHECK(fake_radio::state.module_dio1_pin == PIN_PD3);
    uint8_t version = 0;
    CHECK(smoke.read_chip_version(&version) == RADIOLIB_ERR_NONE);
    CHECK(version == 0x12);
    CHECK(fake_spi::state.route == SPI1_SWAP_DEFAULT);
    CHECK(fake_spi::state.transfer_count == 2);
    CHECK(fake_spi::state.transfer_bytes[0] == 0x42);
    CHECK(fake_spi::state.transfer_bytes[1] == 0x00);
    CHECK(fake_spi::state.cs_pin == 13);
    CHECK(fake_spi::state.cs_low_seen && fake_spi::state.cs_high_seen);
    CHECK(smoke.init(0));
    CHECK(fake_radio::state.spi1_route_at_begin);
    CHECK(fake_radio::state.frequency_mhz == 915.0f);
    CHECK(fake_radio::state.tx_power_dbm == 10);
    CHECK(fake_radio::state.spreading_factor == 7);
    CHECK(fake_radio::state.bandwidth_khz == 125.0f);
    CHECK(fake_radio::state.coding_rate == 5);
    CHECK(fake_radio::state.sync_word == 0x12);
    CHECK(fake_radio::state.preamble_symbols == 8);
    CHECK(fake_radio::state.crc_enabled);
    CHECK(!fake_radio::state.iq_inverted);
    CHECK(fake_radio::state.explicit_header);
    CHECK(fake_radio::state.gain == 0);
    CHECK(fake_radio::state.begin_calls == 1);
    CHECK(fake_radio::state.current_limit_ma == 200);
    CHECK(fake_radio::state.current_limit_calls == 1);
    CHECK(fake_radio::state.frequency_set_calls == 0);
    CHECK(fake_radio::state.output_power_set_calls == 0);

    reset_radio();
    fake_radio::state.begin_status = -7;
    LoRa failed_begin;
    CHECK(!failed_begin.init(0));
    CHECK(failed_begin.last_error() == -7);
    CHECK(fake_radio::state.begin_calls == 1);
    CHECK(fake_radio::state.current_limit_calls == 0);
    CHECK(fake_radio::state.receive_starts == 0);

    reset_radio();
    LoRa tx;
    CHECK(tx.init(0));
    CHECK(fake_radio::state.node_address_calls == 0);
    fake_radio::state.airtime_us = 123456;
    CHECK(tx.time_on_air_us(13) == 123456);
    CHECK(fake_radio::state.airtime_length == 17);
    uint8_t payload[] = {0x08, 0x01, 'H', 'i'};
    CHECK(tx.send(1, 0x34, 0x12, payload, sizeof(payload)) == RADIOLIB_ERR_NONE);
    payload[0] = 0xff;
    const uint8_t expected_tx[] = {1, 0, 0x34, 0x12, 0x08, 0x01, 'H', 'i'};
    CHECK(fake_radio::state.tx_size == sizeof(expected_tx));
    CHECK(std::memcmp(fake_radio::state.tx_data, expected_tx, sizeof(expected_tx)) == 0);
    CHECK(!tx.send_done());
    complete_tx();
    CHECK(tx.send_done());
    CHECK(fake_radio::state.receive_starts == 2);

    reset_radio();
    LoRa software_address;
    CHECK(software_address.init(5));
    CHECK(software_address.my_address() == 5);
    software_address.set_my_address(7);
    CHECK(software_address.my_address() == 7);
    CHECK(fake_radio::state.node_address_calls == 0);

    reset_radio();
    LoRa failed_start;
    CHECK(failed_start.init(0));
    fake_radio::state.start_transmit_status = -7;
    CHECK(failed_start.send(1, payload, sizeof(payload)) == -7);
    CHECK(fake_radio::state.receive_starts == 2);
    CHECK(!failed_start.send_done());

    reset_radio();
    LoRa oversized_tx;
    CHECK(oversized_tx.init(0));
    uint8_t too_large[252] = {};
    CHECK(oversized_tx.send(1, too_large, sizeof(too_large)) ==
          RADIOLIB_ERR_PACKET_TOO_LONG);
    CHECK(fake_radio::state.tx_data == nullptr);

    reset_radio();
    LoRa failed_finish;
    CHECK(failed_finish.init(0));
    CHECK(failed_finish.send(1, payload, sizeof(payload)) == RADIOLIB_ERR_NONE);
    complete_tx();
    fake_radio::state.finish_transmit_status = -8;
    CHECK(!failed_finish.send_done());
    CHECK(fake_radio::state.receive_starts == 2);
    CHECK(!failed_finish.send_done());

    reset_radio();
    LoRa failed_rx_restart;
    CHECK(failed_rx_restart.init(0));
    CHECK(failed_rx_restart.send(1, payload, sizeof(payload)) == RADIOLIB_ERR_NONE);
    complete_tx();
    fake_radio::state.start_receive_status = -9;
    CHECK(!failed_rx_restart.send_done());
    CHECK(failed_rx_restart.last_error() == -9);
    CHECK(failed_rx_restart.send(1, payload, sizeof(payload)) ==
          RADIOLIB_ERR_UNKNOWN);

    reset_radio();
    LoRa rx;
    CHECK(rx.init(1));
    const uint8_t rx_packet[] = {1, 0, 0x34, 0x12, 'O', 'K'};
    deliver(rx_packet, sizeof(rx_packet));
    CHECK(rx.available());
    Address source = 0, destination = 0;
    uint8_t id = 0, flags = 0, output[4] = {}, length = 0;
    CHECK(rx.recv(&source, &destination, &id, &flags, output, &length,
                  sizeof(output)) == RADIOLIB_ERR_NONE);
    CHECK(source == 0 && destination == 1 && id == 0x34 && flags == 0x12);
    CHECK(length == 2 && output[0] == 'O' && output[1] == 'K');
    CHECK(fake_radio::state.receive_starts == 2);

    const uint8_t short_packet[] = {1, 0, 0x34};
    deliver(short_packet, sizeof(short_packet));
    CHECK(rx.recv(&source, &destination, &id, &flags, output, &length,
                  sizeof(output)) == RADIOLIB_ERR_UNKNOWN);
    CHECK(fake_radio::state.receive_starts == 3);

    reset_radio();
    LoRa max_packet_radio;
    CHECK(max_packet_radio.init(1));
    uint8_t max_packet[255] = {1, 0, 0x34, 0x12};
    for (size_t i = 4; i < sizeof(max_packet); ++i) {
        max_packet[i] = static_cast<uint8_t>(i);
    }
    deliver(max_packet, sizeof(max_packet));
    uint8_t max_payload[251] = {};
    CHECK(max_packet_radio.recv(&source, &destination, &id, &flags,
                                max_payload, &length, sizeof(max_payload)) ==
          RADIOLIB_ERR_NONE);
    CHECK(length == sizeof(max_payload));
    CHECK(max_payload[250] == static_cast<uint8_t>(254));
    CHECK(fake_radio::state.receive_starts == 2);

    reset_radio();
    LoRa wide_capacity_radio;
    CHECK(wide_capacity_radio.init(1));
    deliver(max_packet, sizeof(max_packet));
    uint8_t wide_payload[256] = {};
    size_t wide_capacity = sizeof(wide_payload);
    CHECK(wide_capacity_radio.recv(&source, &destination, &id, &flags,
                                   wide_payload, &length, wide_capacity) ==
          RADIOLIB_ERR_NONE);
    CHECK(length == sizeof(max_payload));
    CHECK(wide_payload[250] == static_cast<uint8_t>(254));

    std::printf("PASS %u radio-wrapper checks\n", checks);
    return EXIT_SUCCESS;
}
