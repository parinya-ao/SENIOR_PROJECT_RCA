// Arduino lifecycle for the physical Sender board.
#include <Arduino.h>

#if !defined(LORA_ROLE_SENDER)
#error "Wrong board role for this entry point"
#endif

#if (defined(LORA_APP_GATEWAY) + defined(LORA_APP_RELIABLE) + \
     defined(LORA_APP_ARQ) + defined(LORA_APP_MVP) +          \
     defined(LORA_APP_REVERSE_RAW)) != 1
#error "Select exactly one firmware application"
#endif

#if defined(LORA_APP_RELIABLE)
#include "app/reliable_app.h"
namespace selected = reliable_app;
#elif defined(LORA_APP_ARQ)
#include "app/arq/arq_application.h"
namespace selected = arq::app;
#elif defined(LORA_APP_MVP)
#include <mvp_app.h>
namespace selected = mvp_app;
#elif defined(LORA_APP_REVERSE_RAW)
#include <reverse_raw_app.h>
namespace selected = reverse_raw_app;
#elif defined(LORA_APP_GATEWAY)
#include "gateway/gateway_app.h"
namespace selected = gateway_app;
#else
#error "Select one application for this board"
#endif

#if !defined(LORA_APP_GATEWAY)
void onPreMain() { _PROTECTED_WRITE(CPUINT.CTRLA, 0); }
#endif

void setup() { selected::Initialize(); }
void loop() { selected::Poll(); }
