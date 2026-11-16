// No repository-wide license is declared; existing rights are unchanged.

#include "application.h"

#include <Arduino.h>
#include <RadioLib.h>
#include <SPI.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <updi_uart.h>

#include "application_config.h"
#include "arq.h"
#include "commands.h"
#include "diagnostics.h"
#include "generated/board_ssot.h"
#include "radio_only.h"

namespace arq {
namespace app {
// Radio objects have static lifetime; hardware initialization happens only in
// setup.
static Module module(board_ssot.cs, board_ssot.irq, board_ssot.rst,
                     board_ssot.dio1, SPI,
                     SPISettings(ARQ_SPI_HZ, MSBFIRST, SPI_MODE0));
static SX1276 radio(&module);
// Foreground state machines; radio IRQ flags are consumed by loop, never
// mutated in ISRs.
static arq::Sender sender;
static arq::Receiver receiver;
// Adapter latches coordinate startup, TX ownership, deferred replies and safe
// parking.
static bool ready, radio_tx, response_wait, attached, parked;
// Shared foreground TX/RX storage; wire_length always bounds the valid frame
// bytes.
static uint8_t wire[arq::kMaxFrameBytes], wire_length, reset_flags;
// Millisecond deadlines use unsigned elapsed arithmetic to tolerate clock
// rollover.
static uint32_t tx_started, response_at;
// Cumulative response/TX counters are diagnostic only and do not drive protocol
// decisions.
static uint32_t generated, suppressed, attempted, completed, crc_errors;
// Reception counters distinguish PHY completion from successful protocol
// decoding.
static uint32_t rx_done, decode_errors, control_rejects;
// Last observed receive IRQ bits are retained until captured in the event
// stream.
static uint16_t last_rx_flags;
// Explicit test commands control bounded response suppression; zero disables
// injection.
static uint16_t fault_stride, fault_budget;
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
  static constexpr arq::diagnostics::EventContext kContext{
      receiver.session, receiver.last_sequence, sender.attempts};
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
  for (uint8_t i = 0; i < sizeof addresses; i++) {
    SPI.beginTransaction(SPISettings(ARQ_SPI_HZ, MSBFIRST, SPI_MODE0));
    digitalWrite(board_ssot.cs, LOW);
    SPI.transfer(addresses[i]);
    values[i] = SPI.transfer(0);
    digitalWrite(board_ssot.cs, HIGH);
    SPI.endTransaction();
  }
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
  for (uint8_t i = 0; i < 4; i++) {
    SPI.beginTransaction(SPISettings(ARQ_SPI_HZ, MSBFIRST, SPI_MODE0));
    digitalWrite(board_ssot.cs, LOW);
    SPI.transfer(0x14 + i);
    values[2 + i] = SPI.transfer(0);
    digitalWrite(board_ssot.cs, HIGH);
    SPI.endTransaction();
  }
  arq::diagnostics::RecordFrame(GetEventContext(), name, values, sizeof values,
                                0, 0);
}
// Starts a bounded incremental status dump instead of concatenating a large
// string.
static void ScheduleStatus() {
  if (!status_next) status_next = 1;
}
// Emits at most one pending status item per call so logging cannot monopolize
// loop.
static void FlushStatus() {
  // Yield between status lines so an RX/response burst retains the bounded
  // logger.
  if (!status_next || arq::diagnostics::PendingLineCount()) return;
  switch (status_next++) {
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
    case 4: {
      char* out = arq::diagnostics::AcquireLine();
      if (out)
        snprintf(out, arq::diagnostics::kLineCapacity,
                 "A t=%lu e=STATUS s=%08lX app=%lu dup=%lu gen=%lu sup=%lu "
                 "att=%lu done=%lu crc=%lu overflow=%lu ready=%u\n",
                 static_cast<unsigned long>(millis()),
                 static_cast<unsigned long>(CurrentSession()),
                 static_cast<unsigned long>(receiver.deliveries),
                 static_cast<unsigned long>(receiver.duplicates),
                 static_cast<unsigned long>(generated),
                 static_cast<unsigned long>(suppressed),
                 static_cast<unsigned long>(attempted),
                 static_cast<unsigned long>(completed),
                 static_cast<unsigned long>(crc_errors),
                 static_cast<unsigned long>(arq::diagnostics::OverflowCount()),
                 ready);
      break;
    }
    case 5:
      arq::diagnostics::RecordEvent(GetEventContext(), "RESULT",
                                    static_cast<int16_t>(sender.result),
                                    static_cast<uint32_t>(sender.state));
      break;
    case 6:
      arq::diagnostics::RecordEvent(GetEventContext(), "RTT_LAST", 0,
                                    sender.rtt_last);
      break;
    case 7:
      arq::diagnostics::RecordEvent(GetEventContext(), "RTT_MIN", 0,
                                    sender.rtt_min);
      break;
    case 8:
      arq::diagnostics::RecordEvent(GetEventContext(), "RTT_MAX", 0,
                                    sender.rtt_max);
      break;
    case 9:
      arq::diagnostics::RecordEvent(GetEventContext(), "RTT_COUNT", 0,
                                    sender.rtt_count);
      break;
    case 10:
      arq::diagnostics::RecordEvent(GetEventContext(), "RX_DONE_COUNT", 0,
                                    rx_done);
      break;
    case 11:
      arq::diagnostics::RecordEvent(GetEventContext(), "DECODE_ERRORS", 0,
                                    decode_errors);
      break;
    case 12:
      arq::diagnostics::RecordEvent(GetEventContext(), "CONTROL_REJECTS", 0,
                                    control_rejects);
      break;
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
  }
}
// Restores continuous receive; reports failure before the sender starts its ACK
// timer.
static bool RestoreReceive() {
  receiver.state =
      arq::ReceiverState::kReturningToRx;  // RX restoration is checked after
                                           // every response/error.
  RecordReceiveDiagnostics("RX_RESTART", radio.getIRQFlags());
  int16_t rc = radio.startReceive();
  arq::diagnostics::RecordEvent(GetEventContext(), "RX_READY", rc, 0);
#if defined(ARQ_ROLE_SENDER)
  if (!rc) RecordRadioRegisters("RX_STATE");
#endif
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
  if (arq::IsSenderActive(&sender)) {
    // Fatal adapter errors terminate even if the sender was waiting in RX.
    sender.state = arq::SenderState::kFailed;
    sender.result = arq::Result::kRadioError;
    sender.used_up = true;
  }
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
    receiver.stopped = true;
    arq::diagnostics::RecordEvent(GetEventContext(), "STOP", 0, 0);
    return;
  }
  if (action.kind == arq::CommandKind::kArm) {
    const uint32_t value = action.session;
    bool ok = false;
    uint32_t previous = CurrentSession();
#if defined(ARQ_ROLE_SENDER)
    ok = arq::ArmSender(&sender, value);
#else
    if (receiver.armed && receiver.session == value)
      ok = true;
    else if (!radio_tx && !response_wait)
      ok = arq::ArmReceiver(&receiver, value);
#endif
    if (ok && previous != value) {
      generated = suppressed = attempted = completed = crc_errors = 0;
      rx_done = decode_errors = control_rejects = 0;
      last_rx_flags = 0;
      fault_stride = fault_budget = 0;
    }
    if (ok && ready && parked) {
#if defined(ARQ_ROLE_SENDER)
      if (!sender.stopped) ok = RestoreReceive();
#else
      if (!receiver.stopped) ok = RestoreReceive();
#endif
    }
    arq::diagnostics::RecordEvent(GetEventContext(), ok ? "ARM" : "ARM_REJECT",
                                  ready ? 0 : -1, value);
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
  arq::InitSender(&sender);
  arq::InitReceiver(&receiver);
  reset_flags = GPR_GPR0;
#if defined(ARQ_RADIO_ONLY_DIAGNOSTIC) && defined(LORA_ROLE_RECEIVER)
  if (!PrepareTrackerForRadioOnly()) {
    startup_status = -1;
    arq::diagnostics::RecordEvent(GetEventContext(), "SD_PRESENT_BLOCKED",
                                  startup_status, 0);
    return;
  }
#endif
  // Tracker board init keeps EN-LORA low through DATA/ACK; omit the diagnostic
  // flag to restore normal setup.
  board_ssot_init();
  delay(application_config::startup::kRadioSettleMs);
  if (!SPI.swap(ARQ_SPI_ROUTE)) {
    startup_status = -1;
    return;
  }
  SPI.begin();
  radio.reset();
  bool supported = false;
  for (uint8_t i = 0; i < application_config::startup::kVersionProbeAttempts;
       i++) {
    SPI.beginTransaction(SPISettings(ARQ_SPI_HZ, MSBFIRST, SPI_MODE0));
    digitalWrite(board_ssot.cs, LOW);
    SPI.transfer(0x42);
    uint8_t version = SPI.transfer(0);
    digitalWrite(board_ssot.cs, HIGH);
    SPI.endTransaction();
    supported = version == RADIOLIB_SX1278_CHIP_VERSION ||
                version == RADIOLIB_SX1278_CHIP_VERSION_ALT ||
                version == RADIOLIB_SX1278_CHIP_VERSION_RFM9X;
    if (supported) break;
    delay(application_config::startup::kRadioSettleMs);
  }
  int16_t rc = supported ? 0 : RADIOLIB_ERR_CHIP_NOT_FOUND;
  if (!rc)
    rc = radio.begin(ARQ_FREQUENCY_HZ / 1000000.0f, ARQ_BANDWIDTH_KHZ,
                     ARQ_SPREADING_FACTOR, ARQ_CODING_RATE, ARQ_SYNC_WORD,
                     ARQ_TX_POWER_DBM, ARQ_PREAMBLE_SYMBOLS, 0);
  // The 915 MHz profile uses the HF bank; clear only bit 3 and preserve mode
  // bits.
  if (!rc) rc = module.SPIsetRegValue(RADIOLIB_SX127X_REG_OP_MODE, 0, 3, 3);
  if (!rc) rc = radio.setOutputPower(ARQ_TX_POWER_DBM, false);
  if (!rc) rc = radio.explicitHeader();
  if (!rc) rc = radio.setCRC(ARQ_CRC_ENABLED);
  if (!rc) rc = radio.invertIQ(ARQ_IQ_INVERTED);
  if (!rc) rc = radio.standby();
  startup_status = rc;
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
// Services commands, logging and bounded radio state transitions without heap
// allocation.
void Poll() {
  if (updi_uart_enabled() && !attached) ScheduleStatus();
  attached = updi_uart_enabled();
  if (updi_uart_rx_poll()) FeedCommandByte(updi_uart_rx());
  uint32_t now = millis();
  arq::SenderState old = sender.state;
  if (ready && !parked) {
    uint16_t flags = radio.getIRQFlags();
    if (radio_tx) {
      bool done = flags & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_TX_DONE;
      if (done || now - tx_started >= ARQ_TX_MS) {
        int16_t rc = radio.finishTransmit();
        radio_tx = false;
        arq::diagnostics::RecordEvent(
            GetEventContext(), done ? "TX_DONE" : "TX_TIMEOUT", rc, flags);
        bool rx = RestoreReceive();
#if defined(ARQ_ROLE_SENDER)
        arq::HandleTxCompletion(&sender, millis(), done && !rc && rx);
        if (sender.state == arq::SenderState::kWaitingAck) sender.tx_done = now;
#else
        if (done && !rc) ++completed;
#endif
        if (rc) FailAdapter(rc);
      }
    } else if (!response_wait &&
               (flags & RADIOLIB_SX127X_CLEAR_IRQ_FLAG_RX_DONE))
      HandleReceive(now, flags);
    // Read matching controls before evaluating deadlines or initiating a retry.
    if (sender.state == arq::SenderState::kWaitingAck &&
        arq::IsDeadlineDue(now, sender.retry_at))
      RecordReceiveDiagnostics("RX_TIMEOUT", radio.getIRQFlags());
    arq::PollSender(&sender, now);
#if defined(ARQ_ROLE_SENDER)
    bool start = sender.state == arq::SenderState::kTransmitting && !radio_tx;
    if (start) wire_length = arq::EncodeFrame(&sender.frame, wire, sizeof wire);
#else
    bool start = response_wait && arq::IsDeadlineDue(now, response_at);
#endif
    if (start && ready) {
      response_wait = false;
      int16_t rc = radio.standby();
      if (!rc) rc = radio.startTransmit(wire, wire_length);
      ++attempted;
      if (rc) {
        int16_t cleanup = radio.finishTransmit();
        bool rx = RestoreReceive();
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
#if defined(ARQ_ROLE_SENDER)
  bool stopped = sender.stopped;
#else
  bool stopped = receiver.stopped;
#endif
  if (ready && !parked && stopped && !radio_tx && !response_wait &&
      !arq::IsSenderActive(&sender)) {
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
