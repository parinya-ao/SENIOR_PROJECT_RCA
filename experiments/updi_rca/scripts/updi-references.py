"""Acquire and hash primary references; never opens a target connection."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request
from updi_rca.paths import ARTIFACTS_ROOT

OUT = ARTIFACTS_ROOT / 'runs/deep-debug/references'
OUT.mkdir(parents=True, exist_ok=True)
sources = {
    'errata.pdf': 'https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/Errata/AVR128DA-28-32-48-64-SilConErrataClarif-DS80000882.pdf',
    'datasheet.pdf': 'https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/AVR128DA28-32-48-64-Data-Sheet-DS40002183.pdf',
    'cp2102.pdf': 'https://www.silabs.com/documents/public/data-sheets/CP2102-9.pdf',
    'cp210x.c': 'https://raw.githubusercontent.com/torvalds/linux/v6.17/drivers/usb/serial/cp210x.c',
}
manifest = {}
for name, url in sources.items():
    path = OUT / name
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read()
        path.write_bytes(data)
        manifest[name] = dict(url=url, utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                              bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        if name.endswith('.pdf'):
            subprocess.run(['pdftotext', '-layout', str(path), str(path.with_suffix('.txt'))], check=True)
        print(name, len(data))
    except Exception as exc:
        manifest[name] = dict(url=url, error=str(exc))
        print(name, type(exc).__name__, str(exc))
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
