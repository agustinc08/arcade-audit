#!/usr/bin/env python3
"""Universal, resumable Batocera game certifier; launches only READY adapters."""
import argparse,csv,hashlib,json,os,re,signal,sqlite3,subprocess,sys,time,urllib.request,shutil,fcntl
from datetime import datetime,timezone
from pathlib import Path

TOOLS=Path('/userdata/system/el_gordo_tools'); AUDIT=Path('/userdata/system/state/arcade_audit')
# Explicit precedence: current transactional engine, active audit helpers, then historical scripts.
sys.path.insert(0,str(AUDIT/'scripts'));sys.path.insert(0,str(AUDIT));sys.path.insert(0,str(TOOLS))
import certification_transaction as tx
import certifier_adapters as ad
import smoke_runner as sr
from certification_batch_accounting import new_batch_progress, record_batch_result, set_invocation_selection, phase_summary
from marker_ownership import create_exclusive as create_owned_marker, remove_if_owned as remove_owned_marker

TABLE=AUDIT/'full_game_certification.csv'; MASTER=AUDIT/'arcade_master_checkpoint.json'
STATE=AUDIT/'full_game_certification_checkpoint.json'; RUNTIME=AUDIT/'runtime'/'full_certification'
SYSTEMS_CSV=AUDIT/'data'/'detected_systems.csv'; API='http://127.0.0.1:1234'
CONF=Path('/userdata/system/batocera.conf'); DISP=Path('/userdata/system/el_gordo_tools/controller_dispatcher')
PROFILE=Path('/userdata/system/configs/el_gordo_controller_profiles/controller_technical.json')
MULTI=Path('/userdata/system/configs/el_gordo_controller_profiles/multiplayer.json')
LOGS=[Path('/userdata/system/logs/controller_selector.log'),Path('/userdata/system/logs/es_launch_stdout.log'),
      Path('/userdata/system/logs/es_launch_stderr.log'),Path('/userdata/system/logs/emulog.txt')]
AUTOPILOT_STATE=AUDIT/'autopilot_state.json'; CERTIFIER_LOCK=AUDIT/'jobs'/'.full_game_certifier.lock'
CERTIFIER_JOB_META=AUDIT/'jobs'/'certifier_job.json'
CERTIFIER_LOCK_FD=None
HDMI='alsa_output.pci-0000_01_00.1.hdmi-stereo'
DURATIONS={'mame':20,'fbneo':20,'neogeo':20,'nes':16,'fds':16,'snes':16,'megadrive':16,'mastersystem':16,
 'gb':16,'gbc':16,'gba':16,'pcengine':16,'n64':35,'psx':35,'dreamcast':50,'ps2':75,'psp':35}
PLAYER_WEIGHT={'8':8,'7':7,'6':6,'5':5,'4':4,'3':3,'2':2,'1':1}
PILOT=[('mame','lbgrande.zip'),('mame','1941.zip'),('fbneo','captcomm.zip'),
 ('nes','Super Mario Bros. (ESP-Her-Saki).nes'),('snes','NBA Jam (USA).zip'),
 ('megadrive','Ultimate Mortal Kombat 3 (E) [!].bin'),('psx','CTR - Crash Team Racing (USA).cue'),
 ('gba','Final Fantasy V Advance (Europe) (En,Fr,De,Es,It).gba'),('n64','Super Mario 64.z64'),
 ('mastersystem','Batman Returns (EU).sms')]
STOP_ENGINE={'ENGINE_FAIL','WRONG_GAME_DISPATCH','AUDIO_ROUTE_CHANGED','RESTORE_FAILURE','SYSTEM_SAFETY_FAILURE'}
SAFETY_GATE_FAILURES={'ES_IDLE_TIMEOUT','ES_LAUNCH_PROCESS_ACTIVE','MARKER_FOREIGN_UNKNOWN','MARKER_ALREADY_EXISTS'}
ES_IDLE_TIMEOUT_SECONDS=20
ES_IDLE_POLL_SECONDS=1

def utc():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def stamp():return datetime.now().astimezone().isoformat(timespec='milliseconds')
def atomic_bytes(path,data,mode=0o644):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp')
 fd=os.open(str(tmp),os.O_WRONLY|os.O_CREAT|os.O_TRUNC,mode)
 with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.chmod(tmp,mode);os.replace(tmp,path)
 fd=os.open(str(path.parent),os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
def atomic_json(path,obj):atomic_bytes(path,(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode(),0o600)
def prune_verified_snapshots(txid):
 root=tx.RUNTIME/txid
 if root.parent!=tx.RUNTIME or root.is_symlink() or not root.is_dir():raise RuntimeError('BAD_TRANSACTION_WORKSPACE')
 manifest=json.loads((root/'manifest.json').read_text())
 if manifest.get('transaction_id')!=txid or manifest.get('status')!='RESTORE_VERIFIED':
  raise RuntimeError('TRANSACTION_NOT_VERIFIED_FOR_PRUNE')
 snaps=root/'snapshots'
 if snaps.exists():
  if snaps.is_symlink() or snaps.parent!=root:raise RuntimeError('SNAPSHOT_PATH_UNSAFE')
  shutil.rmtree(snaps)
 manifest['snapshots_pruned_after_verified_restore']=True
 atomic_json(root/'manifest.json',manifest)
def load_rows():
 with TABLE.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f)),list(csv.DictReader(TABLE.open(encoding='utf-8-sig',newline='')).fieldnames or [])
def write_rows(rows,fields):
 extra=['adapter','test_result','test_id','identity_status','audio_status','restore_status','exit_status','visual_status',
        'selected_control_mode','runtime_seconds','tested_at','health_id','failure_class','input_software_status']
 fields=list(fields)+[x for x in extra if x not in fields]
 from io import StringIO
 buf=StringIO(newline='');w=csv.DictWriter(buf,fieldnames=fields,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(rows)
 atomic_bytes(TABLE,buf.getvalue().encode('utf-8'))
 return fields
def api(path,timeout=4):
 with urllib.request.urlopen(API+path,timeout=timeout) as r:return r.status,r.read().decode('utf-8','replace')
def api_state():
 _,ib=api('/isIdle');_,gb=api('/runningGame');idle=json.loads(ib);game=json.loads(gb)
 if isinstance(game,dict) and game.get('msg')=='NO GAME RUNNING':game=None
 return idle[0] is True,game
def es_gate_evidence(idle,game,active,marker_exists,detail=None):
 return {'captured_at':stamp(),'isIdle':idle,'runningGame':game,'launch_processes':active,
         'marker_exists':marker_exists,'detail':detail}
def wait_for_es_idle(timeout=ES_IDLE_TIMEOUT_SECONDS,interval=ES_IDLE_POLL_SECONDS,*,
                     sleep=None,clock=None,evidence_path=None):
 sleep=sleep or time.sleep;clock=clock or time.monotonic
 started=clock();clean_samples=0;last=None
 def save(reason):
  if evidence_path is not None:
   atomic_json(Path(evidence_path),{'reason':reason,'timeout_seconds':timeout,'last_observation':last})
  elif last is not None:
   path=RUNTIME/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'_es_idle_gate.json')
   atomic_json(path,{'reason':reason,'timeout_seconds':timeout,'last_observation':last})
 while True:
  detail=None
  try:idle,game=api_state()
  except Exception as exc:idle,game=False,None;detail=type(exc).__name__+': '+str(exc)
  active=pids();marker_exists=sr.MARKER.exists()
  last=es_gate_evidence(idle,game,active,marker_exists,detail)
  if marker_exists:
   save('MARKER_FOREIGN_UNKNOWN');raise RuntimeError('MARKER_FOREIGN_UNKNOWN')
  if active:
   save('ES_LAUNCH_PROCESS_ACTIVE');raise RuntimeError('ES_LAUNCH_PROCESS_ACTIVE')
  if idle and game is None:
   clean_samples+=1
   if clean_samples>=2:return last
  else:clean_samples=0
  remaining=timeout-(clock()-started)
  if remaining<=0:
   save('ES_IDLE_TIMEOUT');raise RuntimeError('ES_IDLE_TIMEOUT')
  sleep(min(interval,remaining))
def pids():
 out=[]
 for x in Path('/proc').iterdir():
  if not x.name.isdigit():continue
  try:
   comm=(x/'comm').read_text().strip().lower();exe=os.path.basename(os.readlink(x/'exe')).lower();argv=(x/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace').strip()
   launch_argv=('/userdata/system/el_gordo_tools/controller_dispatcher' in argv or
                '/userdata/system/el_gordo_tools/selector_controles' in argv or
                '/usr/bin/emulatorlauncher' in argv)
   if comm in {'retroarch','mame','controller_dispatcher','selector_controles','emulatorlauncher'} or exe in {'retroarch','mame','controller_dispatcher','selector_controles','emulatorlauncher'} or launch_argv:
    st=(x/'stat').read_text().rsplit(')',1)[1].split();out.append({'pid':int(x.name),'ppid':int(st[1]),'comm':comm,'exe':exe,'argv':argv})
  except (OSError,ValueError,IndexError):pass
 return out
def process_identity(pid):
 try:
  proc=Path(f'/proc/{pid}');cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
  fields=(proc/'stat').read_text().rsplit(')',1)[1].split()
  return {'cmdline':cmd,'ppid':int(fields[1]),'start_ticks':int(fields[19])}
 except (OSError,ValueError,IndexError):return None
def delegated_autopilot_owner_matches(state,env_run_id,owner,job,cert_pid,cert_ppid,cert_cmd,owner_proc):
 run_id=state.get('run_id');pid=state.get('pid')
 expected={'run_id':run_id,'pid':pid,'process_start_ticks':state.get('process_start_ticks')}
 return bool(state.get('status') in ('STARTING','RUNNING') and isinstance(pid,int) and run_id and
  env_run_id==run_id and owner==expected and owner_proc and
  owner_proc.get('start_ticks')==state.get('process_start_ticks') and
  'arcade_autopilot.py' in owner_proc.get('cmdline','') and '--worker' in owner_proc.get('cmdline','') and
  run_id in owner_proc.get('cmdline','') and job.get('status')=='RUNNING' and
  job.get('pid')==cert_pid and job.get('worker_pid')==cert_ppid and
  job.get('autopilot_owner')==expected and str(Path(__file__).resolve()) in cert_cmd)
def autopilot_process_owned_by_current_run():
 try:state=json.loads(AUTOPILOT_STATE.read_text())
 except (OSError,ValueError):return True
 if state.get('status') not in ('STARTING','RUNNING'):return True
 run_id=state.get('run_id');pid=state.get('pid')
 if not run_id or os.environ.get('ARCADE_AUTOPILOT_RUN_ID')!=run_id or not isinstance(pid,int):return False
 try:
  cert_pid=os.getpid();cert_proc=process_identity(cert_pid);parent_pid=os.getppid()
  owner_proc=process_identity(pid)
  cert_cmd=cert_proc.get('cmdline','') if cert_proc else ''
  expected={'run_id':run_id,'pid':pid,'process_start_ticks':state.get('process_start_ticks')}
  for _ in range(200):
   job=json.loads(CERTIFIER_JOB_META.read_text())
   if delegated_autopilot_owner_matches(state,os.environ.get('ARCADE_AUTOPILOT_RUN_ID'),
     job.get('autopilot_owner'),job,cert_pid,parent_pid,cert_cmd,owner_proc):return True
   # The detached worker publishes its own PID before spawning this process;
   # allow only that single, owner-matched metadata transition.
   if (job.get('status')!='RUNNING' or job.get('autopilot_owner')!=expected or
       job.get('worker_pid')!=parent_pid or job.get('pid') not in (None,parent_pid)):
    return False
   time.sleep(0.01)
  return False
 except (OSError,ValueError,TypeError):return False
def acquire_certifier_lock():
 global CERTIFIER_LOCK_FD
 CERTIFIER_LOCK.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 fd=os.open(str(CERTIFIER_LOCK),os.O_CREAT|os.O_RDWR,0o600)
 try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:
  os.close(fd);raise RuntimeError('CERTIFIER_ALREADY_RUNNING')
 CERTIFIER_LOCK_FD=fd
 return fd
def conf_sha():return hashlib.sha256(CONF.read_bytes()).hexdigest()
def get_default_sink():
 q=subprocess.run(['pactl','get-default-sink'],capture_output=True,text=True,timeout=3)
 return q.stdout.strip() if q.returncode==0 else None
EXPECTED_ARCADE_USB={'P1':'5','P2':'6','P3':'8','P4':'7'}
EXPECTED_ARCADE_DEVICE=('0079','0006')

def expected_controller_id_path(usb_port):
 return f'pci-0000:00:14.0-usb-0:{usb_port}:1.0'

def expected_controller_by_path(usb_port):
 return f'/dev/input/by-path/{expected_controller_id_path(usb_port)}-event-joystick'

def _udev_properties(sysfs_path):
 q=subprocess.run(['udevadm','info','--query=property','--path',str(sysfs_path)],
                  capture_output=True,text=True,timeout=5)
 if q.returncode:raise RuntimeError('INPUT_UDEV_INFO_FAILED:'+str(sysfs_path))
 out={}
 for line in q.stdout.splitlines():
  if '=' in line:
   k,v=line.split('=',1);out[k]=v
 return out

def _js_for_id_path(id_path):
 for node in Path('/sys/class/input').glob('js*'):
  try:
   props=_udev_properties(node)
  except Exception:
   continue
  if props.get('ID_PATH')==id_path:
   return props.get('DEVNAME')
 return None

def profile_state():
 try:
  profile=json.loads(PROFILE.read_text(encoding='utf-8'))
 except (OSError,ValueError) as exc:
  raise RuntimeError('P1_P4_PROFILE_UNREADABLE') from exc
 configured={x.get('player'):x for x in profile.get('arcade_controllers',[])
             if isinstance(x,dict) and x.get('player') in EXPECTED_ARCADE_USB}
 if set(configured)!=set(EXPECTED_ARCADE_USB):raise RuntimeError('P1_P4_PROFILE_INCOMPLETE')
 for player,expected_port in EXPECTED_ARCADE_USB.items():
  route=configured[player]
  if (str(route.get('usb_port'))!=expected_port or
      route.get('by_path')!=expected_controller_by_path(expected_port)):
   raise RuntimeError('P1_P4_PROFILE_PORT_MISMATCH:'+player)
 runtime_by_path={}
 # sysfs + udev are the identity source. This also works when /dev is not
 # mounted in a diagnostic namespace; event/js names remain informational.
 for node in Path('/sys/class/input').glob('event*'):
  try:
   props=_udev_properties(node)
  except Exception:
   continue
  if props.get('ID_VENDOR_ID','').lower()!=EXPECTED_ARCADE_DEVICE[0] or \
     props.get('ID_MODEL_ID','').lower()!=EXPECTED_ARCADE_DEVICE[1]:
   continue
  for link in props.get('DEVLINKS','').split():
   if '/by-path/' in link and link.endswith('-event-joystick'):
    runtime_by_path.setdefault(link,[]).append((node,props))
 expected_paths={expected_controller_by_path(port) for port in EXPECTED_ARCADE_USB.values()}
 if set(runtime_by_path)!=expected_paths:
  raise RuntimeError('P1_P4_UNEXPECTED_OR_MISSING_DRAGONRISE_PATH')
 result={}
 for player,expected_port in EXPECTED_ARCADE_USB.items():
  route=configured[player]
  expected_by_path=route.get('by_path')
  matches=runtime_by_path.get(expected_by_path,[])
  if len(matches)!=1:raise RuntimeError('P1_P4_STABLE_PATH_MISSING_OR_DUPLICATE:'+player)
  sysfs,props=matches[0]
  name=(sysfs/'device'/'name').read_text(encoding='utf-8',errors='replace').strip()
  phys=(sysfs/'device'/'phys').read_text(encoding='utf-8',errors='replace').strip() if (sysfs/'device'/'phys').exists() else ''
  uniq=(sysfs/'device'/'uniq').read_text(encoding='utf-8',errors='replace').strip() if (sysfs/'device'/'uniq').exists() else ''
  id_path=props.get('ID_PATH','')
  by_path=next((item for item in props.get('DEVLINKS','').split()
                if '/by-path/' in item),None)
  # ID_PATH's stable root port is the number after "usb-0:" (the interface
  # suffix follows the port); use the sysfs/phys port as a second check.
  port_match=re.search(r'usb-0:([0-9]+)(?::|$)',id_path)
  physical_port=port_match.group(1) if port_match else None
  if (id_path!=expected_controller_id_path(expected_port) or by_path!=expected_by_path or
      props.get('ID_VENDOR_ID','').lower()!=EXPECTED_ARCADE_DEVICE[0] or
      props.get('ID_MODEL_ID','').lower()!=EXPECTED_ARCADE_DEVICE[1] or
      'dragonrise' not in name.lower()):
   raise RuntimeError('P1_P4_PROFILE_PORT_MISMATCH:'+player)
  result[player]={
   'expected_usb_port':expected_port,
   'usb_port':physical_port,
   'physical_path':id_path,
   'by_path':by_path,
   'device_identity':{'vendor_id':props.get('ID_VENDOR_ID','').lower(),
                      'product_id':props.get('ID_MODEL_ID','').lower(),
                      'name':name},
   'event':props.get('DEVNAME'),
   'js':_js_for_id_path(id_path),
   'devpath':props.get('DEVPATH'),
   'phys':phys,
   'uniq':uniq or None,
  }
 return result

def stable_profile_matches(state):
 if not isinstance(state,dict) or set(state)!=set(EXPECTED_ARCADE_USB):return False
 seen=set()
 for player,expected_port in EXPECTED_ARCADE_USB.items():
  item=state.get(player)
  if not isinstance(item,dict):return False
  path=item.get('physical_path');by_path=item.get('by_path')
  identity=item.get('device_identity') or {}
  expected_path=expected_controller_id_path(expected_port)
  expected_link=expected_controller_by_path(expected_port)
  if (item.get('expected_usb_port')!=expected_port or item.get('usb_port')!=expected_port or
      path!=expected_path or by_path!=expected_link or path in seen or
      identity.get('vendor_id','').lower()!=EXPECTED_ARCADE_DEVICE[0] or
      identity.get('product_id','').lower()!=EXPECTED_ARCADE_DEVICE[1] or
      'dragonrise' not in identity.get('name','').lower()):
   return False
  seen.add(path)
 return True
def expected_global_core():
 d=ad.parse_defaults();return d.get('mame',{}).get('core')
def safety_baseline():
 wait_for_es_idle()
 if not sr.es_pids():raise RuntimeError('EMULATIONSTATION_NOT_ACTIVE')
 p1=profile_state()
 if not stable_profile_matches(p1):raise RuntimeError('P1_P4_MAPPING_CHANGE')
 audio=get_default_sink()
 if audio!=HDMI:raise RuntimeError('AUDIO_GLOBAL_FAILURE:'+str(audio))
 return {'batocera_conf_sha256':conf_sha(),'global_mame_core':expected_global_core(),'p1_p4':p1,'audio_default':audio,
         'dispatcher_sha256':hashlib.sha256(DISP.read_bytes()).hexdigest(),'profile_sha256':hashlib.sha256(PROFILE.read_bytes()).hexdigest(),
         'multiplayer_sha256':hashlib.sha256(MULTI.read_bytes()).hexdigest()}
def processes_by_pid(before):return [x for x in pids() if x['pid'] not in before]
def game_health_max():
 try:
  with sqlite3.connect('file:/userdata/system/state/game_health.sqlite?mode=ro',uri=True,timeout=3) as c:return c.execute('select coalesce(max(id),0) from launch_events').fetchone()[0]
 except Exception:return 0
def health_for(system,rom,after):
 try:
  with sqlite3.connect('file:/userdata/system/state/game_health.sqlite?mode=ro',uri=True,timeout=3) as c:
   c.row_factory=sqlite3.Row;r=c.execute('select * from launch_events where system=? and rom=? and id>? order by id desc limit 1',(system,str(rom),after)).fetchone()
   return dict(r) if r else None
 except Exception:return None
def read_new_selector_log(offset):
 p=LOGS[0]
 try:
  st=p.stat();start=offset['size'] if isinstance(offset,dict) and st.st_ino==offset['inode'] and st.st_size>=offset['size'] else 0
  if not isinstance(offset,dict):start=offset if st.st_size>=offset else 0
  return p.read_bytes()[start:].decode('utf-8','replace')
 except Exception:return ''
def selector_log_offset():
 try:
  st=LOGS[0].stat();return {'size':st.st_size,'inode':st.st_ino}
 except OSError:return {'size':0,'inode':None}
def dispatcher_log_identity(s,rom):
 for line in s.splitlines():
  try:j=json.loads(line)
  except Exception:continue
  if j.get('event') in ('boot_audit_auto_choice','launch') and j.get('system')==s and j.get('rom')==rom:
   return {'event':j.get('event'),'system':j.get('system'),'rom':j.get('rom'),'choice':j.get('choice'),'one_shot_consumed':j.get('one_shot_consumed')}
 return None
def selector_identity(logtext,system,rom):
 for line in logtext.splitlines():
  try:j=json.loads(line)
  except Exception:continue
  if j.get('system')==system and j.get('rom')==rom:
   if j.get('event')=='boot_audit_auto_choice' and j.get('one_shot_consumed') is True:return {'choice':j.get('choice'),'marker_consumed':True,'event':j.get('event')}
   if j.get('event')=='launch':return {'rom':j.get('rom'),'system':j.get('system'),'event':j.get('event')}
 return None
def core_from_argv(argv):
 m=re.search(r'(?:^|\s)-L\s+([^\s]+)',argv)
 return m.group(1) if m else None
def identify_process(system,rom,adapter,core,rows):
 for proc in rows:
  if proc['exe']=='retroarch' or proc['comm']=='retroarch':
   loaded=core_from_argv(proc['argv']);stem=Path(rom).stem
   cmd=Path('/var/run/cmdfiles')/(stem+'.cmd')
   content_ok=False;content_method=None
   if cmd.is_file():
    try:
     txt=cmd.read_text(errors='replace')
     content_ok=bool(re.search(r'(^|[/\\\s])'+re.escape(stem)+r'(?:\.zip)?(?:\s|$)',txt,re.I)) or stem.lower() in txt.lower().splitlines()[0:1]
     content_method=str(cmd)
    except Exception:pass
   if not content_ok and str(rom) in proc['argv']:content_ok=True;content_method='retroarch argv content path'
   if adapter in ('MAME_CURRENT','MAME078PLUS','FBNEO') and cmd.is_file():
    content_ok=stem.lower() in cmd.read_text(errors='replace').lower();content_method=str(cmd)
   expected='/usr/lib/libretro/'+core+'_libretro.so'
   core_ok=loaded==expected
   if adapter=='MAME_CURRENT':core_ok=loaded=='/usr/lib/libretro/mame_libretro.so'
   if adapter=='MAME078PLUS':core_ok=loaded=='/usr/lib/libretro/mame078plus_libretro.so'
   if adapter=='FBNEO':core_ok=loaded=='/usr/lib/libretro/fbneo_libretro.so'
   return {'pid':proc['pid'],'argv':proc['argv'],'core_loaded':loaded,'core_expected':expected,'core_ok':core_ok,
           'content_ok':content_ok,'content_method':content_method}
  # Generic standalone adapters stay pending until a validated adapter is registered.
 return None
def screenshot_sample():
 # Capture one grayscale frame to a pipe only; no screenshot/media is persisted.
 try:
  display=os.environ.get('DISPLAY') or ':0';env={**os.environ,'DISPLAY':display}
  q=subprocess.run(['xrandr'],capture_output=True,text=True,timeout=3,env=env)
  m=re.search(r'^(.+ connected primary) (\d+x\d+)\+(\d+)\+(\d+)',q.stdout,re.M)
  if not m:return {'status':'UNKNOWN','reason':'PRIMARY_DISPLAY_NOT_FOUND'}
  geometry=m.group(2);x=m.group(3);y=m.group(4)
  cmd=['ffmpeg','-v','error','-f','x11grab','-video_size',geometry,'-i',f'{display}+{x},{y}','-frames:v','1','-f','rawvideo','-pix_fmt','gray','-']
  p=subprocess.run(cmd,capture_output=True,timeout=8,env=env)
  if p.returncode or not p.stdout:return {'status':'UNKNOWN','reason':'FRAME_CAPTURE_FAILED'}
  b=p.stdout;black=sum(1 for v in b if v<=8)/len(b);avg=sum(b)/len(b)
  return {'status':'BLACK_SCREEN_SUSPECT' if black>0.995 else 'VISUAL_ACTIVITY','frame_sha256':hashlib.sha256(b).hexdigest(),
          'black_pixel_ratio':round(black,5),'mean_luma':round(avg,3),'bytes':len(b)}
 except Exception as e:return {'status':'UNKNOWN','reason':type(e).__name__}
def launch_one(game,adapter_info,baseline,mode):
 system=game['system'];rom=Path(game['rom']);core=adapter_info['core'];adapter=adapter_info['adapter']
 result={'system':system,'rom':str(rom),'name':game.get('name'),'adapter':adapter,'core':core,'mode':mode,'started_at':stamp(),
         'test_id':None,'precheck':None,'identity':None,'audio':{},'process':{},'visual':[],'exit':{},'restore':{},'result':None,'failure_class':None}
 proc=None;marker=None
 pre=ad.preflight(system,rom,adapter,core)
 result['precheck']=pre
 if pre['status']!='PASS':
  result['result']='STATIC_FAIL' if pre['status']=='STATIC_FAIL' else 'ADAPTER_NOT_READY';result['failure_class']=pre.get('reason')
  result['restore']={'status':'NOT_REQUIRED_NO_WRITE'};return result
 scope=ad.restore_scope(system,adapter,rom);result['restore_scope']=scope
 if scope['status']!='READY':result['result']='ADAPTER_NOT_READY';result['failure_class']=scope['reason'];result['restore']={'status':'NOT_REQUIRED_NO_WRITE'};return result
 # Per-game scope and all global safety invariants are rechecked immediately before transaction.
 live=safety_baseline();result['safety_before']=live
 if live!=baseline:raise RuntimeError('SYSTEM_SAFETY_BASELINE_DRIFT')
 before_pids={x['pid'] for x in pids()};health_id=game_health_max();log_offset=selector_log_offset();starttime=time.monotonic()
 try:txid=tx.begin(scope['paths'],'full-certifier:'+system+':'+rom.name)
 except Exception as e:result['result']='ADAPTER_NOT_READY';result['failure_class']='TRANSACTION_BEGIN:'+type(e).__name__+': '+str(e);result['restore']={'status':'NOT_REQUIRED_NO_WRITE'};return result
 result['test_id']=txid;result['transaction_id']=txid;txroot=Path('/userdata/system/state/arcade_audit/runtime')/txid
 try:
  # Marker is the existing one-shot controller choice, not synthetic game input.
  marker=create_owned_marker(system,str(rom),'full_game_certifier',txid,path=sr.MARKER)
  result['selector_present']='controller_dispatcher' in ad.parse_es().get(system,{}).get('command','')
  result['control_selected']='BOTONERA';result['control_recommended']=game.get('recommended_control','UNKNOWN')
  req=urllib.request.Request(API+'/launch',data=str(rom).encode('utf-8'),method='POST',headers={'Content-Type':'application/x-www-form-urlencoded'})
  try:
   with urllib.request.urlopen(req,timeout=8) as r:result['http']={'status':r.status,'body':r.read().decode('utf-8','replace')}
  except Exception as e:result['http']={'status':None,'error':type(e).__name__};result['result']='ENGINE_FAIL';result['failure_class']='ES_API_LAUNCH_FAILED';return result
  if result['http']['status']!=200:result['result']='ENGINE_FAIL';result['failure_class']='ES_API_LAUNCH_HTTP';return result
  result['start_time']=stamp();launch_deadline=time.monotonic()+40;wrong=None;running_seen=False
  while time.monotonic()<launch_deadline:
   idle,rg=api_state()
   if rg is not None:
    running_seen=True
    actual=rg.get('path') if isinstance(rg,dict) else None
    if actual!=str(rom):wrong={'requested':str(rom),'es_running_game':actual,'raw':rg};break
   new=processes_by_pid(before_pids);logtxt=read_new_selector_log(log_offset)
   identity=selector_identity(logtxt,system,str(rom))
   for p in new:
    if p['exe']=='retroarch' or p['comm']=='retroarch':
     proc=identify_process(system,str(rom),adapter,core,[p]);break
   if proc:break
   if idle and rg is None and time.monotonic()-starttime>3:
    # ES returned idle without emulator process. This is a game failure only if dispatch identity was correct.
    if identity and identity.get('rom')==str(rom):break
    time.sleep(.2);continue
   time.sleep(.1)
  if wrong:
   result['result']='WRONG_GAME_DISPATCH';result['failure_class']='WRONG_GAME_DISPATCH';result['identity']={'es':wrong}
   for p in processes_by_pid(before_pids):
    if p['exe']=='retroarch' or p['comm']=='retroarch':proc={'pid':p['pid'],'argv':p['argv']};break
   return result
  logtxt=read_new_selector_log(log_offset);sel=selector_identity(logtxt,system,str(rom));result['selector_event']=sel
  if not sel or not sel.get('marker_consumed',False):
   result['result']='ENGINE_FAIL';result['failure_class']='SELECTOR_MARKER_OR_IDENTITY_NOT_PROVEN';return result
  if proc is None:
   result['result']='GAME_FAIL';result['failure_class']='IMMEDIATE_EXIT_OR_NO_EMULATOR_PROCESS';result['identity']={'es_running_game_seen':running_seen,'selector_event':sel};return result
  result['process']={'pid':proc['pid'],'argv':proc['argv'],'core':proc['core_loaded'],'core_ok':proc['core_ok'],'content_ok':proc['content_ok'],
                     'content_method':proc['content_method'],'started_at':stamp()}
  result['identity']={'requested_rom':str(rom),'es_running_game':str(rom),'dispatcher_event':sel,'core_ok':proc['core_ok'],'content_ok':proc['content_ok']}
  if not proc['core_ok'] or not proc['content_ok']:
   result['result']='ENGINE_FAIL';result['failure_class']='CORE_OR_CONTENT_IDENTITY_MISMATCH';return result
  duration=DURATIONS.get(system,20);process_started=time.monotonic();end=process_started+duration;sample_points=[x for x in (5,15,30,45,60) if x<duration];samples=[];audio_seen=[];next_sample=0
  while time.monotonic()<end:
   running=pids();gameproc=next((x for x in running if x['pid']==proc['pid']),None)
   idle,rg=api_state()
   if rg is not None and isinstance(rg,dict) and rg.get('path')!=str(rom):
    result['result']='WRONG_GAME_DISPATCH';result['failure_class']='WRONG_GAME_DISPATCH_DURING_RUN';result['identity']['es_running_game_during']=rg.get('path');break
   if not gameproc:
    result['result']='GAME_FAIL';result['failure_class']='UNEXPECTED_PROCESS_EXIT';break
   sink=get_default_sink();audio_seen.append(sink)
   if sink!=HDMI:
    result['result']='AUDIO_ROUTE_CHANGED';result['failure_class']='AUDIO_ROUTE_CHANGED';result['audio']['changed_to']=sink;break
   elapsed=time.monotonic()-process_started
   if next_sample<len(sample_points) and elapsed>=sample_points[next_sample]:
    sample=screenshot_sample();sample['elapsed']=round(elapsed,2);samples.append(sample);next_sample+=1
   time.sleep(.25)
  result['process']['stable_seconds']=round(time.monotonic()-process_started,3);result['process']['launch_to_process_seconds']=round(process_started-starttime,3);result['visual']=samples
  result['audio']={'default_before':baseline['audio_default'],'unique_during':sorted(set(audio_seen)),'default_during':'HDMI_PASS' if audio_seen and all(x==HDMI for x in audio_seen) else 'UNKNOWN'}
  # The certifier closes only the exact PID it launched; no broad process-name kill.
  if proc and any(x['pid']==proc['pid'] for x in pids()):
   try:os.kill(proc['pid'],signal.SIGTERM);result['exit']['close_signal']='SIGTERM_EXACT_PID'
   except ProcessLookupError:result['exit']['cleanup_race']='PROCESS_ALREADY_EXITED'
   for _ in range(120):
    if not any(x['pid']==proc['pid'] for x in pids()):break
    time.sleep(.1)
  if any(x['pid']==proc['pid'] for x in pids()):
   result['result']='ENGINE_FAIL';result['failure_class']='UNRECOVERED_EMULATOR_ORPHAN';return result
  for _ in range(120):
   try:idle,rg=api_state()
   except Exception:idle,rg=False,{'api':'unavailable'}
   if idle and rg is None:break
   time.sleep(.1)
  else:result['result']='ENGINE_FAIL';result['failure_class']='ES_RETURN_TIMEOUT';return result
  # Confirm one-shot choice and game-health row after clean exit.
  logtxt=read_new_selector_log(log_offset);sel=selector_identity(logtxt,system,str(rom));result['selector_event']=sel
  health=None
  for _ in range(30):
   health=health_for(system,str(rom),health_id)
   if health:break
   time.sleep(.2)
  result['exit']['game_health']=health
  result['exit']['code']=health.get('exit_code') if health else None
  result['exit']['duration_seconds']=health.get('duration_seconds') if health else None
  result['exit']['clean_es_return']=True
  result['exit']['cleanup_race']='CLEANUP_RACE' if health and 'ProcessLookupError' in str(health.get('relevant_error')) and health.get('exit_code')==0 else None
  result['audio']['default_after']=get_default_sink()
  if result['audio']['default_after']!=HDMI:
   result['result']='AUDIO_ROUTE_CHANGED';result['failure_class']='AUDIO_ROUTE_CHANGED_AFTER_EXIT'
  # Seal and restore exact pre-state, then verify global invariants.
  tx.seal(txid);tx.restore(txid)
  manifest=json.loads((tx.RUNTIME/txid/'manifest.json').read_text())
  if manifest.get('status')!='RESTORE_VERIFIED':raise RuntimeError('RESTORE_MANIFEST_NOT_VERIFIED')
  result['restore']={'status':'RESTORE_VERIFIED','transaction_id':txid,'paths':len(manifest.get('entries',[]))}
  prune_verified_snapshots(txid)
  after=safety_baseline();result['safety_after']=after
  if after.get('batocera_conf_sha256')!=baseline.get('batocera_conf_sha256'):
   result['result']='ENGINE_FAIL';result['failure_class']='BATOCERA_CONF_MISMATCH'
  elif after.get('p1_p4')!=baseline.get('p1_p4') or after.get('dispatcher_sha256')!=baseline.get('dispatcher_sha256') or after.get('profile_sha256')!=baseline.get('profile_sha256') or after.get('multiplayer_sha256')!=baseline.get('multiplayer_sha256'):
   result['result']='ENGINE_FAIL';result['failure_class']='CONTROLLER_MAPPING_OR_LAUNCH_CONFIG_CHANGED'
  elif after.get('audio_default')!=HDMI:
   result['result']='AUDIO_ROUTE_CHANGED';result['failure_class']='AUDIO_ROUTE_CHANGED_AFTER_RESTORE'
  elif pids() or sr.MARKER.exists():
   result['result']='ENGINE_FAIL';result['failure_class']='POST_TEST_ORPHAN_OR_MARKER'
  elif result.get('result') in ('WRONG_GAME_DISPATCH','AUDIO_ROUTE_CHANGED','ENGINE_FAIL','GAME_FAIL'):
   pass
  elif result['process']['stable_seconds']<duration or not health or health.get('exit_code') not in (0,'0') or not samples or all(x['status']=='BLACK_SCREEN_SUSPECT' for x in samples):
   result['result']='GAME_FAIL';result['failure_class']='RUNTIME_HEALTH_OR_VISUAL_CHECK_FAILED'
  else:
   frames=[x.get('frame_sha256') for x in samples if x.get('frame_sha256')]
   result['visual_summary']='STATIC_SCREEN_SUSPECT' if len(frames)>1 and len(set(frames))==1 else 'VISUAL_ACTIVITY' if frames else 'UNKNOWN'
   result['result']='AUTO_PASS';result['failure_class']=None
  return result
 except FileExistsError:
  result['result']='ENGINE_FAIL';result['failure_class']='MARKER_ALREADY_EXISTS'
  return result
 except Exception as e:
  if str(e) in SAFETY_GATE_FAILURES:
   result['result']='SYSTEM_SAFETY_FAILURE';result['failure_class']=str(e)
  else:
   result['result']='ENGINE_FAIL';result['failure_class']='CERTIFIER_EXCEPTION:'+type(e).__name__+': '+str(e)
  return result
 finally:
  # If an engine-side exception happened after launch, close only the exact PID observed by this transaction.
  try:
   if proc and any(x['pid']==proc['pid'] for x in pids()):
    os.kill(proc['pid'],signal.SIGTERM)
    for _ in range(100):
     if not any(x['pid']==proc['pid'] for x in pids()):break
     time.sleep(.1)
  except ProcessLookupError:pass
  except Exception:pass
  # On all paths, remove only this transaction's marker if it is still ours.
  try:
   if result.get('transaction_id'):
    remove_owned_marker(result['transaction_id'],owner='full_game_certifier',
                        audit_id=marker.get('audit_id') if isinstance(marker,dict) else None,path=sr.MARKER)
  except Exception:pass
  # Restore if a transaction reached POST_STATE; refuse to overwrite any concurrent edit.
  if result.get('transaction_id'):
   try:
    manifest=json.loads((tx.RUNTIME/result['transaction_id']/'manifest.json').read_text())
    if manifest.get('status')=='PRE_STATE':
     tx.seal(result['transaction_id']);tx.restore(result['transaction_id'])
    elif manifest.get('status')=='POST_STATE':tx.restore(result['transaction_id'])
    manifest=json.loads((tx.RUNTIME/result['transaction_id']/'manifest.json').read_text())
    if manifest.get('status')!='RESTORE_VERIFIED':raise RuntimeError('RESTORE_MANIFEST_NOT_VERIFIED')
    result['restore']={'status':'RESTORE_VERIFIED','transaction_id':result['transaction_id'],'paths':len(manifest.get('entries',[]))}
    prune_verified_snapshots(result['transaction_id'])
   except Exception as e:
    detail=type(e).__name__+': '+str(e)
    marker_conflict=str(e).startswith('FOREIGN_STATE_CONFLICT:')
    result['restore']={'status':'FOREIGN_STATE_CONFLICT' if marker_conflict else 'RESTORE_FAILURE','detail':detail}
    if result.get('failure_class')!='MARKER_ALREADY_EXISTS':
     result['result']='ENGINE_FAIL';result['failure_class']='FOREIGN_STATE_CONFLICT' if marker_conflict else 'RESTORE_FAILURE'
   if result.get('restore',{}).get('status')=='RESTORE_VERIFIED':
    try:
     after=None
     for _ in range(120):
      try:after=safety_baseline();break
      except RuntimeError as e:
       if str(e)!='ES_NOT_IDLE':raise
       time.sleep(.1)
     if after is None:raise RuntimeError('ES_RETURN_TIMEOUT_AFTER_RESTORE')
     result['safety_after_finally']=after
     if after!=baseline:raise RuntimeError('GLOBAL_SAFETY_BASELINE_CHANGED')
    except Exception as e:
     if str(e) in SAFETY_GATE_FAILURES:
      result['result']='SYSTEM_SAFETY_FAILURE';result['failure_class']=str(e)
     else:
      result['result']='ENGINE_FAIL';result['failure_class']='POST_RESTORE_SAFETY_GATE:'+type(e).__name__+': '+str(e)
  result['finished_at']=stamp()
  try:atomic_json(tx.RUNTIME/result['transaction_id']/'result.json',result)
  except Exception:pass

def update_csv(game,result):
 rows,fields=load_rows(); found=None
 for row in rows:
  if row.get('system')==game['system'] and row.get('rom')==game['rom']:found=row;break
 if not found:return False
 mapping={'AUTO_PASS':('AUTO_CERTIFIED','AUTO_CERTIFIED'),'GAME_FAIL':('NEEDS_REPAIR','GAME_FAIL'),
  'STATIC_FAIL':('NEEDS_REPAIR','STATIC_FAIL'),'FLAKY':('FLAKY','FLAKY'),
  'ADAPTER_NOT_READY':('NOT_TESTED','ADAPTER_NOT_READY'),'ENGINE_FAIL':('NOT_TESTED','ENGINE_FAIL'),
  'WRONG_GAME_DISPATCH':('NOT_TESTED','ENGINE_FAIL'),'AUDIO_ROUTE_CHANGED':('NOT_TESTED','ENGINE_FAIL'),
  'RESTORE_FAILURE':('NOT_TESTED','ENGINE_FAIL')}
 life,auto=mapping.get(result.get('result'),('NOT_TESTED','NOT_TESTED'))
 found['lifecycle_state']=life;found['auto_certification']=auto;found['adapter']=result.get('adapter','')
 found['test_result']=result.get('result','');found['test_id']=result.get('transaction_id','')
 identity=result.get('identity') or {}
 found['identity_status']='PASS' if identity.get('core_ok') and identity.get('content_ok') else result.get('failure_class','UNKNOWN')
 found['audio_status']=result.get('audio',{}).get('default_during','NOT_TESTED')
 found['restore_status']=result.get('restore',{}).get('status','NOT_RUN');found['exit_status']=str(result.get('exit',{}).get('code') or '')
 found['visual_status']=result.get('visual_summary') or (result.get('visual') or [{}])[-1].get('status','UNKNOWN')
 found['selected_control_mode']=result.get('control_selected','NOT_TESTED');found['runtime_seconds']=str(result.get('process',{}).get('stable_seconds',''))
 found['tested_at']=result.get('finished_at','');found['health_id']=str((result.get('exit',{}).get('game_health') or {}).get('id',''))
 found['failure_class']=result.get('failure_class') or '';found['input_software_status']='NOT_TESTED'
 if result.get('result')=='AUTO_PASS':found['boot_status']='AUTO_PASS';found['audio_certification']='HDMI_PASS';found['exit_certification']='PASS';found['guest_ready']='NO'
 elif result.get('result') in ('GAME_FAIL','STATIC_FAIL'):found['boot_status']=result.get('failure_class','GAME_FAIL');found['guest_ready']='NO'
 write_rows(rows,fields);return True

def checkpoint_update(cp,**kw):cp.update(kw);cp['updated_at']=utc();atomic_json(STATE,cp)
def systems_export():
 systems=ad.live_systems();SYSTEMS_CSV.parent.mkdir(parents=True,exist_ok=True)
 fields=['system','rom_count','configured_emulator','configured_core','launcher_type','adapter','adapter_status']
 from io import StringIO
 b=StringIO(newline='');w=csv.DictWriter(b,fieldnames=fields,lineterminator='\n');w.writeheader()
 for x in systems:w.writerow({k:x.get(k,'') for k in fields})
 atomic_bytes(SYSTEMS_CSV,b.getvalue().encode())
 return systems
def pilot_games(rows,systems):
 lookup={(r['system'],Path(r['rom']).name):r for r in rows}; ready={s['system']:s for s in systems if s['adapter_status']=='READY'}
 chosen=[];skipped=[];seen_systems=set()
 for system,short in PILOT:
  game=lookup.get((system,short))
  info=ad.game_adapter(system,game['rom'],systems) if game else None
  if not game or not info or info['adapter_status']!='READY' or game.get('installed')!='YES' or not Path(game['rom']).is_file():
   skipped.append({'system':system,'shortname':short,'cause':'ADAPTER_OR_CONTENT_NOT_READY'});continue
  g=dict(game);g['adapter_info']=info
  pf=ad.preflight(system,g['rom'],info['adapter'],info['core'])
  scope=ad.restore_scope(system,info['adapter'],g['rom']) if pf['status']=='PASS' else {'status':'NOT_CHECKED'}
  if pf['status']!='PASS' or scope['status']!='READY':
   skipped.append({'system':system,'rom':g['rom'],'cause':pf.get('reason') if pf['status']!='PASS' else scope.get('reason')});continue
  chosen.append(g);seen_systems.add(system)
 # Missing content or a system without a safe adapter is replaced by another curated, ready sample.
 if len(chosen)<10:
  candidates=queue(rows,systems)
  # The pilot needs only a few cross-system replacements. Bound candidate reads
  # so a missing adapter/scope cannot turn pilot selection into a catalog scan.
  order=['pcengine','gb','gbc','atari2600','nds','c64','saturn','megadrive','snes','nes']
  for system in order:
   if len(chosen)>=10:break
   if system in seen_systems:continue
   attempts=0
   for game in candidates:
    if game['system']!=system or any(x['system']==game['system'] and x['rom']==game['rom'] for x in chosen):continue
    if str(game.get('name','')).startswith('ZZZ(notgame)'):continue
    attempts+=1
    pf=ad.preflight(game['system'],game['rom'],game['adapter_info']['adapter'],game['adapter_info']['core'])
    scope=ad.restore_scope(game['system'],game['adapter_info']['adapter'],game['rom']) if pf['status']=='PASS' else {'status':'NOT_CHECKED'}
    if pf['status']!='PASS' or scope['status']!='READY':
     skipped.append({'system':system,'rom':game['rom'],'cause':pf.get('reason') if pf['status']!='PASS' else scope.get('reason')})
     if attempts>=20:break
     continue
    chosen.append(game);seen_systems.add(system);break
 globals()['PILOT_PREFLIGHT_SKIPS']=skipped
 return chosen
def queue(rows,systems):
 ready={s['system']:s for s in systems if s['adapter_status']=='READY'}; candidates=[]
 sys_order={'mame':0,'fbneo':1,'neogeo':2,'psx':3,'snes':4,'nes':5,'megadrive':6,'gba':7,'n64':8,'mastersystem':9,'gb':10,'gbc':11}
 for r in rows:
  s=r['system']
  if s not in ready or r.get('installed')!='YES' or r.get('auto_certification') not in ('NOT_TESTED',''):
   continue
  if str(r.get('name','')).startswith('ZZZ(notgame)') or str(r.get('special_control','')).lower() in ('lightgun','wheel','special_control','trackball','spinner','paddle'):
   continue
  path=Path(r['rom'])
  if not path.is_file():continue
  try:play=int(r.get('playcount') or 0)
  except ValueError:play=0
  players=str(r.get('players_metadata') or '')
  multiplayer=0
  for n in PLAYER_WEIGHT:
   if re.search(r'\b'+n+r'\b',players):multiplayer=max(multiplayer,PLAYER_WEIGHT[n])
  priority=sys_order.get(s,50)
  # prioritize real use, meaningful multiplayer and known useful systems
  score=(priority,-min(play,20),-multiplayer,str(path).lower())
  g=dict(r);g['adapter_info']=ad.game_adapter(s,r['rom'],systems) or dict(ready[s]);candidates.append((score,g))
 candidates.sort(key=lambda x:x[0]);return [x[1] for x in candidates]

def certification_metrics(rows,cp):
 hist=cp.get('results',[]); latest={}
 for item in hist:latest[(item.get('system'),item.get('rom'))]=item
 csv_counts={k:sum(r.get('auto_certification')==v for r in rows) for k,v in {
  'auto_certified':'AUTO_CERTIFIED','game_fail':'GAME_FAIL','static_fail':'STATIC_FAIL','flaky':'FLAKY'}.items()}
 csv_counts['needs_repair']=sum(r.get('lifecycle_state')=='NEEDS_REPAIR' for r in rows)
 tx_count=sum(bool(x.get('transaction_id')) for x in hist)
 tx_unique=len({(x.get('system'),x.get('rom')) for x in hist if x.get('transaction_id')})
 return {'unique_games_processed':len({(x.get('system'),x.get('rom')) for x in hist}),
  'result_records':len(hist),'launch_transactions':tx_count,'retry_transactions':max(0,tx_count-tx_unique),
  'static_preflight_results':sum(x.get('result')=='STATIC_FAIL' for x in hist),
  'engine_fail_total_historical':sum(x.get('result')=='ENGINE_FAIL' for x in hist),
  'engine_fail_active':sum(x.get('result') in STOP_ENGINE for x in latest.values()),**csv_counts,
  'restores_verified':sum(bool(x.get('transaction_id')) and x.get('restore',{}).get('status')=='RESTORE_VERIFIED' for x in hist),
  'restore_failures':sum(x.get('restore',{}).get('status')=='RESTORE_FAILURE' for x in hist),
  'counts':{k:sum(x.get('result')==k for x in hist) for k in ('AUTO_PASS','GAME_FAIL','STATIC_FAIL','FLAKY','ADAPTER_NOT_READY','ENGINE_FAIL','WRONG_GAME_DISPATCH','AUDIO_ROUTE_CHANGED','RESTORE_FAILURE')}}

def next_cursor(rows,systems):
 q=queue(rows,systems)
 return ('%s:%s'%(q[0]['system'],q[0]['rom'])) if q else None

def reconciled_batch68_retry_matches(game,cp,csv_sha256):
 # A single non-terminal Doom safety record may remain in history after the
 # explicit Batch 68 recovery. Retry it only while every recovery-bound
 # identity and evidence digest still matches the unchanged checkpoint.
 recovery=cp.get('safety_recovery') or {};runtime=recovery.get('runtime_checks') or {}
 system=game.get('system');rom=game.get('rom')
 latest={}
 for item in cp.get('results',[]):latest[(item.get('system'),item.get('rom'))]=item
 incident=latest.get(('prboom','/userdata/roms/prboom/doom1_shareware.wad'),{})
 required=('operator_confirmed_normal_selector_cancel','two_consecutive_clean_runtime_observations',
  'es_idle','running_game_none','marker_absent','all_launch_and_emulator_processes_absent',
  'no_active_certifier','no_active_autopilot','no_partial_transaction','last_result_restore_verified',
  'manifest_restore_verified','restored_paths_match_pre_state','batch68_transactions_consistent',
  'previous_terminal_result_preserved','doom_csv_still_not_tested','cursor_matches_canonical_queue',
  'hdmi_pass','logical_p1_p4_stable_identity','protected_config_pass','result_evidence_unchanged',
  'batch_progress_unchanged','no_game_terminal_result_for_doom')
 results_sha=hashlib.sha256(json.dumps(cp.get('results',[]),ensure_ascii=False,sort_keys=True,
  separators=(',',':')).encode()).hexdigest()
 batch_sha=hashlib.sha256(json.dumps(cp.get('batch_in_progress'),ensure_ascii=False,sort_keys=True,
  separators=(',',':')).encode()).hexdigest()
 return bool(system=='prboom' and rom=='/userdata/roms/prboom/doom1_shareware.wad' and
  cp.get('status')=='STOPPED_SAFE' and cp.get('blocked_reason') is None and cp.get('engine_fail_active')==0 and
  cp.get('next_untested')=='prboom:/userdata/roms/prboom/doom1_shareware.wad' and
  recovery.get('previous_blocked_reason')=='ES_LAUNCH_PROCESS_ACTIVE' and
  recovery.get('recovery_reason')=='NORMAL_SELECTOR_CANCELLATION_AND_RUNTIME_CLEAN' and
  recovery.get('operator_confirmed_normal_selector_cancel') is True and
  recovery.get('previous_active_engine_fail_count')==1 and recovery.get('reconciled_engine_fail_active')==0 and
  recovery.get('transaction_id')=='20261119T143935_d7d3a63e70' and
  recovery.get('next_game')=='prboom:/userdata/roms/prboom/doom1_shareware.wad' and
  all(runtime.get(key) is True for key in required) and
  recovery.get('result_records_sha256')==results_sha and recovery.get('batch_progress_sha256')==batch_sha and
  recovery.get('csv_sha256')==csv_sha256 and incident.get('transaction_id')=='20261119T143935_d7d3a63e70' and
  incident.get('result')=='SYSTEM_SAFETY_FAILURE' and incident.get('failure_class')=='ES_LAUNCH_PROCESS_ACTIVE' and
  incident.get('restore',{}).get('status')=='RESTORE_VERIFIED' and
  incident.get('restore',{}).get('transaction_id')=='20261119T143935_d7d3a63e70')

def assert_reconciled_queue(rows,cp,systems,batch_size=None):
 metrics=certification_metrics(rows,cp)
 for key in ('auto_certified','game_fail','static_fail','flaky','needs_repair'):
  if cp.get(key)!=metrics[key]:raise RuntimeError('QUEUE_INVARIANT_FAIL: '+key)
 if cp.get('attempted_new')!=metrics['launch_transactions']:
  raise RuntimeError('QUEUE_INVARIANT_FAIL: attempted_new transaction semantics')
 if cp.get('counts')!=metrics['counts']:
  raise RuntimeError('QUEUE_INVARIANT_FAIL: result counts differ')
 for key in ('unique_games_processed','result_records','launch_transactions','retry_transactions'):
  if cp.get(key)!=metrics[key]:raise RuntimeError('QUEUE_INVARIANT_FAIL: '+key)
 expected=next_cursor(rows,systems)
 if cp.get('next_untested')!=expected:
  raise RuntimeError('QUEUE_INVARIANT_FAIL: cursor differs from deterministic queue')
 if expected:
  system,rom=expected.split(':',1)
  row=next((r for r in rows if r.get('system')==system and r.get('rom')==rom),None)
  if not row or row.get('installed')!='YES' or row.get('auto_certification') not in ('NOT_TESTED',''):
   raise RuntimeError('QUEUE_INVARIANT_FAIL: cursor is not an installed NOT_TESTED row')
 row_map={(r.get('system'),r.get('rom')):r for r in rows}
 if len(row_map)!=len(rows):raise RuntimeError('QUEUE_INVARIANT_FAIL: CSV identity collision')
 latest={}
 for item in cp.get('results',[]):latest[(item.get('system'),item.get('rom'))]=item
 if any(key not in row_map for key in latest):raise RuntimeError('QUEUE_INVARIANT_FAIL: result without CSV row')
 expected_status={'AUTO_PASS':'AUTO_CERTIFIED','GAME_FAIL':'GAME_FAIL','STATIC_FAIL':'STATIC_FAIL','FLAKY':'FLAKY'}
 for key,item in latest.items():
  wanted=expected_status.get(item.get('result'))
  if wanted and row_map[key].get('auto_certification')!=wanted:
   raise RuntimeError('QUEUE_INVARIANT_FAIL: latest result/CSV mismatch')
  if item.get('transaction_id') and row_map[key].get('test_id')!=item.get('transaction_id'):
   raise RuntimeError('QUEUE_INVARIANT_FAIL: latest transaction/CSV mismatch')
 if batch_size:
  selected=queue(rows,systems)[:batch_size]
  for game in selected:
   status=game.get('auto_certification') or 'NOT_TESTED'
   if status not in ('NOT_TESTED',''):
    raise RuntimeError('QUEUE_INVARIANT_FAIL: selected terminal game')
   has_prior_result=any(x.get('system')==game['system'] and x.get('rom')==game['rom'] for x in cp.get('results',[]))
   current_csv_sha=hashlib.sha256(TABLE.read_bytes()).hexdigest()
   if has_prior_result and not reconciled_batch68_retry_matches(game,cp,current_csv_sha):
    raise RuntimeError('QUEUE_INVARIANT_FAIL: selected game already has a result')
 return metrics

def run_tests(games,cp,mode):
 try:baseline=safety_baseline()
 except RuntimeError as e:
  cp['status']='PAUSED_SYSTEM_SAFETY_FAILURE';cp['blocked_reason']=str(e);checkpoint_update(cp);return False
 cp['baseline']=baseline;cp['mode']=mode
 started=stamp();before_results=len(cp.get('results',[]));batch_pass=batch_game=batch_static=batch_flaky=launched=restored=0;first=games[0]['rom'] if games else None;last=None
 batch_progress=cp.get('batch_in_progress') if mode in ('batch','resume') else None
 if mode in ('batch','resume') and not batch_progress:
  prior=(cp.get('latest_batch') or {}).get('name','priority_batch_0')
  number=int(prior.rsplit('_',1)[-1])+1 if prior.rsplit('_',1)[-1].isdigit() else 1
  batch_progress=new_batch_progress('priority_batch_'+str(number),len(games),first,started)
  cp['batch_in_progress']=batch_progress;checkpoint_update(cp)
 if batch_progress is not None:
  for key in ('adapter_pending','skipped','deferred','other_unlaunched','processed'):
   batch_progress.setdefault(key,0)
 for game in games:
  stop_file=os.environ.get('ARCADE_CERTIFIER_STOP_FILE')
  if stop_file and Path(stop_file).is_file():
   # This boundary is reached only after the previous transaction's restore
   # and global-baseline checks completed successfully.
   rows,_=load_rows();systems=ad.live_systems()
   cp['next_untested']=next_cursor(rows,systems);cp['current_test']=None;cp['next_game']=None
   cp['status']='STOPPED_SAFE';cp['blocked_reason']=None;cp['safe_stop_requested_at']=utc()
   checkpoint_update(cp);print('SAFE_STOP_AT_GAME_BOUNDARY',flush=True);return True
  label=game['system']+'/'+Path(game['rom']).name
  cp['current_test']=label;cp['next_game']=label;cp['status']='RUNNING';checkpoint_update(cp)
  try:result=launch_one(game,game['adapter_info'],baseline,mode)
  except RuntimeError as e:
   if str(e) in SAFETY_GATE_FAILURES:
    cp['status']='PAUSED_SYSTEM_SAFETY_FAILURE';cp['blocked_reason']=str(e);checkpoint_update(cp);return False
   raise
  # Keep structured, bounded evidence per test; no screenshots or raw full logs.
  RUNTIME.mkdir(parents=True,exist_ok=True,mode=0o700)
  if not update_csv(game,result):
   cp['status']='PAUSED_ENGINE_FAILURE';cp['blocked_reason']='CSV_UPDATE_FAILED';checkpoint_update(cp);return False
  hist=cp.setdefault('results',[]);hist.append({'system':result.get('system'),'rom':result.get('rom'),'name':result.get('name'),
      'adapter':result.get('adapter'),'result':result.get('result'),'failure_class':result.get('failure_class'),
      'transaction_id':result.get('transaction_id'),'stable_seconds':result.get('process',{}).get('stable_seconds'),
      'audio':result.get('audio'),'restore':result.get('restore'),'finished_at':result.get('finished_at')})
  rows,_=load_rows();metrics=certification_metrics(rows,cp)
  cp.update({k:metrics[k] for k in ('unique_games_processed','result_records','launch_transactions','retry_transactions','static_preflight_results','engine_fail_total_historical','engine_fail_active','auto_certified','game_fail','static_fail','flaky','needs_repair','restores_verified','restore_failures','counts')})
  cp['attempted_new']=metrics['launch_transactions'];cp['next_untested']=next_cursor(rows,ad.live_systems());cp['next_game']=None;cp['current_test']=None
  if batch_progress is not None:
   record_batch_result(batch_progress,result)
   cp['batch_in_progress']=batch_progress
  checkpoint_update(cp)
  launched+=bool(result.get('transaction_id'));restored+=result.get('restore',{}).get('status')=='RESTORE_VERIFIED';last=game['rom']
  batch_pass+=result.get('result')=='AUTO_PASS';batch_game+=result.get('result')=='GAME_FAIL';batch_static+=result.get('result')=='STATIC_FAIL';batch_flaky+=result.get('result')=='FLAKY'
  health=result.get('exit',{}).get('game_health') or {}
  health_summary={k:health.get(k) for k in ('id','system','rom','core','status','exit_code','duration_seconds') if k in health}
  health_summary['cleanup_race']=result.get('exit',{}).get('cleanup_race')
  print(json.dumps({'system':result.get('system'),'game':result.get('name'),'rom':Path(result.get('rom','')).name,
      'adapter':result.get('adapter'),'precheck':result.get('precheck',{}).get('status'),'identity':result.get('identity'),
      'audio':result.get('audio'),'process':result.get('process'),'visual':result.get('visual_summary') or result.get('visual'),
      'exit':health_summary,'restore':result.get('restore'),'result':result.get('result'),'cause':result.get('failure_class')},ensure_ascii=False),flush=True)
  if result.get('transaction_id') and result.get('restore',{}).get('status')!='RESTORE_VERIFIED':
   cp['status']='PAUSED_RESTORE_FAILURE';cp['blocked_reason']='RESTORE_FAILURE';checkpoint_update(cp);return False
  if result.get('result')=='SYSTEM_SAFETY_FAILURE':
   cp['status']='PAUSED_SYSTEM_SAFETY_FAILURE';cp['blocked_reason']=result.get('failure_class','SYSTEM_SAFETY_FAILURE');checkpoint_update(cp);return False
  if result.get('result') in STOP_ENGINE:
   # Recover only the HDMI default through the already installed, narrow helper.
   if result.get('result')=='AUDIO_ROUTE_CHANGED':
    subprocess.run(['/userdata/system/el_gordo_tools/arcade_audio_policy_service.sh','start'],capture_output=True,timeout=35)
    if get_default_sink()==HDMI:print('AUDIO_RECOVERED_HDMI; batch pause retained for gate review',flush=True)
   cp['status']='PAUSED_ENGINE_FAILURE';cp['blocked_reason']=result.get('failure_class');checkpoint_update(cp);return False
  # Every completed transaction must return to the exact global baseline.
  try:after=safety_baseline()
  except Exception as e:cp['status']='PAUSED_SYSTEM_SAFETY_FAILURE';cp['blocked_reason']=type(e).__name__+': '+str(e);checkpoint_update(cp);return False
  if after!=baseline:
   cp['status']='PAUSED_SYSTEM_SAFETY_FAILURE';cp['blocked_reason']='GLOBAL_BASELINE_CHANGED';checkpoint_update(cp);return False
 rows,_=load_rows();systems=ad.live_systems();metrics=certification_metrics(rows,cp)
 cp.update({k:metrics[k] for k in ('unique_games_processed','result_records','launch_transactions','retry_transactions','static_preflight_results','engine_fail_total_historical','engine_fail_active','auto_certified','game_fail','static_fail','flaky','needs_repair','restores_verified','restore_failures','counts')})
 cp['attempted_new']=metrics['launch_transactions'];cp['next_untested']=next_cursor(rows,systems);cp['next_game']=None;cp['current_test']=None;cp['status']='COMPLETE'
 if mode in ('batch','resume'):
  progress=cp.get('batch_in_progress') or batch_progress or {}
  name=progress.get('name','priority_batch_unknown')
  cp['latest_batch']={'name':name,'considered':progress.get('considered',len(games)),'launched':progress.get('launched',launched),
   'auto_pass':progress.get('auto_pass',batch_pass),'game_fail':progress.get('game_fail',batch_game),'static_fail':progress.get('static_fail',batch_static),'flaky':progress.get('flaky',batch_flaky),
   'restore_verified':f"{progress.get('restore_verified',restored)}/{progress.get('launched',launched)}",'restore_failures':progress.get('restore_failures',0),'engine_failures_unresolved':metrics['engine_fail_active'],
   'started_at':progress.get('started_at',started),'finished_at':stamp(),'first_game':progress.get('first_game',first),'last_game':progress.get('last_game',last),'next_game':cp['next_untested']}
  cp.pop('batch_in_progress',None)
  try:
   m=json.loads(MASTER.read_text());ph=m.get('phases',{}).get('PHASE_14_FULL_GAME_CERTIFICATION',{});ph['updated_at']=utc();ph['summary']=phase_summary(cp['latest_batch'],metrics['auto_certified'],cp['next_untested']);m['certification_counts']={**m.get('certification_counts',{}),'auto_certified':metrics['auto_certified'],'attempted_new':metrics['launch_transactions'],'unique_games_processed':metrics['unique_games_processed'],'result_records':metrics['result_records'],'launch_transactions':metrics['launch_transactions'],'retry_transactions':metrics['retry_transactions'],'static_fail':metrics['static_fail'],'game_fail':metrics['game_fail'],'flaky':metrics['flaky'],'needs_repair':metrics['needs_repair'],'control_certified':metrics['control_certified'] if 'control_certified' in metrics else sum(r.get('control_certification')=='CONTROL_CERTIFIED' for r in rows),'guest_ready':sum(r.get('guest_ready')=='YES' for r in rows),'total_restores':metrics['restores_verified'],'restore_failures':metrics['restore_failures'],'next_game':cp['next_untested'],'engine_failures_unresolved':metrics['engine_fail_active']};m['updated_at']=utc();atomic_json(MASTER,m)
  except Exception as e:
   cp['status']='PAUSED_ENGINE_FAILURE';cp['blocked_reason']='MASTER_CHECKPOINT_UPDATE_FAILED:'+type(e).__name__;checkpoint_update(cp);return False
 checkpoint_update(cp)
 if mode in ('batch','resume'):
  report_lines=[f"# Certificación prioritaria — {cp['latest_batch']['name']}",'',
   f"- Considerados: {cp['latest_batch']['considered']}",f"- Lanzados: {cp['latest_batch']['launched']}",
   f"- AUTO_PASS: {cp['latest_batch']['auto_pass']}",f"- GAME_FAIL: {cp['latest_batch']['game_fail']}",
   f"- STATIC_FAIL: {cp['latest_batch']['static_fail']}",f"- FLAKY: {cp['latest_batch']['flaky']}",
   f"- ENGINE_FAIL activos: {metrics['engine_fail_active']}",f"- Restores: {cp['latest_batch']['restore_verified']}",
   f"- Restore failures: {cp['latest_batch']['restore_failures']}",
   f"- Audio route changes: {sum(x.get('result')=='AUDIO_ROUTE_CHANGED' for x in cp['results'][before_results:])}",
   f"- Wrong dispatch: {sum(x.get('result')=='WRONG_GAME_DISPATCH' for x in cp['results'][before_results:])}",
   f"- NEXT_GAME: `{cp['next_untested'] or 'NONE'}`",'']
  batch_num=int(cp['latest_batch']['name'].rsplit('_',1)[-1])
  accounted=(cp['latest_batch']['launched']+cp['latest_batch']['static_fail']+
             progress.get('adapter_pending',0)+progress.get('skipped',0)+progress.get('deferred',0)+
             progress.get('other_unlaunched',0))
  unprocessed=max(0,cp['latest_batch']['considered']-accounted)
  cp['latest_batch'].update({'adapter_pending':progress.get('adapter_pending',0),'skipped':progress.get('skipped',0),
   'deferred':progress.get('deferred',0),'other_unlaunched':progress.get('other_unlaunched',0),
   'unprocessed':unprocessed,'accounted':accounted})
  checkpoint_update(cp)
  report_lines.extend([
   f"- Adapter pending: {progress.get('adapter_pending',0)}",
   f"- Skipped: {progress.get('skipped',0)}",
   f"- Deferred: {progress.get('deferred',0)}",
   f"- Other unlaunched: {progress.get('other_unlaunched',0)}",
   f"- Not yet processed: {unprocessed}",
   f"- Accounting: {cp['latest_batch']['considered']} = {cp['latest_batch']['launched']} launched + {cp['latest_batch']['static_fail']} static_fail + {progress.get('adapter_pending',0)} adapter_pending + {progress.get('skipped',0)} skipped + {progress.get('deferred',0)} deferred + {progress.get('other_unlaunched',0)} other_unlaunched + {unprocessed} not_yet_processed",
  ])
  atomic_bytes(AUDIT/f'reports/PRIORITY_CERTIFICATION_BATCH_{batch_num}.md','\n'.join(report_lines).encode())
  summary=subprocess.run([sys.executable,str(TOOLS/'rebuild_certification_summary.py')],capture_output=True,text=True,timeout=60)
  print(summary.stdout.strip(),flush=True)
  if summary.returncode or 'REPORT_RECONCILIATION_PASS' not in summary.stdout:
   cp['status']='PAUSED_REPORT_RECONCILIATION';cp['blocked_reason']='REPORT_RECONCILIATION_FAIL';checkpoint_update(cp);return False
  current=subprocess.run([sys.executable,str(TOOLS/'rebuild_arcade_current_state.py')],capture_output=True,text=True,timeout=60)
  print(current.stdout.strip(),flush=True)
  if current.returncode or 'CERTIFICATION_RECONCILIATION_PASS' not in current.stdout:
   cp['status']='PAUSED_REPORT_RECONCILIATION';cp['blocked_reason']='CURRENT_STATE_RECONCILIATION_FAIL';checkpoint_update(cp);return False
 return True

def main():
 p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=False)
 g.add_argument('--plan',action='store_true');g.add_argument('--single',nargs=2,metavar=('SYSTEM','ROM'));g.add_argument('--batch',type=int)
 p.add_argument('--resume',action='store_true');p.add_argument('--pilot',action='store_true')
 p.add_argument('--limit',type=int,default=20);a=p.parse_args()
 if a.pilot and (a.plan or a.single or a.batch is not None):p.error('--pilot cannot be combined with another mode')
 if a.resume and a.pilot and (a.plan or a.single or a.batch is not None):p.error('--resume --pilot cannot be combined with another mode')
 if a.resume and a.pilot is False and (a.plan or a.single or a.batch is not None):p.error('--resume cannot be combined with another mode')
 if not (a.plan or a.single or a.batch is not None or a.resume or a.pilot):p.error('select --plan, --single, --batch, --resume, or --pilot')
 if a.batch is not None and not 1<=a.batch<=100:raise SystemExit('--batch must be 1..100')
 rows,fields=load_rows();systems=systems_export();sys_by={x['system']:x for x in systems}
 if a.plan:
  q=queue(rows,systems);print(json.dumps({'systems_detected':len(systems),'games_in_certification_table':len(rows),
      'adapters':systems,'queue_total_ready':len(q),'next':[{k:x.get(k) for k in ('system','rom','name')} for x in q[:a.limit]],
      'runtime_launch':'NOT RUN'},ensure_ascii=False,indent=2));return 0
 if not autopilot_process_owned_by_current_run():
  print(json.dumps({'result':'REFUSED','reason':'AUTOPILOT_ALREADY_RUNNING_WITHOUT_OWNER_TOKEN'},ensure_ascii=False));return 3
 try:cp=json.loads(STATE.read_text(encoding='utf-8'))
 except Exception:cp={'schema_version':2,'updated_at':utc(),'results':[],'counts':{},'status':'READY'}
 if not (a.plan or a.single or a.pilot):
  try:assert_reconciled_queue(rows,cp,systems)
  except Exception as e:
   print('QUEUE_INVARIANT_FAIL');print(type(e).__name__+': '+str(e));return 6
 if cp.get('status','').startswith('PAUSED_') and not a.resume:
  print(json.dumps({'result':'PAUSED','reason':cp.get('blocked_reason'),'hint':'inspect issue and use --resume only after recovery'},ensure_ascii=False));return 3
 if a.single:
  system,short=a.single;game=next((dict(r) for r in rows if r['system']==system and (Path(r['rom']).name==Path(short).name or r['rom']==short)),None)
  if not game:print('NO_MATCH');return 2
  info=ad.game_adapter(system,game['rom'],systems)
  if not info or info['adapter_status']!='READY':print(json.dumps({'result':'ADAPTER_NOT_READY','system':system,'details':info}));return 4
  game['adapter_info']=dict(info);games=[game];mode='single'
 elif a.pilot and a.resume:
  if cp.get('mode')!='pilot' or cp.get('status')!='PAUSED_ENGINE_FAILURE' or cp.get('blocked_reason')!='CORE_OR_CONTENT_IDENTITY_MISMATCH':
   print(json.dumps({'result':'PILOT_RESUME_NOT_SAFE','status':cp.get('status'),'reason':cp.get('blocked_reason')},ensure_ascii=False));return 3
  roster_path=AUDIT/'certifier_pilot_roster.json'
  try:roster=json.loads(roster_path.read_text(encoding='utf-8'))
  except Exception as e:print(json.dumps({'result':'PILOT_ROSTER_UNAVAILABLE','error':type(e).__name__}));return 3
  passed={(x.get('system'),x.get('rom')) for x in cp.get('results',[]) if x.get('result')=='AUTO_PASS'}
  games=[]
  for item in roster.get('games',[]):
   key=(item.get('system'),item.get('rom'))
   if key in passed:continue
   row=next((dict(r) for r in rows if r.get('system')==key[0] and r.get('rom')==key[1]),None)
   info=ad.game_adapter(key[0],key[1],systems) if row else None
   if not row or not info or info.get('adapter_status')!='READY':
    print(json.dumps({'result':'PILOT_RESUME_ADAPTER_NOT_READY','system':key[0],'rom':key[1],'adapter':info},ensure_ascii=False));return 4
   row['adapter_info']=info;games.append(row)
  if not games:print(json.dumps({'result':'PILOT_ALREADY_COMPLETE'}));return 0
  roster['resumed_at']=utc();roster['adapter_reconciliation']={'system':'pcengine','configured_core':next((g['adapter_info']['configured_core'] for g in games if g['system']=='pcengine'),None),'reason':'ES effective default core takes precedence over configgen fallback'}
  atomic_json(roster_path,roster)
  cp['blocked_reason']=None;cp['resume_reason']='CORE_IDENTITY_EXPECTATION_CORRECTED';mode='pilot'
 elif a.pilot:
  games=pilot_games(rows,systems);mode='pilot'
  if len(games)<10:print(json.dumps({'result':'PILOT_CANDIDATES_INSUFFICIENT','selected':[(x['system'],x['rom']) for x in games],'required':10},ensure_ascii=False));return 4
 elif a.resume:
  if cp.get('blocked_reason'):print(json.dumps({'result':'RESUME_BLOCKED','reason':cp['blocked_reason']},ensure_ascii=False));return 3
  q=queue(rows,systems);games=q[:a.limit];mode='resume'
 elif a.batch is not None:
  q=queue(rows,systems)
  if not q or f"{q[0]['system']}:{q[0]['rom']}"!=cp.get('next_untested'):
   print('QUEUE_INVARIANT_FAIL: NEXT_GAME does not match first eligible queue entry');return 6
  games=q[:a.batch];mode='batch'
 if not games:print('NO_READY_GAMES');return 4
 if mode in ('batch','resume'):
  try:assert_reconciled_queue(rows,cp,systems,len(games))
  except Exception as e:
   print('QUEUE_INVARIANT_FAIL');print(type(e).__name__+': '+str(e));return 6
 # Bind pilot roster before launching so a restart cannot silently replace games.
 if mode=='pilot' and not a.resume:
  roster={'created_at':utc(),'prefilter_skips':globals().get('PILOT_PREFLIGHT_SKIPS',[]),
    'games':[{'system':x['system'],'rom':x['rom'],'adapter':x['adapter_info']['adapter'],'core':x['adapter_info']['configured_core']} for x in games]}
  atomic_json(AUDIT/'certifier_pilot_roster.json',roster)
 try:acquire_certifier_lock()
 except RuntimeError as e:
  print(json.dumps({'result':'REFUSED','reason':str(e)},ensure_ascii=False));return 3
 cp.setdefault('results',[]);cp['status']='RUNNING';cp['mode']=mode;set_invocation_selection(cp,len(games));checkpoint_update(cp)
 ok=run_tests(games,cp,mode)
 print(json.dumps({'batch_status':cp.get('status'),'mode':mode,'selected':len(games),'counts':cp.get('counts',{}),
                   'next_game':cp.get('next_game'),'engine_ok':ok},ensure_ascii=False,indent=2))
 return 0 if ok else 5
if __name__=='__main__':raise SystemExit(main())
