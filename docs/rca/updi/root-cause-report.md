# AVR128DA28 UPDI root-cause report

## 1. Conclusion

**Outcome B: the permitted software campaign is complete; no new causal software
fix is demonstrated.** Control-space communication works while data-space access
depends strongly on whether the CPU is held. An unheld CPU loses 19/60 tested
LDS responses across three bauds despite correct echoes; stopped-state and
programming-held data access work with both implementations. BORF persists after
an ACKed clear, but a retained scratch marker excludes counting those samples as
20 distinct GPR resets. The cause of this reset-domain state remains unproved.

H firmware and fuses were preserved. No erase, memory programming, BOD change,
speculative delay or ignored ACK workaround was applied. Physical measurements
in §15 are required to distinguish the surviving alternatives. The console
remains unaccepted; H/HELLO/HELLO WORLD gates have not passed. All investigation
and final review were performed personally, without delegation or outside models.

## 2. Architecture

PTY → upditerm worker → UPDI → pyserial → Linux cp210x → CP2102 → target.
SIB/LDCS use control space; LDS/STS use the system-domain access layer (ACC).
Receiver sends OCD messages through 0x0f18/0x0f19; GPR2/3 implement host input.

## 3. Timeline and rulings

- 2026-10-26: execution resumed on existing `stabilize-updi-console` branch.
- Ruling: retain the active branch/workspace: project files are untracked and a
  new worktree would omit them. Freeze an inventory instead of discarding state.
- Ruling: supplied plan references seven priors, requested relevance columns,
  commands, and self-review/checkpoint wording without supplying their originals.
  Use explicit reconstructed hypotheses and a full relevance table; do not claim
  the reconstructed numbers were supplied by the user.
- Freeze: 352 untracked files inventoried; nested diff, versions, build and 11
passing tests saved under `artifacts/updi/runs/deep-debug/`.
- First 3-second 38400 PTY trace: both STS ACKs succeed; STOPPED recurs after RUN.
  Existing trace capture stops on transport errors, not STOPPED; this trace is
  only a reproducer. Subsequent decomposition will issue RUN at most once.
- 01–09: independent running-state ACC probes intermittent; control-only probe
  succeeded and reported PESIG=3. Read-only REVID=0x17, SIB suffix A7.
- 10: accepted OCD key, STOPPED=1, RSTFR=2, GPR0=0, MCLKSTATUS=2.
- 11: BORF-only W1C while already stopped, ACK1=ACK2=40; 20 later RSTFR samples
  remain 2, STOPPED remains 1. No RUN or diagnostic reset in this experiment.
- 13: unused GPR1 00→5a→00, both ACK stages and both readbacks correct.
- 14: constructor decomposition accepts key and enables GPR2; RUN once changes
  STOPPED from 1 to 0, then the attempted RSTFR read times out. Failed link closed.
- 15: stopped BOD registers: CTRLA=14, CTRLB=02, monitor/interrupt/status=00.
- Instrumentation correction: first 20 `stopped-oracle-break` SIB records
  contain valid SIB bytes followed by a normal `readline()` timeout that the
  observer incorrectly raised. They are excluded from target failure counts.
  The observer now permits that terminator only during SIB, with a host check;
  the 38400 SIB block was repeated 20/20 under `oracle-sib-repeat/`.
- `stopped-upstream`: 540/540 completed trials across three bauds, including
  scratch restoration. Every read trial records raw precondition control values.
- Native official oracle after previous 115200 attachment: 20/20 SIB attempts,
  20/20 control attempts and 20/20 GPR0 attempts fail at initialization before
  the requested operation. Partial GPR1 attempts also retained. They are not
  LDS failures. Parent campaign was stopped between trials (OS handles closed)
  because repeating the same initialization failure cannot discriminate addresses.
- Ruling: use the oracle's existing `send_double_break()` *before* initialization
  in a new session to isolate the known cross-baud initialization difference.
  Do not retry transactions in the failed session. 16 then reads REVID correctly.
  This is diagnostic initialization, not a new upditerm fix or speculative delay.
  Cost if wrong: library comparisons would be confounded; raw initialization
  and state records permit checking equivalence.
- Official stopped matrix completed: 20/20 control, nine LDS addresses and
  scratch at each baud; SIB 20/20 per baud after excluding/repeating the invalid
  38400 observer block. 720 valid trials total.
- Default CTRLA=0 discriminator: 20/20 MCLKSTATUS reads and scratch per baud,
  120/120 total. Stopped-state success does not require inherited IBDLY=1.
- 17: official enter_progmode succeeds, ASI_SYS_STATUS=08, read-only ACC works;
  RSTFR=22 includes the diagnostic UPDI reset. Official leave_progmode completes.
- 18: after programming exit, a fresh oracle attachment has a corrupt echo
  `55 c3 08`→`50 c3 08`; session stops immediately. The stage label in this
  early harness version still names double-BREAK, but bytes identify the first
  init_datalink CTRLB instruction, after the BREAK routine returned.
- 19: one bounded strace capture succeeds, showing fragmented kernel reads
  aggregated correctly by pyserial; it does not reproduce or explain 18's fault.
- 20: KEY_OCD again yields a stopped CPU and readable low data addresses; no RUN.
- 21: GPR1=5a survives 20/20 post-clear samples while RSTFR remains 02; marker
  restored to 00. This falsifies the claim of 20 separate GPR-reset events.
- 22: one explicitly recorded diagnostic reset, not counted as spontaneous.
- 23: additional read-only clock/watchdog/CPUINT/fuse observations preserved.
- 24: UART flag disabled and UPDIDIS sent once before unheld-state matrix;
  no repeated RUN, erase or programming.
- `running-upstream`: 180 independent attachments; SIB/control each 20/20 per
  baud, MCLKSTATUS missing 9/20,5/20,5/20. Precondition KEY=0 and STOPPED=0.
- 25: bounded syscall trial 0 succeeds; trial 1 ends at the first missing LDS
  response. Full echo delivered by kernel; subsequent pselect times out.
- 26: existing normal UPDI.close sends UPDIDIS and closes the port.

The older generic `teardown` text in 17/24/26 refers to the harness's `finally`
block, which adds no protocol traffic. Explicit operations in those records do
send UPDIDIS, as shown by their values/raw TX; they do not retain debug keys.
The final harness wording makes that distinction explicit.

## 4. Evidence matrix

Evidence levels: E0 conjecture; E1 source/document support; E2 observed trace;
E3 controlled discriminator; E4 regression plus identical before/after result.
Archived 38400 trace: 271 successful STS and 269 STOPPED/RUN cycles (E2).
Fresh baseline HEX: `88c03596bab443c74015d8dfb04e1985f6d14940d227b84a4a943b3d5f47807e`.

| Experiment / hypothesis | Falsifier | Preconditions and single change | Observation / level | Self-review and next discriminator |
|---|---|---|---|---|
| first-failure: reproduce original symptom | Clean output, no stops | H, 38400, no optional reset | Recurring stops, no H / E2 | Existing PTY trace repeats RUN; use bounded decomposition next |
| 01,04,07: read-only ACC snapshot | Same reads always succeed | Existing target state; no KEY/reset | Missing data and one suspicious all-0x20 snapshot / E2 | Preserve suspicious bytes as possible corruption, not decoded register facts |
| 02,09: ASI independent of ACC | ASI fails with ACC | Separate fresh attachments; CS reads | Successful control sessions; initial PESIG=3 then another=4 / E2 | STATUSB/SYSRST are destructive reads; both initial values retained |
| 03,05: independent library/address | Failures only in 8-bit host layer | Installed oracle 24-bit | One ACC timeout; REVID=17 / E2 | Initialization differs; pin official oracle before inference |
| 06: independent low addresses | One address systematically unique | One LDS per new attachment | 3/6 successes; all echoes correct / E2 | Small sample only; compare stopped matrix |
| 08,05: revision cross-check | SIB suffix and REVID disagree | Read-only identity | Prefix AVR/P:2/D:1/-; REVID A7 / E2+E1 | Extended SIB format unresolved officially; use REVID for errata |
| 10: key and state | Still no ACC while STOPPED | KEY_OCD only; no reset/RUN | STOPPED and all low reads succeed / E3 | Key/state changed together; use one RUN from same state |
| 11: historical vs recurring BORF | BORF stays zero after W1C | Already stopped; BORF-only clear | BORF=2 on 20/20 later reads / E3 | Could still be asserted reset, not discrete counted reset edges |
| 13: verify write path | Readback/restore fails | Proven unused GPR1; XOR 5a | Two STS and readbacks correct / E3 | Generic writes work; do not assume RSTFR semantics from ACK alone |
| 14: RUN transition | RUN stays stable | Reliable stopped snapshot; one RUN | STOPPED clears; next ACC read fails / E3 | No repeated RUN; next poll control until restopped |
| 15: BOD retained interrupt | INTCTRL.VLMIE=1 with pending flag | Stopped CPU; reads only | VLMCTRL/INTCTRL/INTFLAGS all zero / E3 | Disfavors that mechanism at sample time; no threshold change |
| stopped-upstream: baud/address matrix | State matched failures | 20 independent trials per operation and baud | 540/540 pass / E3 | No independent power-on trials; CPU remains stopped |
| stopped-oracle: native initialization | Native constructor consistently reads CS | Change physical/link implementation | Cross-baud native initialization fails / E2 | End each failed session; isolate double-BREAK in new attachment |
| 16: explicit existing double-BREAK | First control read still fails | Same official oracle, existing BREAK method | REVID read succeeds / E3 | Do not attribute ACC symptom to constructor difference |

The 07 snapshot had raw 0x20 for all six unrelated LDS addresses before a control
timeout. It is **not reliable register evidence**. Nanosecond ranges show no
overlap among the numbered diagnostic serial sessions; no after-failure bytes
were decoded. The raw record remains available for transport investigation.

## 5. Hypotheses and confidence

These are reconstructed engineering judgments, not probabilities measured from
samples and not mutually exclusive. Updates require evidence IDs and falsifiers.

| Hypothesis | Initial confidence | Status / falsifier |
|---|---:|---|
| Reset/system-domain availability gates ACC | 70% | Open; reliable ACC through equivalent reset state weakens it |
| Host initialization/protocol defect | 35% | Open; independent implementation with equivalent state discriminates |
| Transport/turnaround/USB serial behavior | 35% | Open; state-matched multi-baud trials discriminate |
| Firmware startup or unexpected interrupt loop | 40% | Open; stopped-state flags and generated code discriminate |
| BOD-retained-register erratum causes interrupt/reset loop | 25% | Open; VLMCTRL/INTCTRL/INTFLAGS and vectors discriminate |
| Wrong register address or width | 15% | Open; cross-check official map and 16/24-bit library |
| Power/physical signal behavior | 50% | Unmeasured; software cannot establish waveform integrity |

Updates (judgment percentages, not measured probabilities):

| Evidence group | Reset/system | Host defect | Transport | Firmware/startup | BOD interrupt erratum | Address/width | Physical |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior | 70 | 35 | 35 | 40 | 25 | 15 | 50 |
| 01–09: independent-address failures, ASI success, PESIG=3, REVID | 80 | 25 | 30 | 35 | 25 | 8 | 60 |
| 10–15: stopped access, reversible STS, BORF clear observation, zero VLM interrupts | 90 | 15 | 25 | 20 | 5 | 5 | 75 |
| stopped-upstream: 540/540 complete trials at three bauds | 95 | 10 | 20 | 15 | 5 | 3 | 80 |
| official/default matrices and 17–22: stable held CPU, marker survives BORF | 95 | 8 | 25 | 15 | 3 | 2 | 80 |
| unheld matrix and syscall failure: 19/60 missing LDS with all ASI passing | 97 | 5 | 25 | 12 | 3 | 2 | 85 |

Transport remains viable because shared wiring/bridge can affect target reset or
power; a successful echo only proves the adapter's local return path. BORF
remaining set after W1C can mean a still-asserted or recurrent reset source;
software alone does not distinguish those without confirming flag semantics
against stopped target behavior and external measurements.
The small transport increase reflects the corrupt post-exit echo in 18. The
marker in 21 weakens a rapid series of complete system-register resets; it does
not clear an asserted brownout source or prove that firmware ran between reads.
The final row favors the state-dependent boundary; it does not assign an 85%
measured probability to a physical defect or justify a fuse change.

## 6. 80/20 analysis

First separate control-space success from ACC state, then reset recurrence from
host sequencing. Broad baud sweeps follow those discriminators.

The high-value discriminator is reliable ACC with the CPU stopped versus lost
ACC immediately after RUN, while the ASI clock is independent. Three baud rates
and both address widths reduce the value of further blind baud/delay changes.
The next useful evidence is a reset/power waveform, not a fourth speculative fix.

## 7. Causal tree

Missing data/ACK → echoed instruction? → control-space availability? → ACC
availability at independent addresses? → reset/stop state? → host initialization
or target state? → equivalent independent-library trial → transport/electrical.

- Echo mismatch: not observed in the completed stopped matrices.
- Missing first STS ACK: archived running/resetting state; no data value sent.
- Missing second ACK: not observed in completed stopped scratch trials.
- ACC timeout signature 3 with ASI available: target reports the access-layer
  boundary, not a Python stdin/thread failure.
- Stable stopped ACC: address map and both STS stages work in that state.
- Run then reset/stop: BORF plus no startup progress favors reset-domain
  availability. Retained VLM interrupt and unsafe consecutive CPU writes have
  no matching measured trigger.
- Remaining alternatives: actual VDD/BOD assertion, ground/back-power/connection
  effects, reset-domain silicon behavior, or an undocumented debug interaction.
  CP2102 echo alone cannot discriminate them.

## 8. Complete errata and clarification audit

Personally reviewed all 17 pages of DS80000882F, September 2024, downloaded and
hashed in `references/manifest.json`. All 27 issues below apply to A7 silicon
in the revision table. REVID=0x17 establishes A7 using DS40002183E §8.3.2;
the matching SIB suffix is corroboration, not the official revision decoder.
Applicability to silicon does not establish that an issue's trigger occurs.

The original requested column list was absent from the supplied plan. Columns
below cover identity, revision, mechanism, trigger, present evidence, relevance,
discriminator, workaround and disposition. “Inactive” is specific to this H image.

| F section / issue | Revisions | Trigger / mechanism | H image evidence | Relevance / discriminator | Workaround / disposition |
|---|---|---|---|---|---|
| 2.2.1 reserved fuse defaults | A6,A7,A8,AB | Older material, reserved defaults | No fuse writes; read raw values | Date code unknown; cannot explain ACC state transitions alone | None; preserve raw reserved bits |
| 2.2.2 flash endurance | All four | Excess write cycles | One verified H upload in earlier campaign; lifetime unknown | Does not explain stable ASI vs transient ACC | None; no extra flashing |
| 2.2.3 reset CRC | A6,A7,A8 | Reset CRC selection ignored on older material | Startup code reviewed; fuse read remains discriminator | A7 silicon applies; not a demonstrated reset generator | None; check SYSCFG0, do not enable CRC |
| 2.2.4 consecutive stores | All four | CPU store ≥64 then ST/STD <64, or SLPCTRL write | ELF .init3 uses OUT for GPR0; ISR uses OUT for SREG; no SLPCTRL store | Reviewed generated instructions, not confused with serial STS ACK | NOP/OUT; no matching unsafe instruction pair found |
| 2.3.1 LUT3 link | All four | CCL LUT3 LINK on 28/32 pins | No LUT configuration | Inactive; check compiled stores | EVSYS alternative; no change |
| 2.4.1 PLL status | All four | PLL RUNSTDBY without request | OSCHF selected; MCLKSTATUS=02 | A false PLLS cannot explain missing GPR reads | None; use OSCHFS evidence |
| 2.5.1 DAC drift | All four | DAC output disabled over life | No DAC use | Inactive for digital ACC | Enable/compensate if using DAC; no change |
| 2.6.1 EVSYS pin routes | All four | PB6/7 or PE4..7 events | H has no such routes | Inactive; 28-pin part lacks these exposed ports | None |
| 2.7.1 flash mapping protection | All four | FLMAP plus protected flash regions | GPR/RSTFR/SRAM reads do not use flash mapping | Inactive for tested addresses; never infer from programming | LPM/SPM for affected flash use; no change |
| 2.7.2 multi-page erase protection | All four | Multi-page erase crosses protected section | No erase commands issued | Inactive | None; erase prohibited |
| 2.7.3 EEPROM erase protection | All four | EEPROM erase despite EEWP | No EEPROM erase | Inactive | None; erase prohibited |
| 2.8.1 digital pin input disable | All four | Analog input selection disables digital input | Core initializes ADC; UPDI is a dedicated pin | No application USART/input path; inspect ADC register stores | None; no causal match |
| 2.9.1 BOD register retention | All four | Non-POR reset with UPDI enabled retains VLMCTRL/INTCTRL/INTFLAGS | 0x88/89/8a all 00 while stopped; BOD_VLM vector is default handler | Could dirty-reset via an enabled interrupt, but VLM disabled and interrupt disabled | None; trigger absent in measured stopped snapshot |
| 2.10.1 SPI host SS | All four | SPI route NONE without SSD | SPI unused | Inactive | Disable SS if using SPI; no change |
| 2.11.1 TCA1 routing | All four | Alternative routes 2/3 | Core configures timers; H has no output routing | Does not govern TCB2 timekeeping or ACC | Use routes 0/1 if needed |
| 2.11.2 TCA direction | All four | RESTART in NORMAL/FRQ | No application restart/event command | Inactive | None |
| 2.12.1 TCB byte access | All four | 8-bit PWM CNT/CCMP register access | H delay uses TCB2 periodic interrupt; ELF reads/writes paired bytes | Not 8-bit PWM; periodic delay problem cannot directly set BORF | Use 16-bit accesses; no change |
| 2.13.1 TCD async events | All four | Counter prescaler + async event | Core starts/configures TCD; no async input event configuration | Startup reviewed; required trigger absent | Sync prescaler/event if needed |
| 2.13.2 TCD alternative output enable | All four | Alternative WO pin routing | No H waveform output | Inactive | None |
| 2.13.3 TCD halt/restart | All four | Waiting for software restart with CMPA=0 or dual slope | No application halt/restart sequence | Inactive | Nonzero compare and supported mode if needed |
| 2.14.1 TWI output override | All four | TWI active and OUT latch high | TWI unused | Inactive | Clear OUT before enabling TWI |
| 2.14.2 SDA hold encoding | All four | TWI hold time selection | TWI unused | Inactive | Swap affected selections if needed |
| 2.14.3 TWI flush | All four | FLUSH can stick host state | No FLUSH | Inactive | Disable/re-enable TWI host if needed |
| 2.15.1 USART open drain | All four | TXD output direction overrides open drain | No target USART console | Inactive; CP2102 host UART is a different device | TXD input configuration if needed |
| 2.15.2 USART false start detection | All four | SFDEN in active receive | No target USART RX | Inactive | Disable SFDEN in active mode if needed |
| 2.15.3 USART sync recovery | All four | Auto-baud inconsistent synchronization | No target USART auto-baud | Inactive; UPDI has its own PHY | Toggle RXEN if using affected USART |
| 2.16.1 ZCD output routing | All four | ZCD1/2 route selection | No ZCD use | Inactive | EVSYS/CCL alternative if needed |
| §3 clarifications | Document-wide | Section contains introduction only | No active clarification entries in F | Confirmed page 11; E removed nine prior clarification topics | Use current DS40002183E; do not resurrect removed text |

“All four” means A6,A7,A8,AB. No issue in F asserts that every UPDI attachment
causes BOD resets. The BOD erratum concerns three retained monitor/interrupt
registers, not a prescription to disable the detector or change its threshold.

The downloaded current product-linked data sheet is **DS40002183E (2024)**.
Its §7.9.2.2 decodes 0x54 as LVL=2 (2.70 V typical), SAMPFREQ=1 (32 Hz),
ACTIVE=1 (continuous), SLEEP=0 (disabled). Sample frequency does not make active
mode sampled. BOD.CTRLA=0x14 and CTRLB=0x02 agree; supply voltage is unmeasured.

## 9. Source research

Official AVR DA ASI_SYS_STATUS §35.5.9 defines SYSRST bit 5 as clear-on-read.
Bits 7 and 1 are unnamed: record raw bits without importing other-family names.
Installed Microchip/DxCore physical layer discards echo; diagnostic observation
must preserve echo independently. It also differs in BREAK, DTR/RTS, CTRLA and
address width, so outcomes alone cannot identify an upditerm defect.

Source audit and cross-checks:

- DS40002183E §35.2 separates the bus-dependent ACC from asynchronous ASI.
  §35.5.2 decodes STATUSB.PESIG=3 as an ACC response timeout. STATUSB clears on
  read, like SYSRST; initial raw 03 is preserved before decoding.
- §35.3.6 and Figure 35-18 specify a 16-byte official SIB: family bytes 0–6,
  reserved byte 7, NVM bytes 8–10, OCD bytes 11–13, reserved byte 14, oscillator
  byte 15. The observed 32-byte extension is `    AVR P:2D:1-3M2 (A7.KV001.0)\0`.
  Only the documented prefix is treated as specified. The extension's `A7`
  agrees with read-only REVID=0x17; its complete meaning remains undocumented.
- §8.1/§9 map GPR0–3 at 0x1c–1f; §13 RSTFR=0x40; §11 MCLKSTATUS=0x63;
  SYSCFG.REVID=0x0f01; BOD=0x80, monitor/interrupt/status at 0x88–8b;
  FUSE.BODCFG=0x1051; SRAM starts at 0x4000. ELF .bss occupies 0x4000–4003;
  0x4000 is a safe read of the timer overflow counter, never a scratch write.
- Every generated H instruction was reviewed. GPR1 (0x1d) is not referenced
  directly, and every indirect data pointer is constrained to SRAM or a named
  peripheral region. GPR0 is startup reset storage; GPR2 is the UART flag;
  GPR3 is reserved host input. Scratch writes use only GPR1 and restore it.
- DxCore 1.6.2 `.init3` reads RSTFR, writes its set bits back to clear them,
  requests a protected software reset when that read was zero, then stores the
  flags in GPR0. This behavior exists in the actual ELF at 0xb0–0xc6. GPR0=0
  plus BORF=2 while stopped is consistent with stopping before startup records
  the new cause; neither value alone proves repeated startup execution.
- BOD_VLM uses default vector 2, which jumps through `__bad_interrupt` to reset
  vector 0 rather than issuing an ASI reset. Only TCB2 vector 30 is a live ISR.
  The zero BOD.INTCTRL and VLM level snapshots do not support that interrupt
  mechanism. WDRF/SWRF/EXTRF were not set in the stable stopped snapshots.
- Additional stopped readouts: MCLKCTRLA=00, MCLKCTRLB=00, OSCHFCTRLA=0c,
  WDT.CTRLA=00, WDT.STATUS=00, CPUINT.CTRLA=00, CPUINT.STATUS=00,
  FUSE.WDTCFG=00 and SYSCFG0=c9. These show no running interrupt or watchdog
  configuration in that snapshot. Public ASI_CRC_STATUS=0 corroborates no active
  reset CRC; no reset-CRC or interrupt workaround is supported by these readings.
- Upditerm UPDI construction sends two 300-baud zero BREAKs and CTRLB=8;
  SerialUPDI then sends KEY_OCD and STS GPR2=1, optionally issuing ASI reset.
  recv1 repeatedly RUNs after STOPPED. Diagnostics deliberately RUN once.
- Pinned official pymcuprog `e2fa9a7f0b9cc413367c51b9ccf19d93cdca6c8d`
  physical/link/application files were read in full. Native physical sends one
  zero at connection baud, defaults DTR/RTS through pyserial, and discards echo.
  Link initializes CTRLB=8 and CTRLA=0x80 (IBDLY), validates both STS ACKs, and
  supports 16- or 24-bit addresses. No broad application constructor, erase or
  flash programming is needed for low-level reads. An observation hook checks
  the discarded echo and ends the experiment on the first missing response.
- Installed DxCore's older pymcuprog differs: DTR/RTS false, CTRLA=6, three
  response timeout attempts, and an application constructor that selects address
  width after SIB. Early records 03 and 05 used that installed copy; later records
  explicitly pin the official checkout. They are not pooled as equivalent trials.
- Host and target GPR2/3 mappings agree. Target OCDM/OCDMS are 0x0f18/19 in
  upstream source and ELF. Microchip Data Visualizer's OCD messaging guide
  documents the side channel, handshaking and target-specific support; its
  examples do not certify these undocumented AVR DA addresses. This limitation
  cannot explain why ordinary GPR/RSTFR reads fail while CPU is running.
- Linux cp210x v6.17 source supports 38400/57600/115200, even parity and two stop
  bits; rate quantization keeps these requested standard rates. The reviewed
  driver has a CP2102 event-mode quirk but no evidence it applies to this adapter.
  Driver source does not verify the UART waveform, actual part identity, wiring,
  voltage, or latency on this system. CP2102/9 data sheet Rev 1.8 (01/2017) §7
  supports the requested frame format and range. PDF download via urllib was
  denied (403); the primary PDF was read through the web tool instead.

No upstream patch matching the demonstrated reset-dependent boundary was found
in the reviewed implementations. Do not replace the protocol or alter ACK rules
to make a reset-domain failure appear successful.

Raw control decoding (02/09 and state-matched matrix; unlisted bits retained):

| Register | Observed raw | Defined fields and side effects |
|---|---|---|
| STATUSA 00 | 30 | UPDIREV=3; low nibble unnamed |
| STATUSB 01 | 03, later 04, then 00 | PESIG=3 ACC timeout; 4 clock recovery error; 0 no error; clears on read |
| CTRLA 02 | 00 or 80 | IBDLY=0/1; PARD=DTD=RSD=0; GTVAL=0 (128 UPDI cycles); bit 6 unnamed |
| CTRLB 03 | 08 | CCDETDIS=1; NACKDIS=UPDIDIS=0 |
| ASI_KEY_STATUS 07 | 00 or 02 | Public CHIPER/NVMPROG/UROWWRITE all clear; bit 1 treated as upstream OCD convention, absent in DA public table |
| ASI_RESET_REQ 08 | 00 | No 0x59 host reset request held |
| ASI_CTRLA 09 | 03 | UPDICLKSEL=3 (4 MHz); higher bits unnamed |
| ASI_SYS_CTRLA 0a | 01 | CLKREQ=1, UROWDONE=0 |
| ASI_SYS_STATUS 0b | a2/20/00 while running; 82 while stopped | SYSRST bit 5 observed/re-read; ERASEFAIL/INSLEEP/NVMPROG/UROWPROG/LOCKSTATUS clear in these samples; unknown mask=raw&0x82 retained |
| ASI_CRC_STATUS 0c | 00 | CRC_STATUS=0, not enabled |
| 04 / 05 | 00 / 00→01 | Upstream OCD control/status conventions: STOPPED bit 0 and message-valid bit 4; not defined in DA public register summary |

KEY acceptance does not prove CPU execution. SYSRST's clear-on-read property
means a second set bit can reflect reset reassertion after the first read; an
unnamed bit is never promoted to a guessed cross-family status meaning.

## 10. Supported mechanism

Demonstrated boundary: target ACC availability varies with system/debug state;
ASI remains accessible independently of that bus path. STATUSB reports an ACC
timeout; the same low address works reliably while stopped and intermittently
while unheld. Both STS ACK stages work with readback/restoration while stopped.
The independent official 24-bit library also accesses SRAM/high registers while
held, and programming-mode entry/exit works without erase/programming.

This does not demonstrate a host software cause. Target BOD/reset availability
is favored by persistent BORF, transient SYSRST, unheld-state data loss and the
independent-library comparison. The retained BOD interrupt mechanism is not
supported by VLMCTRL/INTCTRL/INTFLAGS=0. A continuous reset condition, intermittent
power/reference effects, transport corruption or undocumented debug/silicon
behavior survive. In particular, GPR1 survives while BORF stays set: it is wrong
to equate each BORF sample with a fresh complete register reset.

The bounded failing syscall capture `25-running-1.strace` shows the kernel
returning the entire `55 00 63` echo, then a one-second pselect timeout with no
target response delivered to userspace. It excludes a response discarded by
Python in that trial. It cannot distinguish target silence from a lost UART/USB
receive response. No speculative USB configuration change follows from it.

## 11. Fix

No speculative fix. Existing fail-fast lifecycle changes remain intact.
No new public API, target compatibility-shim change or production protocol patch.
The diagnostic observer additionally validates ACK values: upditerm's existing
`expected` parameter formats errors but does not compare a received byte with
0x40. No wrong ACK occurred in the completed scratch matrices, so that source
finding is not promoted to the causal fix for the observed missing responses.
The observer's wrong-ACK check has a test observed failing before implementation
and passing afterward. No production fix attempts were made (zero of three).

## 12. File changes

Added `experiments/updi_rca/scripts/updi-freeze.py`, `updi-diagnose.py`, `updi-campaign.py`,
`updi-references.py`, `updi-finish-evidence.py`, `experiments/updi_rca/tests/test_updi_diagnose.py`, this
report, and `artifacts/updi/runs/deep-debug/` artifacts. The pinned reference checkout
under `.automation/research/pymcuprog` is sparse to the relevant package and
serialupdi files. Graphify was updated using AST extraction, with no model/API.
Existing production source and nested lifecycle diff are unchanged.

## 13. Verification numbers

Baseline: receiver 774 bytes, existing host regressions 11/11, H HEX unchanged.
Final host suite includes five diagnostic-glue checks (16 tests total). Detailed
final build/test/diff/hash/port and raw ACK/echo counts are in `verification.json`.

| State / operation | 38400 | 57600 | 115200 |
|---|---:|---:|---:|
| Stopped, upditerm SIB | 20/20 | 20/20 | 20/20 |
| Stopped, upditerm control snapshot | 20/20 | 20/20 | 20/20 |
| Stopped, upditerm LDS **each** 1c,1d,1e,1f,40,63 | 20/20 | 20/20 | 20/20 |
| Stopped, upditerm reversible GPR1 STS | 20/20 | 20/20 | 20/20 |
| Stopped, official oracle SIB (corrected observer) | 20/20 | 20/20 | 20/20 |
| Stopped, official oracle control snapshot | 20/20 | 20/20 | 20/20 |
| Stopped, official oracle LDS **each** low address plus 4000,0f01,1051 | 20/20 | 20/20 | 20/20 |
| Stopped, official oracle reversible GPR1 STS | 20/20 | 20/20 | 20/20 |
| Stopped, CTRLA=0 MCLKSTATUS LDS | 20/20 | 20/20 | 20/20 |
| Stopped, CTRLA=0 reversible GPR1 STS | 20/20 | 20/20 | 20/20 |
| Unheld, key=0, default CTRLA, SIB | 20/20 | 20/20 | 20/20 |
| Unheld, key=0, default CTRLA, control snapshot | 20/20 | 20/20 | 20/20 |
| Unheld, MCLKSTATUS **byte returned**, not integrity acceptance | 11/20 | 15/20 | 15/20 |

Stopped matrix totals: upditerm 540/540, official oracle 720/720 valid trials,
default-CTRLA discriminator 120/120. Every scratch trial includes two STS
transactions (test and restore), separate ACK1/ACK2 and readbacks. Zero echo,
missing data, wrong/missing first ACK or wrong/missing second ACK in those valid
stopped matrices. The 20 invalid SIB-observer records are retained and excluded;
the corrected repeat supplies the missing valid block.

All 19 unheld LDS failures are missing data after correct echo, with KEY=0 and
STOPPED=0 in each precondition snapshot. Of 41 returned bytes, 38 are 06
(OSCHFS+OSC32KS), two are 02, and one is suspicious 20. The last is not accepted
as a trustworthy clock snapshot. These byte-return rates are not corruption-free
acceptance rates. The early independent-library and post-exit failures remain
separate from state-matched matrices; 18 has one corrupt echo.

| Required gate | Final disposition |
|---|---|
| SIB / LDCS 20/20 | Transaction counts met, stopped and unheld; no-reset acceptance is not established |
| LDS 20/20 each safe address | Counts met while stopped; **fails unheld** (19/60 missing at 63) |
| Reversible STS 20/20 | Counts met while stopped; unheld write matrix omitted because reliable snapshot prerequisite fails |
| Terminal connect 20/20 | **Unperformed as an acceptance matrix**; symptom reproduces and target does not stay running |
| H 60/60 over ≥120 s | **Not passed; full duration unperformed** after repeated stop/reset symptom and zero H in reproducer |
| HELLO 120/120 over ≥120 s | **Unperformed**, preceding H gate fails |
| HELLO WORLD 600/600 over ≥600 s | **Unperformed**, preceding gates fail |

No firmware expansion or reflash was made. A stopped-state matrix alone cannot
satisfy the terminal gates, and intentional diagnostic resets are excluded from
any no-reset acceptance claim.

Final verification: 16/16 host tests and both sender/receiver builds pass;
receiver remains 774 bytes. H HEX matches the frozen SHA256, original nested
diff is byte-identical, both git diff checks and new-file whitespace checks pass,
no diagnostic serial sessions overlap, and fuser confirms no process owns the
port. AST Graphify update succeeds; its existing AVR-header parsing/empty-symbol
limitations remain, and new Markdown semantics are not model-extracted. The graph
is a navigation aid; the recorded sources and raw evidence are authoritative.

## 14. Risks

Serial attachment sends BREAK and changes UPDI control state. KEY_OCD arms stop
on reset. SYSRST reads consume evidence. Preserve RSTFR/GPR0 before flag clears;
startup clears RSTFR and may request software reset if it reads no reset flags.

## 15. Software limitations and physical discriminators

The permissible software campaign cannot measure voltage, reset edges, line
levels, reference-ground offset, decoupling, cable impedance or back-powering.
Repeated serial opens are not independent power cycles. An asserted BOR source
can keep BORF set without providing software a count of distinct reset events.
No fuse, BOD threshold, firmware instrumentation or instruction-stepping change
is justified to force a different outcome. Undocumented OCD behavior remains a
surviving software/silicon alternative, not an established electrical diagnosis.

Exact next measurements, **not performed here**:

1. Measure DC VDD at the MCU's supply pin relative to its local GND, and the
   MCU-to-CP2102 ground difference. Record actual supply source, regulator,
   decoupling locations, board identity and the TX/RX/UPDI resistor topology.
   Compare against the active 2.70 V typical BOD threshold and the full E data
   sheet's tolerance/operating-voltage limits, not a nominal USB supply label.
2. Capture MCU VDD, RESET, UPDI node and adapter TX simultaneously during one
   attachment and one RUN. Trigger on VDD droop and separately on RESET/UPDI
   activity; include ≥100 ms before and after the event. Use low-capacitance
   probes and enough bandwidth/sample rate to resolve 115200-baud bit edges
   (at least 20 MS/s for the digital channels). Timestamp against the logged RUN.
3. Determine whether VDD crosses the BOD trip/release region while BORF reappears,
   whether RESET is externally asserted, and whether local VDD stays stable while
   UPDI is driven outside its valid input range or contends with TX. Probe both
   sides of the actual series/isolation element. These distinguish supply/reset
   behavior from signal turnaround and ground-reference faults.
4. If supply, RESET and levels are stable through a repeatable failure, decode
   the echoed instruction and expected target turnaround on the UPDI node.
   Determine whether the target emits a NACK/ACK/data that the CP2102 fails to
   deliver. A target-emitted response lost before host read points toward the
   bridge/receive path; no response with stable electrical conditions calls for
   a silicon/debug-state investigation with Microchip support or a known-good
   debug probe. No support message was sent during this task.

Interpretations require calibrated measurements. Successful programming and SIB
never establish electrical integrity, and a local TX echo does not prove that
the target recognized that instruction.

## 16. Source table

Access date 2026-10-26. Reference downloads and hashes are in `references/manifest.json`.

| Source | Revision / section | Supported claim |
|---|---|---|
| [Microchip errata](https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/Errata/AVR128DA-28-32-48-64-SilConErrataClarif-DS80000882.pdf) | DS80000882F / §2.9.1 | Retained BOD registers are VLMCTRL, INTCTRL and INTFLAGS |
| [AVR DA system status](https://onlinedocs.microchip.com/oxy/GUID-3EE676DF-490E-41BC-98F0-5774B35DC989-en-US-25/GUID-EA5FFD12-2C97-428B-9560-7D0E3D6BD964.html) | §35.5.9 | SYSRST bit 5 clears on read |
| [upditerm](https://github.com/streef/upditerm) | f2222b02ceeff7668caab0f240d2e13298116356 + frozen nested diff | Current protocol and lifecycle |
| [AVR DA product-linked PDF](https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/AVR128DA28-32-48-64-Data-Sheet-DS40002183.pdf) | DS40002183E, 2024; §§7.9.2.2,8.1,8.3,9,11,13,18,35 | BOD decode, REVID, memory/register map, reset semantics, ASI/ACC and error signatures |
| [Official pymcuprog](https://github.com/microchip-pic-avr-tools/pymcuprog/tree/e2fa9a7f0b9cc413367c51b9ccf19d93cdca6c8d/pymcuprog/serialupdi) | e2fa9a7f0b9cc413367c51b9ccf19d93cdca6c8d; physical/link/application/constants | Independent transport, addressing and programming-mode entry/exit |
| [DxCore](https://github.com/SpenceKonde/DxCore/tree/c9e8ddfd79daee5bee877a2b223c2f83d484606a/megaavr/cores/dxcore) | 1.6.2 tag commit c9e8ddfd79daee5bee877a2b223c2f83d484606a; exact installed local file hashes in verification.json | Compiled startup, reset flag storage, timer/interrupt behavior; no claim local files equal remote tag |
| [OCD messaging](https://onlinedocs.microchip.com/oxy/GUID-F897CF19-8EAC-457A-BE11-86BDAC9B59CF-en-US-10/GUID-01647562-39B4-4115-9A61-E011680A6D21.html) | Online edition en-US-10 §2.1.6.4 | Message side-channel and target-dependent support |
| [Blocking OCD example](https://onlinedocs.microchip.com/oxy/GUID-F897CF19-8EAC-457A-BE11-86BDAC9B59CF-en-US-10/GUID-A2AA4352-2351-435F-AA22-E33A1EE68FCA.html) | §2.1.6.4.2 | ATtiny817 example uses reserved offsets 18/19 and tests bit 0; not an AVR DA register specification |
| [CP2102/9](https://www.silabs.com/documents/public/data-sheets/CP2102-9.pdf) | Rev 1.8, January 2017, §7 | UART formats, supported rates, buffering; urllib 403 retained in manifest |
| [Linux cp210x](https://github.com/torvalds/linux/blob/e5f0a698b34ed76002dc5cff3804a61c80233a7a/drivers/usb/serial/cp210x.c) | v6.17 commit e5f0a698b34ed76002dc5cff3804a61c80233a7a | Baud quantization, parity/stop control, CP2102 event-mode quirk; not an attestation of the running kernel binary |

Official 16-byte [SIB figure](https://onlinedocs.microchip.com/oxy/GUID-3EE676DF-490E-41BC-98F0-5774B35DC989-en-US-25/GUID-DCCF1B12-3521-4083-B8E0-54D7F7D35697-high.pdf)
specifies no silicon revision field. Therefore the complete 32-byte extension is
explicitly unresolved; revision applicability comes from REVID, not folklore.

## 17. Reproduction commands

Run from `experiments/updi_rca/`. `scripts/updi-freeze.py` asserts the expected H hash and
records a host-only baseline. `scripts/updi-session.py 38400 3 H <prefix> --trace`
captures the terminal. Do not re-run the original freeze over existing evidence.

The pinned oracle is already available under `.automation/research/pymcuprog`.
On another machine, clone Microchip's repository at commit
`e2fa9a7f0b9cc413367c51b9ccf19d93cdca6c8d`, then use sparse-checkout for
`pymcuprog/serialupdi`. The harness imports those actual physical/link/application
classes and requires the existing pyserial environment. It rejects reused output
paths. Example commands (new evidence prefixes required):

```sh
uv run python scripts/updi-diagnose.py control /tmp/updi-control-new.json \
  --hypothesis 'ASI remains accessible' --falsifier 'control read fails' \
  --variable 'control-space only'
uv run python scripts/updi-diagnose.py key-snapshot /tmp/updi-key-new.json \
  --hypothesis 'accepted key allows stopped snapshot' \
  --falsifier 'ACC fails while stopped' --variable 'OCD key without RUN'
uv run python scripts/updi-campaign.py /tmp/updi-stopped-new
uv run python scripts/updi-campaign.py /tmp/updi-oracle-new \
  --backend oracle24 --double-break
uv run pytest
pio run
```

Campaigns do not power-cycle the target or guarantee their preconditions. Inspect
each record's KEY/STOPPED/CTRLA fields before comparing results. Do not run a
scratch campaign unless the matching H source/ELF still proves GPR1 unused.
After a write failure, stop and inspect the recorded original GPR1 before any
restoration in a new, healthy connection. Never resume the failed session.
`progmode` uses only official entry/read/exit; `bor-clear`/`bor-marker` require an
already stopped CPU. They consume diagnostic state and are not acceptance tests.

## 18. Diffs and inventory

`artifacts/updi/runs/deep-debug/nested-diff.txt` contains the complete pre-existing
nested diff; `untracked-inventory.json` accounts for files absent from git diff.
The project tracked diff is empty because the project files are untracked.
`final-untracked-inventory.json` adds final hashes; `investigation-additions.diff`
contains every authored script, test and report addition. `verification.json`
pins source hashes and checks the unchanged original nested diff and H HEX.

Final review: self-review by the author, as required by the single-agent scope.
Checked every plan constraint and all 18 report sections, address ownership,
write/restore paths, first-failure termination, actual ACK bytes, matrix state
equivalence, no overlapping serial sessions, and explicitly unperformed gates.
The SIB observer mistake was corrected, excluded and repeated; the corrupt echo
and suspicious raw 0x20 clock byte are retained rather than counted as clean
acceptance. No production correction is justified by this evidence. No deferred
code finding is presented as a solved target problem.
