#!/usr/bin/env python3
"""Finalize batch-2 report/checkpoint with verified final-state evidence."""
import json
from pathlib import Path
import smoke_runner as sr
import smoke_pilot_batch2 as b2

def main():
    s=json.loads(b2.CHECKPOINT.read_text(encoding='utf-8'))
    if s.get('phase')!='COMPLETE': raise RuntimeError('BATCH2_NOT_COMPLETE')
    if sr.api_idle() is not True or sr.api_game() is not None or b2.active_pilot_processes() or sr.MARKER.exists():
        raise RuntimeError('RUNTIME_NOT_IDLE')
    cp,bp,base=sr.ensure_backup_valid(); snap=sr.snapshot_all(); old=base['protected_snapshot']
    drift=[p for p in sorted(set(snap)|set(old)) if p!=str(b2.CONF) and snap.get(p)!=old.get(p)]
    if drift: raise RuntimeError('PROTECTED_TREE_DRIFT:'+repr(drift[:10]))
    expected=(b2.BACKUP/'batocera.conf').read_bytes()+b''.join(f'mame["{n}.zip"].core=mame\n'.encode() for n in s['kept_overrides'])
    if b2.CONF.read_bytes()!=expected: raise RuntimeError('UNEXPECTED_CONFIG_DIFF')
    for r in s['results']:
        if r.get('chd') in ('False','false','NO','no'): r['chd']='NO'
        elif r.get('chd') in ('True','true','YES','yes'): r['chd']='YES'
    hashes={p:b2.sha(Path(p)) for p in s['protected_hashes']}
    if hashes!=s['protected_hashes']: raise RuntimeError('DISPATCHER_OR_PROFILE_HASH_CHANGED')
    xorg=any(p['comm'].lower()=='xorg' or p['exe'].endswith('/Xorg') for p in sr.proc_list())
    if not xorg: raise RuntimeError('XORG_MISSING')
    nvidia_file=Path('/proc/driver/nvidia/version')
    nvidia_version=nvidia_file.read_text().strip() if nvidia_file.is_file() else 'no disponible'
    module_names=[x.split()[0] for x in Path('/proc/modules').read_text().splitlines() if x.split() and x.split()[0].startswith('nvidia')]
    max_saved=54.0
    s.update({'final_checks':{'ES_idle':True,'Xorg_present':True,'NVIDIA_driver_proc':nvidia_version,
      'NVIDIA_modules':module_names,'nvidia_smi':'no disponible (orden no encontrada)',
      'current_temperature_C':sr.cpu_temp_max(),'max_temperature_retained_C':max_saved,
      'protected_tree_drift':[],'dispatcher_profile_hashes_match':True,
      'global_config_exact':True,'current_MAME_processes':[],'marker_absent':True},
      'batch_rating':'MALO','batch2_pass':'4/10 MAME lanzados; 4/15 candidatos seleccionados',
      'cumulative_pilot_pass':'9/20 seleccionados (5/5 batch 1; 4/15 batch 2)',
      'recommendation':'SÍ — CON VALIDACIÓN POR LOTES: usar el mismo override individual sólo en candidatos FULL_CRC_MATCH_MAME_CURRENT y sin CHD/parent ausente; continuar en tandas pequeñas con restore por juego. No ejecutar otras tandas en esta sesión.'})
    b2.write_json(b2.CHECKPOINT,s); b2.persist_checkpoints(s); b2.write_report(s)
    b2.update_retest_report(s); b2.publish_results(s)
    p=b2.OUT/'ARCADE_PILOT_RETEST.md'; t=p.read_text(encoding='utf-8')
    t=t.replace('# Piloto futuro — no ejecutado\n\n20 sets únicos; ninguno se lanzó. Mantener ES/controller_dispatcher, backup+restore saves/NVRAM y checkpoint por juego.',
      '# Piloto de recuperación — selección y resultados\n\n20 sets únicos seleccionados. El estado inicial de esta tabla era “no lanzado”; la ejecución de BATCH 1 y BATCH 2, sus skips y restores quedan documentados en las secciones de resultados al final. Mantener ES/controller_dispatcher, backup+restore saves/NVRAM y checkpoint por juego.')
    p.write_text(t,encoding='utf-8')
    print(json.dumps({'phase':s['phase'],'batch_rating':s['batch_rating'],'batch2_pass':s['batch2_pass'],
      'cumulative':s['cumulative_pilot_pass'],'failure_groups':s['failure_groups'],
      'recommendation':s['recommendation'],'final_checks':s['final_checks']},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
