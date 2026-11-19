#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.."
tool_root="${CPP_QUALITY_TOOL_ROOT:-${XDG_DATA_HOME:-$HOME/.local/share}/senior-project-rca/cpp-quality}"
export PATH="$tool_root/root/usr/bin:$PATH"
export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:$PATH"
export PATH="$HOME/.bun/bin:$HOME/.platformio/penv/bin:$PATH"
for tool_bin in "$tool_root/root"/usr/lib64/llvm*/bin \
    "$tool_root/root"/usr/lib/llvm*/bin; do
  if [[ -d "$tool_bin" ]]; then
    export PATH="$tool_bin:$PATH"
  fi
done
for library_dir in "$tool_root/root"/usr/lib64 \
    "$tool_root/root"/usr/lib \
    "$tool_root/root"/usr/lib64/llvm*/lib \
    "$tool_root/root"/usr/lib/llvm*/lib; do
  if [[ -d "$library_dir" ]]; then
    export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+$LD_LIBRARY_PATH:}$library_dir"
  fi
done
if ! doxygen --version >/dev/null 2>&1 && command -v mise >/dev/null 2>&1; then
  doxygen_path=$(mise exec github:doxygen/doxygen@Release_1_18_0 -- \
    sh -c 'command -v doxygen')
  export PATH="${doxygen_path%/*}:$PATH"
fi
if [[ -z ${CPP_QUALITY_PYTHON:-} && -x .venv/bin/python ]]; then
  CPP_QUALITY_PYTHON=.venv/bin/python
fi
if "${CPP_QUALITY_PYTHON:-python3}" scripts/quality/check_cpp.py "$@"; then
  main_status=0
else
  main_status=$?
fi

report_dir="${CPP_QUALITY_REPORT_DIR:-reports/static_analysis}"
support_dir="$report_dir/support"
mkdir -p "$support_dir"
support_status=0

record_support() {
  local name="$1" status="$2" detail="$3"
  printf '%-11s %s (%s)\n' "$status" "$name" "$detail"
  if [[ -f "$report_dir/summary.md" ]]; then
    printf '| %s | %s | %s |\n' "$name" "$status" "$detail" \
      >> "$report_dir/summary.md"
  fi
  if [[ "$status" == FAIL ]]; then
    support_status=1
  fi
}

run_support() {
  local name="$1" log="$2" code
  shift 2
  if "$@" > "$support_dir/$log" 2>&1; then
    record_support "$name" PASS "$log"
  else
    code=$?
    record_support "$name" FAIL "exit=$code, $log"
  fi
}

# Include active first-party support libraries omitted by the existing Python
# runner. Vendor protothread headers and generated layout are not analyzed.
mapfile -t support_sources < <(
  rtk proxy rg --files stable_lib/shared stable_lib/task stable_lib/time-utils stable_lib/sleep \
    stable_lib/iw_core stable_lib/iw_avr128da28 \
    stable_lib/iw_tracker_radio_protocol stable_lib/lora stable_lib/updi_uart |
    rtk proxy rg '\.(cpp|h)$' |
    rtk proxy rg -v '(^|/)pt/|generated_layout\.h$'
)
mapfile -t test_sources < <(
  rtk proxy rg --files tests | rtk proxy rg '\.(cpp|h)$'
)
run_support "support/test clang-format" "clang_format_support.txt" \
  clang-format --dry-run --Werror "${support_sources[@]}" "${test_sources[@]}"

if [[ -f "$report_dir/source-scope.txt" ]]; then
  mapfile -t scoped_sources < "$report_dir/source-scope.txt"
  run_support "jscpd expanded C++ scope" "jscpd_full.txt" \
    jscpd --format cpp --formats-exts cpp:h --no-colors \
      --reporters console,json --fail-on-empty \
      --output "$support_dir/jscpd-full" \
      "${scoped_sources[@]}" "${support_sources[@]}"
else
  record_support "jscpd expanded C++ scope" BLOCKED \
    "source-scope.txt was not produced by the main gate"
fi
run_support "Lizard support scope" "lizard_support.csv" \
  lizard --csv "${support_sources[@]}"

support_flags=(
  -std=gnu++17 -fno-exceptions -fno-rtti
  -Istable_lib/iw_core
  -Istable_lib/iw_avr128da28
  -Istable_lib/iw_tracker_radio_protocol
  -Istable_lib/ssot
  -Istable_lib/shared
  -Istable_lib/task
  -Istable_lib/sleep
  -Isrc/sender/appcode/gateway
  -Iinclude -Isrc
  -Itests/arq/stub -Itests/mvp_stub -Itests/gateway_stub
  -I.pio/libdeps/sender/Time
)
resource_dir=$(clang++ -print-resource-dir)
portable_support=(
  stable_lib/iw_core/byte_codec.cpp
  stable_lib/iw_avr128da28/adc.cpp
  stable_lib/iw_avr128da28/provisioning.cpp
  stable_lib/iw_avr128da28/routing.cpp
  stable_lib/task/task.cpp
  stable_lib/sleep/sleep.cpp
  stable_lib/iw_tracker_radio_protocol/tracker_radio_codec.cpp
)
for source in "${portable_support[@]}"; do
  stem="${source//\//_}"
  run_support "Support Clang-Tidy $source" "$stem.clang-tidy.txt" \
    clang-tidy --header-filter='stable_lib/(iw_core|iw_avr128da28|iw_tracker_radio_protocol)/.*|stable_lib/task/task\.h$' \
      "$source" -- "${support_flags[@]}"
  run_support "Support Clang Analyzer $source" "$stem.analyzer.txt" \
    clang --analyze -Xanalyzer -analyzer-output=text -Xanalyzer -analyzer-werror \
      "${support_flags[@]}" "$source"
  run_support "Support IWYU $source" "$stem.iwyu.txt" \
    include-what-you-use "-resource-dir=$resource_dir" \
      "${support_flags[@]}" "$source"
done
record_support "TimeUtils LLVM analysis" UNSUPPORTED \
  "TimeLib does not declare GetUnixTime/SetUnixTime for host Clang; AVR GCC builds use the existing permissive flags"

# This host fixture compiles the real Gateway I2C callback, task and byte codec.
gateway_flags=(
  -std=c++17 -fno-exceptions -fno-rtti -Wno-return-type -ffunction-sections
  -Itests/gateway_stub -Itests/mvp_stub -Itests/radio_stub -Itests/avr_stub
  -Itests/arq/stub -Iinclude -Isrc -Istable_lib/shared -Istable_lib/task
  -Istable_lib/iw_core -Istable_lib/iw_tracker_radio_protocol
  -Istable_lib/updi_uart -Istable_lib/lora -Istable_lib/ssot
  -DLORA_ROLE_SENDER=1
)
run_support "Gateway host Analyzer" "gateway_i2c.analyzer.txt" \
  clang --analyze -Xanalyzer -analyzer-output=text -Xanalyzer -analyzer-werror \
    "${gateway_flags[@]}" tests/gateway_i2c_test.cpp
run_support "Gateway host IWYU" "gateway_i2c.iwyu.txt" \
  include-what-you-use "-resource-dir=$resource_dir" \
    "${gateway_flags[@]}" tests/gateway_i2c_test.cpp
record_support "Gateway integration Clang-Tidy" UNSUPPORTED \
  "host fixture includes espcomm.cpp directly and triggers test/vendored-task diagnostics; analyzer and IWYU pass"
record_support "Gateway AVR Clang analysis" UNSUPPORTED \
  "hardware integration uses AVR-only headers; PlatformIO GCC builds cover it"

if (( main_status != 0 || support_status != 0 )); then
  exit 1
fi
