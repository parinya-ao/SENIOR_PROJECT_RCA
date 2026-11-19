// Coordinates ARQ command input, radio work, deadlines, and deferred logs.
#include <Arduino.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <updi_uart.h>

#include "application_config.h"
#include "arq.h"
#include "arq_application.h"
#include "arq_commands.h"
#include "arq_diagnostics.h"
#include "radio.h"

namespace arq {
namespace app {
// Foreground state machines; radio IRQ flags are consumed by loop, never
// mutated in ISRs.
#if defined(ARQ_ROLE_SENDER)
static arq::Sender sender;
static uint32_t control_rejects;
#else
static arq::Receiver receiver;
static bool response_wait;
static uint32_t response_at, generated, suppressed, completed;
#if defined(ARQ_TEST_MODE)
static uint16_t fault_stride, fault_budget;
#endif
#endif
// Adapter latches coordinate startup, TX ownership, deferred replies and safe
// parking.
static bool ready, radio_tx, attached, parked;
// Shared foreground TX/RX storage; wire_length always bounds the valid frame
// bytes.
static uint8_t wire[arq::kMaxFrameBytes], wire_length, reset_flags;
// Millisecond deadlines use unsigned elapsed arithmetic to tolerate clock
// rollover.
static uint32_t tx_started;
// Cumulative response/TX counters are diagnostic only and do not drive protocol
// decisions.
static uint32_t attempted, crc_errors;
// Reception counters distinguish PHY completion from successful protocol
// decoding.
static uint32_t rx_done, decode_errors;
// Last observed receive IRQ bits are retained until captured in the event
// stream.
static uint16_t last_rx_flags;
// Foreground command accumulator owns its bounded input buffer.
static arq::CommandInput command_input;
// Retains the first startup status for incremental STATUS reporting.
static int16_t startup_status;
// One-based pending STATUS item; zero means no status dump is queued.
static uint8_t status_next;

// Selects the session belonging to the current DATA direction.
static uint32_t CurrentSession() {
#if defined(ARQ_ROLE_SENDER)
  return sender.session;
#else
  return receiver.session;
#endif
}
// Selects the last frame sequence for direction-correct event correlation.
static uint16_t CurrentSequence() {
#if defined(ARQ_ROLE_SENDER)
  return sender.frame.sequence;
#else
  return receiver.last_sequence;
#endif
}
// Captures the current direction's transaction fields for diagnostic
// correlation.
static const arq::diagnostics::EventContext& GetEventContext() {
#if defined(ARQ_ROLE_SENDER)
  static constexpr arq::diagnostics::EventContext kContext{
      sender.session, sender.frame.sequence, sender.attempts};
#else
  static constexpr uint8_t kNoDataAttempts = 0;
  static constexpr arq::diagnostics::EventContext kContext{
      receiver.session, receiver.last_sequence, kNoDataAttempts};
#endif
  return kContext;
}
// Captures relevant SPI readback before later mode transitions erase diagnostic
// evidence.
static void RecordRadioRegisters(const char* name) {
  static const uint8_t addresses[] = {
      0x01, 0x06, 0x07, 0x08, 0x09, 0x4d, 0x1d, 0x1e, 0x26, 0x39, 0x33, 0x3b,
      0x12, 0x13, 0x10, 0x1b, 0x40, 0x11, 0x18, 0x31, 0x42, 0x20, 0x21, 0x41};
  uint8_t values[sizeof addresses];
  for (size_t i = 0; i < sizeof addresses; ++i)
    values[i] = ReadRadioRegister(addresses[i]);
  arq::diagnostics::RecordFrame(GetEventContext(), name, values, sizeof values,
                                0, 0);
}
// Captures receive IRQ/FIFO state for the first failing boundary.
static void RecordReceiveDiagnostics(const char* name, uint16_t flags) {
  // Snapshot band counters before startReceive resets their observation window.
  uint8_t values[6] = {static_cast<uint8_t>(flags >> 8),
                       static_cast<uint8_t>(flags),
                       0,
                       0,
                       0,
                       0};
  for (uint8_t i = 0; i < 4; ++i) values[2 + i] = ReadRadioRegister(0x14 + i);
  arq::diagnostics::RecordFrame(GetEventContext(), name, values, sizeof values,
                                0, 0);
}
// Starts a bounded incremental status dump instead of concatenating a large
// string.
static void ScheduleStatus() {
  if (!status_next) status_next = 1;
}
// Preserve the sender-only STATUS fields as zeros on the responder.
static void RecordStatusTiming(uint8_t step) {
  if (step == 5) {
#if defined(ARQ_ROLE_SENDER)
    const arq::Result result = sender.result;
    const arq::SenderState state = sender.state;
#else
    constexpr arq::Result result = arq::Result::kPending;
    constexpr arq::SenderState state = arq::SenderState::kIdle;
#endif
    arq::diagnostics::RecordEvent(GetEventContext(), "RESULT",
                                  static_cast<int16_t>(result),
                                  static_cast<uint32_t>(state));
    return;
  }
  static const char* const fields[] = {"RTT_LAST", "RTT_MIN", "RTT_MAX",
                                       "RTT_COUNT"};
  const uint8_t index = step - 6;
#if defined(ARQ_ROLE_SENDER)
  const uint32_t values[] = {sender.rtt_last, sender.rtt_min, sender.rtt_max,
                             sender.rtt_count};
  const uint32_t value = values[index];
#else
  constexpr uint32_t value = 0;
#endif
  arq::diagnostics::RecordEvent(GetEventContext(), fields[index], 0, value);
}
// The initiator keeps the responder-only counters as zeros in STATUS.
static void RecordStatusCounters() {
#if defined(ARQ_ROLE_SENDER)
  constexpr uint32_t deliveries = 0, duplicates = 0, generated = 0,
                     suppressed = 0, completed = 0;
#else
  const uint32_t deliveries = receiver.deliveries;
  const uint32_t duplicates = receiver.duplicates;
#endif
  char* out = arq::diagnostics::AcquireLine();
  if (out)
    snprintf(out, arq::diagnostics::kLineCapacity,
             "A t=%lu e=STATUS s=%08lX app=%lu dup=%lu gen=%lu sup=%lu "
             "att=%lu done=%lu crc=%lu overflow=%lu ready=%u\n",
             static_cast<unsigned long>(millis()),
             static_cast<unsigned long>(CurrentSession()),
             static_cast<unsigned long>(deliveries),
             static_cast<unsigned long>(duplicates),
             static_cast<unsigned long>(generated),
             static_cast<unsigned long>(suppressed),
             static_cast<unsigned long>(attempted),
             static_cast<unsigned long>(completed),
             static_cast<unsigned long>(crc_errors),
             static_cast<unsigned long>(arq::diagnostics::OverflowCount()),
             ready);
}
// Emits at most one pending status item per call so logging cannot monopolize
// loop.
static void FlushStatus() {
  // Yield between status lines so an RX/response burst retains the bounded
  // logger.
  if (!status_next || arq::diagnostics::PendingLineCount()) return;
  const uint8_t step = status_next++;
  switch (step) {
    case 1:
      arq::diagnostics::RecordEvent(GetEventContext(), "BOOT", startup_status,
                                    reset_flags);
      break;
    case 2:
#if defined(ARQ_RADIO_ONLY_DIAGNOSTIC)
      arq::diagnostics::RecordEvent(GetEventContext(), "RADIO_ONLY",
                                    startup_status, 1);
#endif
      break;
    case 3: {
      char* identity = arq::diagnostics::AcquireLine();
      if (identity)
        snprintf(identity, arq::diagnostics::kLineCapacity,
                 "A t=%lu e=IDENTITY s=%08lX build=%s config=%s\n",
                 static_cast<unsigned long>(millis()),
                 static_cast<unsigned long>(CurrentSession()), LORA_BUILD_ID,
                 ARQ_CONFIG_HASH);
      break;
    }
    case 4:
      RecordStatusCounters();
      break;
    case 5:
    case 6:
    case 7:
    case 8:
    case 9:
      RecordStatusTiming(step);
      break;
    case 10:
      arq::diagnostics::RecordEvent(GetEventContext(), "RX_DONE_COUNT", 0,
                                    rx_done);
      break;
    case 11:
      arq::diagnostics::RecordEvent(GetEventContext(), "DECODE_ERRORS", 0,
                                    decode_errors);
      break;
    case 12: {
#if !defined(ARQ_ROLE_SENDER)
      constexpr uint32_t control_rejects = 0;
#endif
      arq::diagnostics::RecordEvent(GetEventContext(), "CONTROL_REJECTS", 0,
                                    control_rejects);
      break;
    }
    case 13:
      // Read-only register evidence separates RX mode/configuration from RF
      // path failure.
      if (ready) RecordRadioRegisters("REG");
      break;
    case 14:
      arq::diagnostics::RecordEvent(GetEventContext(), "STATUS_END", 0,
                                    arq::diagnostics::OverflowCount());
      status_next = 0;
      break;
    default:
      break;
  }
}
// Restores continuous receive; reports failure before the sender starts its ACK
// timer.
static bool RestoreReceive() {
#if !defined(ARQ_ROLE_SENDER)
  receiver.state = arq::ReceiverState::kReturningToRx;
#endif
  RecordReceiveDiagnostics("RX_RESTART", radio.getIRQFlags());
  int16_t rc = radio.startReceive();
  arq::diagnostics::RecordEvent(GetEventContext(), "RX_READY", rc, 0);
#if defined(ARQ_ROLE_SENDER)
  if (!rc) RecordRadioRegisters("RX_STATE");
#else
  receiver.state = arq::ReceiverState::kListening;
#endif
  if (rc) {
    ready = false;
    arq::diagnostics::RecordEvent(GetEventContext(), "RX_ERROR", rc, 0);
  } else
    parked = false;
  return !rc;
}
// Parks the adapter on radio failure while preserving protocol and diagnostic
// state.
static void FailAdapter(int16_t rc) {
  ready = false;
  arq::diagnostics::RecordEvent(GetEventContext(), "ADAPTER_ERROR", rc, 0);
#if defined(ARQ_ROLE_SENDER)
  if (arq::IsSenderActive(&sender)) {
    // Fatal adapter errors terminate even if the sender was waiting in RX.
    sender.state = arq::SenderState::kFailed;
    sender.result = arq::Result::kRadioError;
    sender.used_up = true;
  }
#endif
}
static void ResetStatistics() {
  attempted = crc_errors = rx_done = decode_errors = 0;
  last_rx_flags = 0;
#if defined(ARQ_ROLE_SENDER)
  control_rejects = 0;
#else
  generated = suppressed = completed = 0;
#if defined(ARQ_TEST_MODE)
  fault_stride = fault_budget = 0;
#endif
#endif
}
// Arms the selected protocol direction and resets counters for a new session.
static void ArmSession(uint32_t value) {
  bool ok = false;
  uint32_t previous = CurrentSession();
#if defined(ARQ_ROLE_SENDER)
  ok = arq::ArmSender(&sender, value);
  const bool stopped = sender.stopped;
#else
  if (receiver.armed && receiver.session == value)
    ok = true;
  else if (!radio_tx && !response_wait)
    ok = arq::ArmReceiver(&receiver, value);
  const bool stopped = receiver.stopped;
#endif
  if (ok && previous != value) ResetStatistics();
  if (ok && ready && parked && !stopped) ok = RestoreReceive();
  arq::diagnostics::RecordEvent(GetEventContext(), ok ? "ARM" : "ARM_REJECT",
                                ready ? 0 : -1, value);
}
// Executes one complete null-terminated bench command from the foreground
// buffer.
static void ExecuteCommand(const char* text) {
  arq::Command action;
  if (!arq::ParseCommand(text, &action)) {
    arq::diagnostics::RecordEvent(GetEventContext(), "COMMAND_ERROR", -1, 0);
    return;
  }
  if (action.kind == arq::CommandKind::kStatus) {
    ScheduleStatus();
    return;
  }
  if (action.kind == arq::CommandKind::kStop) {
#if defined(ARQ_ROLE_SENDER)
    arq::StopSender(&sender);
#else
    receiver.stopped = true;
#endif
    arq::diagnostics::RecordEvent(GetEventContext(), "STOP", 0, 0);
    return;
  }
  if (action.kind == arq::CommandKind::kArm) {
    ArmSession(action.session);
    return;
  }
#if defined(ARQ_ROLE_SENDER)
  if (action.kind == arq::CommandKind::kSend) {
    uint32_t rto =
        ARQ_ACK_MIN_MS +
        static_cast<uint32_t>(random(ARQ_ACK_MAX_MS - ARQ_ACK_MIN_MS + 1));
    bool ok =
        ready && arq::RequestTransmission(&sender, action.payload,
                                          action.payload_length, millis(), rto);
    arq::diagnostics::RecordEvent(GetEventContext(),
                                  ok ? "REQUEST" : "SEND_REJECT", 0, rto);
    return;
  }
#elif defined(ARQ_TEST_MODE)
  if (action.kind == arq::CommandKind::kFault && !radio_tx && !response_wait) {
    fault_stride = action.stride;
    fault_budget = action.budget;
    arq::diagnostics::RecordEvent(GetEventContext(), "FAULT", 0, fault_budget);
    return;
  }
#endif
  arq::diagnostics::RecordEvent(GetEventContext(), "COMMAND_ERROR", -1, 0);
}
// Accumulates a bounded line and drops overflowed commands until their
// terminator.
static void FeedCommandByte(char value) {
  switch (command_input.Feed(value)) {
    case arq::InputResult::kComplete:
      ExecuteCommand(command_input.text());
      break;
    case arq::InputResult::kOverflow:
      arq::diagnostics::RecordEvent(GetEventContext(), "COMMAND_ERROR", -1, 0);
      break;
    case arq::InputResult::kPending:
      break;
  }
}
// Initializes logging, role-specific power isolation, SPI and the existing
// radio profile.
void Initialize() {
#if defined(ARQ_ROLE_SENDER)
  arq::InitSender(&sender);
#else
  arq::InitReceiver(&receiver);
#endif
  reset_flags = GPR_GPR0;
  bool sd_blocked = false, spi_selected = false;
  const int16_t rc = InitializeRadio(&sd_blocked, &spi_selected);
  startup_status = rc;
  if (sd_blocked)
    arq::diagnostics::RecordEvent(GetEventContext(), "SD_PRESENT_BLOCKED", rc,
                                  0);
  if (!spi_selected) return;
  ready = !rc;
  parked = !rc;
  randomSeed(micros());
}
// Validates radio IRQ/CRC and decoded context before accepting DATA or control.
static void HandleReceive(uint32_t now, uint16_t flags) {
  ++rx_done;
  last_rx_flags = flags;
  RecordReceiveDiagnostics("RX_IRQ", flags);
  int16_t rc = radio.standby();
  if (rc) {
    FailAdapter(rc);
    return;
  }
  size_t length = radio.getPacketLength();
  uint8_t bytes[arq::kMaxFrameBytes];
  if (length < arq::kHeaderBytes || length > sizeof bytes) {
    arq::diagnostics::RecordEvent(GetEventContext(), "LENGTH_DISCARD", 0,
                                  length);
    RestoreReceive();
    return;
  }
  rc = radio.readData(bytes, length);
  if (rc || (flags & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_PAYLOAD_CRC_ERROR)) {
    if (rc == RADIOLIB_ERR_CRC_MISMATCH ||
        (flags & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_PAYLOAD_CRC_ERROR))
      ++crc_errors;
    arq::diagnostics::RecordEvent(GetEventContext(), "RX_DISCARD", rc, flags);
    RestoreReceive();
    return;
  }
  arq::diagnostics::RecordFrame(GetEventContext(), "RX", bytes, length,
                                static_cast<int16_t>(radio.getRSSI() * 100),
                                static_cast<int16_t>(radio.getSNR() * 100));
  arq::Frame frame;
  if (!arq::DecodeFrame(&frame, bytes, length)) {
    ++decode_errors;
    arq::diagnostics::RecordEvent(GetEventContext(), "DECODE_DISCARD", 0,
                                  length);
    RestoreReceive();
    return;
  }
#if defined(ARQ_ROLE_SENDER)
  uint8_t reason = 0;
  if (frame.type != arq::kAck && frame.type != arq::kNack)
    reason = 1;
  else if (frame.src != arq::config::kReceiverId ||
           frame.dst != arq::config::kSenderId)
    reason = 2;
  else if (frame.session != sender.session)
    reason = 3;
  else if (frame.sequence != sender.sequence)
    reason = 4;
  else if ((sender.state != arq::SenderState::kWaitingAck &&
            sender.state != arq::SenderState::kBackoff) ||
           !sender.attempts)
    reason = 5;
  else if (arq::IsDeadlineDue(now, sender.terminal_at))
    reason = 6;
  if (reason) {
    ++control_rejects;
    arq::diagnostics::RecordDiscard(GetEventContext(), "CONTROL_DISCARD",
                                    &frame, reason);
  }
  arq::HandleControlFrame(&sender, &frame, now);
  if (!RestoreReceive()) FailAdapter(-1);
#else
  arq::Frame response;
  uint32_t deliveries = receiver.deliveries;
  if (!arq::HandleDataFrame(&receiver, &frame, &response, false)) {
    arq::diagnostics::RecordDiscard(GetEventContext(), "DATA_DISCARD", &frame,
                                    1);
    RestoreReceive();
    return;
  }
  ++generated;
  if (receiver.deliveries != deliveries)
    arq::diagnostics::RecordEvent(GetEventContext(), "ACCEPT", 0,
                                  receiver.deliveries);
  else if (response.type == arq::kAck)
    arq::diagnostics::RecordEvent(GetEventContext(), "DUPLICATE", 0,
                                  receiver.duplicates);
  else
    arq::diagnostics::RecordEvent(GetEventContext(), "DATA_REJECT",
                                  response.reason, 0);
#if defined(ARQ_TEST_MODE)
  if (receiver.deliveries != deliveries && fault_budget && fault_stride &&
      receiver.deliveries % fault_stride == 0) {
    --fault_budget;
    ++suppressed;
    arq::diagnostics::RecordEvent(GetEventContext(), "SUPPRESS", 0, suppressed);
    RestoreReceive();
    return;
  }
#endif
  wire_length = arq::EncodeFrame(&response, wire, sizeof wire);
  response_at = now + ARQ_RESPONSE_GUARD_MS;
  response_wait = true;
  receiver.state =
      arq::ReceiverState::kSendingResponse;  // Response guard precedes RF TX.
#endif
}
// Handles TxDone and timeout for the current direction before processing RX.
static void PollTransmit(uint32_t now, uint16_t flags) {
  bool done = flags & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_TX_DONE;
  if (done || now - tx_started >= ARQ_TX_MS) {
    int16_t rc = radio.finishTransmit();
    radio_tx = false;
    arq::diagnostics::RecordEvent(GetEventContext(),
                                  done ? "TX_DONE" : "TX_TIMEOUT", rc, flags);
#if defined(ARQ_ROLE_SENDER)
    const bool rx = RestoreReceive();
    arq::HandleTxCompletion(&sender, millis(), done && !rc && rx);
    if (sender.state == arq::SenderState::kWaitingAck) sender.tx_done = now;
#else
    RestoreReceive();
    if (done && !rc) ++completed;
#endif
    if (rc) FailAdapter(rc);
  }
}
// Services commands, logging and bounded radio state transitions without heap
// allocation.
void Poll() {
  if (updi_uart_enabled() && !attached) ScheduleStatus();
  attached = updi_uart_enabled();
  if (updi_uart_rx_poll()) FeedCommandByte(static_cast<char>(updi_uart_rx()));
  uint32_t now = millis();
#if defined(ARQ_ROLE_SENDER)
  const arq::SenderState old = sender.state;
  constexpr bool response_wait = false;
#endif
  if (ready && !parked) {
    uint16_t flags = radio.getIRQFlags();
    if (radio_tx) {
      PollTransmit(now, flags);
    } else if (!response_wait &&
               (flags & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_RX_DONE))
      HandleReceive(now, flags);
#if defined(ARQ_ROLE_SENDER)
    // Read matching controls before evaluating deadlines or initiating a retry.
    if (sender.state == arq::SenderState::kWaitingAck &&
        arq::IsDeadlineDue(now, sender.retry_at))
      RecordReceiveDiagnostics("RX_TIMEOUT", radio.getIRQFlags());
    arq::PollSender(&sender, now);
    bool start = sender.state == arq::SenderState::kTransmitting && !radio_tx;
    if (start) wire_length = arq::EncodeFrame(&sender.frame, wire, sizeof wire);
#else
    bool start = response_wait && arq::IsDeadlineDue(now, response_at);
#endif
    if (start && ready) {
#if !defined(ARQ_ROLE_SENDER)
      response_wait = false;
#endif
      int16_t rc = radio.standby();
      if (!rc) rc = radio.startTransmit(wire, wire_length);
      ++attempted;
      if (rc) {
        int16_t cleanup = radio.finishTransmit();
#if defined(ARQ_ROLE_SENDER)
        RestoreReceive();
#else
        const bool rx = RestoreReceive();
#endif
        arq::diagnostics::RecordEvent(GetEventContext(), "TX_ERROR", rc,
                                      cleanup);
#if defined(ARQ_ROLE_SENDER)
        FailAdapter(cleanup ? cleanup : rc);
#else
        if (cleanup || !rx) FailAdapter(cleanup ? cleanup : rc);
#endif
      } else {
        radio_tx = true;
        tx_started = now;
        arq::diagnostics::RecordFrame(GetEventContext(), "TX", wire,
                                      wire_length, 0, 0);
        RecordRadioRegisters("TX_STATE");
      }
    }
  }
#if defined(ARQ_ROLE_SENDER)
  if (old != sender.state && (sender.state == arq::SenderState::kDelivered ||
                              sender.state == arq::SenderState::kFailed)) {
    static const char* const names[] = {"PENDING",           "DELIVERED",
                                        "REJECTED",          "PROTOCOL_ERROR",
                                        "TIMEOUT_EXHAUSTED", "RADIO_ERROR"};
    arq::diagnostics::RecordEvent(GetEventContext(),
                                  names[static_cast<size_t>(sender.result)], 0,
                                  sender.attempts);
    if (sender.result == arq::Result::kOk && sender.attempts == 1)
      arq::diagnostics::RecordEvent(GetEventContext(), "RTT", 0,
                                    sender.rtt_last);
  }
  const bool idle = sender.stopped && !arq::IsSenderActive(&sender);
#else
  const bool idle = receiver.stopped && !response_wait;
#endif
  if (ready && !parked && idle && !radio_tx) {
    // X parks only after the outstanding exchange terminates.
    int16_t rc = radio.standby();
    if (rc)
      FailAdapter(rc);
    else
      parked = true;
    arq::diagnostics::RecordEvent(GetEventContext(), "STANDBY", rc, 0);
    if (!rc) RecordRadioRegisters("PARKED");
  }
  FlushStatus();
  arq::diagnostics::FlushByte();
}

}  // namespace app
}  // namespace arq
