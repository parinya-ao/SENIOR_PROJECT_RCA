// Owns the ARQ sender transaction and foreground radio sequencing.
#include <Arduino.h>
#include <updi_uart.h>

#include "application.h"
#include "application_config.h"
#include "arq_commands.h"
#include "arq_diagnostics.h"
#include "arq_sender.h"
#include "shared/diagnostics/arq_bench.h"
#include "shared/protocol/arq_ingress.h"
#include "shared/radio/arq_radio.h"

namespace arq {
namespace app {
// Foreground state machines; radio IRQ flags are consumed by loop, never
// mutated in ISRs.
static arq::Sender sender;
static uint32_t control_rejects;
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
static uint32_t CurrentSession() { return sender.session; }
// Captures the current direction's transaction fields for diagnostic
// correlation.
static const arq::diagnostics::EventContext& GetEventContext() {
  static constexpr arq::diagnostics::EventContext kContext{
      sender.session, sender.frame.sequence, sender.attempts};
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
  RecordReceiveDiagnostics(GetEventContext(), "RX_RESTART",
                           radio.getIRQFlags());
  int16_t rc = radio.startReceive();
  arq::diagnostics::RecordEvent(GetEventContext(), "RX_READY", rc, 0);
  if (!rc) RecordRadioRegisters(GetEventContext(), "RX_STATE");
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
  if (arq::IsSenderActive(&sender)) {
    // Fatal adapter errors terminate even if the sender was waiting in RX.
    sender.state = arq::SenderState::kFailed;
    sender.result = arq::Result::kRadioError;
    sender.used_up = true;
  }
}
static void ResetStatistics() {
  attempted = 0;
  receive_counters = {};
  control_rejects = 0;
}
// Arms the selected protocol direction and resets counters for a new session.
static void ArmSession(uint32_t value) {
  bool ok = false;
  uint32_t previous = CurrentSession();
  ok = arq::ArmSender(&sender, value);
  const bool stopped = sender.stopped;
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
    arq::StopSender(&sender);
    arq::diagnostics::RecordEvent(GetEventContext(), "STOP", 0, 0);
    return;
  }
  if (action.kind == arq::CommandKind::kArm) {
    ArmSession(action.session);
    return;
  }
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
  arq::InitSender(&sender);
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
}
// Handles TxDone and timeout for the current direction before processing RX.
static void PollTransmit(uint32_t now, uint16_t flags) {
  bool done = flags & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_TX_DONE;
  if (done || now - tx_started >= ARQ_TX_MS) {
    int16_t rc = radio.finishTransmit();
    radio_tx = false;
    arq::diagnostics::RecordEvent(GetEventContext(),
                                  done ? "TX_DONE" : "TX_TIMEOUT", rc, flags);
    const bool rx = RestoreReceive();
    arq::HandleTxCompletion(&sender, millis(), done && !rc && rx);
    if (sender.state == arq::SenderState::kWaitingAck) sender.tx_done = now;
    if (rc) FailAdapter(rc);
  }
}
// Captures currently visible values only when a STATUS line is due.
static void FlushStatus() {
  if (status_next && !diagnostics::PendingLineCount()) {
    const BenchStatus status{
        startup_status,
        reset_flags,
        ready,
        0,
        0,
        0,
        0,
        attempted,
        0,
        receive_counters.crc_errors,
        receive_counters.rx_done,
        receive_counters.decode_errors,
        control_rejects,
        static_cast<int16_t>(sender.result),
        static_cast<uint8_t>(sender.state),
        {sender.rtt_last, sender.rtt_min, sender.rtt_max, sender.rtt_count}};
    FlushBenchStatus(status_next, GetEventContext(), status);
  }
}

// Starts this direction's encoded TX and handles partial driver failure.
static void StartTransmit(uint32_t now) {
  int16_t rc = radio.standby();
  if (!rc) rc = radio.startTransmit(wire, wire_length);
  ++attempted;
  if (rc) {
    int16_t cleanup = radio.finishTransmit();
    RestoreReceive();
    arq::diagnostics::RecordEvent(GetEventContext(), "TX_ERROR", rc, cleanup);
    FailAdapter(cleanup ? cleanup : rc);
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

// Reports terminal completion and samples RTT only for the first attempt.
static void ReportTerminalState(arq::SenderState old) {
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
}

// Services IRQs before progressing ACK deadlines or starting a retry.
static void PollRadio(uint32_t now) {
  uint16_t flags = radio.getIRQFlags();
  if (radio_tx) {
    PollTransmit(now, flags);
  } else if (flags & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_RX_DONE)
    HandleReceive(now, flags);
  // Read matching controls before evaluating deadlines or initiating a retry.
  if (sender.state == arq::SenderState::kWaitingAck &&
      arq::IsDeadlineDue(now, sender.retry_at))
    RecordReceiveDiagnostics(GetEventContext(), "RX_TIMEOUT",
                             radio.getIRQFlags());
  arq::PollSender(&sender, now);
  bool start = sender.state == arq::SenderState::kTransmitting && !radio_tx;
  if (start) wire_length = arq::EncodeFrame(&sender.frame, wire, sizeof wire);
  if (start && ready) StartTransmit(now);
}

// Services commands, logging and bounded radio state transitions without heap
// allocation.
void Poll() {
  if (updi_uart_enabled() && !attached) ScheduleStatus();
  attached = updi_uart_enabled();
  if (updi_uart_rx_poll()) FeedCommandByte(static_cast<char>(updi_uart_rx()));
  uint32_t now = millis();
  const arq::SenderState old = sender.state;
  if (ready && !parked) PollRadio(now);
  ReportTerminalState(old);
  const bool idle = sender.stopped && !arq::IsSenderActive(&sender);
  if (ready && !parked && idle && !radio_tx) ParkRadio();
  FlushStatus();
  arq::diagnostics::FlushByte();
}

}  // namespace app
}  // namespace arq
