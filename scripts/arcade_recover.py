#!/usr/bin/env python3
"""Diagnose ES/launcher state; optional safe ES quit/relaunch, never kill arbitrary PIDs."""
import argparse,json,os,re,subprocess,time,urllib.request
from datetime import datetime,timezone
from pathlib import Path
API='http://127.0.0.1:1234';ROOT=Path('/userdata/system/state/arcade_audit')
NAMES=('retroarch','mame','controller_dispatcher','selector_controles','emulatorlauncher','emulationstation')
def get_api(path,timeout=2):
    with urllib.request.urlopen(API+path,timeout=timeout) as r:return r.status,json.loads(r.read().decode('utf-8','replace'))
def processes():
    out=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            raw=(p/'cmdline').read_bytes().split(b'\0');argv=[x.decode('utf-8','replace') for x in raw if x]
            comm=(p/'comm').read_text().strip()
            if any(n in comm.lower() or any(n in a.lower() for a in argv) for n in NAMES):
                stat=(p/'stat').read_text().split();out.append({'pid':int(p.name),'ppid':int(stat[3]),'comm':comm,'argv':argv})
        except (OSError,ValueError):continue
    return out
def es_pids(ps):return sorted(x['pid'] for x in ps if 'emulationstation' in x['comm'].lower() or any('emulationstation' in a.lower() for a in x['argv']))
def diagnose():
    ps=processes();obs={'at':datetime.now(timezone.utc).isoformat(timespec='seconds'),'processes':ps,'es_pids':es_pids(ps)}
    try:obs['is_idle']=get_api('/isIdle')[1];obs['running_game']=get_api('/runningGame')[1]
    except Exception as e:obs['api_error']=type(e).__name__
    marker=Path('/userdata/system/state/boot_audit_once.json')
    obs['marker']={'exists':marker.exists()}
    if marker.exists():
        try:
            m=json.loads(marker.read_text());obs['marker'].update({k:m.get(k) for k in ('enabled','system','rom','choice','created_at','expires_at')})
            obs['marker']['expired']=float(m.get('expires_at',0))<time.time()
        except Exception:obs['marker']['parse']='INVALID'
    return obs
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--restart-es',action='store_true');ap.add_argument('--timeout',type=int,default=30);a=ap.parse_args()
    before=diagnose()
    if not a.restart_es:print(json.dumps(before,ensure_ascii=False,indent=2));return 0
    if before.get('is_idle') not in ([True],True) or before.get('marker',{}).get('exists') or before.get('running_game') not in ({'msg':'NO GAME RUNNING'},None):
        print(json.dumps({'result':'REFUSED_NOT_SAFE','diagnosis':before},ensure_ascii=False,indent=2));return 2
    launcher=[x for x in before['processes'] if any('emulatorlauncher' in v.lower() or 'controller_dispatcher' in v.lower() for v in x['argv'])]
    if launcher:
        print(json.dumps({'result':'REFUSED_LAUNCHER_ACTIVE','pids':[x['pid'] for x in launcher]},ensure_ascii=False));return 2
    settings=[Path('/userdata/system/configs/emulationstation/es_settings.cfg'),Path('/userdata/system/configs/emulationstation/es_input.cfg'),Path('/userdata/system/configs/emulationstation/es_systems_el_gordo.cfg'),Path('/userdata/system/batocera.conf')]
    dest=ROOT/'recovery_runtime'/datetime.now().strftime('ES_RESTART_PRE_%Y%m%d_%H%M%S');dest.mkdir(parents=True,mode=0o700)
    manifest=[]
    for p in settings:
        if p.is_file():
            target=dest/p.name;target.write_bytes(p.read_bytes());os.chmod(target,0o600);manifest.append({'source':str(p),'copy':str(target),'size':p.stat().st_size})
    # Hash gamelists; no large media or ROMs copied.
    import hashlib
    gl=[]
    for p in Path('/userdata/roms').glob('*/gamelist.xml'):
        if p.is_file():gl.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size})
    (dest/'manifest.json').write_text(json.dumps({'files':manifest,'gamelist_hashes':gl,'created_at':datetime.now(timezone.utc).isoformat()},indent=2)+'\n')
    # Use the validated Batocera ES API quit path, never signal/kill a PID.
    try:get_api('/quit')
    except Exception as e:
        print(json.dumps({'result':'QUIT_API_FAILED','error':type(e).__name__,'snapshot':str(dest)},ensure_ascii=False));return 3
    old=set(before['es_pids']);deadline=time.time()+max(5,min(a.timeout,90));after=None
    while time.time()<deadline:
        time.sleep(.5);after=diagnose()
        new=set(after.get('es_pids',[]))-old
        if new and after.get('is_idle') in ([True],True) and after.get('running_game') in ({'msg':'NO GAME RUNNING'},None):
            print(json.dumps({'result':'ES_RESTARTED','new_es_pids':sorted(new),'api_idle':True,'running_game':after['running_game'],'snapshot':str(dest),'manual_p1_p4_check_required':True},ensure_ascii=False,indent=2));return 0
    print(json.dumps({'result':'ES_RESTART_TIMEOUT','snapshot':str(dest),'last_state':after},ensure_ascii=False,indent=2));return 4
if __name__=='__main__':raise SystemExit(main())
