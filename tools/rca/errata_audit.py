"""Offline supplement: SX127x counter limitations and conditional link budget."""

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.rca.analyze import ADDRESSES, analyze

REGISTERS = tuple(
    dict.fromkeys(
        (*ADDRESSES, 0x0B, 0x12, 0x14, 0x15, 0x16, 0x17, 0x18, 0x1C, 0x2F, 0x30, 0x36, 0x3A)
    )
)


def interpret_rx(irq_flags, hardware_packets, *, crc_present=None):
    """Interpret one pre-clear event, not repeated polls of the same latched IRQ."""
    for value, maximum in ((irq_flags, 255), (hardware_packets, 65535)):
        if value is not None and (type(value) is not int or not 0 <= value <= maximum):
            raise ValueError("register value outside range")
    if crc_present is not None and type(crc_present) is not bool:
        raise ValueError("CRC presence must be bool or unknown")
    result = {
        name: None if irq_flags is None else bool(irq_flags & mask)
        for name, mask in (
            ("rx_done", 0x40),
            ("crc_error", 0x20),
            ("valid_header", 0x10),
            ("rx_timeout_irq", 0x80),
        )
    }
    increment = None
    if irq_flags is not None:
        if not result["rx_done"] or result["crc_error"] or crc_present is False:
            increment = 0
        elif crc_present is True:
            increment = 1
    result.update(
        hardware_packets=hardware_packets,
        zero_counter_proves_no_reception=False,
        valid_packet_increment=increment,
        limitation="SX1276 erratum 2.4: RX Continuous can omit first valid packet; RX Single counter does not increment",
    )
    return result


def decode_snapshot(snapshot):
    result = {f"{address:02X}": None for address in REGISTERS}
    if snapshot is None:
        return result
    if not isinstance(snapshot, str) or len(snapshot) != 2 * len(ADDRESSES):
        raise ValueError("expected original 23-byte snapshot")
    data = bytes.fromhex(snapshot)
    if len(data) != len(ADDRESSES):
        raise ValueError("snapshot length")
    result.update({f"{address:02X}": value for address, value in zip(ADDRESSES, data)})
    return result


def link_budget(frequency_hz, distance_m, configured_tx_dbm, reported_rssi_dbm):
    values = (frequency_hz, distance_m, configured_tx_dbm, reported_rssi_dbm)
    if not all(math.isfinite(x) for x in values) or frequency_hz <= 0 or distance_m <= 0:
        raise ValueError("finite values and positive frequency/distance required")
    loss = 20 * math.log10(4 * math.pi * distance_m * frequency_hz / 299792458)
    ideal = configured_tx_dbm - loss
    return dict(
        fspl_db=loss,
        ideal_rx_dbm=ideal,
        conditional_difference_db=ideal - reported_rssi_dbm,
        measured_path_loss_db=None,
        assumptions="Free space, isotropic antennas, actual conducted TX equals configured TX, calibrated packet RSSI; unverified on hardware",
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args(argv)
    result = analyze(args.evidence)
    diagnostics = []
    for event in result["observed_events"]:
        if event["e"] in ("RAW_RX_READY", "RAW_RX_DONE", "RAW_RX_TIMEOUT"):

            def number(key):
                return int(event[key]) if key in event else None

            hop = number("hop")
            diagnostics.append(
                dict(
                    event=event["e"],
                    host_ns=event["host_ns"],
                    **interpret_rx(
                        number("flags"),
                        number("packets"),
                        crc_present=None if hop is None else bool(hop & 0x40),
                    ),
                )
            )
    result["receiver_counter_audit"] = diagnostics
    result["counter_interpretation"] = (
        "A zero counter is not evidence of zero receptions; no events are inferred"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result["evidence_integrity"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
