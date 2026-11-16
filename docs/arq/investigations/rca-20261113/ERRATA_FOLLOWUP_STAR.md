# STAR — Tracker→Rudolph receiver errata and transport follow-up

FACT: **verdict remains HARDWARE_MEASUREMENT_REQUIRED**. This is the current
offline addendum to [RCA_REPORT.md](RCA_REPORT.md); it does not overwrite history
or claim a physical fix. Every numerical calculation is explicitly conditional
where its physical inputs are not measured.

## S — Situation

FACT: two different incidents are preserved:

| UTC incident | Captured evidence | Classification / limit |
| --- | --- | --- |
| [20261113T121506Z](../../../../artifacts/arq/20261113T121506Z-reverse-raw/bundle.json) |1 Tracker11-byte TX,1 localTxDone(flags8),1 Rudolph15000ms timeout;12 journal events;62 original hashes|PHYSICAL_RF_FAILURE_UNISOLATED; actual radiation and receiver input UNKNOWN |
| [20261113T123620Z](../../../../artifacts/arq/20261113T123620Z-reverse-raw/bundle.json) |8 journal events;74 original hashes; actualRX_READY precedesSEND by136922ns; Tracker stderr `received b''`|HOST_TRANSPORT_ERROR; RF INCONCLUSIVE; no confirmed TrackerTX |

FACT: B restored to [20261113T123837Z standby](../../../../artifacts/arq/20261113T123837Z-standby/standby-verified.json).
That historical restoration does not measure uninterrupted power during SEND.
Forward [raw-regression logs](../../../../artifacts/arq/20261113T080205Z-raw-regression/rf-monitor-receiver.stdout.log)
contain exact11-byte CRC-accepted payloads and packetRSSI around−109dBm; earlier
forward logs contain−107dBm. These observations support forward interoperability
at those moments, not TrackerTX/RudolphRX operation or a calibrated link margin.

FACT: prior software verification was221 tests **run**, one skipped (220 passed),
not221 passed plus a skip. The new fresh result is232 run,231 passed,1 skipped.
Physical ACK/NACK reception remains unverified; no new RF outcome is reported.

## T — Task and hard constraints

FACT: work was limited to source/evidence review, external documentation,
host-only diagnostic code/tests and new documentation. No subagents were used.
No production firmware, original evidence, fuses, BOOTSIZE, EEPROM or hardware
configuration was changed; no live port, RF trial, flash or recovery sequence was
used. New follow-up files leave the original reports intact.

FACT: investigation acceptance is six-part: separate incidents; map all recovered
errata to915/BW125/SF7; explain IF configuration and counter limitations; pass
offline diagnostics; specify an experiment separating at least two mechanisms;
name the missing measurement if causation cannot be proved.

## A — Decision logic and execution

FACT: track0 verified the original1553-file baseline, reread the complete15-section
RCA and original A/B/rollback artifacts, and independently checked15 SHA maps
(971 recorded entries, including overlaps). Zero recorded hashes mismatched.
An earlier12:06 acquisition's62 file hashes also pass; its declared-build mismatch
is an identity/readiness failure, not evidence that bytes changed. The old
generic analyzer calls that identity failure EVIDENCE_CORRUPTED; do not interpret
that label as a failed SHA check. [Hash results](errata-followup/archive-hashes.json).

FACT: tracks1/4 checked reported packetRSSI and operational snapshot provenance.
At915MHz/1m, free-space loss is31.676205dB. With **assumed actual**+2dBm and0dBi
antennas, idealRX is−29.676205dBm; reported−107/−109 differs by77.323795/79.323795dB.
Those are conditional calculations, not measured insertion loss. The configured
power is+2dBm; a generic+10–20dBm module example is not this experiment's power.

FACT: installed915MHz RSSI handling selects−157 and packet register1A, adds SNR
only if negative, and the MVP reads it before RX restart. An HF/LF offset mistake
would shift the report by7dB, not77dB. Manufacturer SF7/BW125 typical sensitivity
is−123dBm under specified test conditions: −107dBm is16dB above that typical
reference, so “zero margin/demodulation cliff” is **not established**. Actual noise,
sensitivity, output and antenna gain are UNKNOWN. Positive SNR does not calibrate
the RSSI or localize a failed connector. [Register/RSSI audit](ERRATA_REGISTERS.md),
[manufacturer references](ERRATA_SOURCES.md).

FACT: tracks2/3/5 recovered and visually read the complete Semtech-authored7-page
Rev1 errata, mapped6 entries, checked13 installed7.1.2 library copies (one set
of relevant source hashes), and byte-compared3 key files with upstream tag7.1.2.
The currently linked vendor download returnedHTML; recovered mirror equivalence
to the current vendor PDF remains UNKNOWN. [Errata audit](ERRATA_AUDIT.md).

FACT: erratum2.3's BW125 candidate is31.bit7=0 /2F=40 /30=00 with **zero** Frf
offset. Current activeRX31=C3 leaves AutomaticIFOn1; model candidate gives43.
This control is separate from OpMode01.bit3, which stays1. Erratum2.4 can omit
the first CRC-valid packet from the continuous-RX counter: packets0 cannot prove
no reception. B's packets0 was measured atREADY beforeSEND, not across its window.
A has no corresponding counter history. Neither limitation changes A's captured
negative RxDone observation or makes B an RF trial result.

FACT: the default-disable “fence” was resolved by source and issue388: historic
below62.5kHz failures led the maintainer to make mitigation optional. Source
inspection and the pinned-master diff found the same BW125 tuple, no applicable
new fix to import. No library upgrade or blanket workaround was applied.

FACT: tracks6/7 traced setup→mailbox parser→startTransmit and startReceive→IRQ
poll→readData/clear→timeout. PA7 is asserted in setup, not toggled by SEND.
Current source cannot establish an actual rail or PLL state. B contains23 active
RudolphRX snapshot bytes, **zero** Tracker activeTX bytes;35 address rows explicitly
retain missing values. [Exact table and modeled write order](ERRATA_REGISTERS.md).

FACT: track8 rechecked the exact [Tracker stderr](../../../../artifacts/arq/20261113T123620Z-reverse-raw/rf-monitor-receiver.stderr.log)
and transport parser. `b''` is zero returned bytes; `expected=None` skips value
comparison but still requires the requested length. This is not evidence of an
unexpected echo. The error propagates to monitor exit; it does not identify USB
removal, a reset, RF start, or the first failed LDS/LDCS instruction. Last-request
logging was added after B and cannot reconstruct it. Core saves/reset-clears
RSTFR before setup; B has no contemporaneous saved flags/PESIG/rail trace.
[Original UPDI analysis](UPDI_ANALYSIS.md), [DA primary source](ERRATA_SOURCES.md).

FACT: tracks9/10 group remaining mechanisms into6 falsifiable branches and prepare
bounded20/20 non-RF status acquisition, a2-packet receiver-only A/B, and2 reference
direction tests. Confirmation/rejection conditions, rollback, cost/time estimates,
and required missing observations are in [ERRATA_NEXT_EXPERIMENT.md](ERRATA_NEXT_EXPERIMENT.md).

FACT: new `tools/rca/errata_audit.py` reuses original offline parsing/integrity
checks. Tests first exposed its missing import; implementation then passed10
semantic tests. An additional real-driver test compiles the installed library
twice through the public fakeHAL. It checks receiverIF, unchangedPHY/OpMode bit3,
repeatRX, HF RSSI offset and W1C. These are model results, never RF measurements.

FACT: hard constraints prevented proposed fuse/BOD changes, frequency trim,
power increases, antenna swaps, Q1 bypass and production UART changes. Those
would mix hypotheses without measurements. Soft constraints favor existing
parsers, standard-library Python and existing compilers over a new framework.
No speculative protocol work or broad production refactor was needed.

## R — Result, proposed minimum correction and limits

FACT: **232 tests run =231 passed +1 skipped**, with0 failures/errors;11 new
follow-up tests passed. The full suite emitted2 pre-existing warnings from the
older renamed-main C++ harness; the new harness passed. No firmware builds were
needed or claimed. [Fresh full log](errata-followup/full-suite.log).

FACT: **1553/1553 original files match,0 changed**, and15/15 archived SHA maps
have0 mismatches across971 overlapping entries. [Before/after hashes](errata-followup/preservation.json).
There were0 flash/RF/live-port operations. New offline files are additional work,
not included in the “original files changed=0” claim.

FACT: **6/6 recovered errata mapped**:2 relevant receiver/diagnostic entries,
2 BW500 entries outside current conditions (one with a baseline restoration rule),
2 FSK entries outside current mode. **23** activeRX bytes were observed, **0**
activeTX bytes in B; missing IF2F/30 values remain UNKNOWN.

FACT: **6 grouped causal hypotheses →6 unresolved groups**; source concern has
HIGH confidence, its physical causation LOW confidence. Verdict remains
**HARDWARE_MEASUREMENT_REQUIRED**, not a fixed radio. The minimum missing evidence
is (1) synchronized MCUUPDI/adapterRX/MCUVDD/radioVDD during the failed transaction,
and (2) a compatible915MHz reference observation distinguishing Tracker output
from Rudolph reception. Actual defective component is UNKNOWN—needs these tests.

HYPOTHESIS: minimum candidate is **one receiver-only IF treatment** via the
existing7.1.2 compile option on isolated RudolphRX atBW125:31bit7→0,2F→40,30→00;
keep Tracker image and allPHY settings unchanged. This is a proposed experiment,
not an implemented physical repair. Initial A/B target is1 packet per arm; only
discriminating results justify preregistered replication up to6 total packets.

HYPOTHESIS: next-step estimates are0.5–1.5h for transport/scope setup,1–2h for
receiverA/B,0.5–1.5h for reference isolation and1–3h for deeper calibrated RF work.
Incremental hardware USD0 applies only to already available/borrowed equipment;
otherwise cost is **UNKNOWN—needs a local equipment quote**. Potential decision
rates and risk are tabulated in the experiment plan, not measured productivity.

UNKNOWN—needs synchronized rail/UPDI capture: whether a power/reset event caused
B. UNKNOWN—needs calibrated reference/RF measurement: whether Tracker radiated
correctly or Rudolph's front end is defective. A wrong component/fuse change
would add at least1 uncontrolled variable and destroy causal clarity; actual
repair cost and schedule impact are UNKNOWN—need a confirmed mechanism and quote.

FACT: **2 lessons** follow from this audit: retain pre-clear event history plus
software-valid counters rather than infer absence from counter0; and preserve
last-transaction/reset/rail evidence before recovery. Existing forward successes
and localTxDone each establish only their own observed boundaries.

## Reproduce offline

FACT: these commands consume archived evidence and have no hardware-control option:

```sh
uv run python tools/rca/errata_audit.py artifacts/arq/20261113T121506Z-reverse-raw
uv run python tools/rca/errata_audit.py artifacts/arq/20261113T123620Z-reverse-raw
uv run python -m unittest discover -s tests -p test_rca_errata_audit.py -v
```

FACT: C++ tests require the existing extracted host-toolchain environment documented
in [VERIFICATION.md](VERIFICATION.md). Exact fresh commands, deadlines and output
are retained in [follow-up verification](errata-followup/). Hardware stability,
3/3 reverseRF and H01–H04 remain unexecuted targets, not software-test conclusions.
