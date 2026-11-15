#!/usr/bin/env python3
"""Normalize batch-2 failure labels from the exact RetroArch/MAME log evidence."""
import json
from pathlib import Path
import smoke_runner as sr
import smoke_pilot_batch2 as b2

MAP={
 'mvp':('FAIL_MISSING_CONTENT','317-0143.key; 315-5298.b9','MAME 0.285 abortó con Fatal error: Required files are missing; ambos archivos figuran NOT FOUND.'),
 'redearth':('FAIL_CHD','cap-wzd-5.chd','MAME 0.285 abortó con cap-wzd-5.chd NOT FOUND y Required files are missing.'),
 'jojo':('FAIL_CHD','cap-jjk-3.chd; jojo_euro.29f400.u2','MAME 0.285 abortó con cap-jjk-3.chd NOT FOUND y jojo_euro.29f400.u2 NOT FOUND.'),
 'jojoba':('FAIL_ROMSET','jojoba-simm5.0 a jojoba-simm5.7','MAME 0.285 reportó los ocho miembros SIMM5 NOT FOUND y Required files are missing; el inventario no halló CRC actual coincidente.'),
 'nbapbp':('FAIL_MISSING_CONTENT','778b01.27p; security_eeprom_uab','MAME 0.285 reportó 778b01.27p y security_eeprom_uab NOT FOUND; Required files are missing.'),
 'hyperath':('FAIL_CHD','gv021-j1.chd','MAME 0.285 abortó con gv021-j1.chd NOT FOUND (parent konamigv) y Required files are missing.'),
}

def main():
    s=json.loads(b2.CHECKPOINT.read_text(encoding='utf-8'))
    if s.get('phase')!='COMPLETE': raise RuntimeError('BATCH2_NOT_COMPLETE')
    if sr.api_idle() is not True or sr.api_game() is not None or sr.MARKER.exists() or b2.active_pilot_processes():
        raise RuntimeError('RUNTIME_NOT_IDLE')
    cp,bp,base=sr.ensure_backup_valid(); now=sr.snapshot_all(); old=base['protected_snapshot']
    drift=[p for p in sorted(set(now)|set(old)) if p!=str(b2.CONF) and now.get(p)!=old.get(p)]
    if drift: raise RuntimeError('PROTECTED_TREE_DRIFT:'+repr(drift[:10]))
    expected=(b2.BACKUP/'batocera.conf').read_bytes()+b''.join(f'mame["{n}.zip"].core=mame\n'.encode() for n in s['kept_overrides'])
    if b2.CONF.read_bytes()!=expected: raise RuntimeError('CONFIG_DIFF_BEYOND_PASS_OVERRIDES')
    for r in s['results']:
        if r['game'] not in MAP: continue
        status,missing,detail=MAP[r['game']]
        h=sr.game_health_row('mame',r['rom'],0)
        if not h or h.get('core')!='mame' or h.get('exit_code')!=1: raise RuntimeError('RUNTIME_RECORD_MISMATCH:'+r['game'])
        evidence=h.get('error','')
        expected_token=missing.split(';')[0].split(' a ')[0]
        if expected_token.lower() not in evidence.lower(): raise RuntimeError('LOG_EVIDENCE_MISMATCH:'+r['game'])
        r.update({'boot':status,'exit_code':1,'missing_dependency':missing,'detail':detail+' Override revertido; restore VERIFIED.',
                  'health_status':h.get('status'),'health_core':h.get('core'),'health_emulator':h.get('emulator'),'health_pid':h.get('pid')})
    s['failure_groups']={'CHD':3,'MISSING_CONTENT':2,'ROMSET':1,'DRIVER':0,'CRASH_CONFIRMED':0,'OTHER':0}
    s['restore_status']='15/15: 10 ejecutados/restaurados y 5 omitidos sin escrituras, snapshot idéntico'
    s['batch_rating']='MALO' # 4 PASS of 15 selected; 5 were skipped by strategy.
    s['recommendation']='NO generalizar aún a los otros candidatos: los seis fallos del lote se explican por contenido/CHD/ROMset; revisar este grupo antes de una nueva tanda.'
    b2.write_json(b2.CHECKPOINT,s); b2.persist_checkpoints(s); b2.write_report(s)
    for r in s['results']: b2.update_csv_result(r)
    b2.update_retest_report(s); b2.publish_results(s)
    print(json.dumps({'classified':{n:MAP[n][0] for n in MAP},'pass':sum(x['boot']=='BOOT_OK' for x in s['results']),
      'fail':sum(x['boot'].startswith('FAIL') for x in s['results']),'skipped':sum(x['boot']=='SKIP_WRONG_STRATEGY' for x in s['results']),
      'restore':s['restore_status'],'snapshot_equal':True,'config_exact':True},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
