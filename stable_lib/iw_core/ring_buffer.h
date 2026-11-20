/**
 * @file
 * @brief Fixed-capacity in-memory ring buffer.
 */
#ifndef IW_CORE_RING_BUFFER_H_
#define IW_CORE_RING_BUFFER_H_

#include <stdint.h>
#include <string.h>

namespace iw::core {

/// One byte range in a multi-part frame passed to RingBuffer::WriteFrame().
struct RingBufferPart {
  const void* data;  ///< Borrowed source bytes for this frame part.
  size_t length;     ///< Number of source bytes in data.
};

/// Stores a fixed-capacity byte stream without allocation or overwrite.
///
/// Unread data is never overwritten. Capacity must be a power of two.
template <size_t Capacity>
class RingBuffer {
 public:
  RingBuffer() : first_free_(0), free_(Capacity), buffer_{} {}

  /**
   * @brief Returns the total storage capacity.
   * @return Capacity bytes.
   */
  size_t CapacityBytes() const;

  /**
   * @brief Checks whether the ring buffer is empty.
   * @return True when no bytes are stored.
   */
  bool Empty() const;

  /**
   * @brief Checks whether the ring buffer is full.
   * @return True when no free bytes remain.
   */
  bool Full() const;

  /**
   * @brief Returns the number of free bytes.
   * @return Free storage capacity in bytes.
   */
  size_t Free() const;

  /**
   * @brief Returns the number of bytes stored.
   * @return Used storage capacity in bytes.
   */
  size_t Used() const;

  /**
   * @brief Appends one byte when space is available.
   *
   * @param data
   * byte value to be written
   *
   * @retval false
   * write cannot be done because the buffer is already full.
   * @retval true
   * write is successful.
   */
  bool WriteByte(uint8_t data);

  /**
   * @brief Appends as many bytes as fit.
   *
   * @param data
   * readable source bytes; required when length is nonzero.
   *
   * @param length
   * number of source bytes requested.
   *
   * @return
   * number of bytes actually written, which may be less than length.
   */
  size_t Write(const void* data, size_t length);

  /**
   * @brief Appends the object representation when it fits.
   *
   * @param object Object whose bytes are copied to the buffer.
   *
   * @retval false
   * write cannot be done because the object does not fit.
   * @retval true
   * write is successful.
   */
  template <typename T>
  bool Write(const T& object);

  /**
   * Write a frame made of several byte ranges as a single atomic unit.
   *
   * Unlike write(const void*, size_t), which silently truncates on
   * overflow, this either writes every part of the frame or writes
   * nothing at all -- a full buffer drops the whole frame instead of
   * corrupting the stream with a partial record.
   *
   * @param parts
   * array of {pointer, length} fragments making up one frame, written in
   * array order
   *
   * @param count
   * number of entries in parts
   *
   * @retval false
   * the frame's total length exceeds free(); the buffer is unchanged
   * @retval true
   * every part was written, in order
   */
  bool WriteFrame(const RingBufferPart* parts, size_t count);

  /**
   * @brief Removes and returns the next byte.
   *
   * @return
   * next byte, or zero when the buffer is empty.
   */
  uint8_t ReadByte();

  /**
   * @brief Removes up to length bytes from the buffer.
   *
   * @param data
   * destination for copied bytes, or nullptr to discard them.
   *
   * @param length
   * maximum number of bytes to remove.
   *
   * @return
   * number of bytes actually removed, which may be less than length.
   */
  size_t Read(void* data, size_t length);

  /**
   * @brief Removes one object representation when enough bytes are stored.
   *
   * @param object Destination object overwritten with the bytes read.
   *
   * @retval false
   * read cannot be done because fewer than sizeof(T) bytes are stored.
   * @retval true
   * read is successful.
   */
  template <typename T>
  bool Read(T& object);

  /**
   * @brief Discards all stored bytes and resets the read/write positions.
   */
  void Clear();

 private:
  // Enforce capacity to be power of two to improve performance; i.e., the
  // compiler will optimize (x % Capacity) to (x & (Capacity - 1))
  static_assert((Capacity & (Capacity - 1)) == 0,
                "Capacity must be a power of 2");
  size_t first_free_;  ///< index of the first free byte
  size_t free_;        ///< number of remaining free bytes
  uint8_t buffer_[Capacity];
};

/************************************************/
template <size_t Capacity>
size_t RingBuffer<Capacity>::CapacityBytes() const {
  return Capacity;
}

/************************************************/
template <size_t Capacity>
bool RingBuffer<Capacity>::Empty() const {
  return free_ == Capacity;
}

/************************************************/
template <size_t Capacity>
bool RingBuffer<Capacity>::Full() const {
  return free_ == 0;
}

/************************************************/
template <size_t Capacity>
size_t RingBuffer<Capacity>::Free() const {
  return free_;
}

/************************************************/
template <size_t Capacity>
size_t RingBuffer<Capacity>::Used() const {
  return Capacity - free_;
}

/************************************************/
template <size_t Capacity>
bool RingBuffer<Capacity>::WriteByte(uint8_t data) {
  if (Full()) return false;
  free_--;
  buffer_[first_free_] = data;
  first_free_ = (first_free_ + 1) % Capacity;
  return true;
}

/************************************************/
template <size_t Capacity>
size_t RingBuffer<Capacity>::Write(const void* data, size_t length) {
  size_t bytes_to_boundary;

  // overflow protection
  if (free_ < length) length = free_;

  if (length == 0) return 0;

  // Make sure we are not writing beyond the buffer boundary
  bytes_to_boundary = Capacity - first_free_;

  if (bytes_to_boundary >= length)
    memcpy(&buffer_[first_free_], data, length);
  else {
    // split write into two chunks
    // (1) from first-free to boundary
    memcpy(&buffer_[first_free_], data, bytes_to_boundary);

    // (2) from 0 to remaining bytes (after wrap-around)
    memcpy(buffer_, static_cast<const uint8_t*>(data) + bytes_to_boundary,
           length - bytes_to_boundary);
  }

  // Update properties accordingly
  free_ = (free_ - length) % Capacity;
  first_free_ = (first_free_ + length) % Capacity;

  return length;
}

/************************************************/
template <size_t Capacity>
template <typename T>
bool RingBuffer<Capacity>::Write(const T& object) {
  // make sure there is enough room for the object
  if (Free() < sizeof(T)) return false;

  Write(&object, sizeof(T));
  return true;
}

/************************************************/
template <size_t Capacity>
bool RingBuffer<Capacity>::WriteFrame(const RingBufferPart* parts,
                                      size_t count) {
  size_t total = 0;
  for (size_t i = 0; i < count; i++) {
    total += parts[i].length;
  }
  if (total > free_) return false;

  for (size_t i = 0; i < count; i++) {
    Write(parts[i].data, parts[i].length);
  }
  return true;
}

/************************************************/
template <size_t Capacity>
uint8_t RingBuffer<Capacity>::ReadByte() {
  if (Empty()) return 0;

  size_t first_index = (first_free_ + free_) % Capacity;
  free_++;
  return buffer_[first_index];
}

/************************************************/
template <size_t Capacity>
size_t RingBuffer<Capacity>::Read(void* data, size_t length) {
  size_t first_index;
  size_t bytes_to_boundary;

  // limit read to only stored bytes
  if ((Capacity - free_) < length) length = Capacity - free_;
  if (length == 0) return 0;

  // Locate the first stored byte
  first_index = (first_free_ + free_) % Capacity;

  // Make sure we are not writing beyond the buffer boundary
  bytes_to_boundary = Capacity - first_index;

  // Store contents in the provided memory location only when it is not null
  if (data) {
    if (bytes_to_boundary >= length)
      memcpy(static_cast<uint8_t*>(data), &buffer_[first_index], length);
    else {
      // split read into two chunks
      // (1) from first-free to boundary
      memcpy(static_cast<uint8_t*>(data), &buffer_[first_index],
             bytes_to_boundary);

      // (2) from 0 to remaining bytes (after wrap-around)
      memcpy(static_cast<uint8_t*>(data) + bytes_to_boundary, buffer_,
             length - bytes_to_boundary);
    }
  }

  // Update properties accordingly
  free_ += length;

  return length;
}
/************************************************/
template <size_t Capacity>
template <typename T>
bool RingBuffer<Capacity>::Read(T& object) {
  // make sure there is enough data
  if (Used() < sizeof(T)) return false;

  Read(&object, sizeof(T));
  return true;
}

/************************************************/
template <size_t Capacity>
void RingBuffer<Capacity>::Clear() {
  first_free_ = 0;
  free_ = Capacity;
}

}  // namespace iw::core

#endif  // IW_CORE_RING_BUFFER_H_
