#!/usr/bin/env bash
# Run independent upstream SIB connections without resetting or reflashing.
set -eu
experiment_root=$(cd "$(dirname "$0")/.." && pwd)
root=$(cd "$experiment_root/../.." && pwd)
cd "$experiment_root"
out=${1:-"$root/artifacts/updi/runs/$(date -u +%Y%m%dT%H%M%SZ)-baseline-sib"}
case "$out" in /*) ;; *) out="$root/$out" ;; esac
mkdir -p "$out"
hash=$(sha256sum "$root/.pio/build/receiver/firmware.hex" | cut -d ' ' -f 1)
printf 'ID,firmware_sha256,baud,reset,wiring,exit,sib,echo_errors,short_reads,first_failure\n' > "$out/results.csv"
for baud in 115200 57600 38400; do
  for attempt in $(seq 1 20); do
    id="sib-$baud-$attempt"
    status=0
    timeout 12 uv run --project "$experiment_root" python "$repo_root/third_party/upditerm/upditerm.py" /dev/ttyUSB0 "$baud" -i > "$out/$id.stdout" 2> "$out/$id.stderr" || status=$?
    sib=$(grep -a -m 1 'AVR ' "$out/$id.stdout" | tr -d '\000\r\n' | tr ',' ';' || true)
    echo_errors=$(cat "$out/$id.stdout" "$out/$id.stderr" | grep -a -c -E 'No echo|/echo:|/send/echo:' || true)
    short_reads=$(cat "$out/$id.stdout" "$out/$id.stderr" | grep -a -c -E 'Short read|/response:' || true)
    first=$(cat "$out/$id.stdout" "$out/$id.stderr" | grep -a -m 1 -E 'No echo|Short read|Error|Exception|baud=.*expected=' | tr ',' ';' || true)
    if [ "$status" -ne 0 ] && [ -z "$first" ]; then first="process exit $status"; fi
    printf '%s,%s,%s,no,unverified,%s,%s,%s,%s,%s\n' "$id" "$hash" "$baud" "$status" "$sib" "$echo_errors" "$short_reads" "$first" >> "$out/results.csv"
    printf '%s exit=%s sib=%s echo=%s short=%s\n' "$id" "$status" "$sib" "$echo_errors" "$short_reads"
  done
done
