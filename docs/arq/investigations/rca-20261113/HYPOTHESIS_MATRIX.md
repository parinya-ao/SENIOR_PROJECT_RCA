# Hypothesis matrix

Confidence refers to the causal claim, not how important it is to test.
HIGH requires direct mechanism evidence/discriminating reproduction; MEDIUM
requires source-consistent specific evidence with unresolved alternatives; LOW
means indirect clue only; INSUFFICIENT_EVIDENCE means no discriminating evidence.
No probabilities are assigned. No physical cause earns HIGH here.

| ID | Hypothesis | Supporting evidence | Contradicting/limiting evidence | Missing evidence | Confidence | Next discriminating test |
| --- | --- | --- | --- | --- | --- | --- |
|H1|Unexpected echo/framing|UPDI empty response|Not the echo-mismatch branch; no PESIG|Raw request/reply/PESIG|INSUFFICIENT_EVIDENCE|Analog UPDI + decoded first failed request|
|H2|Host lifecycle defect|Dead-peer cleanup aborted live-peer X|Does not cause original read failure; later restore succeeded|First failing request/thread|HIGH for cleanup only|Offline peer-exit regression, already passing|
|H3|Adapter/electrical transport|Reply missing after SEND|Programming/startup worked|Levels, edges, adapter IC, wire integrity|INSUFFICIENT_EVIDENCE|Target UPDI vs adapter RX capture|
|H4|Parser/logging contention|Failure follows command issue|Fixed bounds/nonblocking logger; fake tests pass|MCU command progress trace|LOW|Request delivery and target log generation capture|
|H5|MCU reset during SEND|Compatible with silence|No fresh BOOT/reset generation captured|Fresh saved flags/uptime before recovery|INSUFFICIENT_EVIDENCE|Core-aware reset capture with supply trace|
|H6|TX load transient|TX can change supply demand|TX initiation unknown; BOD disabled at fuse reset|Actual feed and rail waveform|INSUFFICIENT_EVIDENCE|U6 VDD + U4 pin13 synchronized trace|
|H7|Tracker TX not initiated|B lacks TX_START|Missing logs cannot prove nonexecution|Complete mailbox and TX evidence|INSUFFICIENT_EVIDENCE|Trace newline delivery/command processing|
|H8|Internal TX but ineffective RF|A has TxDone/no RX|No external RF measurement|RF at ANT/reference receiver|INSUFFICIENT_EVIDENCE|One separately authorized reference-endpoint trial|
|H9|Rudolph detects no valid frame|A RX timeout|Header/packet history missing|Active counters through full trial|LOW|Reference source + bounded receiver counters|
|H10|PHY/config incompatibility|AutomaticIFOn retained; errata disabled|Common standby PHY matches; bit3 retention alone not causal|Operational Tracker TX, external comparison|MEDIUM for configuration concern; LOW for RF cause|Single errata-switch comparison after transport gate|
|H11|Lost IRQ/FIFO event|Destructive clears exist in driver|IRQ polled; B pre-clear code; no observed packet counter increase|Same-window silicon counters/IRQ history|INSUFFICIENT_EVIDENCE|Record counters/flags before every destructive transition|
|H12|Antenna/front-end defect|A negative RF result|Operator visual checks passed; no defective endpoint isolated|Continuity/impedance/RF output|INSUFFICIENT_EVIDENCE|Power-off measured continuity; reference RF endpoint|
|H13|Independent defects|A negative RF vs B transport failure are distinct|Two symptoms do not prove two physical defects|Separate discriminating observations|LOW|Isolate UPDI first, RF second|
|H14|Evidence insufficient for physical mechanism|Missing first request, rail/RF measurements|Does not exclude any mechanism|Measurements above|HIGH|Acquire smallest missing boundary evidence|
