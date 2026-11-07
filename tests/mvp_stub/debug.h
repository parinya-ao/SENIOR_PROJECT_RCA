#pragma once
template <typename... Args> inline void host_debug(const char*, const Args&...) {}
#define DEBUG_TS(...) host_debug(__VA_ARGS__)
