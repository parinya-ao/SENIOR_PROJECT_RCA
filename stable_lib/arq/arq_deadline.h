/// Shared wrap-safe deadline comparison for both ARQ roles.

#ifndef SENIOR_PROJECT_RCA_SRC_ARQ_ARQ_DEADLINE_H_
#define SENIOR_PROJECT_RCA_SRC_ARQ_ARQ_DEADLINE_H_

#include <stdint.h>

namespace arq {
/// Returns true when now equals or follows deadline modulo uint32_t.
///
/// Timestamps must be in the same millisecond clock domain and less than
/// 2^31 ms apart.
/// @param now Current tick in milliseconds.
/// @param deadline Absolute tick in the same clock domain.
/// @return True when the deadline is due.
inline bool IsDeadlineDue(uint32_t now, uint32_t deadline) {
  return now - deadline < (UINT32_C(1) << 31U);
}
}  // namespace arq

#endif  // SENIOR_PROJECT_RCA_SRC_ARQ_ARQ_DEADLINE_H_
