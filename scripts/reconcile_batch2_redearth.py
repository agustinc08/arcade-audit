#!/usr/bin/env python3
"""Classify redearth from the exact core log, after the runner's idle-check pause."""
import json, sys
from pathlib import Path
import smoke_runner as sr
import smoke_pilot_batch2 as b2

def main():
    state=json.loads(b2.CHECKPOINT.read_text(encoding='utf-8'))
    if state.get('phase')!='PAUSED_SAFETY' or state.get('next_game')!='redearth': raise RuntimeError('UNEXPECTED_BATCH_STATE')
    if sr.api_idle() is not True or sr.api_game() is not None or sr.MARKER.exists(): raise RuntimeError('ES_NOT_IDLE')
    if b2.active_pilot_processes(): raise RuntimeError('PILOT_RETROARCH_STILL_ACTIVE')
    cp,bp,base=sr.ensure_backup_valid(); current=sr.snapshot_all(); old=base['protected_snapshot']
    drift=[p for p in sorted(set(current)|set(old)) if p!=str(b2.CONF) and current.get(p)!=old.get(p)]
    if drift: raise RuntimeError('PROTECTED_TREE_DRIFT:'+repr(drift[:10]))
    conf=(b2.BACKUP/'batocera.conf').read_bytes()+b'mame["sia2650.zip"].core=mame\n'
    if b2.CONF.read_bytes()!=conf: raise RuntimeError('CONFIG_NOT_EXACT_BATCH2_STATE')
    health=sr.game_health_row('mame','/userdata/roms/mame/redearth.zip',0)
    if not health or health.get('core')!='mame' or health.get('exit_code')!=1: raise RuntimeError('REDEARTH_HEALTH_ROW_MISMATCH')
    err=health.get('error','')
    if 'cap-wzd-5.chd NOT FOUND' not in err or 'Fatal error: Required files are missing' not in err:
        raise RuntimeError('REDEARTH_CHD_LOG_NOT_CONFIRMED')
    result=next(x for x in state['results'] if x['game']=='redearth')
    result.update({'boot':'FAIL_CHD','exit_code':health['exit_code'],'health_status':health.get('status'),
      'health_core':health.get('core'),'health_emulator':health.get('emulator'),'health_pid':health.get('pid'),
      'detail':'MAME 0.285 cargó; log confirma cap-wzd-5.chd NOT FOUND y Fatal error: Required files are missing. Override revertido; restore verificado.',
      'missing_dependency':'cap-wzd-5.chd'})
    state.update({'phase':'PAUSED_SAFETY','error':'Redeearth clasificó FAIL_CHD; ES idle y restore verificado; harness actualizado para esperar transición a idle. Reanudar en jojo.',
      'next_game':'jojo','restore_status':'VERIFIED'})
    b2.write_json(b2.CHECKPOINT,state); b2.persist_checkpoints(state); b2.write_report(state); b2.update_csv_result(result)
    print(json.dumps({'reconcile':'VERIFIED','game':'redearth','status':'FAIL_CHD','missing':'cap-wzd-5.chd',
      'override':'REVERTED','restore':'VERIFIED','ES_idle':True,'next_game':'jojo'},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
