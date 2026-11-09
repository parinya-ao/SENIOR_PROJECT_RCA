// Encodes and decodes the legacy tracker radio packets without relying on
// compiler-specific struct layout or unaligned pointer casts.
#ifndef IW_TRACKER_RADIO_CODEC_H_
#define IW_TRACKER_RADIO_CODEC_H_

#include <stddef.h>
#include <stdint.h>

#include "iw/tracker/radio/packets.h"

namespace iw::tracker::radio {

inline constexpr size_t kReportEntryBytes = 24U;
inline constexpr size_t kPacketAdvertiseBytes = 2U;
inline constexpr size_t kPacketAckBytes = 2U;
inline constexpr size_t kPacketReportBytes = 2U + kReportEntryBytes;
inline constexpr size_t kPacketReportWithAckBytes = kPacketReportBytes;
inline constexpr size_t kPacketMaintenanceBytes = 2U;
inline constexpr size_t kPacketMaintenanceAckBytes = 2U;
inline constexpr size_t kConfigBytes = 27U;
inline constexpr size_t kPacketBootBytes = 6U + kConfigBytes;

// Encodes/decodes one legacy report entry into its frozen 24-byte layout.
[[nodiscard]] bool EncodeReportEntry(const ReportEntry& entry, uint8_t* output,
                                     size_t output_size) noexcept;
// Decodes a report entry only when input_size contains the complete layout.
[[nodiscard]] bool DecodeReportEntry(const uint8_t* input, size_t input_size,
                                     ReportEntry* entry) noexcept;

// Encodes/decodes the legacy two-byte ADVERTISE packet.
[[nodiscard]] bool EncodePacketAdvertise(const PacketAdvertise& packet,
                                         uint8_t* output,
                                         size_t output_size) noexcept;
// Decodes an ADVERTISE packet only when input_size is exactly its frozen size.
[[nodiscard]] bool DecodePacketAdvertise(const uint8_t* input,
                                         size_t input_size,
                                         PacketAdvertise* packet) noexcept;

// Encodes/decodes the legacy report packet.
[[nodiscard]] bool EncodePacketReport(const PacketReport& packet,
                                      uint8_t* output,
                                      size_t output_size) noexcept;
// Decodes a REPORT packet only when input_size is exactly its frozen size.
[[nodiscard]] bool DecodePacketReport(const uint8_t* input, size_t input_size,
                                      PacketReport* packet) noexcept;

// Encodes/decodes the legacy report-with-ack packet.
[[nodiscard]] bool EncodePacketReportWithAck(const PacketReportWithAck& packet,
                                             uint8_t* output,
                                             size_t output_size) noexcept;
// Decodes a REPORT_WITH_ACK packet only when input_size is exactly its frozen
// size.
[[nodiscard]] bool DecodePacketReportWithAck(
    const uint8_t* input, size_t input_size,
    PacketReportWithAck* packet) noexcept;

// Encodes/decodes the legacy two-byte ACK packet.
[[nodiscard]] bool EncodePacketAck(const PacketAck& packet, uint8_t* output,
                                   size_t output_size) noexcept;
// Decodes an ACK packet only when input_size is exactly its frozen size.
[[nodiscard]] bool DecodePacketAck(const uint8_t* input, size_t input_size,
                                   PacketAck* packet) noexcept;

// Encodes/decodes the legacy BOOT packet, including its packed Config bytes.
[[nodiscard]] bool EncodePacketBoot(const PacketBoot& packet, uint8_t* output,
                                    size_t output_size) noexcept;
// Decodes a BOOT packet only when input_size is exactly its frozen size.
[[nodiscard]] bool DecodePacketBoot(const uint8_t* input, size_t input_size,
                                    PacketBoot* packet) noexcept;

// Encodes/decodes the legacy maintenance command packet.
[[nodiscard]] bool EncodePacketMaintenance(const PacketMaintenance& packet,
                                           uint8_t* output,
                                           size_t output_size) noexcept;
// Decodes a maintenance packet only when input_size is exactly its frozen size.
[[nodiscard]] bool DecodePacketMaintenance(const uint8_t* input,
                                           size_t input_size,
                                           PacketMaintenance* packet) noexcept;

// Encodes/decodes the legacy maintenance acknowledgement packet.
[[nodiscard]] bool EncodePacketMaintenanceAck(
    const PacketMaintenanceAck& packet, uint8_t* output,
    size_t output_size) noexcept;
// Decodes a maintenance acknowledgement only when input_size is exactly its
// frozen size.
[[nodiscard]] bool DecodePacketMaintenanceAck(
    const uint8_t* input, size_t input_size,
    PacketMaintenanceAck* packet) noexcept;

}  // namespace iw::tracker::radio

#endif  // IW_TRACKER_RADIO_CODEC_H_
