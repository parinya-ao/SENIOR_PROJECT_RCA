# LoRa Chat Firmware Requirements

The Python console uses the existing readback-verified UPDI monitors and the
production ACK/NACK bench runner. It does not write firmware, generate protocol
events, or send arbitrary bytes through a SerialUPDI programmer.

## Installed behavior

- Gateway command S calls the existing StartRadioTransaction() and transmits
  LORA_HELLO_PAYLOAD with the configured sequence and campaign.
- The host command channel accepts single-byte diagnostic commands. It has no
  length-delimited message injection command.
- The shared transport allows at most 249 application bytes per DATA packet, but
  the installed Tracker application accepts only the configured 11-byte
  hello world payload.
- Tracker's application callback validates the payload and the transport sends
  ACK or NACK. The Tracker application does not start an application DATA reply.
- Gateway's installed application is the DATA sender and accepts protocol
  responses; it has no Tracker-originated application DATA receive-and-ACK flow.
- The profile currently has null radio and antenna inventory. The console therefore
  permits read-only monitoring but blocks RF transmission even when the explicit
  bench authorization option is supplied.

## Firmware work required for arbitrary round trips

1. Add a supported Gateway host command that accepts a bounded byte length and
   payload, validates it, and submits it through the existing reliable transport.
   The command must not repurpose the one-byte diagnostic commands.
2. Let Tracker validate arbitrary application bytes within the existing transport
   limit. For longer messages, add compatible fragment identity, ordered
   reassembly, duplicate suppression, and a bounded SRAM policy before enabling
   host-side fragmentation.
3. Add a Tracker-originated DATA response using the existing frame and reliable
   transport, plus Gateway receive handling that sends the matching ACK.
4. Preserve campaign, peer, and sequence correlation in both directions so a
   delayed ACK or duplicate DATA cannot complete or deliver the wrong message.

Until those firmware capabilities exist, the console accepts only the configured
diagnostic payload and reports an ACK-only exchange. It never labels that result
as an Echo or a successful round trip.
