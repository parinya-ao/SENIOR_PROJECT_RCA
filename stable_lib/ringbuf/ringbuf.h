/** 
 * @file
 * @brief In-memory ring buffer
 *
 * Definitions for creating and maintaining ring buffers on RAM
 *
 * @author Chaiporn Jaikaeo <chaiporn.j@ku.ac.th>
 *
 */
#pragma once

#include <stdint.h>
#include <string.h>

template <size_t Capacity>
class RingBuffer {
public: 
    RingBuffer(): _firstFree(0), _free(Capacity) {}

    /**
     * Return the total capacity of the ring buffer
     */
    size_t capacity();

    /**
     * Check if the ring buffer is empty
     * @return true if the buffer is empty; false otherwise
     */
    bool empty();

    /**
     * Check if the ring buffer is full
     * @return true if the buffer is full; false otherwise
     */
    bool full();

    /**
     * Return the number of free bytes left in the buffer
     */
    size_t free();

    /**
     * Return the number of bytes stored in the buffer
     */
    size_t used();

    /**
     * Write a single byte to the ring buffer
     *
     * @param data
     * byte value to be written
     *
     * @retval false
     * write cannot be done because the buffer is already full
     * @retval true
     * write is successful
     */
    bool write_byte(uint8_t data);

    /**
     * Write byte contents to the ring buffer
     *
     * @param data
     * pointer to the first byte of data
     *
     * @param len
     * number of bytes to be written
     *
     * @return
     * the number of bytes successfully written
     */
    size_t write(const void *data, size_t len);

    /**
     * Write object to the ring buffer
     *
     * @param data
     * object whose contents will be copied to the buffer
     *
     * @retval false
     * write cannot be done because the buffer is already full
     * @retval true
     * write is successful
     */
    template <typename T>
    bool write(const T& obj);

    /**
     * Read a single byte from the ring buffer
     *
     * @return
     * next data byte from the buffer.  If the buffer is empty, 0 is return.
     */
    uint8_t read_byte();

    /**
     * Read contents out of the ring buffer and advance the read pointer
     *
     * @param data
     * pointer to the first byte of data.  If data is null, the contents will
     * simply be removed from the ring buffer
     *
     * @param len
     * number of bytes to be copied
     *
     * @return
     * the number of bytes successfully read out
     */
    size_t read(void *data, size_t len);

    /**
     * Read contents out of the ring buffer and advance the read pointer
     *
     * @param obj
     * object whose contents will be replaced by data read from the buffer
     *
     * @retval false
     * read cannot be done because the buffer doesn't have enough data
     * @retval true
     * read is successful
     */
    template <typename T>
    bool read(T& obj);

    /**
     * Clear all data from the ring buffer
     */
    void clear();

private:
    // Enforce capacity to be power of two to improve performance; i.e., the
    // compiler will optimize (x % Capacity) to (x & (Capacity - 1))
    static_assert(
        (Capacity & (Capacity - 1)) == 0,
        "Capacity must be a power of 2"
    );
    size_t _firstFree; ///< index of the first free byte
    size_t _free;      ///< number of remaining free bytes
    uint8_t _buffer[Capacity];
};

/************************************************/
template <size_t Capacity>
size_t RingBuffer<Capacity>::capacity() {
    return Capacity;
}

/************************************************/
template <size_t Capacity>
bool RingBuffer<Capacity>::empty() {
    return _free == Capacity;
}

/************************************************/
template <size_t Capacity>
bool RingBuffer<Capacity>::full() {
    return _free == 0;
}

/************************************************/
template <size_t Capacity>
size_t RingBuffer<Capacity>::free() {
    return _free;
}

/************************************************/
template <size_t Capacity>
size_t RingBuffer<Capacity>::used() {
    return Capacity - _free;
}

/************************************************/
template <size_t Capacity>
bool RingBuffer<Capacity>::write_byte(uint8_t data) {
    if (full()) return false;
    _free--;
    _buffer[_firstFree] = data;
    _firstFree = (_firstFree + 1) % Capacity;
    return true;
}

/************************************************/
template <size_t Capacity>
size_t RingBuffer<Capacity>::write(const void *data, size_t len) {
    size_t bytesToBoundary;

    // overflow protection
    if (_free < len) len = _free;

    if (len == 0) return 0;

    // Make sure we are not writing beyond the buffer boundary
    bytesToBoundary = Capacity - _firstFree;

    if (bytesToBoundary >= len)
        memcpy((uint8_t*)&_buffer[_firstFree], data, len);
    else
    {
        // split write into two chunks
        // (1) from first-free to boundary
        memcpy((uint8_t*)&_buffer[_firstFree], data, bytesToBoundary);

        // (2) from 0 to remaining bytes (after wrap-around)
        memcpy((uint8_t*)_buffer, (uint8_t*)data + bytesToBoundary, len - bytesToBoundary);
    }

    // Update properties accordingly
    _free = (_free - len) % Capacity;
    _firstFree = (_firstFree + len) % Capacity;

    return len;
}

/************************************************/
template <size_t Capacity>
template <typename T>
bool RingBuffer<Capacity>::write(const T& obj) {
    // make sure there is enough room for the object
    if (free() < sizeof(T)) return false;

    write(&obj, sizeof(T));
    return true;
}

/************************************************/
template <size_t Capacity>
uint8_t RingBuffer<Capacity>::read_byte() {
    if (empty()) return 0;

    size_t firstIndex = (_firstFree + _free) % Capacity;
    _free++;
    return _buffer[firstIndex];
}

/************************************************/
template <size_t Capacity>
size_t RingBuffer<Capacity>::read(void *data, size_t len) {
    uint16_t firstIndex;
    uint16_t bytesToBoundary;

    // limit read to only stored bytes
    if ( (Capacity - _free) < len )
        len = Capacity - _free; 
    if (len == 0) return 0;

    // Locate the first stored byte
    firstIndex = (_firstFree + _free) % Capacity;

    // Make sure we are not writing beyond the buffer boundary
    bytesToBoundary = Capacity - firstIndex;

    // Store contents in the provided memory location only when it is not null
    if (data)
    {
        if (bytesToBoundary >= len)
            memcpy((uint8_t*)data, &_buffer[firstIndex], len);
        else
        {
            // split read into two chunks
            // (1) from first-free to boundary
            memcpy((uint8_t*)data, &_buffer[firstIndex], bytesToBoundary);

            // (2) from 0 to remaining bytes (after wrap-around)
            memcpy((uint8_t*)data+bytesToBoundary, _buffer, len - bytesToBoundary);
        }
    }

    // Update properties accordingly
    _free += len;

    return len;
}
/************************************************/
template <size_t Capacity>
template <typename T>
bool RingBuffer<Capacity>::read(T& obj) {
    // make sure there is enough data
    if (used() < sizeof(T)) return false;

    read(&obj, sizeof(T));
    return true;
}

/************************************************/
template <size_t Capacity>
void RingBuffer<Capacity>::clear() {
    _firstFree = 0;
    _free = Capacity;
}

