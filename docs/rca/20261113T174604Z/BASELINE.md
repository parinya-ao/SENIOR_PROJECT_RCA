# Baseline

- Active source: `SENIOR_PROJECT_RCA`; the separately supplied `iwing-tracker/gateway-lora/loraboard` is a legacy component, not the ARQ V1 source.
- HEAD: `1e2dd303e2ca63b93826df030e8fd116683d7284`; branch `fix/receiver-rfm-rev1-pins`; dirty entries at RCA start are recorded in `original_hashes.json`.
- Physical Tracker: receiver board port path `/dev/serial/by-path/pci-0000:00:14.0-usb-0:1:1.0-port0`, MCU signature `1e970a`, serial `42032240221092150158013400000000`. Identity was read over the Monitor UPDI session in the Gate 1 bundle.
- Physical Rudolph Gateway: gateway port path `/dev/serial/by-path/pci-0000:00:14.0-usb-0:4:1.0-port0`; historical MCU serial `42032240221023150129012600000000`. No live Gateway read was made during Gate 1.
- Gate 1 live: two normal startup BREAKs; 8,114 SYNCH operations; one STATUS request; no firmware output; zero low-level serial exceptions before the deadline; verdict `GATE1_FAIL / STATUS_RESPONSE_TIMEOUT`. Exact evidence is in `artifacts/arq/gate1-updi/20261113T153146Z/`.
- Original RF Incident A: one Tracker local TxDone; Rudolph no RxDone in its 15 s window; physical endpoint not isolated.
- Original Incident B: UPDI response timeout before any confirmed RF start; RF result inconclusive.
