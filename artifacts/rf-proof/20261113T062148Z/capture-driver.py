import os,sys,time,json,subprocess,threading,queue
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,'tools')
import rf_proof as rf
p=Path(Path('/tmp/lora-mvp-run').read_text())
assert 'FINAL sender_mvp RESULT 0' in Path('/tmp/lora-mvp-final-upload.log').read_text()
assert not rf.check_port_owners(object_with_run_dir := type('Proof',(),{'run_dir':p,'command':rf.ProofRun.command})(),'raw-capture')
q=queue.Queue(); processes={}; streams=[]; events=[]; texts={'receiver':[],'sender':[]}
def start(role,port):
 err=(p/(role+'-final.stderr.log')).open('w');streams.append(err)
 proc=subprocess.Popen(['uv','run','third_party/upditerm/upditerm.py','-l',str(p/(role+'-final.upditerm.log')),port,'38400'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True,bufsize=1,env=dict(os.environ,PYTHONUNBUFFERED='1'))
 processes[role]=proc
 def reader():
  for line in proc.stdout:q.put((time.monotonic(),role,line.rstrip('\n')))
 threading.Thread(target=reader,daemon=True).start()
def pump(seconds,predicate=lambda e:False):
 deadline=time.monotonic()+seconds
 while time.monotonic()<deadline:
  try:t,role,line=q.get(timeout=min(.2,max(.001,deadline-time.monotonic())))
  except queue.Empty:continue
  event={'monotonic':t,'utc':datetime.now(timezone.utc).isoformat(),'role':role,'line':line}
  events.append(event);texts[role].append(line)
  print(role,line,flush=True)
  if predicate(event):return True
 return False
summary={'origin':'PHYSICAL_UPDI','passed':False}
try:
 start('receiver',rf.PORTS['receiver'])
 assert pump(25,lambda e:e['line']=='[MVP RECEIVER] RX_READY rc=0'),'Receiver not ready'
 start('sender',rf.PORTS['gateway'])
 assert pump(35,lambda e:' PASS bytes=48656C6C6F20576F726C64' in e['line']),'No matching physical reception'
 pump(5)
 processes['sender'].stdin.write('X');processes['sender'].stdin.flush()
 summary['stop_sent_monotonic']=time.monotonic()
 assert pump(10,lambda e:e['role']=='sender' and '[MVP SENDER] STOP ' in e['line']),'Stop not acknowledged'
 pump(3.5)
 quiet_start=time.monotonic()
 pump(15)
 quiet_end=time.monotonic()
 quiet_matches=[e for e in events if e['role']=='receiver' and quiet_start<=e['monotonic']<=quiet_end and ' PASS bytes=' in e['line']]
 quiet_tx=[e for e in events if e['role']=='sender' and quiet_start<=e['monotonic']<=quiet_end and ' TX_START ' in e['line']]
 summary.update(quiet_start_monotonic=quiet_start,quiet_end_monotonic=quiet_end,quiet_seconds=quiet_end-quiet_start,quiet_matching_receptions=len(quiet_matches),quiet_transmit_starts=len(quiet_tx))
 summary['raw_evidence']=rf.parse_raw_mvp_logs('\n'.join(texts['sender']),'\n'.join(texts['receiver']))
 summary['passed']=summary['raw_evidence']['passed'] and not quiet_matches and not quiet_tx and quiet_end-quiet_start>=15
 assert summary['passed'],'Evidence validation failed'
except Exception as error:
 summary['error']=str(error)
finally:
 if 'sender' in processes and processes['sender'].poll() is None:
  try:processes['sender'].stdin.write('X');processes['sender'].stdin.flush();pump(1)
  except (BrokenPipeError,OSError):pass
 for role,proc in processes.items():
  if proc.stdin and not proc.stdin.closed:proc.stdin.close()
  try:proc.wait(5)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(3)
 for stream in streams:stream.close()
 (p/'raw-mvp-events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
 (p/'raw-mvp-physical-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps(summary,indent=2),flush=True)
raise SystemExit(0 if summary['passed'] else 1)
