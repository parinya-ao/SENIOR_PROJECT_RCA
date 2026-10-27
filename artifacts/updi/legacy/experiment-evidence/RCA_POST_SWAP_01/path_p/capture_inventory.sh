#!/usr/bin/env bash
# Read-only direct-host inventory recorder. This script never opens a serial device.
set +e
ROOT="$(pwd)"
BASE="$ROOT/experiments/updi_rca/evidence/RCA_POST_SWAP_01/path_p"
OUT="$BASE/commands"
STABLE="/dev/serial/by-path/pci-0000:00:14.0-usb-0:4:1.0-port0"
ID_PATH="pci-0000:00:14.0-usb-0:4:1.0"

if [[ -e "$OUT" ]]; then
    printf 'Refusing to overwrite existing command inventory: %s\n' "$OUT" >&2
    exit 2
fi
mkdir "$OUT" || exit 2

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
        printf 'label=%s\n' "$label"
        printf 'argv_shell_escaped=%s\n' "${quoted% }"
        printf 'start_utc=%s\nend_utc=%s\n' "$start_utc" "$end_utc"
        printf 'start_proc_uptime_s=%s\nend_proc_uptime_s=%s\n' "$start_uptime" "$end_uptime"
        printf 'exit_code=%s\n' "$rc"
        printf 'stdout_sha256='
        sha256sum "$stdout_file" | awk '{print $1}'
        printf 'stderr_sha256='
        sha256sum "$stderr_file" | awk '{print $1}'
    } >"$meta_file"
    printf '%s exit=%s start=%s end=%s\n' "$label" "$rc" "$start_utc" "$end_utc"
}

printf 'epoch=RCA_POST_SWAP_01\nlane=P\nexpected_ID_PATH=%s\nuser_reported_physical_pairing=P->Y\nserial_open_attempted=false\nhardware_moved=false\n' "$ID_PATH" >"$BASE/capture_context.txt"

run_capture date_snapshot date -u --iso-8601=ns
run_capture cli_inventory uv run --project experiments/updi_rca python -m updi_rca.cli inventory
run_capture by_path_listing ls -la /dev/serial/by-path
run_capture stable_udev_properties udevadm info --query=property --name="$STABLE"
run_capture stable_udev_sysfs_path udevadm info --query=path --name="$STABLE"
run_capture stable_link_target readlink -e "$STABLE"
run_capture stable_udev_attribute_walk udevadm info --attribute-walk --name="$STABLE"
run_capture usb_topology lsusb -t
run_capture fuser_stable_path fuser -v "$STABLE"
run_capture lsof_stable_path lsof -nP "$STABLE"
run_capture upditerm_processes pgrep -a -f '[u]pditerm'
run_capture avrdude_processes pgrep -a -f '[a]vrdude'
run_capture kernel_log_last_15_minutes journalctl -k --since '15 minutes ago' --no-pager -o short-iso
run_capture power_supply_files find /sys/class/power_supply -maxdepth 2 -type f -print
run_capture uv_version uv --version
run_capture python_version uv run --project experiments/updi_rca python --version
run_capture pyserial_version_and_hash uv run --project experiments/updi_rca python -c 'import hashlib, pathlib, serial; p=pathlib.Path(serial.__file__); print("version="+serial.__version__); print("module="+str(p)); print("sha256="+hashlib.sha256(p.read_bytes()).hexdigest())'
run_capture source_hashes sha256sum experiments/updi_rca/src/updi_rca/probes.py experiments/updi_rca/src/updi_rca/runner.py experiments/updi_rca/src/updi_rca/identity.py experiments/updi_rca/src/updi_rca/cli.py experiments/updi_rca/pyproject.toml

printf 'Command results are in %s; no tty was opened.\n' "$OUT"
