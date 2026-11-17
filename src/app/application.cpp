// Selects one role implementation at compile time and forwards its lifecycle.

#include "application.h"

#include <Arduino.h>

#if (defined(LORA_APP_GATEWAY) + defined(LORA_APP_RELIABLE) +          \
     defined(LORA_APP_ARQ) + defined(LORA_APP_MVP) +                   \
     defined(LORA_APP_REVERSE_RAW) + defined(LORA_APP_LEGACY_SENDER) + \
     defined(LORA_APP_LEGACY_RECEIVER)) != 1
#error "Select exactly one firmware application"
#endif

#if defined(LORA_APP_GATEWAY)
#include <gateway_app.h>
#elif defined(LORA_APP_RELIABLE)
#include <reliable_app.h>
#elif defined(LORA_APP_ARQ)
#include <arq/application.h>
#elif defined(LORA_APP_MVP)
#include <mvp_app.h>
#elif defined(LORA_APP_REVERSE_RAW)
#include <reverse_raw_app.h>
#elif defined(LORA_APP_LEGACY_SENDER)
#include <legacy_sender.h>
#elif defined(LORA_APP_LEGACY_RECEIVER)
#include <legacy_receiver.h>
#endif

namespace firmware_app {

void Initialize() {
#if defined(LORA_APP_GATEWAY)
  gateway_app::Initialize();
#elif defined(LORA_APP_RELIABLE)
  reliable_app::Initialize();
#elif defined(LORA_APP_ARQ)
  arq::app::Initialize();
#elif defined(LORA_APP_MVP)
  mvp_app::Initialize();
#elif defined(LORA_APP_REVERSE_RAW)
  reverse_raw_app::Initialize();
#elif defined(LORA_APP_LEGACY_SENDER)
  legacy_sender::Initialize();
#elif defined(LORA_APP_LEGACY_RECEIVER)
  legacy_receiver::Initialize();
#endif
}

void Poll() {
#if defined(LORA_APP_GATEWAY)
  gateway_app::Poll();
#elif defined(LORA_APP_RELIABLE)
  reliable_app::Poll();
#elif defined(LORA_APP_ARQ)
  arq::app::Poll();
#elif defined(LORA_APP_MVP)
  mvp_app::Poll();
#elif defined(LORA_APP_REVERSE_RAW)
  reverse_raw_app::Poll();
#elif defined(LORA_APP_LEGACY_SENDER)
  legacy_sender::Poll();
#elif defined(LORA_APP_LEGACY_RECEIVER)
  legacy_receiver::Poll();
#endif
}

void PreMain() {
#if !defined(LORA_APP_GATEWAY) && !defined(LORA_APP_LEGACY_SENDER)
  _PROTECTED_WRITE(CPUINT.CTRLA, 0);
#endif
}

}  // namespace firmware_app
