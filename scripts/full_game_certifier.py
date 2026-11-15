#!/usr/bin/env python3
"""Resumable full-library certification planner; game launching is safety-gated."""
import argparse,csv,json,os,sys,urllib.request
from datetime import datetime,timezone
from pathlib import Path

AUDIT=Path('/userdata/system/state/arcade_audit')
TABLE=AUDIT/'full_game_certification.csv'
CHECKPOINT=AUDIT/'arcade_master_checkpoint.json'
STATE=AUDIT/'full_game_certification_checkpoint.json'
API='http://127.0.0.1:1234'
BLOCKERS=['SAFE-001','AUD-002','CERT-001']

def atomic_json(path,obj):
    tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('w',encoding='utf-8') as f:
        json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)
def rows():
    with TABLE.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def current_state():
    result={'at':datetime.now(timezone.utc).isoformat(timespec='seconds')}
    try:
        with urllib.request.urlopen(API+'/isIdle',timeout=2) as r: result['is_idle']=json.load(r)
        with urllib.request.urlopen(API+'/runningGame',timeout=2) as r: result['running_game']=json.load(r)
    except Exception as e:result['api_error']=type(e).__name__
    result['marker_exists']=Path('/userdata/system/state/boot_audit_once.json').exists()
    names={'retroarch','mame','controller_dispatcher','selector_controles','emulatorlauncher'}
    procs=[]
    for item in Path('/proc').iterdir():
        if not item.name.isdigit():continue
        try:
            comm=(item/'comm').read_text().strip().lower();exe=os.path.basename(os.readlink(item/'exe')).lower()
            argv=(item/'cmdline').read_bytes().split(b'\0');arg0=os.path.basename(argv[0].decode(errors='replace')).lower() if argv and argv[0] else ''
            if comm in names or exe in names or arg0 in names:
                st=(item/'stat').read_text().split();procs.append({'pid':int(item.name),'ppid':int(st[3]),'comm':comm,'exe':exe})
        except (OSError,IndexError,ValueError):continue
    result['launch_processes']=procs
    return result
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--system');p.add_argument('--rom');p.add_argument('--limit',type=int,default=20)
    p.add_argument('--plan',action='store_true',help='solo lectura; predeterminado')
    p.add_argument('--certify-once',action='store_true',help='solicita una prueba; aborta si falta cualquier guard')
    a=p.parse_args(); allrows=rows()
    candidates=[r for r in allrows if (not a.system or r['system']==a.system) and (not a.rom or Path(r['rom']).name==Path(a.rom).name)]
    if not candidates:print('NO_MATCH');return 2
    try:cp=json.loads(CHECKPOINT.read_text(encoding='utf-8'))
    except Exception:cp={}
    blockers=[x for x in BLOCKERS if cp.get('issues') and any(i.get('id')==x and i.get('status') not in ('CLOSED','FIXED','MITIGATED') for i in cp['issues'])]
    live=current_state()
    if a.certify_once:
        # Never bypass dispatcher or run a test without a transaction baseline.
        reasons=[]
        if blockers:reasons.append('OPEN_GLOBAL_BLOCKERS:'+','.join(blockers))
        if not (isinstance(live.get('is_idle'), list) and live['is_idle'] and live['is_idle'][0] is True): reasons.append('ES_NOT_IDLE_OR_API_UNKNOWN')
        game=live.get('running_game')
        if isinstance(game,dict) and game.get('msg')!='NO GAME RUNNING':reasons.append('GAME_ALREADY_RUNNING')
        if live['marker_exists']:reasons.append('STALE_ONE_SHOT_MARKER')
        if live.get('launch_processes'):reasons.append('LAUNCH_PROCESS_ALREADY_ACTIVE')
        reasons.append('CURRENT_PER_GAME_TRANSACTION_RESTORE_NOT_IMPLEMENTED; no launch performed')
        print(json.dumps({'result':'BLOCKED','reasons':reasons,'live':live,'games_considered':len(candidates)},ensure_ascii=False,indent=2));return 3
    print(json.dumps({'mode':'PLAN_ONLY','selected':candidates[:a.limit],'total_matches':len(candidates),
                      'runtime_launch':'NOT RUN','known_global_blockers':blockers,'live':live,
                      'next_required':'safe current transaction baseline; resolve HDMI default sink before AUTO_CERTIFIED'},ensure_ascii=False,indent=2))
    return 0
if __name__=='__main__':raise SystemExit(main())
