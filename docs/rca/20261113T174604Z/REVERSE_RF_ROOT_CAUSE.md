# Reverse-RF root cause status

Incident A remains a valid negative reverse-RF observation: Tracker reported local TxDone, Rudolph timed out without RxDone in the 15 s window. It does not identify which endpoint failed. Source/manifests show correct static board map assignment for the reverse test: Tracker receiver-board pin profile is compiled into the image that transmits; Gateway sender-board profile is compiled into the image that receives. This rejects a static board-role pin-map swap, not physical wiring, RF output, power, runtime register, timing or receiver-event hypotheses.

No new RF trial was run during this SSOT/mailbox review. No RF root cause is confirmed.
