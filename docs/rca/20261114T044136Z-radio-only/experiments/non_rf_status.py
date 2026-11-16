"""One-run acquisition using the existing tested recorder/Monitor; STATUS only, no programming."""
from pathlib import Path
import importlib.util
import json
import os
import subprocess
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from tools.rca import gate1_live as gate
from tools.arq_trial import read_reset_state,close_updi_without_recovery
import serial

RUN=Path(__file__).resolve().parents[1]
hardware=json.loads((ROOT/'config/current_hardware.json').read_text())
restored=json.loads((ROOT/'artifacts/arq/20261114T025609Z-standby/status.json').read_text())
addresses={'gpior0':0x1c,'rstfr':0x40,'bod_ctrla':0x80,'bod_ctrlb':0x81,
    'porta_dir':0x400,'porta_out':0x404,'porta_in':0x408,
    'portc_dir':0x440,'portc_out':0x444,'portd_dir':0x460,'portd_out':0x464,'portd_in':0x468,
    'portf_dir':0x4a0,'portf_out':0x4a4,'portf_pin0ctrl':0x4b0,'portf_pin1ctrl':0x4b1,
    'usart2_ctrla':0x845,'usart2_ctrlb':0x846,'silicon_revision':0xf01,'fuse_bodcfg':0x1051}

for target,role,count in [('receiver','receiver',20),('gateway','sender',1)]:
    directory=RUN/'raw'/target
    directory.mkdir()
    audit=gate.Gate1Audit(directory)
    spec=importlib.util.spec_from_file_location('radio_only_'+target,ROOT/'third_party/upditerm/upditerm.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    port=hardware[target]['port_path']
    owners=subprocess.run(['fuser','-v',port],capture_output=True,text=True)
    udev=subprocess.run(['udevadm','info','--query=property','--name',port],capture_output=True,text=True,check=True)
    props=dict(x.split('=',1) for x in udev.stdout.splitlines() if '=' in x)
    assert owners.returncode==1 and not owners.stdout, 'port ownership not clear'
    assert props['ID_VENDOR_ID']=='10c4' and props['ID_MODEL_ID']=='ea60'
    assert props['ID_PATH']==Path(port).name.rsplit('-port',1)[0]
    identity=next(x for x in restored if x['role']==role and x['e']=='IDENTITY')
    expected={'role':role,'build_id':identity['build'],'config_hash':identity['config']}
    audit.device_path=port;audit.adapter_identity=props['ID_SERIAL']
    (directory/'preflight.json').write_text(json.dumps(dict(expected=expected,udev=props,
        port_owner_stdout=owners.stdout,port_owner_stderr=owners.stderr),indent=2)+'\n')
    original_serial=gate.instrument(module,audit,serial)
    connection=session=monitor=console=None
    verdict={'result':'INCONCLUSIVE','status_attempted':0,'status_passed':0,'status_failed':0,
        'rf_transmissions':0,'firmware_flashes':0,'fuse_writes':0,'first_failure':None}
    try:
        acquired=time.monotonic()+45
        connection=module.UPDI(port,38400)
        signature=bytes(gate.read_data_space_byte(connection,0x1100+i) for i in range(3)).hex()
        sernum=bytes(gate.read_data_space_byte(connection,0x1110+i) for i in range(16)).hex()
        assert signature=='1e970a' and sernum==hardware[target]['device_serial_hex'], 'target identity mismatch'
        audit.event('TARGET_IDENTITY_VERIFIED',signature=signature,serial=sernum)
        before={name:gate.read_data_space_byte(connection,address) for name,address in addresses.items()}
        (directory/'registers-before.json').write_text(json.dumps(before,indent=2)+'\n')
        connection.key(module.KEY_OCD)
        connection.sts8(module.UART_FLAGS,module.FLAG_ENABLE)
        session=module.SerialUPDI.__new__(module.SerialUPDI);session.updi=connection
        console=gate.MonitorConsole();monitor=module.Terminal(console,session)
        with audit.stdout.open('ab',buffering=0) as output:
            gate._read_block(console,audit,monitor,expected,acquired,output,startup=True)
            deadline=time.monotonic()+gate.STATUS_STABILITY_TIMEOUT_S
            for index in range(1,count+1):
                assert time.monotonic()<deadline, 'overall STATUS deadline expired'
                audit.current_transaction=index;audit.status_command_hex=b'STATUS\n'.hex()
                audit.status_command_bytes_sent=[];audit.current_status_output=bytearray()
                start=time.monotonic_ns();utc=gate.utc()
                verdict['status_attempted']+=1
                console.send(b'STATUS\n')
                _,events,raw=gate._read_block(console,audit,monitor,expected,min(deadline,time.monotonic()+15),output)
                assert bytes(audit.status_command_bytes_sent)==b'STATUS\n'
                assert monitor.failure is None
                row=dict(transaction_index=index,utc_start=utc,utc_end=gate.utc(),
                    monotonic_start_ns=start,monotonic_end_ns=time.monotonic_ns(),
                    request_hex=b'STATUS\n'.hex(),accepted_hex=bytes(audit.status_command_bytes_sent).hex(),
                    raw_response_hex=raw.hex(),raw_response_length=len(raw),events=events,result='PASS')
                audit.write_transaction(row);verdict['status_passed']+=1
                print(target,index,'STATUS_PASS',flush=True)
        audit.current_transaction=None
        with monitor.serport_lock:
            after={name:gate.read_data_space_byte(connection,address) for name,address in addresses.items()}
        (directory/'registers-after.json').write_text(json.dumps(after,indent=2)+'\n')
        verdict.update(result='PASS',signature=signature,mcu_serial=sernum,firmware_identity=expected,
                       reset_before=before['gpior0'],reset_after=after['gpior0'])
    except Exception as error:
        audit.fail(error,'LIVE_STATUS',failure_layer='STATUS_RESPONSE' if isinstance(error,TimeoutError) else None)
        audit.stderr.write_text(traceback.format_exc())
        verdict.update(result='FAIL' if audit.current_transaction else 'INCONCLUSIVE',
            status_failed=int(audit.current_transaction is not None),first_failure=audit.first_failure)
    finally:
        audit.current_transaction=None
        if monitor:
            gate.wait_for_reader_idle(monitor.reader_busy,2)
            console.input.put(None)
            monitor.writer_thread.join(2);monitor.reader_thread.join(2)
            if monitor.writer_thread.is_alive() or monitor.reader_thread.is_alive():
                verdict['result']='INCONCLUSIVE'
            audit.event('MONITOR_THREADS_CLOSED',writer_alive=monitor.writer_thread.is_alive(),reader_alive=monitor.reader_thread.is_alive())
        if connection and connection.ser:
            if not audit.first_failure:
                connection.sts8(module.UART_FLAGS,0)
                connection.stcs(module.CTRLB,module.UPDIDIS)
            close_updi_without_recovery(session or connection)
        serial.Serial=original_serial
        verdict.update(break_count=audit.break_count,synch_count=audit.synch_count,
                       cpu_resumes=audit.resume_count,cpu_resets_requested=audit.reset_count)
        (directory/'verdict.json').write_text(json.dumps(verdict,indent=2)+'\n')
        print(json.dumps(verdict),flush=True)
    if verdict['result']!='PASS':
        break
