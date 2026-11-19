/// @file
/// Encodes and validates complete ARQ wire frames without radio access.

#ifndef SENIOR_PROJECT_RCA_SRC_ARQ_CODEC_H_
#define SENIOR_PROJECT_RCA_SRC_ARQ_CODEC_H_
#include "arq_frame.h"
namespace arq {
/// Encodes to caller-owned bytes; returns zero for null/invalid input or short
/// capacity. Failure leaves output unchanged; input/output storage must not
/// overlap.
/// @param frame Borrowed logical frame to encode.
/// @param output Caller-owned writable bytes.
/// @param capacity Writable byte count.
/// @return Encoded byte count, or zero on failure.
size_t EncodeFrame(const Frame* frame, uint8_t* output, size_t capacity);
/// Decodes exactly one frame; null or malformed input fails without changing
/// frame. Input must span length readable bytes. Neither function retains
/// caller pointers.
/// @param frame Caller-owned output frame.
/// @param input Borrowed wire bytes, disjoint from frame.
/// @param length Number of readable input bytes.
/// @return True only after a complete valid frame was assigned.
bool DecodeFrame(Frame* frame, const uint8_t* input, size_t length);
/// Checks type, payload length and reason consistency; a null frame is invalid.
/// @param frame Borrowed logical frame, or null.
/// @return True when type, payload length and reason agree.
bool IsValidFrame(const Frame* frame);
}  // namespace arq
#endif  // SENIOR_PROJECT_RCA_SRC_ARQ_CODEC_H_
