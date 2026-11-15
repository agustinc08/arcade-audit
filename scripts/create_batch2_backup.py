#!/usr/bin/env python3
"""Create a narrow, verified rollback point for the arcade core pilot batch 2."""
import hashlib, json, os, shutil
from datetime import datetime
from pathlib import Path
import smoke_runner as sr

OUT=Path('/userdata/system/state/arcade_audit')
CONF=Path('/userdata/system/batocera.conf')
B1=Path('/media/ROMS/ARCADE_BACKUPS/ARCADE_CORE_PILOT_2026-11-13_093236')
SAVE_BACKUP=Path('/media/ROMS/ARCADE_BACKUPS/ARCADE_SMOKE_TEST_SAVES_2026-11-13_011039')
B1_GAMES=['ffight2b','altair','apache3','blazlaz','cubeqst']
EXTRA=[OUT/'pilot_checkpoint.json',OUT/'ARCADE_CORE_PILOT_RESULTS.md',
       OUT/'arcade_core_compatibility.csv',OUT/'ARCADE_PILOT_RETEST.md']

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()

def main():
    cp,bp,baseline=sr.ensure_backup_valid()
    if bp!=SAVE_BACKUP or not SAVE_BACKUP.is_dir(): raise RuntimeError('VERIFIED_SAVE_BACKUP_MISMATCH')
    if not (B1/'batocera.conf').is_file(): raise RuntimeError('BATCH1_CONFIG_BACKUP_MISSING')
    original=(B1/'batocera.conf').read_bytes()
    expected=original+b''.join(f'mame["{n}.zip"].core=mame\n'.encode() for n in B1_GAMES)
    if CONF.read_bytes()!=expected: raise RuntimeError('BATCH1_OVERRIDES_OR_GLOBAL_CONFIG_DRIFT')
    current=sr.snapshot_all(); old=baseline['protected_snapshot']
    drift=[p for p in sorted(set(current)|set(old)) if p!=str(CONF) and current.get(p)!=old.get(p)]
    if drift: raise RuntimeError('PROTECTED_STATE_DRIFT:'+repr(drift[:20]))
    if sr.api_idle() is not True or sr.api_game() is not None or sr.launcher_processes() or not sr.es_pids():
        raise RuntimeError('ARCADE_NOT_IDLE')
    if sr.MARKER.exists(): raise RuntimeError('ONE_SHOT_MARKER_EXISTS')
    dispatcher=Path('/userdata/system/el_gordo_tools/controller_dispatcher')
    profile=Path('/userdata/system/configs/el_gordo_controller_profiles/controller_technical.json')
    if not dispatcher.is_file() or not profile.is_file(): raise RuntimeError('DISPATCHER_OR_PROFILE_MISSING')
    stamp=datetime.now().astimezone().strftime('%Y-%m-%d_%H%M%S')
    parent=Path('/media/ROMS/ARCADE_BACKUPS')
    dest=parent/f'ARCADE_CORE_PILOT_BATCH2_{stamp}'
    if dest.exists(): raise RuntimeError('BACKUP_DESTINATION_ALREADY_EXISTS:'+str(dest))
    dest.mkdir(mode=0o700)
    sources=[CONF,*EXTRA]
    for src in sources:
        if not src.is_file(): raise RuntimeError('BACKUP_SOURCE_MISSING:'+str(src))
        shutil.copy2(src,dest/src.name)
        if sha(src)!=sha(dest/src.name): raise RuntimeError('BACKUP_HASH_MISMATCH:'+str(src))
    (dest/'SOURCE_PATHS.txt').write_text(
      '\n'.join([str(x) for x in sources]+[
        f'REUSED_VERIFIED_SAVE_BACKUP={SAVE_BACKUP}',
        f'controller_dispatcher SHA256={sha(dispatcher)} (record only; not modified)',
        f'controller_technical.json SHA256={sha(profile)} (record only; not modified)',
        'Protected save/NVRAM trees match the verified baseline before batch 2.'])+'\n',encoding='utf-8')
    (dest/'PRE_TEST_FILELIST.txt').write_text('\n'.join(
      f'{m.get("type")}\t{m.get("size","-")}\t{m.get("mtime_ns","-")}\t{m.get("sha256",m.get("target","-"))}\t{p}'
      for p,m in sorted(current.items()))+'\n',encoding='utf-8')
    files=[dest/src.name for src in sources]
    manifest='\n'.join(f'{sha(p)}  {p.name}  {p.stat().st_size} bytes' for p in files)+'\n'
    (dest/'MANIFEST_SHA256.txt').write_text(manifest,encoding='utf-8')
    (dest/'VERIFIED_SAVE_BACKUP_REFERENCE.txt').write_text(
      f'{SAVE_BACKUP}\nBackup contents verified by smoke_runner.ensure_backup_valid at {datetime.now().astimezone().isoformat(timespec="seconds")}\n',encoding='utf-8')
    # Final verification of source stability and all copied data.
    if sr.snapshot_all()!=current: raise RuntimeError('SOURCE_STATE_CHANGED_DURING_BACKUP')
    for src in sources:
        if sha(src)!=sha(dest/src.name): raise RuntimeError('FINAL_BACKUP_VERIFY_FAILED:'+str(src))
    (OUT/'pilot_batch2_backup_path.txt').write_text(str(dest)+'\n',encoding='utf-8')
    print(json.dumps({'backup':str(dest),'files_copied':len(sources),'manifest_sha256':sha(dest/'MANIFEST_SHA256.txt'),
      'save_backup_reused':str(SAVE_BACKUP),'protected_snapshot_equal':True,'verified':True},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
