"""Complete Sender standby installation after a failed pre-write UPDI init; no RF commands."""
from pathlib import Path
import sys,json,subprocess
ROOT=Path.cwd();sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/config')]
import rf_proof as rf
from arq_trial import Capture,sha

def run():
    proof=rf.ProofRun(ROOT/'artifacts/arq/sender-standby-completion')
    config=subprocess.check_output(['pio','project','config','--json-output'],text=True)
    if rf.check_port_owners(proof,'standby-completion'):raise ValueError('UPDI owner present')
    if rf.program_application(proof,'sender_arq',config):raise ValueError('Sender programming/readback failed')
    c=Capture(proof)
    try:
        c.start();c.wait(lambda:all(c.seen(r,'STATUS_END') for r in ('sender','receiver')),45)
        for r in ('sender','receiver'):c.command(r,'X');c.command(r,'STATUS')
        c.wait(lambda:all(len(c.seen(r,'STATUS_END'))>=2 for r in ('sender','receiver')),45)
        for r in ('sender','receiver'):
            assert bytes.fromhex(c.seen(r,'REG')[-1]['bytes'])[0]&7==1
            assert c.seen(r,'STATUS')[-1]['ready']=='1'
            assert c.seen(r,'STATUS_END')[-1]['v']=='0'
            assert c.seen(r,'IDENTITY')[-1]['config']==json.loads((ROOT/'generated/arq_manifest.json').read_text())['config_hash']
            assert not c.seen(r,'TX')
        assert c.seen('sender','RESULT')[-1]['v']=='0'
    finally:
        c.close();(proof.run_dir/'status.json').write_text(json.dumps(c.events,indent=2)+'\n')
    report=dict(standby=True,sender_idle=True,rf_transmissions=0,
        receiver_preservation_proof='artifacts/arq/20261113T082243Z-standby',
        firmware={r:sha(ROOT/'.pio/build'/(r+'_arq')/'firmware.hex') for r in ('sender','receiver')},
        files={str(p.relative_to(proof.run_dir)):sha(p) for p in proof.run_dir.rglob('*') if p.is_file()})
    (proof.run_dir/'standby-verified.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':run()
