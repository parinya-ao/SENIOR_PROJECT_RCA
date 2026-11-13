# Exact register comparison and real-driver write order

FACT: source snapshot order is `src/reverse_raw/main.cpp:18–25`;35 distinct addresses below combine23 captured snapshot registers and12 explicitly missing diagnostic registers. Addresses/fields were checked against Rev7 pp108–116 and installed definitions. UNKNOWN cells are not default values.

FACT: this is **Tracker standby versus Rudolph activeRX**, not an activeTX comparison. Tracker immediately-before-TX, activeTX and post-TxDone snapshots are all NOT CAPTURED in Incident B. Standby matching cannot establish operationalTX compatibility.

| Address | Register | Tracker standby FACT | Rudolph activeRX FACT | Tracker activeTX | Interpretation |
| --- | --- | --- | --- | --- | --- |
|01|RegOpMode|89|8D|NOT CAPTURED|LoRa; bit3 retained; standby1 versus continuousRX5|
|06|FrfMSB|E4|E4|NOT CAPTURED|E4C000 nominal915MHz with32MHz reference|
|07|FrfMID|C0|C0|NOT CAPTURED|Carrier byte|
|08|FrfLSB|00|00|NOT CAPTURED|Carrier byte|
|09|PaConfig|F0|F0|NOT CAPTURED|F0 selects PA_BOOST, configured+2dBm|
|0B|Ocp|UNKNOWN|UNKNOWN|NOT CAPTURED|Not captured; model initialization writes23, not a measurement|
|0C|Lna|23|23|NOT CAPTURED|23 gain code1/HFboost11; AGC enabled separately|
|11|IrqFlagsMask|00|00|NOT CAPTURED|00 no masked IRQ bits|
|12|IrqFlags|UNKNOWN|UNKNOWN|NOT CAPTURED|Separate RX_READY sample00; NOT part of23-byte snapshot|
|14|HeaderCountMSB|UNKNOWN|UNKNOWN|NOT CAPTURED|Separate combined READY header count0 beforeSEND only|
|15|HeaderCountLSB|UNKNOWN|UNKNOWN|NOT CAPTURED|Counter reset/lifetime matters|
|16|PacketCountMSB|UNKNOWN|UNKNOWN|NOT CAPTURED|Separate READY packet count0; erratum2.4 applies|
|17|PacketCountLSB|UNKNOWN|UNKNOWN|NOT CAPTURED|Zero cannot exclude first continuous-RX packet|
|18|ModemStat|UNKNOWN|UNKNOWN|NOT CAPTURED|Separate RX_READY stat04 = RXongoing, not packet acceptance|
|1C|HopChannel|UNKNOWN|UNKNOWN|NOT CAPTURED|Separate RX_READY hop00 before any packet; not CRC success|
|1D|ModemConfig1|72|72|NOT CAPTURED|72 = BW125 / CR4/5 / explicit|
|1E|ModemConfig2|74|74|NOT CAPTURED|74 = SF7 / CRC setting enabled|
|20|PreambleMSB|00|00|NOT CAPTURED|0008 =8 programmed symbols|
|21|PreambleLSB|08|08|NOT CAPTURED|Preamble low byte|
|24|HopPeriod|00|00|NOT CAPTURED|00 FHSS disabled|
|26|ModemConfig3|04|04|NOT CAPTURED|04 = AGC enabled / LDRO disabled|
|2F|IfFreq2|UNKNOWN|UNKNOWN|NOT CAPTURED|Candidate40; physical baselineUNKNOWN|
|30|IfFreq1|UNKNOWN|UNKNOWN|NOT CAPTURED|Candidate00; physical baselineUNKNOWN|
|31|DetectOptimize|C3|C3|NOT CAPTURED|C3 = AutomaticIFOn1 + SF7–12 optimize3 / reserved bits retained|
|33|InvertIQ|27|27|NOT CAPTURED|27 normalRX, library normalTX bit0=1|
|36|HighBwOptimize1|UNKNOWN|UNKNOWN|NOT CAPTURED|BW125 requires baseline03; physical readbackUNKNOWN|
|37|DetectionThreshold|0A|0A|NOT CAPTURED|0A SF7–12 threshold|
|39|SyncWord|12|12|NOT CAPTURED|12 private sync|
|3A|HighBwOptimize2|UNKNOWN|UNKNOWN|NOT CAPTURED|No BW500 optimization in candidate; physical readbackUNKNOWN|
|3B|InvertIQ2|1D|1D|NOT CAPTURED|1D normal companion setting|
|40|DioMapping1|00|00|NOT CAPTURED|00 DIO0=RxDone inRX; actualTX mapping UNKNOWN|
|41|DioMapping2|00|00|NOT CAPTURED|00 retained mapping|
|42|RegVersion|12|12|NOT CAPTURED|12 identifies V1b per recovered note|
|4B|Tcxo|09|09|NOT CAPTURED|09 bit4=0 crystal path; does not measure actual oscillator|
|4D|PaDac|84|84|NOT CAPTURED|84 normal PA DAC setting|

FACT: of23 snapshot bytes,22 match across these two differently staged observations;01 differs89→8D as expected. There are0 captured Tracker activeTX bytes to compare. Separate READY fields must not be silently merged into an earlier snapshot. RegRxNbBytes13 and FIFO-current10 were not in this snapshot either.

## Source call order

FACT: `SX1276.cpp:8–38`: commonSX127x begin → setBandwidth125 → setFrequency915 → setSpreadingFactor7 → setCodingRate5 → setOutputPower2 → setGain0 → setCRC(true). Common begin initializes module, finds/resets chip, entersLoRa, standby, sync/current-limit/preamble. Project then explicitly selectsPA_BOOST, explicitHeader, CRC, normalIQ, standby. `src/reverse_raw/main.cpp:84–94`.

FACT: `SX127x.cpp:392–450`: standby → DIO IRQ mapping → optionalerrataFix(true) → clearIRQ(FF) → FIFO base/readpointer → RXContinuous. Errata calls standby → carrier write →31.bit7 →2F →30. SPIsetRegValue skips no-op writes; the carrierLSB write is forced.

FACT: below is chronological modeled SPI output from the installed7.1.2 driver using the existing public fakeHAL. Labels group publiccalls; `begin` subcall order is defined above. This is a partial reset-register model, **not physicalSPI evidence**, and does not validate PLL/analog/IRQ-event generation. Model seeds C3/20/00/03/65 and relevant reserved bits; actual IF/test-register baselines remain UNKNOWN.

### FACT: option0, 25 modeled register writes

| Stage | Ordered address=value writes |
| --- | --- |
|begin|01=08, 01=88, 01=89, 39=12, 0B=23, 21=08, 1D=70, 06=E4, 07=C0, 08=00, 1E=70, 37=0A, 1D=72, 09=80, 09=F0, 26=04, 0C=23, 1E=74|
|explicit|22=FF|
|RX|12=FF, 01=8D|
|RX_again|01=89, 12=FF, 01=8D|
|IRQ_read_clear|12=40|

### FACT: option1, 29 modeled register writes

| Stage | Ordered address=value writes |
| --- | --- |
|begin|01=08, 01=88, 01=89, 39=12, 0B=23, 21=08, 1D=70, 06=E4, 07=C0, 08=00, 1E=70, 37=0A, 1D=72, 09=80, 09=F0, 26=04, 0C=23, 1E=74|
|explicit|22=FF|
|RX|08=00, 31=43, 2F=40, 12=FF, 01=8D|
|RX_again|01=89, 08=00, 12=FF, 01=8D|
|IRQ_read_clear|12=40|

FACT: B adds31=43 and2F=40 on firstRX plus an unchanged forced08=00 write perRX. The30 setter is executed but the seeded00 readback needs no bus write. RepeatedRX has no500kHz36/3A writes. Both options retain8D/E4C000/72/74/04/12/27/1D, PA F0/84 and LNA23 in the model. Repeated startReceive clears pending IRQs; production rejects repeatedRX commands before that call.

FACT: modeled packet RSSI raw50 and SNR raw32 produce−107dBm/+8dB at915MHz. Installed `SX1278.cpp:477–482` selects HF offset−157 based on frequency; `SX127x::getRSSI` uses packet1A and adds SNR only when negative. CurrentMVP reads metrics before restartingRX (`src/mvp/main.cpp:179–187`), so a current-channel noise read is not what this source requests. UNKNOWN: calibration, historical rawRSSI register, actual RF output and environmental noise.
