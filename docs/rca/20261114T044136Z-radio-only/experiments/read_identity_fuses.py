"""Capture fresh AVR128DA identity, fuse, reset and GPIO bytes over read-only UPDI LDS."""
from pathlib import Path
from datetime import datetime, timezone
import importlib.util
import json
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[4]
RUN=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.rca import gate1_live as gate
import serial

HARDWARE=json.loads((ROOT/'config/current_hardware.json').read_text())
FUSES={name:address for name,address in (
    ('WDTCFG',0x1050),('BODCFG',0x1051),('OSCCFG',0x1052),
    ('SYSCFG0',0x1055),('SYSCFG1',0x1056),('CODESIZE',0x1057),('BOOTSIZE',0x1058))}
REGISTERS={name:address for name,address in (
    ('RSTFR',0x0040),('GPIOR0',0x001c),('BOD_CTRLA',0x0080),('BOD_CTRLB',0x0081),
    ('SYSCFG_REVID',0x0f01),
    ('PORTA_DIR',0x0400),('PORTA_OUT',0x0404),('PORTD_DIR',0x0460),('PORTD_OUT',0x0464),
    ('PORTC_DIR',0x0440),('PORTC_OUT',0x0444),('PORTF_DIR',0x04a0),('PORTF_OUT',0x04a4),
    ('PORTF_PIN0CTRL',0x04b0),('PORTF_PIN1CTRL',0x04b1),('USART2_CTRLA',0x0845),('USART2_CTRLB',0x0846))}

for role in ('receiver','gateway'):
    target={'receiver':'receiver','gateway':'gateway'}[role]
    port=HARDWARE[target]['port_path']
    out=RUN/'raw'/f'{role}-fuses';out.mkdir(exist_ok=True)
    audit=gate.Gate1Audit(out)
    properties=subprocess.run(['udevadm','info','--query=property','--name',port],capture_output=True,text=True,check=True)
    props=dict(line.split('=',1) for line in properties.stdout.splitlines() if '=' in line)
    owner=subprocess.run(['fuser','-v',port],capture_output=True,text=True)
    assert owner.returncode==1 and not owner.stdout, f'{role} port is owned'
    assert props.get('ID_VENDOR_ID')=='10c4' and props.get('ID_MODEL_ID')=='ea60'
    assert props.get('ID_PATH')==Path(port).name.rsplit('-port',1)[0]
    spec=importlib.util.spec_from_file_location(f'updi_fuse_{role}',ROOT/'third_party/upditerm/upditerm.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    original_serial=gate.instrument(module,audit,serial)
    connection=None
    record={'role':role,'utc_start':datetime.now(timezone.utc).isoformat(),
        'monotonic_start_ns':time.monotonic_ns(),'device_path':port,'usb_path':props.get('ID_PATH'),
        'adapter_id':props.get('ID_SERIAL'),'expected_mcu_serial':HARDWARE[target]['device_serial_hex'],
        'cpu_reset_requested':False,'nvm_write_requested':False,'rf_tx':0}
    try:
        connection=module.UPDI(port,38400)
        record['sib']=connection.sib()
        record['signature']=bytes(gate.read_data_space_byte(connection,0x1100+i) for i in range(3)).hex()
        record['mcu_serial']=bytes(gate.read_data_space_byte(connection,0x1110+i) for i in range(16)).hex()
        assert record['signature']=='1e970a' and record['mcu_serial']==record['expected_mcu_serial']
        record['fuses']={name:gate.read_data_space_byte(connection,address) for name,address in FUSES.items()}
        record['registers']={name:gate.read_data_space_byte(connection,address) for name,address in REGISTERS.items()}
        record['identity_match']=True
        record['result']='READ_ONLY_PASS'
    except Exception as error:
        record['result']='FAIL'
        record['exception_type']=type(error).__name__
        record['exception_message']=str(error)
    finally:
        if connection and connection.ser:
            dev=connection.ser.dev
            connection.ser=None
            dev.close()
        serial.Serial=original_serial
        record['monotonic_end_ns']=time.monotonic_ns()
        record['utc_end']=datetime.now(timezone.utc).isoformat()
        (out/'readback.json').write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps(record),flush=True)
    if record['result']!='READ_ONLY_PASS':break
