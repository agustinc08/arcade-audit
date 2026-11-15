#!/usr/bin/env python3
"""Narrow recovery after the batch-2 rollback comparison newline defect."""
import json, os, shutil, sys
from pathlib import Path
import smoke_runner as sr
import smoke_pilot_batch2 as b2

def main():
    backup=b2.BACKUP/'batocera.conf'
    original=backup.read_bytes()
    line=b'mame["mvp.zip"].core=mame\n'
    current=b2.CONF.read_bytes()
    if current!=original+line: raise RuntimeError('MVP_OVERRIDE_DIFF_NOT_EXACT')
    if sr.api_idle() is not True or sr.api_game() is not None or sr.MARKER.exists():
        raise RuntimeError('RUNTIME_NOT_SAFE_FOR_RECOVERY')
    active=[p for p in sr.proc_list() if p['exe'].endswith('/retroarch') and
            b2.CORE_PATH in p['cmd'] and '/var/run/cmdfiles/mvp.cmd' in p['cmd']]
    if active: raise RuntimeError('MVP_RETROARCH_STILL_ACTIVE')
    cp,bp,base=sr.ensure_backup_valid()
    before=sr.snapshot_all(); old=base['protected_snapshot']
    drift=[p for p in sorted(set(before)|set(old)) if p!=str(b2.CONF) and before.get(p)!=old.get(p)]
    if drift: raise RuntimeError('PROTECTED_TREE_DRIFT_BEFORE_RECOVERY:'+repr(drift[:10]))
    st=backup.stat(); b2.restore_conf(original,st)
    if b2.sha(b2.CONF)!=b2.sha(backup): raise RuntimeError('MVP_OVERRIDE_ROLLBACK_HASH_FAILED')
    after=sr.snapshot_all()
    drift=[p for p in sorted(set(after)|set(old)) if p!=str(b2.CONF) and after.get(p)!=old.get(p)]
    if drift: raise RuntimeError('PROTECTED_TREE_DRIFT_AFTER_RECOVERY:'+repr(drift[:10]))
    if sr.api_idle() is not True or sr.api_game() is not None or sr.MARKER.exists(): raise RuntimeError('ES_NOT_IDLE_AFTER_RECOVERY')
    health=sr.game_health_row('mame','/userdata/roms/mame/mvp.zip',0)
    if not health or health.get('core')!='mame' or health.get('exit_code')!=1: raise RuntimeError('MVP_RUNTIME_EVIDENCE_MISMATCH')
    text=health.get('error','')
    if '317-0143.key NOT FOUND' not in text or '315-5298.b9 NOT FOUND' not in text:
        raise RuntimeError('MVP_MISSING_CONTENT_LOG_MISMATCH')
    audit=json.loads((b2.OUT/'arcade_games_audit.json').read_text(encoding='utf-8'))
    meta=next(x for x in audit if x.get('system')=='mame' and x.get('rom')=='mvp.zip')
    result={'game':'mvp','rom':'/userdata/roms/mame/mvp.zip','display_name':'MVP',
      'old_core':'mame078plus','new_core':'mame libretro current','boot':'FAIL_MISSING_CONTENT',
      'input':'MANUAL_VALIDATE','override':'REVERTED','duration':round(float(health['duration']),2),
      'exit_code':health['exit_code'],'restore':'VERIFIED','detail':'MAME 0.285 core cargado; salida controlada por contenido obligatorio ausente: 317-0143.key y 315-5298.b9. Error de comparación del harness corregido; override retirado y snapshot verificado.',
      'tested_at':health['launched_at'],'override_diff':'+mame["mvp.zip"].core=mame (revertido)',
      'core_path':b2.CORE_PATH,'crc':meta.get('romset_status'),'chd':'NO','chd_ok':'NOT_REQUIRED',
      'bios':meta.get('bios_status'),'players':meta.get('players'),'buttons':meta.get('buttons'),
      'control_type':meta.get('control_type'),'multiplayer_priority':'NORMAL','physical_input':'NOT_YET_CERTIFIED',
      'missing_dependency':'317-0143.key; 315-5298.b9','health_status':health.get('status'),
      'health_core':health.get('core'),'health_emulator':health.get('emulator'),'health_pid':health.get('pid'),
      'launcher_log':health.get('launcher_log',''),'emulator_log':health.get('emulator_log','')}
    state=json.loads(b2.CHECKPOINT.read_text(encoding='utf-8'))
    if state.get('results') and any(x.get('game')=='mvp' for x in state['results']): raise RuntimeError('MVP_ALREADY_CHECKPOINTED')
    state['results'].append(result); state['reverted_overrides'].append('mvp')
    state.update({'phase':'PAUSED_SAFETY','next_game':'sia2650','restore_status':'VERIFIED',
      'error':'mvp confirmó FAIL_MISSING_CONTENT; rollback del override verificado; runner corregido y listo para reanudar.'})
    b2.write_json(b2.CHECKPOINT,state); b2.persist_checkpoints(state); b2.write_report(state); b2.update_csv_result(result)
    print(json.dumps({'recovery':'VERIFIED','mvp':'FAIL_MISSING_CONTENT','missing':['317-0143.key','315-5298.b9'],
      'override_reverted':True,'protected_snapshot_equal':True,'next_game':'sia2650'},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
