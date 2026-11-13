"""UPDI-only, one-variable response-guard experiments authorized by the operator."""
from pathlib import Path
import json
import re
import subprocess
import sys
from datetime import datetime,timezone
ROOT=Path.cwd()
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/config')]
import rf_proof as rf
import receiver_boot as boot
from arq_trial import trial,sha
from generate_lora_config import generate,digest

def run():
    parent=ROOT/'artifacts/arq'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-turnaround')
    parent.mkdir();results=[]
    for guard in (50,100,200):
        proof=rf.ProofRun(parent/f'guard-{guard}')
        path=ROOT/'config/arq_test.toml'
        path.write_text(re.sub(r'(?m)^response_guard_ms = \d+$',f'response_guard_ms = {guard}',path.read_text()))
        generate()
        code,_,_=proof.command('build',['pio','run','-e','sender_arq_test','-e','receiver_arq_test'],300)
        if code:raise ValueError('guard build failed')
        manifest=json.loads((ROOT/'generated/arq_manifest.json').read_text())
        (proof.run_dir/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        (proof.run_dir/'arq_test.toml').write_bytes(path.read_bytes())
        config=subprocess.check_output(['pio','project','config','--json-output'],text=True)
        programming={};firmware={}
        for role in ('receiver','sender'):
            env=role+'_arq_test'
            image=ROOT/'.pio/build'/env/'firmware.hex'
            (proof.run_dir/(env+'.hex')).write_bytes(image.read_bytes())
            firmware[role]=sha(image)
            if rf.program_application(proof,env,config):raise ValueError('guard programming/readback failed: '+role)
            if not (proof.run_dir/f'{env}-after-page-write-flash.bin').exists():
                boot.read_snapshot(proof,env+'-after-page-write','gateway' if role=='sender' else 'receiver',current_target=True)
            build_id=re.search(r'LORA_BUILD_ID "([0-9a-f]{64})"',(ROOT/'.pio/build'/env/'lora_build_identity.h').read_text()).group(1)
            programming[role]=dict(environment=env,hex_sha256=firmware[role],build_id=build_id,verified=True)
        record=dict(response_guard_ms=guard,config_hash=manifest['config_hash'],firmware=firmware)
        try:
            record['H01']=trial(proof.run_dir,'H01',1,manifest,programming,firmware)
            record['H04']=trial(proof.run_dir,'H04',10,manifest,programming,firmware)
        except ValueError as error:record['failure']=str(error)
        results.append(record);(parent/'matrix.json').write_text(json.dumps(results,indent=2)+'\n')
        print('GUARD_RESULT',json.dumps(record),flush=True)
    print('MATRIX',parent,flush=True)

if __name__=='__main__':
    if sys.argv[1:]!=['--rf-path-confirmed']:raise SystemExit('Physical RF-path inspection must be confirmed before transmission.')
    run()
