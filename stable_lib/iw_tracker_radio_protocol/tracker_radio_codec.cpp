// Implements explicit codecs for the legacy tracker radio packet schema.
#include "tracker_radio_codec.h"

#include <string.h>

#include "byte_codec.h"

namespace iw::tracker::radio {

namespace {

bool HasSpace(size_t output_size, size_t required) noexcept {
  return required <= output_size;
}

void StoreSigned16(uint8_t* output, int16_t value) noexcept {
  iw::core::StoreLittleEndian16(output, static_cast<uint16_t>(value));
}

void StoreSigned32(uint8_t* output, int32_t value) noexcept {
  iw::core::StoreLittleEndian32(output, static_cast<uint32_t>(value));
}

int16_t LoadSigned16(const uint8_t* input) noexcept {
  return static_cast<int16_t>(iw::core::LoadLittleEndian16(input));
}

int32_t LoadSigned32(const uint8_t* input) noexcept {
  return static_cast<int32_t>(iw::core::LoadLittleEndian32(input));
}

void StoreFloat(uint8_t* output, float value) noexcept {
  uint32_t bits = 0U;
  static_assert(sizeof(bits) == sizeof(value));
  memcpy(&bits, &value, sizeof(bits));
  iw::core::StoreLittleEndian32(output, bits);
}

float LoadFloat(const uint8_t* input) noexcept {
  const uint32_t bits = iw::core::LoadLittleEndian32(input);
  float value = 0.0F;
  memcpy(&value, &bits, sizeof(value));
  return value;
}

void EncodeConfig(const Config& config, uint8_t* output) noexcept {
  output[0] = config.lora_device_address;
  output[1] = config.lora_gateway_address;
  StoreFloat(&output[2], config.lora_freq);
  output[6] = config.lora_tx_power;
  iw::core::StoreLittleEndian16(&output[7], config.collect_interval_day);
  iw::core::StoreLittleEndian16(&output[9], config.collect_interval_night);
  output[11] = config.day_start_hour;
  output[12] = config.day_end_hour;
  output[13] = static_cast<uint8_t>(config.time_zone);
  output[14] = config.use_ack;
  iw::core::StoreLittleEndian16(&output[15], config.ack_timeout);
  output[17] = config.long_range;
  output[18] = config.tx_repeat;
  iw::core::StoreLittleEndian16(&output[19], config.gps_max_wait_for_fix);
  iw::core::StoreLittleEndian16(&output[21], config.next_collect_no_fix);
  iw::core::StoreLittleEndian16(&output[23], config.total_slots);
  iw::core::StoreLittleEndian16(&output[25], config.slot_interval);
}

void DecodeConfig(const uint8_t* input, Config* config) noexcept {
  config->lora_device_address = input[0];
  config->lora_gateway_address = input[1];
  config->lora_freq = LoadFloat(&input[2]);
  config->lora_tx_power = input[6];
  config->collect_interval_day = iw::core::LoadLittleEndian16(&input[7]);
  config->collect_interval_night = iw::core::LoadLittleEndian16(&input[9]);
  config->day_start_hour = input[11];
  config->day_end_hour = input[12];
  config->time_zone = static_cast<int8_t>(input[13]);
  config->use_ack = input[14];
  config->ack_timeout = iw::core::LoadLittleEndian16(&input[15]);
  config->long_range = input[17];
  config->tx_repeat = input[18];
  config->gps_max_wait_for_fix = iw::core::LoadLittleEndian16(&input[19]);
  config->next_collect_no_fix = iw::core::LoadLittleEndian16(&input[21]);
  config->total_slots = iw::core::LoadLittleEndian16(&input[23]);
  config->slot_interval = iw::core::LoadLittleEndian16(&input[25]);
}

}  // namespace

bool EncodeReportEntry(const ReportEntry& entry, uint8_t* output,
                       size_t output_size) noexcept {
  if (output == nullptr || !HasSpace(output_size, kReportEntryBytes)) {
    return false;
  }
  output[0] = entry.year;
  output[1] = entry.month;
  output[2] = entry.day;
  output[3] = entry.hour;
  output[4] = entry.minute;
  output[5] = entry.second;
  iw::core::StoreLittleEndian16(&output[6], entry.vbat);
  StoreSigned32(&output[8], entry.latitude);
  StoreSigned32(&output[12], entry.longitude);
  output[16] = entry.quality;
  output[17] = entry.satellites;
  StoreSigned16(&output[18], entry.temperature);
  iw::core::StoreLittleEndian32(&output[20], entry.ttf);
  return true;
}

bool DecodeReportEntry(const uint8_t* input, size_t input_size,
                       ReportEntry* entry) noexcept {
  if (input == nullptr || entry == nullptr || input_size < kReportEntryBytes) {
    return false;
  }
  entry->year = input[0];
  entry->month = input[1];
  entry->day = input[2];
  entry->hour = input[3];
  entry->minute = input[4];
  entry->second = input[5];
  entry->vbat = iw::core::LoadLittleEndian16(&input[6]);
  entry->latitude = LoadSigned32(&input[8]);
  entry->longitude = LoadSigned32(&input[12]);
  entry->quality = input[16];
  entry->satellites = input[17];
  entry->temperature = LoadSigned16(&input[18]);
  entry->ttf = iw::core::LoadLittleEndian32(&input[20]);
  return true;
}

bool EncodePacketAdvertise(const PacketAdvertise& packet, uint8_t* output,
                           size_t output_size) noexcept {
  if (output == nullptr || !HasSpace(output_size, kPacketAdvertiseBytes)) {
    return false;
  }
  output[0] = packet.type;
  output[1] = packet.seq;
  return true;
}

bool DecodePacketAdvertise(const uint8_t* input, size_t input_size,
                           PacketAdvertise* packet) noexcept {
  if (input == nullptr || packet == nullptr ||
      input_size < kPacketAdvertiseBytes || input[0] != PKT_TYPE_ADVERTISE) {
    return false;
  }
  packet->type = input[0];
  packet->seq = input[1];
  return true;
}

bool EncodePacketReport(const PacketReport& packet, uint8_t* output,
                        size_t output_size) noexcept {
  if (output == nullptr || !HasSpace(output_size, kPacketReportBytes)) {
    return false;
  }
  output[0] = packet.type;
  output[1] = packet.seq;
  return EncodeReportEntry(packet.report, &output[2], output_size - 2U);
}

bool DecodePacketReport(const uint8_t* input, size_t input_size,
                        PacketReport* packet) noexcept {
  if (input == nullptr || packet == nullptr ||
      input_size < kPacketReportBytes || input[0] != PKT_TYPE_REPORT) {
    return false;
  }
  packet->type = input[0];
  packet->seq = input[1];
  return DecodeReportEntry(&input[2], input_size - 2U, &packet->report);
}

bool EncodePacketReportWithAck(const PacketReportWithAck& packet,
                               uint8_t* output, size_t output_size) noexcept {
  if (output == nullptr || !HasSpace(output_size, kPacketReportWithAckBytes)) {
    return false;
  }
  output[0] = packet.type;
  output[1] = packet.seq;
  return EncodeReportEntry(packet.report, &output[2], output_size - 2U);
}

bool DecodePacketReportWithAck(const uint8_t* input, size_t input_size,
                               PacketReportWithAck* packet) noexcept {
  if (input == nullptr || packet == nullptr ||
      input_size < kPacketReportWithAckBytes ||
      input[0] != PKT_TYPE_REPORT_WITH_ACK) {
    return false;
  }
  packet->type = input[0];
  packet->seq = input[1];
  return DecodeReportEntry(&input[2], input_size - 2U, &packet->report);
}

bool EncodePacketAck(const PacketAck& packet, uint8_t* output,
                     size_t output_size) noexcept {
  if (output == nullptr || !HasSpace(output_size, kPacketAckBytes)) {
    return false;
  }
  output[0] = packet.type;
  output[1] = packet.seq;
  return true;
}

bool DecodePacketAck(const uint8_t* input, size_t input_size,
                     PacketAck* packet) noexcept {
  if (input == nullptr || packet == nullptr || input_size < kPacketAckBytes ||
      input[0] != PKT_TYPE_ACK) {
    return false;
  }
  packet->type = input[0];
  packet->seq = input[1];
  return true;
}

bool EncodePacketBoot(const PacketBoot& packet, uint8_t* output,
                      size_t output_size) noexcept {
  if (output == nullptr || !HasSpace(output_size, kPacketBootBytes)) {
    return false;
  }
  output[0] = packet.type;
  iw::core::StoreLittleEndian16(&output[1], packet.firmware);
  output[3] = packet.device_model;
  output[4] = packet.reset_flags;
  output[5] = packet.checkpoint;
  EncodeConfig(packet.config, &output[6]);
  return true;
}

bool DecodePacketBoot(const uint8_t* input, size_t input_size,
                      PacketBoot* packet) noexcept {
  if (input == nullptr || packet == nullptr || input_size < kPacketBootBytes ||
      input[0] != PKT_TYPE_BOOT) {
    return false;
  }
  packet->type = input[0];
  packet->firmware = iw::core::LoadLittleEndian16(&input[1]);
  packet->device_model = input[3];
  packet->reset_flags = input[4];
  packet->checkpoint = input[5];
  DecodeConfig(&input[6], &packet->config);
  return true;
}

bool EncodePacketMaintenance(const PacketMaintenance& packet, uint8_t* output,
                             size_t output_size) noexcept {
  if (output == nullptr || !HasSpace(output_size, kPacketMaintenanceBytes)) {
    return false;
  }
  output[0] = packet.type;
  output[1] = packet.command;
  return true;
}

bool DecodePacketMaintenance(const uint8_t* input, size_t input_size,
                             PacketMaintenance* packet) noexcept {
  if (input == nullptr || packet == nullptr ||
      input_size < kPacketMaintenanceBytes ||
      input[0] != PKT_TYPE_MAINTENANCE) {
    return false;
  }
  packet->type = input[0];
  packet->command = input[1];
  return true;
}

bool EncodePacketMaintenanceAck(const PacketMaintenanceAck& packet,
                                uint8_t* output, size_t output_size) noexcept {
  if (output == nullptr || !HasSpace(output_size, kPacketMaintenanceAckBytes)) {
    return false;
  }
  output[0] = packet.type;
  output[1] = packet.response;
  return true;
}

bool DecodePacketMaintenanceAck(const uint8_t* input, size_t input_size,
                                PacketMaintenanceAck* packet) noexcept {
  if (input == nullptr || packet == nullptr ||
      input_size < kPacketMaintenanceAckBytes ||
      input[0] != PKT_TYPE_MAINTENANCE_ACK) {
    return false;
  }
  packet->type = input[0];
  packet->response = input[1];
  return true;
}

}  // namespace iw::tracker::radio
