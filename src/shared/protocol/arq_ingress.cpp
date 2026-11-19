#include "arq_ingress.h"

#include "arq_codec.h"
#include "shared/diagnostics/arq_bench.h"
#include "shared/radio/arq_radio.h"

namespace arq::app {

FrameRead ReadReceivedFrame(const diagnostics::EventContext& context,
                            uint16_t flags, ReceiveCounters& counters,
                            Frame& frame, int16_t& standby_error) {
  ++counters.rx_done;
  counters.last_rx_flags = flags;
  RecordReceiveDiagnostics(context, "RX_IRQ", flags);
  int16_t rc = radio.standby();
  if (rc) {
    standby_error = rc;
    return FrameRead::kRadioError;
  }
  size_t length = radio.getPacketLength();
  uint8_t bytes[arq::kMaxFrameBytes];
  if (length < arq::kHeaderBytes || length > sizeof bytes) {
    arq::diagnostics::RecordEvent(context, "LENGTH_DISCARD", 0, length);
    return FrameRead::kDiscard;
  }
  rc = radio.readData(bytes, length);
  if (rc || (flags & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_PAYLOAD_CRC_ERROR)) {
    if (rc == RADIOLIB_ERR_CRC_MISMATCH ||
        (flags & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_PAYLOAD_CRC_ERROR))
      ++counters.crc_errors;
    arq::diagnostics::RecordEvent(context, "RX_DISCARD", rc, flags);
    return FrameRead::kDiscard;
  }
  arq::diagnostics::RecordFrame(context, "RX", bytes, length,
                                static_cast<int16_t>(radio.getRSSI() * 100),
                                static_cast<int16_t>(radio.getSNR() * 100));
  if (!arq::DecodeFrame(&frame, bytes, length)) {
    ++counters.decode_errors;
    arq::diagnostics::RecordEvent(context, "DECODE_DISCARD", 0, length);
    return FrameRead::kDiscard;
  }
  return FrameRead::kValid;
}

}  // namespace arq::app
