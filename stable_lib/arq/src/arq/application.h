/// @file
/// Coordinates one bench radio; all calls run in the Arduino foreground
/// context.

#ifndef SENIOR_PROJECT_RCA_SRC_ARQ_APPLICATION_H_
#define SENIOR_PROJECT_RCA_SRC_ARQ_APPLICATION_H_
namespace arq {
namespace app {
/// Initializes protocol, board power, SPI and radio after Arduino
/// initialization. Leaves failed/unsafe configurations parked; sends no
/// application DATA.
void Initialize();
/// Services command input, IRQ polling, RX/TX recovery, deadlines and
/// diagnostics. Call frequently; this function never waits for a host
/// diagnostic reader.
void Poll();
}  // namespace app
}  // namespace arq
#endif  // SENIOR_PROJECT_RCA_SRC_ARQ_APPLICATION_H_
