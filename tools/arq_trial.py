"""Command-driven physical ARQ trials; integrity checks do not prove physical origin.

python tools/arq_trial.py --campaign   # program verified pages, then sequential gates
python tools/arq_trial.py --validate artifacts/arq/<run>/H01/bundle.json
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'tools/config'))
import receiver_boot as boot
import rf_proof as rf


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_event(line):
    if not line.startswith('A '): return None
    pairs=dict(re.findall(r'(\w+)=([^\s]+)',line))
    if not {'t','e','s'} <= pairs.keys(): raise ValueError('incomplete event')
    # AVR printf_min ignores zero-padding; ARM input remains exactly eight hex digits.
    if not re.fullmatch(r'[0-9A-F]{1,8}',pairs['s']): raise ValueError('invalid event session')
    int(pairs['t']);return pairs


def wire_frame(raw):
    b=bytes.fromhex(raw)
    if len(b)<12 or len(b)>44 or b[0]!=1 or b[1] not in (1,2,3) or b[10]>32 or len(b)!=12+b[10]:
        raise ValueError('invalid wire frame')
    if (b[1] in (1,2) and b[11]) or (b[1]!=1 and b[10]) or (b[1]==3 and b[11] not in (1,2,3)):
        raise ValueError('invalid wire fields')
    return dict(type=b[1],src=b[2],dst=b[3],session=int.from_bytes(b[4:8],'little'),
        sequence=int.from_bytes(b[8:10],'little'),reason=b[11],payload=b[12:])


def reserve_session(directory):
    directory.mkdir(parents=True,exist_ok=True)
    # Lock a stable inode; replace only the counter so crashes cannot truncate it.
    with (directory/'session.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        counter=directory/'session.json'
        value=json.loads(counter.read_text()) if counter.exists() else 0
        if type(value) is not int or not 0<=value<0xFFFFFFFF:raise ValueError('session counter exhausted/corrupt')
        value+=1
        from generate_lora_config import _write_atomic
        _write_atomic(counter,json.dumps(value)+'\n')
        return value


def checked_events(events,directory):
    captured=[]
    for role in ('sender','receiver'):
        rows=[]
        for line in (Path(directory)/f'rf-monitor-{role}.stdout.log').read_text().splitlines():
            event=parse_event(line.strip())
            if event:rows.append(dict(event,role=role))
        supplied=[{k:v for k,v in event.items() if k!='host_ns'} for event in events if event['role']==role]
        if supplied!=rows:raise ValueError('event journal differs from raw captured stream')
        captured+=rows
    return captured


def status_complete(events,role,session):
    rows=[e for e in events if e['role']==role and int(e['s'],16)==session]
    statuses=[i for i,e in enumerate(rows) if e['e']=='STATUS']
    ends=[i for i,e in enumerate(rows) if e['e']=='STATUS_END']
    return bool(statuses and ends and ends[-1]>statuses[-1] and rows[ends[-1]].get('v')=='0')


def validate_bundle(b,directory=None):
    required={'acquisition','session','gate','count','events','files','programming','config_hash','firmware','commands'}
    if not isinstance(b,dict) or not required<=b.keys() or b.get('synthetic') is not False or b['acquisition']!='updi-live':
        raise ValueError('not a complete live-acquisition bundle; text/simulation is insufficient')
    if not b['programming'] or set(b['firmware'])!={'sender','receiver'} or not b['files']:
        raise ValueError('missing programming/firmware provenance')
    if directory is None:raise ValueError('bundle directory required for independent file verification')
    directory=Path(directory).resolve()
    for name,expected in b['files'].items():
        p=(directory/name).resolve()
        if not p.is_relative_to(directory) or sha(p)!=expected:raise ValueError('evidence file integrity mismatch')
    events=checked_events(b['events'],directory);session=b['session'];count=b['count']
    if type(count) is not int or count<1 or count>100:raise ValueError('invalid trial count')
    for role in ('sender','receiver'):
        rows=[x for x in events if x['role']==role]
        arms=[x for x in rows if x['e']=='ARM' and int(x['s'],16)==session and x.get('rc')=='0']
        statuses=[x for x in rows if x['e']=='STATUS' and int(x['s'],16)==session]
        if len(arms)!=1 or not statuses or statuses[-1]['overflow']!='0' or statuses[-1]['ready']!='1' or not status_complete(events,role,session):
            raise ValueError('missing ARM/final status or overflow/radio failure')
        if any(int(x['s'],16)!=session for x in rows[rows.index(arms[0])+1:]):
            raise ValueError('reset/session changed during trial')
        identities=[x for x in rows if x['e']=='IDENTITY']
        if not identities or any(x['config']!=b['config_hash'] or x['build']!=b['programming'][role]['build_id'] for x in identities):
            raise ValueError('firmware/config identity mismatch')
        if any(x['e']=='BOOT' and x.get('v')!='0' for x in rows[rows.index(arms[0])+1:]):
            # Retained BOOT repeats via STATUS; compare reset flags, not their nonzero value.
            boots=[x.get('v') for x in rows if x['e']=='BOOT']
            if len(set(boots))>1:raise ValueError('reset evidence')
    relevant=[x for x in events if int(x['s'],16)==session]
    manifest=json.loads((directory/'provenance/manifest.json').read_text())
    if manifest['config_hash']!=b['config_hash']:raise ValueError('manifest/config hash mismatch')
    for role in ('sender','receiver'):
        env=b['programming'][role]['environment']
        image=directory/'provenance'/(env+'.hex')
        if sha(image)!=b['firmware'][role]:raise ValueError('firmware hash mismatch')
        before={};after={}
        for memory in ('signature','sernum','flash','eeprom','fuses','lock'):
            for label,target in (('before',before),('after',after)):
                target[memory]=(directory/'provenance'/f'{env}-{label}-page-write-{memory}.bin').read_bytes()
        region=rf.parse_ihex_range(image.read_bytes());first=region['start'];end=(region['end_exclusive']+511)//512*512
        boot.require_preserved(before,after,first,end)
        from device_detection.firmware_identity import normalize_ihex_region
        if after['flash'][first:end]!=normalize_ihex_region(image.read_text(),first,end):
            raise ValueError('independent installed-image mismatch')
    terminals=[x for x in relevant if x['role']=='sender' and x['e'] in
        ('DELIVERED','REJECTED','PROTOCOL_ERROR','TIMEOUT_EXHAUSTED','RADIO_ERROR')]
    expected='REJECTED' if b['gate']=='H02' else 'DELIVERED'
    if len(terminals)!=count or any(x['e']!=expected for x in terminals):raise ValueError('missing/failed terminal outcomes')
    if len({x['q'] for x in terminals})!=count:raise ValueError('reused sequence')
    frames=[]
    for x in relevant:
        if x['e'] in ('TX','RX'):
            f=wire_frame(x['bytes'])
            if f['session']!=session:raise ValueError('stale session RF')
            frames.append((x,f))
    for terminal in terminals:
        seq=int(terminal['q']);data=[(x,f) for x,f in frames if x['role']=='sender' and x['e']=='TX' and f['type']==1 and f['sequence']==seq]
        if not data or len({x['bytes'] for x,f in data})!=1:raise ValueError('missing/nonimmutable DATA')
        d=data[0][1]
        cfg=manifest['config']
        payload=cfg['negative_payload' if b['gate']=='H02' else 'payload'].encode('ascii')
        if d['src']!=cfg['sender_id'] or d['dst']!=cfg['receiver_id'] or d['payload']!=payload:
            raise ValueError('incorrect DATA')
        if int(terminal['v'])!=len(data):raise ValueError('attempt count differs from RF frames')
        kind=3 if expected=='REJECTED' else 2
        controls=[(x,f) for x,f in frames if f['type']==kind and f['sequence']==seq and
            f['src']==cfg['receiver_id'] and f['dst']==cfg['sender_id'] and (kind!=3 or f['reason']==2)]
        if not any(x['role']=='receiver' and x['e']=='TX' for x,f in controls) or not any(x['role']=='sender' and x['e']=='RX' for x,f in controls):
            raise ValueError('matching real control pair missing')
        if not any(x['role']=='receiver' and x['e']=='RX' and x['bytes']==data[0][0]['bytes'] for x,f in frames):
            raise ValueError('receiver DATA evidence missing')
    status=[x for x in relevant if x['role']=='receiver' and x['e']=='STATUS'][-1]
    if int(status['app'])!=(0 if expected=='REJECTED' else count):raise ValueError('application delivery count')
    if b['gate'] in ('H03','H06'):
        drops=1 if b['gate']=='H03' else min(count//manifest['config']['fault_ack_stride'],manifest['config']['fault_drop_budget'])
        if int(status['sup'])!=drops or int(status['dup'])<drops:raise ValueError('injected-loss accounting')
    if int(status['gen'])!=int(status['sup'])+int(status['att']) or int(status['done'])!=int(status['att']):
        raise ValueError('response accounting incomplete')
    samples=[int(x['v']) for x in relevant if x['role']=='sender' and x['e']=='RTT']
    sample_counts=[x for x in relevant if x['role']=='sender' and x['e']=='RTT_COUNT']
    if not sample_counts or int(sample_counts[-1]['v'])!=len(samples):raise ValueError('RTT evidence incomplete')
    samples.sort()
    return dict(complete=True,validation_scope='integrity-and-completeness; physical origin requires trusted acquisition',
        messages=count,delivered=sum(x['e']=='DELIVERED' for x in terminals),
        first_attempt=sum(x['v']=='1' and x['e']=='DELIVERED' for x in terminals),
        rtt=dict(count=len(samples),min=min(samples) if samples else None,max=max(samples) if samples else None,
            average=sum(samples)/len(samples) if samples else None,p95=samples[math.ceil(.95*len(samples))-1] if samples else None))


class Capture:
    def __init__(self,proof):
        self.proof=proof;self.monitors={};self.queue=queue.Queue();self.events=[];self.commands=[];self.errors=[]
    def start(self):
        for role,target in (('receiver','receiver'),('sender','gateway')):
            self.monitors[role]=rf.start_rf_monitor(self.proof,role,rf.PORTS[target],self.queue)
    def command(self,role,text):
        process=self.monitors[role]['process']
        if process.poll() is not None:raise ValueError('monitor disconnected')
        data=(text+'\n').encode('ascii')
        if process.stdin.write(data)!=len(data):raise ValueError('short command write')
        process.stdin.flush();self.commands.append(dict(role=role,text=text,host_ns=time.monotonic_ns()))
    def wait(self,predicate,seconds=30):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            if any(m['process'].poll() is not None for m in self.monitors.values()):raise ValueError('monitor exited')
            if predicate():return
            try:role,stream,raw=self.queue.get(timeout=.1)
            except queue.Empty:continue
            if stream=='stdout' and raw:
                event=parse_event(raw.decode('ascii',errors='replace').strip())
                if event:event.update(role=role,host_ns=time.monotonic_ns());self.events.append(event)
        raise ValueError('incomplete evidence: capture deadline')
    def acquire(self,programming,config_hash,seconds=45,expected_session=0):
        """Drain startup, then recover each missing status once within one deadline."""
        deadline=time.monotonic()+seconds
        def complete(role):
            rows=[e for e in self.events if e['role']==role]
            starts=[i for i,e in enumerate(rows) if e['e']=='BOOT']
            if not starts:return False
            block=rows[starts[-1]:]
            for e in block:
                if int(e['s'],16)!=expected_session:raise ValueError('unexpected startup session before acquisition')
                if e['e']=='IDENTITY' and (e.get('build')!=programming[role]['build_id'] or e.get('config')!=config_hash):
                    raise ValueError('installed firmware/config mismatch before ARM')
                if e['e']=='STATUS' and (e.get('ready')!='1' or e.get('overflow')!='0'):
                    raise ValueError('startup radio failure or logger overflow')
                if e['e']=='STATUS_END' and e.get('v')!='0':raise ValueError('startup logger overflow')
            return {'BOOT','IDENTITY','STATUS','REG','STATUS_END'}<={e['e'] for e in block} and status_complete(block,role,expected_session)
        try:self.wait(lambda:all(complete(r) for r in programming),min(12,seconds))
        except ValueError as error:
            if str(error)!='incomplete evidence: capture deadline':raise
        for role in programming:
            if complete(role):continue
            self.command(role,'STATUS')
            self.wait(lambda:complete(role),max(0,deadline-time.monotonic()))
    def seen(self,role,event):return [x for x in self.events if x['role']==role and x['e']==event]
    def close(self):
        for m in self.monitors.values():
            try:rf.stop_rf_monitor(m)
            except Exception as error:self.errors.append(str(error))
        # Reader threads may finish trailing lines while stop waits for the mailbox to drain.
        while True:
            try:role,stream,raw=self.queue.get_nowait()
            except queue.Empty:break
            if stream=='stdout' and raw:
                try:event=parse_event(raw.decode('ascii',errors='replace').strip())
                except ValueError as error:
                    self.errors.append(f'{role}: {error}: {raw!r}');continue
                if event:event.update(role=role,host_ns=time.monotonic_ns());self.events.append(event)


def trial(parent,gate,count,manifest,programming,firmware,startup_session=0):
    proof=rf.ProofRun(parent/gate);c=Capture(proof)
    provenance=proof.run_dir/'provenance';provenance.mkdir()
    for p in parent.iterdir():
        if p.is_file():shutil.copy2(p,provenance/p.name)
    session=reserve_session(ROOT/'artifacts/arq')
    bundle=dict(acquisition='updi-live',synthetic=False,gate=gate,count=count,session=session,
        config_hash=manifest['config_hash'],firmware=firmware,programming=programming)
    try:
        bundle['phase']='acquisition';c.start()
        c.acquire(programming,manifest['config_hash'],expected_session=startup_session)
        bundle['phase']='arming'
        for r in ('sender','receiver'):c.command(r,f'ARM {session:08X}')
        c.wait(lambda:all(c.seen(r,'ARM') for r in ('sender','receiver')))
        for r in ('sender','receiver'):
            if c.seen(r,'ARM')[-1].get('rc')!='0':raise ValueError('ARM failed')
        stride,budget=(1,1) if gate=='H03' else (manifest['config']['fault_ack_stride'],manifest['config']['fault_drop_budget']) if gate=='H06' else (0,0)
        c.command('receiver',f'FAULT {stride} {budget}')
        c.wait(lambda:bool(c.seen('receiver','FAULT')))
        payload=manifest['config']['negative_payload' if gate=='H02' else 'payload'].encode().hex()
        bundle['phase']='rf-trial'
        for i in range(count):
            c.command('sender','SEND '+payload)
            c.wait(lambda:len([x for x in c.events if x['role']=='sender' and x['e'] in
                ('DELIVERED','REJECTED','PROTOCOL_ERROR','TIMEOUT_EXHAUSTED','RADIO_ERROR')])>i,180)
            terminal=[x for x in c.events if x['role']=='sender' and x['e'] in
                ('DELIVERED','REJECTED','PROTOCOL_ERROR','TIMEOUT_EXHAUSTED','RADIO_ERROR')][-1]
            if terminal['e']!=('REJECTED' if gate=='H02' else 'DELIVERED'):raise ValueError('transaction failed: '+terminal['e'])
        for r in ('sender','receiver'):
            c.command(r,'X')
            c.wait(lambda:bool(c.seen(r,'PARKED')),10)
            c.command(r,'STATUS')
            c.wait(lambda:status_complete(c.events,r,session),45)
        bundle.update(events=c.events,commands=c.commands)
    except Exception as failure:
        bundle['failure_reason']=str(failure)
        bundle['classification']='capture-failure' if bundle.get('phase')=='acquisition' else 'trial-failure'
        counts={r:len(c.seen(r,'STATUS')) for r in c.monitors}
        try:
            if bundle.get('phase')!='acquisition':
                for r in c.monitors:c.command(r,'X');c.command(r,'STATUS')
                c.wait(lambda:all(len(c.seen(r,'STATUS'))>n and status_complete(c.events,r,session) for r,n in counts.items()),45)
        except Exception as error:proof.note('final-status-error.log',str(error)+'\n')
        raise
    finally:
        c.close();bundle.update(events=c.events,commands=c.commands,capture_errors=c.errors)
        bundle['files']={str(p.relative_to(proof.run_dir)):sha(p) for p in proof.run_dir.rglob('*') if p.is_file()}
        (proof.run_dir/'bundle.json').write_text(json.dumps(bundle,indent=2)+'\n')
    if c.errors:raise ValueError('incomplete capture cleanup: '+str(c.errors))
    report=validate_bundle(bundle,proof.run_dir)
    report['session']=session
    (proof.run_dir/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(gate,json.dumps(report));return report


def campaign(gates=None):
    from generate_lora_config import generate
    generate(check=True)
    parent=ROOT/'artifacts/arq'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    proof=rf.ProofRun(parent);manifest=json.loads((ROOT/'generated/arq_manifest.json').read_text())
    config=subprocess.check_output(['pio','project','config','--json-output'],cwd=ROOT,text=True)
    if rf.check_port_owners(proof,'arq-preflight'):raise ValueError('UPDI ports owned')
    programming={};firmware={};results=[]
    try:
        for role in ('receiver','sender'):
            environment=role+'_arq_test'
            for suffix in ('hex','elf'):
                src=ROOT/'.pio/build'/environment/('firmware.'+suffix)
                (parent/(environment+'.'+suffix)).write_bytes(src.read_bytes())
            firmware[role]=sha(parent/(environment+'.hex'))
            # Fresh serial/signature/fuses plus independent full-memory comparison.
            if rf.check_port_owners(proof,environment+'-preflight'):raise ValueError('UPDI ports owned')
            if rf.program_application(proof,environment,config):raise ValueError('programming failed: '+role)
            identity=(ROOT/'.pio/build'/environment/'lora_build_identity.h').read_text()
            build_id=re.search(r'LORA_BUILD_ID "([0-9a-f]{64})"',identity).group(1)
            # Existing exact images still need an independent after snapshot for bundle validation.
            after=parent/f'{environment}-after-page-write-flash.bin'
            if not after.exists():boot.read_snapshot(proof,environment+'-after-page-write',
                'gateway' if role=='sender' else 'receiver',current_target=True)
            programming[role]=dict(environment=environment,hex_sha256=firmware[role],build_id=build_id,verified=True)
        (parent/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        startup_session=0
        for gate,count in gates or tuple((f'H{i:02}',n) for i,n in enumerate(manifest['config']['test_counts'],1)):
            results.append(trial(parent,gate,count,manifest,programming,firmware,startup_session))
            startup_session=results[-1]['session']
    finally:
        (parent/'campaign.json').write_text(json.dumps(results,indent=2)+'\n')
        restored=prepare()
        proof.note('restore.json',json.dumps(dict(standby_evidence=str(restored)))+'\n')
    return parent


def prepare():
    """Install unarmed normal firmware and verify standby without ARM or SEND."""
    from generate_lora_config import generate
    generate(check=True)
    proof=rf.ProofRun(ROOT/'artifacts/arq'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-standby'))
    config=subprocess.check_output(['pio','project','config','--json-output'],cwd=ROOT,text=True)
    if rf.check_port_owners(proof,'standby-preflight'):raise ValueError('UPDI ports owned')
    programming={}
    for role in ('receiver','sender'):
        env=role+'_arq';image=ROOT/'.pio/build'/env/'firmware.hex'
        (proof.run_dir/(env+'.hex')).write_bytes(image.read_bytes())
        if rf.check_port_owners(proof,env+'-preflight'):raise ValueError('UPDI ports owned')
        if rf.program_application(proof,env,config):raise ValueError('standby programming/readback failed: '+role)
        identity=(ROOT/'.pio/build'/env/'lora_build_identity.h').read_text()
        programming[role]=dict(build_id=re.search(r'LORA_BUILD_ID "([0-9a-f]{64})"',identity).group(1))
    capture=Capture(proof)
    try:
        capture.start()
        capture.acquire(programming,json.loads((ROOT/'generated/arq_manifest.json').read_text())['config_hash'])
        counts={r:len(capture.seen(r,'STATUS_END')) for r in ('sender','receiver')}
        for r in ('sender','receiver'):
            capture.command(r,'X');capture.command(r,'STATUS')
            capture.wait(lambda:len(capture.seen(r,'STATUS_END'))>counts[r] and status_complete(capture.events,r,0),45)
        for r in ('sender','receiver'):
            mode=bytes.fromhex(capture.seen(r,'REG')[-1]['bytes'])[0]
            if mode&7!=1 or capture.seen(r,'STATUS')[-1]['ready']!='1' or capture.seen(r,'STATUS_END')[-1]['v']!='0':
                raise ValueError('radio did not verify standby: '+r)
        if capture.seen('sender','TX') or capture.seen('receiver','TX'):raise ValueError('unexpected RF transmission')
    finally:
        capture.close()
        (proof.run_dir/'status.json').write_text(json.dumps(capture.events,indent=2)+'\n')
    if capture.errors:
        proof.note('capture-errors.json',json.dumps(capture.errors)+'\n')
        raise ValueError('standby capture cleanup failed')
    proof.note('standby-verified.json',json.dumps(dict(standby=True,rf_transmissions=0,
        firmware={r:sha(proof.run_dir/(r+'_arq.hex')) for r in ('sender','receiver')}),indent=2)+'\n')
    return proof.run_dir


def validate_reverse(events):
    if any(e.get('overflow','0')!='0' for e in events):raise ValueError('raw logger overflow')
    starts=[e for e in events if e['role']=='receiver' and e['e']=='RAW_TX']
    done=[e for e in events if e['role']=='receiver' and e['e']=='RAW_TX_DONE' and e.get('rc')=='0' and int(e['flags'])&8]
    received=[e for e in events if e['role']=='sender' and e['e']=='RAW_RX']
    if len(starts)!=1 or starts[0].get('rc')!='0' or starts[0].get('flags')!='11' or len(done)!=1:
        raise ValueError('missing single successful raw transmission')
    if len(received)!=1:raise ValueError('missing single actual raw reception')
    packet=received[0];flags=int(packet['flags'])
    if packet.get('rc')!='0' or flags&0x60!=0x40 or packet.get('len')!='11' or packet.get('match')!='1' or packet.get('bytes')!='48656C6C6F20576F726C64':
        raise ValueError('raw RxDone/CRC/payload mismatch')
    return dict(complete=True,payload=packet['bytes'],rssi=int(packet['rssi']),snr=int(packet['snr']),
        validation_scope='captured physical UPDI; radio metrics in hundredths')


def audit_raw_configuration(event):
    values=bytes.fromhex(event['bytes'])
    # Address order matches reverse_raw configuration(); compare PHY, not mode/DIO state.
    expected=bytes.fromhex('E4C000F084727404000812271D')
    if len(values)!=23 or values[0] not in (0x11,0x12,0x13) or values[2:15]!=expected:
        raise ValueError('reverse radio configuration mismatch')


def reverse_exchange(c):
    # Host deadline starts before RX: delayed mailbox delivery cannot extend the RF window.
    armed=time.monotonic()
    c.command('sender','RX')
    c.wait(lambda:bool(c.seen('sender','RAW_RX_READY')),5)
    ready=c.seen('sender','RAW_RX_READY')[-1]
    if ready.get('rc')!='0' or int(ready.get('mode','0'))&0xc7!=0x85:
        raise ValueError('reverse RX continuous not verified')
    if time.monotonic()-armed>=10 or c.seen('sender','RAW_RX_TIMEOUT'):
        raise ValueError('reverse receive window expired before SEND')
    configs=c.seen('sender','RAW_RX_ACTIVE')
    if not configs:raise ValueError('missing active RX configuration')
    audit_raw_configuration(configs[-1])
    c.command('receiver','SEND 48656C6C6F20576F726C64')
    # Allow the bounded device timeout plus mailbox drain; preserve its actual event.
    c.wait(lambda:bool(c.seen('sender','RAW_RX') or c.seen('sender','RAW_RX_TIMEOUT') or c.seen('receiver','RAW_TX_TIMEOUT')),20)
    c.wait(lambda:bool(c.seen('receiver','RAW_TX_DONE') or c.seen('receiver','RAW_TX_TIMEOUT')),5)
    return validate_reverse(c.events)


def park_reverse(c):
    errors=[]
    for role in c.monitors:
        try:c.command(role,'X')
        except Exception as error:errors.append(role+': '+str(error))
    try:
        if c.monitors:c.wait(lambda:all(c.seen(r,'RAW_STANDBY') for r in c.monitors),5)
    except Exception as error:errors.append(str(error))
    return errors


def reverse_raw():
    """One explicitly commanded Tracker TX, Rudolph RX; always restore normal images."""
    from generate_lora_config import generate
    generate(check=True)
    proof=rf.ProofRun(ROOT/'artifacts/arq'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-reverse-raw'))
    config=subprocess.check_output(['pio','project','config','--json-output'],cwd=ROOT,text=True)
    c=Capture(proof);bundle=dict(acquisition='updi-live',synthetic=False,phase='programming',firmware={})
    try:
        for role in ('sender','receiver'):
            env=role+'_reverse_raw'
            for suffix in ('hex','elf'):
                shutil.copy2(ROOT/'.pio/build'/env/('firmware.'+suffix),proof.run_dir/(env+'.'+suffix))
            identity=(ROOT/'.pio/build'/env/'lora_build_identity.h').read_text()
            bundle['firmware'][role]=dict(sha256=sha(proof.run_dir/(env+'.hex')),
                build_id=re.search(r'LORA_BUILD_ID "([0-9a-f]{64})"',identity).group(1))
            if rf.check_port_owners(proof,env+'-preflight'):raise ValueError('UPDI ports owned')
            if rf.program_application(proof,env,config):raise ValueError('reverse programming failed: '+role)
        bundle['phase']='acquisition';c.start()
        def status(role):
            ids=c.seen(role,'IDENTITY');rows=c.seen(role,'RAW_STATUS');configs=c.seen(role,'RAW_CONFIG')
            if not ids or not rows or not configs:return False
            if ids[-1]['build']!=bundle['firmware'][role]['build_id'] or ids[-1]['config']!=json.loads((ROOT/'generated/arq_manifest.json').read_text())['config_hash']:
                raise ValueError('reverse firmware/config identity mismatch')
            if rows[-1].get('rc')!='0' or rows[-1].get('overflow')!='0':raise ValueError('reverse radio not ready')
            audit_raw_configuration(configs[-1])
            return True
        deadline=time.monotonic()+45
        try:c.wait(lambda:all(status(r) for r in ('sender','receiver')),12)
        except ValueError as error:
            if str(error)!='incomplete evidence: capture deadline':raise
        for role in ('sender','receiver'):
            if not status(role):
                c.command(role,'STATUS');c.wait(lambda:status(role),max(0,deadline-time.monotonic()))
        bundle['phase']='rf-trial';bundle['result']=reverse_exchange(c)
    except Exception as error:
        bundle['failure_reason']=str(error);raise
    finally:
        cleanup_errors=park_reverse(c)
        if cleanup_errors:bundle['cleanup_error']='; '.join(cleanup_errors)
        c.close();bundle.update(events=c.events,commands=c.commands)
        bundle['capture_errors']=c.errors
        bundle['files']={str(p.relative_to(proof.run_dir)):sha(p) for p in proof.run_dir.rglob('*') if p.is_file()}
        (proof.run_dir/'bundle.json').write_text(json.dumps(bundle,indent=2)+'\n')
        # Monitors release both ports before normal-image restoration and verification.
        restored=prepare()
        proof.note('restore.json',json.dumps(dict(standby_evidence=str(restored)))+'\n')
    if c.errors:raise ValueError('incomplete raw capture tail: '+str(c.errors))
    print(json.dumps(bundle['result']));return proof.run_dir


def main():
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--campaign',action='store_true');mode.add_argument('--mvp',action='store_true')
    mode.add_argument('--prepare',action='store_true');mode.add_argument('--validate',type=Path)
    mode.add_argument('--reverse-raw',action='store_true')
    p.add_argument('--rf-path-confirmed',action='store_true',help='operator has physically verified antenna connector and solder bridges')
    args=p.parse_args()
    if args.validate:
        print(json.dumps(validate_bundle(json.loads(args.validate.read_text()),args.validate.parent),indent=2))
    elif args.prepare:print(prepare())
    else:
        if not args.rf_path_confirmed:p.error('RF transmission requires --rf-path-confirmed after physical inspection')
        if args.reverse_raw:print(reverse_raw())
        else:print(campaign((('H01',1),('H02',1),('H03',1),('H04',10))) if args.mvp else campaign())


if __name__=='__main__':main()
