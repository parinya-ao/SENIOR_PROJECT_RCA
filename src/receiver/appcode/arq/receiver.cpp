// Owns the ARQ receiver transaction and foreground radio sequencing.
#include <Arduino.h>
#include <updi_uart.h>

#include "application.h"
#include "application_config.h"
#include "arq_commands.h"
#include "arq_deadline.h"
#include "arq_diagnostics.h"
#include "arq_receiver.h"
#include "shared/diagnostics/arq_bench.h"
#include "shared/protocol/arq_ingress.h"
#include "shared/radio/arq_radio.h"

namespace arq {
namespace app {
// Foreground state machines; radio IRQ flags are consumed by loop, never
// mutated in ISRs.
static arq::Receiver receiver;
static bool response_wait;
static uint32_t response_at, generated, suppressed, completed;
#if defined(ARQ_TEST_MODE)
static uint16_t fault_stride, fault_budget;
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
static uint32_t attempted;
static ReceiveCounters receive_counters;
// Foreground command accumulator owns its bounded input buffer.
static arq::CommandInput command_input;
// Retains the first startup status for incremental STATUS reporting.
static int16_t startup_status;
// One-based pending STATUS item; zero means no status dump is queued.
static uint8_t status_next;

// Selects the session belonging to the current DATA direction.
static uint32_t CurrentSession() { return receiver.session; }
// Captures the current direction's transaction fields for diagnostic
// correlation.
static const arq::diagnostics::EventContext& GetEventContext() {
  static constexpr uint8_t kNoDataAttempts = 0;
  static constexpr arq::diagnostics::EventContext kContext{
      receiver.session, receiver.last_sequence, kNoDataAttempts};
  return kContext;
}
// Starts a bounded incremental status dump instead of concatenating a large
// string.
static void ScheduleStatus() {
  if (!status_next) status_next = 1;
}
// Restores continuous receive; reports failure before the sender starts its ACK
// timer.
static bool RestoreReceive() {
  receiver.state = arq::ReceiverState::kReturningToRx;
  RecordReceiveDiagnostics(GetEventContext(), "RX_RESTART",
                           radio.getIRQFlags());
  int16_t rc = radio.startReceive();
  arq::diagnostics::RecordEvent(GetEventContext(), "RX_READY", rc, 0);
  receiver.state = arq::ReceiverState::kListening;
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
}
static void ResetStatistics() {
  attempted = 0;
  receive_counters = {};
  generated = suppressed = completed = 0;
#if defined(ARQ_TEST_MODE)
  fault_stride = fault_budget = 0;
#endif
}
// Arms the selected protocol direction and resets counters for a new session.
static void ArmSession(uint32_t value) {
  bool ok = false;
  uint32_t previous = CurrentSession();
  if (receiver.armed && receiver.session == value)
    ok = true;
  else if (!radio_tx && !response_wait)
    ok = arq::ArmReceiver(&receiver, value);
  const bool stopped = receiver.stopped;
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
    receiver.stopped = true;
    arq::diagnostics::RecordEvent(GetEventContext(), "STOP", 0, 0);
    return;
  }
  if (action.kind == arq::CommandKind::kArm) {
    ArmSession(action.session);
    return;
  }
#if defined(ARQ_TEST_MODE)
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
  arq::InitReceiver(&receiver);
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
  arq::Frame frame;
  int16_t standby_error;
  const auto read = ReadReceivedFrame(GetEventContext(), flags,
                                      receive_counters, frame, standby_error);
  if (read == FrameRead::kRadioError) {
    FailAdapter(standby_error);
    return;
  }
  if (read == FrameRead::kDiscard) {
    RestoreReceive();
    return;
  }
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
}
// Handles TxDone and timeout for the current direction before processing RX.
static void PollTransmit(uint32_t now, uint16_t flags) {
  bool done = flags & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_TX_DONE;
  if (done || now - tx_started >= ARQ_TX_MS) {
    int16_t rc = radio.finishTransmit();
    radio_tx = false;
    arq::diagnostics::RecordEvent(GetEventContext(),
                                  done ? "TX_DONE" : "TX_TIMEOUT", rc, flags);
    RestoreReceive();
    if (done && !rc) ++completed;
    if (rc) FailAdapter(rc);
  }
}
// Captures currently visible values only when a STATUS line is due.
static void FlushStatus() {
  if (status_next && !diagnostics::PendingLineCount()) {
    const BenchStatus status{startup_status,
                             reset_flags,
                             ready,
                             receiver.deliveries,
                             receiver.duplicates,
                             generated,
                             suppressed,
                             attempted,
                             completed,
                             receive_counters.crc_errors,
                             receive_counters.rx_done,
                             receive_counters.decode_errors,
                             0,
                             0,
                             0,
                             {}};
    FlushBenchStatus(status_next, GetEventContext(), status);
  }
}

// Starts this direction's encoded TX and handles partial driver failure.
static void StartTransmit(uint32_t now) {
  response_wait = false;
  int16_t rc = radio.standby();
  if (!rc) rc = radio.startTransmit(wire, wire_length);
  ++attempted;
  if (rc) {
    int16_t cleanup = radio.finishTransmit();
    const bool rx = RestoreReceive();
    arq::diagnostics::RecordEvent(GetEventContext(), "TX_ERROR", rc, cleanup);
    if (cleanup || !rx) FailAdapter(cleanup ? cleanup : rc);
  } else {
    radio_tx = true;
    tx_started = now;
    arq::diagnostics::RecordFrame(GetEventContext(), "TX", wire, wire_length, 0,
                                  0);
    RecordRadioRegisters(GetEventContext(), "TX_STATE");
  }
}

// Parks after the outstanding exchange and records the final radio mode.
static void ParkRadio() {
  // X parks only after the outstanding exchange terminates.
  int16_t rc = radio.standby();
  if (rc)
    FailAdapter(rc);
  else
    parked = true;
  arq::diagnostics::RecordEvent(GetEventContext(), "STANDBY", rc, 0);
  if (!rc) RecordRadioRegisters(GetEventContext(), "PARKED");
}

// Services one IRQ and starts a queued response when its guard expires.
static void PollRadio(uint32_t now) {
  uint16_t flags = radio.getIRQFlags();
  if (radio_tx) {
    PollTransmit(now, flags);
  } else if (!response_wait && (flags & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_RX_DONE))
    HandleReceive(now, flags);
  bool start = response_wait && arq::IsDeadlineDue(now, response_at);
  if (start && ready) StartTransmit(now);
}

// Services commands, logging and bounded radio state transitions without heap
// allocation.
void Poll() {
  if (updi_uart_enabled() && !attached) ScheduleStatus();
  attached = updi_uart_enabled();
  if (updi_uart_rx_poll()) FeedCommandByte(static_cast<char>(updi_uart_rx()));
  uint32_t now = millis();
  if (ready && !parked) PollRadio(now);
  const bool idle = receiver.stopped && !response_wait;
  if (ready && !parked && idle && !radio_tx) ParkRadio();
  FlushStatus();
  arq::diagnostics::FlushByte();
}

}  // namespace app
}  // namespace arq
