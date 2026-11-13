# Power and reset evidence

OBSERVED design source: [Tracker SSOT](../../../ssot/TRACKER_SSOT.md) and local
`/home/parinya/university/iwing-tracker/device-lora/pcb/2025-02-16/Schematic_LoRa-Tracker-RFM_2025-02-16.pdf`.
Schematic text was extracted for component/net checks; existing SSOT supplies
the connectivity interpretation. This is design evidence, not measured wiring.

JP1 battery → U7 TPS7A0233DBV →3V3 powers MCU U6. Q1 P-channel switch supplies
3V3-LORA to radio U4; PA7 LOW enables Q1. H1 supplies a downstream3V3 node;
feeding H1 bypasses U7. Actual source voltage/current path during SEND is UNKNOWN.
Schematic already includes radio C11 100µF and C8 100nF; blindly adding another
100nF/10µF is not an evidence-based repair. Ground return impedance is unmeasured.
[TI TPS7A02](https://www.ti.com/product/TPS7A02) rates the LDO200mA, but that rating
cannot be applied to an unknown upstream path or used to prove this board sagged.

[HopeRF module specifications](https://www.hoperf.com/uploads/RFM95W-V2.0_1695351437.pdf)
and [Semtech SX1276 Rev7](https://cdn.sparkfun.com/assets/7/7/3/2/2/SX1276_Datasheet.pdf)
distinguish RX, standby, sleep and TX load. Quoted high-power TX currents are not
measurements of this2dBm trial. Supply current, radio-enable inrush, rail minima,
ripple and ground bounce are UNKNOWN. Radio power was already enabled during
startup; SEND does not toggle PA7 in the inspected implementation. Thus cold
radio-enable inrush and later PA startup are different proposed mechanisms.

## DA-specific fuse/reset interpretation

[Microchip DS40002183C §§7.8,13.5](https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/AVR128DA28-32-48-64-Data-Sheet-40002183C.pdf)
is authoritative, not a DB/DU register map. Captured fuses decode as follows:

| Offset | Value | Meaning relevant to RCA |
| --- | --- | --- |
|00 WDTCFG|00|WDT window/period0 at reset |
|01 BODCFG|00|Active/sleep BOD disabled at reset; LVL0 nominal1.9V if enabled; runtime state unmeasured |
|02 OSCCFG|F0|CLKSEL low nibble0: internal HF oscillator; preserve reserved upper bits |
|05 SYSCFG0|D2|CRCSRC3, CRCSEL0, RSTPINCFG0 (bits3:2), EESAVE0; preserve reserved bits4/1; no UPDI-disable fuse implied |
|06 SYSCFG1|F8|SUT low3 bits0; preserve reserved bits |
|07/08 CODESIZE/BOOTSIZE|00/00|Captured section fuse values; do not change |

RSTFR bits0..5: PORF power-on, BORF brownout, EXTRF external, WDRF watchdog,
SWRF software, UPDIRF UPDI reset. Write-one clears flags. POR clears other flags;
BOR clears all except PORF/BORF. The core already captures/clears startup flags
(see firmware analysis). No fresh SEND-time reset observation exists. BODCFG00
also means absence of a new BORF cannot establish supply stability. Signature
and unlocked lock key prove identity/access state, not electrical health.

## Smallest discriminating measurements — future authorization only

| Signal | Probe point / trigger | Distinguishing observation |
| --- | --- | --- |
| MCU VDD | U6 local decoupling vs local ground; pretrigger before SEND | Correlated rail collapse supports supply mechanism; stable captured rail rejects that measured collapse only |
|3V3-LORA| U4 pin13/C8, Q1 input/output | Separates upstream sag from switch/contact drop |
|UPDI| MCU pin and adapter RX, decode38400 8E2 | Target reply vs adapter reception distinguishes electrical transport boundaries |
|Reset history| Capture startup generation/core-saved flags before any programmer reset | Establishes reset occurrence; fresh flag alone may still need rail correlation |

Design supply target is3.3V; AVR allowed1.8–5.5V and SX1276 allowed1.8–3.7V
must be checked against applicable operating/clock/threshold tables. A3.0V
scope trigger is a proposed observation threshold, not proof of a BOD trip.
No rail, continuity, current or oscilloscope measurement was made in this RCA.
