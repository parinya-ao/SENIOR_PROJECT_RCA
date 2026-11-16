// Allocation-free UART event trace for AVR firmware boundaries.
#ifndef IW_DEBUG_EVENT_TRACE_H_
#define IW_DEBUG_EVENT_TRACE_H_

#include <Arduino.h>
#include <stdint.h>

// Set per build. Zero removes all UART setup and event formatting.
#ifndef DEBUG_LEVEL
#define DEBUG_LEVEL 0
#endif

namespace Debug {

// Runtime verbosity levels encoded in the UART event stream.
enum class Level : uint8_t {
  kOff = 0U,
  kError = 1U,
  kWarn = 2U,
  kInfo = 3U,
  kDebug = 4U,
  kTrace = 5U,
};

// Numeric protocol values are intentionally stable; host evidence may retain
// them after firmware strings and symbols are unavailable.
enum class Role : uint8_t { kBoot = 1U, kApplication = 2U, kHil = 3U };
enum class Component : uint8_t {
  kBoot = 1U,
  kApplication = 2U,
  kNvm = 3U,
  kHil = 4U
};
enum class EventId : uint8_t {
  kStartup = 1U,
  kAuthenticationStarted = 2U,
  kReceiptPersisted = 3U,
  kReceiptAccepted = 4U,
  kInstallStarted = 5U,
  kTrialBoot = 6U,
  kF6Admission = 64U,
  kF6JournalBegin = 65U,
  kF6BeforeProgram = 66U,
  kF6AfterProgram = 67U,
  kF6Readback = 68U,
  kF6FinalVerify = 69U,
  kF6TrialPublish = 70U,
  kF6Handoff = 71U,
  kF6Confirmation = 72U,
};
enum class Result : uint8_t {
  kOk = 0U,
  kRejected = 1U,
  kIoFailure = 2U,
  kIntegrityFailure = 3U,
  kAssertionFailed = 4U,
};

constexpr bool kEnabled = DEBUG_LEVEL != 0;

// P10-LOG-001: this assertion macro is the small, required logging boundary.
#if DEBUG_LEVEL > 0
inline uint16_t g_sequence = 0U;          // P10-LOG-001: event sequence state.
inline Role g_role = Role::kApplication;  // P10-LOG-001: emitting image role.
inline uint8_t g_reset_cause = 0U;        // P10-LOG-001: captured reset flags.

// Starts a new event sequence with the image role and reset flags.
inline void Initialize(Role role, uint8_t reset_cause) noexcept {
  g_sequence = 0U;
  g_role = role;
  g_reset_cause = reset_cause;
}

// RX stays disabled because PA1 is the maintenance-request input.
// Initializes the debug UART in transmit-only mode.
inline void BeginSerial() { Serial.begin(115200, SERIAL_TX_ONLY); }

// Emits one bounded, pipe-delimited event when level is enabled.
inline void Event(Level level, Component component, EventId event,
                  Result result = Result::kOk) {
  if (static_cast<uint8_t>(level) > DEBUG_LEVEL) return;
  Serial.print(F("DBG|"));
  Serial.print(static_cast<uint16_t>(g_role));
  Serial.print('|');
  Serial.print(static_cast<uint16_t>(g_sequence++));
  Serial.print('|');
  Serial.print(static_cast<uint16_t>(g_reset_cause));
  Serial.print('|');
  Serial.print(static_cast<uint16_t>(component));
  Serial.print('|');
  Serial.print(static_cast<uint16_t>(event));
  Serial.print('|');
  Serial.println(static_cast<uint16_t>(result));
}
// F6 page indexes remain separate from stable event IDs and existing DBG
// frames.
inline void FaultEvent(EventId event, uint32_t page) {
  Serial.print(F("F6|"));
  Serial.print(static_cast<uint16_t>(event));
  Serial.print('|');
  Serial.println(page);
}
#else
inline void Initialize(Role, uint8_t) noexcept {}
inline void BeginSerial() {}
inline void Event(Level, Component, EventId, Result = Result::kOk) {}
inline void FaultEvent(EventId, uint32_t) {}
#endif

}  // namespace Debug

#if DEBUG_LEVEL > 0
// P10-LOG-001: this assertion macro is the small, required logging boundary.
#define DBG_ASSERT(condition, component, event)                    \
  do {                                                             \
    if (!(condition)) {                                            \
      ::Debug::Event(::Debug::Level::kError, (component), (event), \
                     ::Debug::Result::kAssertionFailed);           \
    }                                                              \
  } while (0)
#else
// P10-LOG-001: the disabled assertion macro preserves call-site syntax.
#define DBG_ASSERT(condition, component, event) \
  do {                                          \
  } while (0)
#endif

#endif  // IW_DEBUG_EVENT_TRACE_H_
