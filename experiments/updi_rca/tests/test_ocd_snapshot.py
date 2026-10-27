from updi_rca.probes import collect_ocd_messages


def test_ocd_snapshot_reads_only_messages_marked_valid():
    statuses = iter([0x10, 0x10, 0x00])
    messages = iter([ord("H"), ord("i")])

    result = collect_ocd_messages(lambda: next(statuses), lambda: next(messages), max_bytes=8)

    assert result == {"statuses": [0x10, 0x10, 0x00], "message": b"Hi", "truncated": False}


def test_ocd_snapshot_stops_at_the_byte_bound():
    status_reads = []

    def read_status():
        status_reads.append(0x10)
        return 0x10

    result = collect_ocd_messages(read_status, lambda: ord("x"), max_bytes=3)

    assert result["message"] == b"xxx"
    assert result["truncated"] is True
    assert len(status_reads) == 4
