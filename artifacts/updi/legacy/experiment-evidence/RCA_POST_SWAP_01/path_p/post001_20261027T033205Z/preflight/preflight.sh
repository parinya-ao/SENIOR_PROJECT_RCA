#!/usr/bin/env bash
# Read-only direct-host preflight; this script does not open serial ports.
set +e
BASE="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$BASE/post001_20261027T033205Z/preflight"
STABLE="/dev/serial/by-path/pci-0000:00:14.0-usb-0:4:1.0-port0"
ID_PATH="pci-0000:00:14.0-usb-0:4:1.0"

run_capture() {
    local label="$1"
    shift
    local stdout_file="$OUT/$label.stdout.txt"
    local stderr_file="$OUT/$label.stderr.txt"
    local meta_file="$OUT/$label.meta.txt"
    local start_utc end_utc start_uptime end_uptime rc quoted
    start_utc="$(date -u +%Y-%m-%dT%H:%M:%S.%NZ)"
    read -r start_uptime _ < /proc/uptime
    printf -v quoted '%q ' "$@"
    "$@" >"$stdout_file" 2>"$stderr_file"
    rc=$?
    end_utc="$(date -u +%Y-%m-%dT%H:%M:%S.%NZ)"
    read -r end_uptime _ < /proc/uptime
    {
        printf 'label=%s\nargv_shell_escaped=%s\n' "$label" "${quoted% }"
        printf 'start_utc=%s\nend_utc=%s\n' "$start_utc" "$end_utc"
        printf 'start_proc_uptime_s=%s\nend_proc_uptime_s=%s\nexit_code=%s\n' "$start_uptime" "$end_uptime" "$rc"
        printf 'stdout_sha256='
        sha256sum "$stdout_file" | awk '{print $1}'
        printf 'stderr_sha256='
        sha256sum "$stderr_file" | awk '{print $1}'
    } >"$meta_file"
}

run_capture cli_inventory env PYTHONPATH=experiments/updi_rca/src uv run --project experiments/updi_rca python -m updi_rca.cli inventory
run_capture stable_udev_properties udevadm info --query=property --name="$STABLE"
run_capture stable_link_target readlink -e "$STABLE"
run_capture fuser_stable_path fuser -v "$STABLE"
run_capture lsof_stable_path lsof -nP "$STABLE"
run_capture upditerm_processes pgrep -a -f '[u]pditerm'
run_capture avrdude_processes pgrep -a -f '[a]vrdude'
run_capture usb_topology lsusb -t
run_capture kernel_log_last_15_minutes journalctl -k --since '15 minutes ago' --no-pager -o short-iso
run_capture power_supply_files find /sys/class/power_supply -maxdepth 2 -type f -print

properties="$OUT/stable_udev_properties.stdout.txt"
inventory="$OUT/cli_inventory.stdout.txt"
matches="$(grep -Fxc "ID_PATH=$ID_PATH" "$properties")"
inventory_matches="$(grep -Fc "\"id_path\": \"$ID_PATH\"" "$inventory")"
link_target_rc="$(cat "$OUT/stable_link_target.meta.txt" | sed -n 's/^exit_code=//p')"
fuser_rc="$(cat "$OUT/fuser_stable_path.meta.txt" | sed -n 's/^exit_code=//p')"
lsof_rc="$(cat "$OUT/lsof_stable_path.meta.txt" | sed -n 's/^exit_code=//p')"
updi_rc="$(cat "$OUT/upditerm_processes.meta.txt" | sed -n 's/^exit_code=//p')"
avrdude_rc="$(cat "$OUT/avrdude_processes.meta.txt" | sed -n 's/^exit_code=//p')"
if [[ "$matches" == 1 && "$inventory_matches" == 1 && "$link_target_rc" == 0 && "$fuser_rc" == 1 && "$lsof_rc" == 1 && "$updi_rc" == 1 && "$avrdude_rc" == 1 ]]; then
    printf 'PREFLIGHT=GREEN\nID_PATH=%s\nCLI_ID_PATH_MATCHES=%s\nFUSER_EXIT=%s (no holder)\nLSOF_EXIT=%s (no open file rows; inspect stderr warning)\nUPDITERM_EXIT=%s (no process match)\nAVRDUDE_EXIT=%s (no process match)\n' "$ID_PATH" "$inventory_matches" "$fuser_rc" "$lsof_rc" "$updi_rc" "$avrdude_rc" >"$OUT/GATE.txt"
else
    printf 'PREFLIGHT=RED\nID_PATH_PROPERTY_MATCHES=%s\nCLI_ID_PATH_MATCHES=%s\nLINK_EXIT=%s\nFUSER_EXIT=%s\nLSOF_EXIT=%s\nUPDITERM_EXIT=%s\nAVRDUDE_EXIT=%s\n' "$matches" "$inventory_matches" "$link_target_rc" "$fuser_rc" "$lsof_rc" "$updi_rc" "$avrdude_rc" >"$OUT/GATE.txt"
fi
cat "$OUT/GATE.txt"
