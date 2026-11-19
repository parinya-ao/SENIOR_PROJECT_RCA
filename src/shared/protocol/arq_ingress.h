#pragma once

#include "arq_diagnostics.h"

namespace arq::app {

/// Foreground counters separating observed IRQs from valid protocol frames.
struct ReceiveCounters {
  uint32_t rx_done;        ///< Number of receive completions observed.
  uint32_t crc_errors;     ///< Number of PHY CRC rejections.
  uint32_t decode_errors;  ///< Number of malformed protocol frames.
  uint16_t
      last_rx_flags;  ///< IRQ flags observed at the last receive completion.
};

/// Outcome of reading one completed radio packet.
enum class FrameRead : uint8_t {
  kValid,       ///< Frame decoded successfully.
  kDiscard,     ///< Length, CRC, read or decode rejected the frame.
  kRadioError,  ///< Radio could not enter standby.
};

/// Captures RX evidence and decodes a complete packet. The caller owns
/// address/session policy, the radio restart, and any fatal state transition.
FrameRead ReadReceivedFrame(const diagnostics::EventContext& context,
                            uint16_t flags, ReceiveCounters& counters,
                            Frame& frame, int16_t& standby_error);

}  // namespace arq::app
