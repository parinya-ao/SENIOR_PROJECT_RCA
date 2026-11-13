"""One-off authorized raw regression followed by verified idle ARQ restoration."""
from pathlib import Path
import sys
import json
import queue
import subprocess
import time
import shutil
sys.path.insert(0,str(Path.cwd()/'tools'))
import rf_proof as rf
from arq_trial import Capture, sha

def run():
    root=Path.cwd()
    from datetime import datetime,timezone
    proof=rf.ProofRun(root/'artifacts/arq'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-raw-regression'))
    config=subprocess.check_output(['pio','project','config','--json-output'],text=True)
    monitors={};output=queue.Queue();texts={'sender':'','receiver':''};result={}
    try:
        for role in ('receiver','sender'):
            env=role+'_mvp'
            assert rf.application_bounds_for_environment(config,env)==(0,130048)
            assert rf.program_application(proof,env,config)==0
            image=root/'.pio/build'/env/'firmware.hex'
            (proof.run_dir/(env+'.hex')).write_bytes(image.read_bytes())
        for role,target in (('receiver','receiver'),('sender','gateway')):
            monitors[role]=rf.start_rf_monitor(proof,role,rf.PORTS[target],output)
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            if any(m['process'].poll() is not None for m in monitors.values()):raise ValueError('raw monitor disconnected')
            try:role,stream,raw=output.get(timeout=.1)
            except queue.Empty:continue
            if stream=='stdout' and raw:texts[role]+=raw.decode(errors='replace')
            result=rf.parse_raw_mvp_logs(texts['sender'],texts['receiver'])
            if result['tx_completed']>=3 and result['rx_matches']>=3:break
        for m in monitors.values():m['process'].stdin.write(b'X');m['process'].stdin.flush()
        assert result.get('passed') and result['tx_completed']>=3 and result['rx_matches']>=3,result
        (proof.run_dir/'raw-result.json').write_text(json.dumps(result,indent=2)+'\n')
        print('RAW',json.dumps(result),flush=True)
    finally:
        for m in monitors.values():rf.stop_rf_monitor(m)
        for p in proof.run_dir.glob('rf-monitor-*'):
            if p.is_file():shutil.copy2(p,proof.run_dir/('raw-'+p.name))
        restore_errors=[]
        for role in ('receiver','sender'):
            if rf.program_application(proof,role+'_arq',config):restore_errors.append(role)
        if restore_errors:raise ValueError('restore failed: '+','.join(restore_errors))
    capture=Capture(proof)
    try:
        capture.start();capture.wait(lambda:all(capture.seen(r,'STATUS_END') for r in ('sender','receiver')),45)
        for r in ('sender','receiver'):capture.command(r,'X');capture.command(r,'STATUS')
        capture.wait(lambda:all(len(capture.seen(r,'STATUS_END'))>=2 for r in ('sender','receiver')),45)
        assert capture.seen('sender','RESULT')[-1]['v']=='0'
        assert all(capture.seen(r,'STATUS')[-1]['ready']=='1' and capture.seen(r,'STATUS')[-1]['overflow']=='0' for r in ('sender','receiver'))
        assert not capture.seen('sender','TX')
    finally:capture.close()
    report=dict(raw=result,normal_firmware={r:sha(root/'.pio/build'/(r+'_arq')/'firmware.hex') for r in ('sender','receiver')},
        final_events=capture.events,sender_idle=True,files={str(p.relative_to(proof.run_dir)):sha(p) for p in proof.run_dir.rglob('*') if p.is_file()})
    (proof.run_dir/'final-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('FINAL',proof.run_dir,flush=True)

if __name__=='__main__':
    if sys.argv[1:]!=['--rf-path-confirmed']:raise SystemExit('Physical RF-path inspection must be confirmed before transmission.')
    run()
