#!/usr/bin/env python3
"""Universal, resumable Batocera game certifier; launches only READY adapters."""
import argparse,csv,hashlib,json,os,re,signal,sqlite3,subprocess,sys,time,urllib.request,shutil
from datetime import datetime,timezone
from pathlib import Path

TOOLS=Path('/userdata/system/el_gordo_tools'); AUDIT=Path('/userdata/system/state/arcade_audit')
# Explicit precedence: current transactional engine, active audit helpers, then historical scripts.
sys.path.insert(0,str(AUDIT/'scripts'));sys.path.insert(0,str(AUDIT));sys.path.insert(0,str(TOOLS))
import certification_transaction as tx
import certifier_adapters as ad
import smoke_runner as sr

TABLE=AUDIT/'full_game_certification.csv'; MASTER=AUDIT/'arcade_master_checkpoint.json'
STATE=AUDIT/'full_game_certification_checkpoint.json'; RUNTIME=AUDIT/'runtime'/'full_certification'
SYSTEMS_CSV=AUDIT/'data'/'detected_systems.csv'; API='http://127.0.0.1:1234'
CONF=Path('/userdata/system/batocera.conf'); DISP=Path('/userdata/system/el_gordo_tools/controller_dispatcher')
PROFILE=Path('/userdata/system/configs/el_gordo_controller_profiles/controller_technical.json')
MULTI=Path('/userdata/system/configs/el_gordo_controller_profiles/multiplayer.json')
LOGS=[Path('/userdata/system/logs/controller_selector.log'),Path('/userdata/system/logs/es_launch_stdout.log'),
      Path('/userdata/system/logs/es_launch_stderr.log'),Path('/userdata/system/logs/emulog.txt')]
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
def pids():
 out=[]
 for x in Path('/proc').iterdir():
  if not x.name.isdigit():continue
  try:
   comm=(x/'comm').read_text().strip().lower();exe=os.path.basename(os.readlink(x/'exe')).lower();argv=(x/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace').strip()
   if comm in {'retroarch','mame','controller_dispatcher','selector_controles','emulatorlauncher'} or exe in {'retroarch','mame','controller_dispatcher','selector_controles','emulatorlauncher'}:
    st=(x/'stat').read_text().rsplit(')',1)[1].split();out.append({'pid':int(x.name),'ppid':int(st[1]),'comm':comm,'exe':exe,'argv':argv})
  except (OSError,ValueError,IndexError):pass
 return out
def conf_sha():return hashlib.sha256(CONF.read_bytes()).hexdigest()
def get_default_sink():
 q=subprocess.run(['pactl','get-default-sink'],capture_output=True,text=True,timeout=3)
 return q.stdout.strip() if q.returncode==0 else None
def profile_state():
 q=subprocess.run([str(DISP),'--diagnose'],capture_output=True,text=True,timeout=20)
 if q.returncode:raise RuntimeError('P1_P4_DIAGNOSE_FAILED')
 j=json.loads(q.stdout);players=j.get('profiles',{}).get('arcade',{}).get('players',[])
 return {x.get('arcade_player'):(x.get('usb_port'),x.get('path')) for x in players if x.get('arcade_player') in ('P1','P2','P3','P4')}
def expected_global_core():
 d=ad.parse_defaults();return d.get('mame',{}).get('core')
def safety_baseline():
 idle,game=api_state()
 if not idle or game is not None:raise RuntimeError('ES_NOT_IDLE')
 if sr.MARKER.exists():raise RuntimeError('MARKER_ALREADY_EXISTS')
 if pids():raise RuntimeError('LAUNCH_PROCESSES_ALREADY_ACTIVE')
 if not sr.es_pids():raise RuntimeError('EMULATIONSTATION_NOT_ACTIVE')
 p1=profile_state();exp={'P1':('5','/dev/input/event17'),'P2':('6','/dev/input/event18'),'P3':('8','/dev/input/event20'),'P4':('7','/dev/input/event19')}
 if any(p1.get(k)!=v for k,v in exp.items()):raise RuntimeError('P1_P4_MAPPING_REGRESSION')
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
  marker=sr.marker_value(system,str(rom))
  with sr.MARKER.open('x',encoding='utf-8') as f:json.dump(marker,f);f.flush();os.fsync(f.fileno())
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
 except Exception as e:
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
   if sr.MARKER.is_file():
    data=json.loads(sr.MARKER.read_text())
    if data.get('audit_id')==marker.get('audit_id'):sr.MARKER.unlink()
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
    result['restore']={'status':'RESTORE_FAILURE','detail':type(e).__name__+': '+str(e)}
    result['result']='RESTORE_FAILURE';result['failure_class']='RESTORE_FAILURE'
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
 found['identity_status']='PASS' if result.get('identity',{}).get('core_ok') and result.get('identity',{}).get('content_ok') else result.get('failure_class','UNKNOWN')
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
def run_tests(games,cp,mode):
 baseline=safety_baseline();cp['baseline']=baseline;cp['mode']=mode
 for game in games:
  label=game['system']+'/'+Path(game['rom']).name
  cp['current_test']=label;cp['next_game']=label;cp['status']='RUNNING';checkpoint_update(cp)
  result=launch_one(game,game['adapter_info'],baseline,mode)
  # Keep structured, bounded evidence per test; no screenshots or raw full logs.
  RUNTIME.mkdir(parents=True,exist_ok=True,mode=0o700)
  hist=cp.setdefault('results',[]);hist.append({'system':result.get('system'),'rom':result.get('rom'),'name':result.get('name'),
      'adapter':result.get('adapter'),'result':result.get('result'),'failure_class':result.get('failure_class'),
      'transaction_id':result.get('transaction_id'),'stable_seconds':result.get('process',{}).get('stable_seconds'),
      'audio':result.get('audio'),'restore':result.get('restore'),'finished_at':result.get('finished_at')})
  cp['counts']={k:sum(1 for x in hist if x.get('result')==k) for k in ('AUTO_PASS','GAME_FAIL','STATIC_FAIL','FLAKY','ADAPTER_NOT_READY','ENGINE_FAIL','WRONG_GAME_DISPATCH','AUDIO_ROUTE_CHANGED','RESTORE_FAILURE')}
  cp['next_game']=None;cp['current_test']=None;checkpoint_update(cp)
  update_csv(game,result)
  health=result.get('exit',{}).get('game_health') or {}
  health_summary={k:health.get(k) for k in ('id','system','rom','core','status','exit_code','duration_seconds') if k in health}
  health_summary['cleanup_race']=result.get('exit',{}).get('cleanup_race')
  print(json.dumps({'system':result.get('system'),'game':result.get('name'),'rom':Path(result.get('rom','')).name,
      'adapter':result.get('adapter'),'precheck':result.get('precheck',{}).get('status'),'identity':result.get('identity'),
      'audio':result.get('audio'),'process':result.get('process'),'visual':result.get('visual_summary') or result.get('visual'),
      'exit':health_summary,'restore':result.get('restore'),'result':result.get('result'),'cause':result.get('failure_class')},ensure_ascii=False),flush=True)
  if result.get('transaction_id') and result.get('restore',{}).get('status')!='RESTORE_VERIFIED':
   cp['status']='PAUSED_RESTORE_FAILURE';cp['blocked_reason']='RESTORE_FAILURE';checkpoint_update(cp);return False
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
 cp['status']='COMPLETE';cp['next_game']=None;checkpoint_update(cp);return True

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
 try:cp=json.loads(STATE.read_text(encoding='utf-8'))
 except Exception:cp={'schema_version':2,'updated_at':utc(),'results':[],'counts':{},'status':'READY'}
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
  q=queue(rows,systems);games=q[:a.batch];mode='batch'
 if not games:print('NO_READY_GAMES');return 4
 # Bind pilot roster before launching so a restart cannot silently replace games.
 if mode=='pilot' and not a.resume:
  roster={'created_at':utc(),'prefilter_skips':globals().get('PILOT_PREFLIGHT_SKIPS',[]),
    'games':[{'system':x['system'],'rom':x['rom'],'adapter':x['adapter_info']['adapter'],'core':x['adapter_info']['configured_core']} for x in games]}
  atomic_json(AUDIT/'certifier_pilot_roster.json',roster)
 cp.setdefault('results',[]);cp['status']='RUNNING';cp['mode']=mode;cp['selected_count']=len(games);checkpoint_update(cp)
 ok=run_tests(games,cp,mode)
 print(json.dumps({'batch_status':cp.get('status'),'mode':mode,'selected':len(games),'counts':cp.get('counts',{}),
                   'next_game':cp.get('next_game'),'engine_ok':ok},ensure_ascii=False,indent=2))
 return 0 if ok else 5
if __name__=='__main__':raise SystemExit(main())
