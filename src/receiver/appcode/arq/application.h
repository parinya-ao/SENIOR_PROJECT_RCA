#pragma once

namespace arq::app {

/// Initializes the receiver transaction and configures the active board radio.
void Initialize();
/// Advances command, radio, deadline, and diagnostic work without waiting.
void Poll();

}  // namespace arq::app
