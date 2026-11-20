// Incremental bounded UPDI command decoding for the existing reliable transport.
#ifndef SENIOR_PROJECT_RCA_SRC_SHARED_PROTOCOL_INTERACTIVE_COMMAND_H_
#define SENIOR_PROJECT_RCA_SRC_SHARED_PROTOCOL_INTERACTIVE_COMMAND_H_

#include <stddef.h>
#include <stdint.h>

namespace reliable {

/// Decodes `X` + a two-digit byte length + uppercase or lowercase payload hex.
template <size_t Maximum>
class HexDataCommandDecoder {
  static_assert(Maximum > 0U && Maximum <= UINT8_MAX,
                "interactive data capacity must fit one length byte");

 public:
  /// Status of one byte consumed from the host control stream.
  enum class Result : uint8_t {
    kNotCommand,
    kPending,
    kComplete,
    kInvalidHex,
    kInvalidLength,
    kInvalidBuffer,
    kInvalidState,
  };

  /// Consume one ASCII byte without blocking or retaining caller buffers.
  /// @param byte Next byte from the existing UPDI control interface.
  /// @param output Bounded destination buffer supplied by the Gateway app.
  /// @param capacity Writable bytes in `output`.
  /// @return Whether the byte is unrelated, pending, complete, or invalid.
  Result Feed(uint8_t byte, uint8_t* output, size_t capacity) {
    if (state_ == State::kIdle) {
      if (byte != 'X') return Result::kNotCommand;
      if (!HasOutput(output, capacity)) return Result::kInvalidBuffer;
      state_ = State::kLengthHigh;
      length_ = received_ = 0U;
      return Result::kPending;
    }
    if (state_ == State::kComplete) return Result::kInvalidState;
    if (!HasOutput(output, capacity)) {
      Reset();
      return Result::kInvalidBuffer;
    }

    const int8_t digit = HexDigit(byte);
    if (digit < 0) {
      Reset();
      return Result::kInvalidHex;
    }
    if (state_ == State::kLengthHigh) {
      length_ = static_cast<uint8_t>(static_cast<uint8_t>(digit) << 4U);
      state_ = State::kLengthLow;
      return Result::kPending;
    }
    if (state_ == State::kLengthLow) {
      length_ = static_cast<uint8_t>(length_ | static_cast<uint8_t>(digit));
      if (!length_ || length_ > Maximum) {
        Reset();
        return Result::kInvalidLength;
      }
      state_ = State::kPayloadHigh;
      return Result::kPending;
    }
    if (state_ == State::kPayloadHigh) {
      high_nibble_ = static_cast<uint8_t>(digit);
      state_ = State::kPayloadLow;
      return Result::kPending;
    }

    output[received_++] = static_cast<uint8_t>(
        static_cast<uint8_t>(high_nibble_ << 4U) | static_cast<uint8_t>(digit));
    if (received_ == length_) {
      state_ = State::kComplete;
      return Result::kComplete;
    }
    state_ = State::kPayloadHigh;
    return Result::kPending;
  }

  /// Reset after completion or rejection before accepting another command.
  void Reset() {
    state_ = State::kIdle;
    length_ = received_ = high_nibble_ = 0U;
  }

  /// Return the decoded byte length, or zero when the command is not complete.
  uint8_t size() const { return state_ == State::kComplete ? length_ : 0U; }

  /// Report whether the decoder is consuming a command rather than idle.
  bool in_progress() const {
    return state_ != State::kIdle && state_ != State::kComplete;
  }

  /// Route the frame before console commands. Park (P) always interrupts it.
  bool Consumes(uint8_t byte) const {
    return byte == 'X' || (in_progress() && byte != 'P');
  }

 private:
  enum class State : uint8_t {
    kIdle,
    kLengthHigh,
    kLengthLow,
    kPayloadHigh,
    kPayloadLow,
    kComplete,
  };

  static bool HasOutput(const uint8_t* output, size_t capacity) {
    return output != nullptr && capacity >= Maximum;
  }

  static int8_t HexDigit(uint8_t byte) {
    if (byte >= '0' && byte <= '9') return static_cast<int8_t>(byte - '0');
    if (byte >= 'A' && byte <= 'F') return static_cast<int8_t>(byte - 'A' + 10);
    if (byte >= 'a' && byte <= 'f') return static_cast<int8_t>(byte - 'a' + 10);
    return -1;
  }

  State state_ = State::kIdle;
  uint8_t length_ = 0U;
  uint8_t received_ = 0U;
  uint8_t high_nibble_ = 0U;
};

}  // namespace reliable

#endif  // SENIOR_PROJECT_RCA_SRC_SHARED_PROTOCOL_INTERACTIVE_COMMAND_H_
