#!/usr/bin/env python3
"""Build a distinct current protected baseline without altering historical backups."""
import hashlib,importlib.util,json,os,re,shutil,stat,sys,urllib.request
from datetime import datetime,timezone
from pathlib import Path
AUD=Path('/userdata/system/state/arcade_audit')
RUNNER=AUD/'smoke_runner.py'
RUNTIME=AUD/'certification_runtime'
CONF=Path('/userdata/system/batocera.conf')
EXPECTED={x+'.zip' for x in ('ffight2b','altair','apache3','blazlaz','cubeqst','sia2650','evosocc','hoops95','funcube4','lbgrande','sws98','tenkomor','multigam','multigm3','nratechu','ertictac','kov2p','martmast')}
def main():
    spec=importlib.util.spec_from_file_location('historic_smoke_runner',RUNNER);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    cp,bp,old=m.ensure_backup_valid()
    idle=m.api_idle();game=m.api_game();procs=m.launcher_processes();marker=m.MARKER.exists();es=m.es_pids()
    if idle is not True or game is not None or procs or marker or not es:raise RuntimeError('RUNTIME_NOT_IDLE')
    config=CONF.read_text(encoding='utf-8',errors='strict')
    overrides=set(re.findall(r'^mame\["([^"\n]+\.zip)"\]\.core=mame$',config,re.M))
    if overrides!=EXPECTED:raise RuntimeError('MAME_OVERRIDE_BASELINE_MISMATCH')
    system_cfg=Path('/userdata/system/configs/emulationstation/es_systems_el_gordo.cfg').read_text(encoding='utf-8')
    if '<core>mame078plus</core>' not in system_cfg:raise RuntimeError('GLOBAL_CORE_NOT_MAME078PLUS')
    current=m.snapshot_all();created,modified,deleted=m.differences(old['protected_snapshot'],current)
    if created or deleted or modified!=['/userdata/system/batocera.conf']:
        raise RuntimeError('UNEXPECTED_PROTECTED_STATE_DELTA:'+json.dumps({'created':created[:5],'modified':modified[:5],'deleted':deleted[:5]}))
    text=CONF.read_text(encoding='utf-8');oldconf=(bp/m.rel_to_userdata(str(CONF))).read_text(encoding='utf-8')
    added=sorted(set(text.splitlines())-set(oldconf.splitlines()))
    removed=sorted(set(oldconf.splitlines())-set(text.splitlines()))
    if removed or len(added)!=18 or any(x not in added for x in (f'mame["{name}"].core=mame' for name in EXPECTED)):
        raise RuntimeError('CONFIG_DELTA_NOT_EXACTLY_18_APPROVED_OVERRIDES')
    RUNTIME.mkdir(mode=0o700,parents=True,exist_ok=True);os.chmod(RUNTIME,0o700)
    confcopy=RUNTIME/'batocera.conf.current';tmp=RUNTIME/'batocera.conf.current.tmp'
    shutil.copy2(CONF,tmp);os.chmod(tmp,0o600)
    digest=hashlib.sha256(CONF.read_bytes()).hexdigest()
    if hashlib.sha256(tmp.read_bytes()).hexdigest()!=digest:raise RuntimeError('CURRENT_CONFIG_COPY_HASH_MISMATCH')
    os.replace(tmp,confcopy)
    # The manifest points to historical verified save/config copies except for the
    # one intentionally newer system config. It never mutates that historical tree.
    sources={}
    for path,item in old['backup_files'].items():
        if item.get('type')=='file':sources[path]=str(bp/m.rel_to_userdata(path))
    sources[str(CONF)]=str(confcopy)
    baseline={'schema_version':1,'created_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'protected_snapshot':current,'backup_sources':sources,
              'historical_backup':str(bp),'historical_baseline_created_at':old.get('created_at'),
              'authorized_config_delta':'exactly 18 existing per-game MAME current overrides; no other line changes',
              'global_mame_core':'mame078plus','restore_design':'restore only differences from this current snapshot; use backup_sources for pre-existing files; remove only files created inside monitored roots; refuse any unrecognized root/type change'}
    # Recheck original source state before committing local baseline evidence.
    if m.snapshot_all()!=current:raise RuntimeError('PROTECTED_STATE_CHANGED_DURING_BASELINE')
    dest=RUNTIME/'master_game_baseline.json';tmpj=RUNTIME/'master_game_baseline.json.tmp'
    with tmpj.open('w',encoding='utf-8') as f:json.dump(baseline,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.chmod(tmpj,0o600);os.replace(tmpj,dest)
    print(json.dumps({'baseline':'CURRENT_BASELINE_VERIFIED','path':str(dest),'historical_backup_preserved':True,
                      'protected_state_delta':'only 18 authorized MAME overrides in batocera.conf','override_count':18,
                      'global_core':'mame078plus','runtime_launch':'NOT RUN','file_permissions':'0600'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
