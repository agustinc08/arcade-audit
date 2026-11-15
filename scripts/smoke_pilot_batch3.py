#!/usr/bin/env python3
"""Run a bounded MAME-current pilot through EmulationStation's launch API."""
import csv, hashlib, json, os, re, shutil, subprocess, sys, time, xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

OUT=Path('/userdata/system/state/arcade_audit')
sys.path.insert(0,str(OUT))
import smoke_runner as sr
import smoke_pilot_batch2 as pilot

CONF=Path('/userdata/system/batocera.conf')
CORE='/usr/lib/libretro/mame_libretro.so'
MAME='/usr/bin/mame/mame'
PREFLIGHT=OUT/'mame_batch3_preflight.json'
REPORT=OUT/'ARCADE_MAME_BATCH3_RESULTS.md'
CHECKPOINT=OUT/'mame_batch3_checkpoint.json'
STATE=OUT/'mame_batch3_runtime'
BACKUP_DIR=OUT/'mame_batch3_backups'
MATRIX=OUT/'arcade_core_compatibility.csv'
TESTED_B1={'ffight2b','altair','apache3','blazlaz','cubeqst'}
TESTED_B2={'mvp','sia2650','redearth','jojo','jojoba','evosocc','hoops95','nbapbp','funcube4','hyperath'}
FBNEO_RESERVED={'gprider','sfiii2n','sfiii3n','sfiiin','neotris'}
EXCLUDED=TESTED_B1|TESTED_B2|FBNEO_RESERVED
EXPECTED_OVERRIDES={'ffight2b.zip','altair.zip','apache3.zip','blazlaz.zip','cubeqst.zip',
                    'sia2650.zip','evosocc.zip','hoops95.zip','funcube4.zip'}
# Eight verified ordinary joystick games, then six real games requiring special input.
SELECTED=['kinstb','lbgrande','sws98','tenkomor','multigam','multigm3','nratechu','ertictac',
          'pacapp2','pacappsp','ghlpanic','midnrun','cclownz','qb3']

def stamp(): return datetime.now().astimezone().isoformat(timespec='seconds')
def sha_bytes(data): return hashlib.sha256(data).hexdigest()
def sha_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def atomic_json(path,obj):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(tmp,path)
def matrix_rows():
    with MATRIX.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def active_overrides():
    return sorted(x.decode() for x in set(re.findall(rb'^mame\["([^"]+)"\]\.core=mame\s*$',CONF.read_bytes(),re.M)))
def canonical_state_hash(snap):
    return sha_bytes(json.dumps(snap,sort_keys=True,separators=(',',':')).encode())
def state_without_conf(snap): return {k:v for k,v in snap.items() if k!=str(CONF)}
def mem_available_mb():
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'): return int(line.split()[1])//1024
    return None
def json_profile_check():
    p=subprocess.run(['/userdata/system/el_gordo_tools/controller_dispatcher','--diagnose'],capture_output=True,text=True,timeout=20)
    if p.returncode: raise RuntimeError('DISPATCHER_DIAGNOSE_FAILED:'+p.stderr[-300:])
    d=json.loads(p.stdout); prof=d.get('profiles',{}).get('arcade',{})
    got={x['arcade_player']:(x.get('usb_port'),x.get('path')) for x in prof.get('players',[])}
    expected={'P1':('5','/dev/input/event17'),'P2':('6','/dev/input/event18'),
              'P3':('8','/dev/input/event20'),'P4':('7','/dev/input/event19')}
    if prof.get('duplicates') or got!=expected: raise RuntimeError('P1_P4_MAPPING_REGRESSION:'+repr(got))
    q=subprocess.run(['sdl2-jstest','--list'],capture_output=True,text=True,timeout=20)
    if q.returncode or 'Found 4 joystick(s)' not in q.stdout: raise RuntimeError('P1_P4_DEVICE_COUNT_REGRESSION')
    paths=re.findall(r"Joystick Path:\s+'([^']+)'",q.stdout)
    if paths!=['/dev/input/event17','/dev/input/event18','/dev/input/event19','/dev/input/event20']:
        raise RuntimeError('SDL_DEVICE_ORDER_REGRESSION:'+repr(paths))
    return {'dispatcher':'PASS','duplicates':False,'players':got,'sdl_paths':paths}
def mame_preflight(shortname):
    rom=Path('/userdata/roms/mame')/(shortname+'.zip')
    if not rom.is_file() or not os.access(rom,os.R_OK): return False,'ZIP_NOT_PRESENT_OR_READABLE'
    prefix=[MAME,'-noreadconfig','-rompath','/userdata/roms/mame;/userdata/bios',
      '-cfg_directory','/tmp/mame_batch3_cfg','-nvram_directory','/tmp/mame_batch3_nvram',
      '-input_directory','/tmp/mame_batch3_input','-state_directory','/tmp/mame_batch3_state',
      '-snapshot_directory','/tmp/mame_batch3_snap','-diff_directory','/tmp/mame_batch3_diff',
      '-comment_directory','/tmp/mame_batch3_comment','-share_directory','/tmp/mame_batch3_share']
    v=subprocess.run(prefix+['-verifyroms',shortname],cwd='/tmp',capture_output=True,text=True,timeout=45)
    output=v.stdout+'\n'+v.stderr
    if v.returncode or re.search(r'romset\s+'+re.escape(shortname)+r'\s+is good',output,re.I) is None:
        return False,'VERIFYROM:'+re.sub(r'\s+',' ',output)[-400:]
    x=subprocess.run(prefix+['-listxml',shortname],cwd='/tmp',capture_output=True,text=True,timeout=45)
    if x.returncode: return False,'LISTXML_FAILED:'+x.stderr[-300:]
    try:
        root=ET.fromstring(x.stdout)
        machine=next(m for m in root.findall('machine') if m.get('name')==shortname)
    except Exception as e: return False,'DRIVER_NOT_FOUND_IN_LISTXML:'+str(e)
    if machine.get('runnable','yes')=='no' or machine.get('isbios')=='yes' or machine.get('isdevice')=='yes':
        return False,'NOT_A_RUNNABLE_GAME_DRIVER'
    if machine.findall('disk'):
        return False,'DISK_MEDIA_REQUIRED'
    if machine.findall('biosset'):
        return False,'BIOS_SET_PRESENT_REQUIRES_SEPARATE_VERIFICATION'
    return True,'DRIVER_AND_ROMSET_VERIFIED'
def corrected_pool(rows):
    use=[r for r in rows if r.get('system')=='mame' and r.get('recommended_action')=='USE_MAME_CORE_X']
    by={r['shortname']:r for r in use}
    target=[r for r in use if r['shortname'] not in EXCLUDED]
    return use,by,target
def health_checkpoint(start_dmesg,es_before):
    temp=pilot.host_health(start_dmesg,es_before)
    mapping=json_profile_check()
    mem=mem_available_mb()
    if mem is not None and mem<512: raise RuntimeError('CRITICAL_LOW_MEMORY:'+str(mem)+'MB')
    active=[p for p in sr.proc_list() if p['comm'].lower() in ('retroarch','mame','emulatorlauncher','controller_dispatcher','selector_controles')]
    if active: raise RuntimeError('ORPHAN_OR_DUPLICATE_LAUNCH_PROCESSES:'+repr(active))
    return {'cpu_temp_c':temp,'mem_available_mb':mem,'mapping':mapping,'launch_processes':active,'checked_at':stamp()}
def backup_matrix_once():
    BACKUP_DIR.mkdir(parents=True,exist_ok=True)
    backup=BACKUP_DIR/'arcade_core_compatibility.csv.pre_batch3'
    if not backup.exists(): shutil.copy2(MATRIX,backup)
    return {'path':str(backup),'sha256':sha_file(backup)}
def update_matrix(results,backup_info):
    rows=matrix_rows()
    prior={}
    for fn,key in [('pilot_checkpoint.json','results'),('pilot_batch2_checkpoint.json','results')]:
        d=json.loads((OUT/fn).read_text(encoding='utf-8'))
        for x in d.get(key,[]):
            name=x.get('game')
            if name and x.get('boot') not in ('SKIP_WRONG_STRATEGY',): prior[name]=x
    for x in results: prior[x['shortname']]=x
    explicit_tested=set(prior)
    fields=list(rows[0].keys()) if rows else []
    new_fields=['tested_default_core','tested_mame_current','tested_fbneo','not_tested_target_core',
                'mame_current_result','mame_current_tested_at','mame_current_restore']
    for name in new_fields:
        if name not in fields: fields.append(name)
    for r in rows:
        n=r.get('shortname','')
        r['tested_default_core']='YES' if r.get('current_core')=='mame078plus' and r.get('current_result')=='GAME_DRIVER_NOT_FOUND' else 'UNKNOWN'
        r['tested_mame_current']='YES' if n in explicit_tested else 'NO'
        r['tested_fbneo']='NO' if n in FBNEO_RESERVED else 'UNKNOWN'
        r['not_tested_target_core']='NO' if n in explicit_tested else 'YES'
        if n in prior:
            x=prior[n]
            r['mame_current_result']=x.get('boot') or x.get('classification') or x.get('boot_status','')
            r['mame_current_tested_at']=x.get('tested_at') or x.get('started_at','')
            r['mame_current_restore']=x.get('restore') or x.get('restore_verified','')
    tmp=MATRIX.with_suffix('.csv.batch3.tmp')
    with tmp.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    os.replace(tmp,MATRIX)
def classify(result):
    boot=result.get('boot','')
    if boot=='BOOT_OK': return 'BOOT_PASS'
    text=(result.get('detail','')+' '+str(result.get('health_status',''))+' '+str(result.get('health_signal',''))).lower()
    if 'chd' in text and any(t in text for t in ('missing','not found','required')): return 'MISSING_CHD'
    if 'bios' in text and any(t in text for t in ('missing','not found','required')): return 'MISSING_BIOS'
    if any(t in text for t in ('parent','romof')) and any(t in text for t in ('missing','not found')): return 'MISSING_PARENT'
    if 'game driver not found' in text: return 'CORE_DRIVER_REJECTED'
    if any(t in text for t in ('sigsegv','sigsegmentation','segmentation fault','signal 11')): return 'SIGSEGV'
    if any(t in text for t in ('romset','crc mismatch','wrong crc','wrong size','mismatch')): return 'ROMSET_MISMATCH'
    if any(t in text for t in ('required rom','missing rom','not found','no such file','missing content')): return 'MISSING_ROM_MEMBER'
    if 'fatal' in text: return 'MAME_FATAL'
    if result.get('duration',0)<3: return 'IMMEDIATE_EXIT'
    if 'timeout' in text: return 'TIMEOUT'
    return 'UNKNOWN'
def persist(cp): atomic_json(CHECKPOINT,cp)
def main():
    if CHECKPOINT.exists():
        prior=json.loads(CHECKPOINT.read_text(encoding='utf-8'))
        raise RuntimeError('BATCH3_CHECKPOINT_ALREADY_EXISTS; no automatic resume or relaunch: '+str(prior.get('phase')))
    started=stamp(); rows=matrix_rows(); use,by,pool=corrected_pool(rows)
    prepared=json.loads(PREFLIGHT.read_text(encoding='utf-8'))
    pre={x['shortname']:x for x in prepared['preflight']}
    if len(use)!=61 or len(pool)!=56: raise RuntimeError(f'POOL_RECONCILIATION_MISMATCH:{len(use)}/{len(pool)}')
    report1=(OUT/'ARCADE_CORE_PILOT_RESULTS.md').read_text(encoding='utf-8')
    report2=(OUT/'ARCADE_CORE_PILOT_BATCH2_RESULTS.md').read_text(encoding='utf-8')
    if any(f'| {n} |' not in report1 for n in TESTED_B1) or any(f'| {n} |' not in report2 for n in TESTED_B2|FBNEO_RESERVED):
        raise RuntimeError('PILOT_REPORT_RECONCILIATION_FAILED')
    for n in SELECTED:
        if n not in by or n not in pre or pre[n]['verify']!='PASS': raise RuntimeError('SELECTED_NOT_PREFLIGHT_VERIFIED:'+n)
        if n in EXCLUDED or n in active_overrides(): raise RuntimeError('SELECTED_ALREADY_TESTED_OR_OVERRIDDEN:'+n)
    if not Path(CORE).is_file() or not Path(MAME).is_file(): raise RuntimeError('MAME_CURRENT_CORE_OR_PREFLIGHT_TOOL_MISSING')
    cp0,bp,baseline=sr.ensure_backup_valid()
    current=sr.snapshot_all()
    if state_without_conf(current)!=state_without_conf(baseline['protected_snapshot']):
        raise RuntimeError('INITIAL_PROTECTED_BASELINE_DRIFT_OUTSIDE_BATOCERA_CONF')
    if set(active_overrides())!=EXPECTED_OVERRIDES: raise RuntimeError('ACTIVE_OVERRIDE_SET_MISMATCH:'+repr(active_overrides()))
    b2cp=json.loads((OUT/'pilot_batch2_checkpoint.json').read_text(encoding='utf-8'))
    b2backup=Path((OUT/'pilot_batch2_backup_path.txt').read_text(encoding='utf-8').strip())
    expected_conf=(b2backup/'batocera.conf').read_bytes()
    for n in b2cp.get('kept_overrides',[]):
        line=f'mame["{n}.zip"].core=mame\n'.encode()
        if expected_conf and not expected_conf.endswith(b'\n'): expected_conf+=b'\n'
        expected_conf+=line
    if CONF.read_bytes()!=expected_conf: raise RuntimeError('CONFIG_DIFF_NOT_EXPLAINED_BY_BATCH1_BATCH2_OVERRIDES')
    # Verify global default through the active EmulationStation system definition.
    escfg=Path('/userdata/system/configs/emulationstation/es_systems_el_gordo.cfg').read_text(errors='replace')
    if '<core default="true">mame078plus</core>' not in escfg: raise RuntimeError('GLOBAL_CORE_DEFAULT_NOT_MAME078PLUS')
    pilot.MAME_GAMES=SELECTED
    pilot.STATE=STATE
    pilot.CORE_PATH=CORE
    STATE.mkdir(parents=True,exist_ok=True)
    initial_conf=CONF.read_bytes(); conf_meta=CONF.stat()
    initial_copy=STATE/'batocera.conf.batch3.initial'
    if not initial_copy.exists(): shutil.copy2(CONF,initial_copy)
    if sha_file(initial_copy)!=sha_bytes(initial_conf): raise RuntimeError('INITIAL_CONFIG_BACKUP_MISMATCH')
    backup_info=backup_matrix_once()
    dmesg0=sr.read_dmesg(); es0=sr.es_pids()
    if not es0 or sr.api_idle() is not True or sr.api_game() is not None: raise RuntimeError('ES_NOT_IDLE_OR_PID_MISSING')
    pilot.idle_check(baseline)
    m0=json_profile_check()
    cp={'batch':'MAME_BATCH3','phase':'IN_PROGRESS','started_at':started,
       'sources':{'compatibility_csv_sha256':sha_file(MATRIX),'preflight_json_sha256':sha_file(PREFLIGHT),
         'pilot_batch1_report':str(OUT/'ARCADE_CORE_PILOT_RESULTS.md'),'pilot_batch2_report':str(OUT/'ARCADE_CORE_PILOT_BATCH2_RESULTS.md')},
       'pool_target_core_untested':len(pool),'pool_shortnames':[r['shortname'] for r in pool],
       'preflight_considered':len(prepared['preflight']),
       'preflight_pass':sum(x['verify']=='PASS' for x in prepared['preflight']),
       'skip_preflight':[x for x in prepared['preflight'] if x['verify']!='PASS'],
       'selected':SELECTED,'launches':[],'passes':[],'failures':[],'skips':[],
       'overrides_before':active_overrides(),'overrides_added':[],'overrides_removed':[],
       'baseline':{'backup_path':str(bp),'backup_manifest_sha256':sha_file(bp/'MANIFEST_SHA256.txt'),
         'protected_baseline_sha256':sha_file(OUT/'protected_baseline.json'),
         'protected_entries':len(baseline['protected_snapshot']),
         'initial_conf_sha256':sha_bytes(initial_conf),'initial_conf_backup':str(initial_copy)},
       'restore_verified_count':0,'restore_required_count':0,
       'system_before':{'es_pids':es0,'api_idle':True,'api_game':None,'mapping':m0,
         'cpu_temp_c':sr.cpu_temp_max(),'mem_available_mb':mem_available_mb(),'global_core':'mame078plus'},
       'prior_config_reconciled_to_b1_b2':True,
       'system_checkpoints':[],'matrix_backup':backup_info,'error':None}
    persist(cp)
    for index,n in enumerate(SELECTED,1):
        row=by[n]; rom=Path('/userdata/roms/mame')/(n+'.zip')
        ok,why=mame_preflight(n)
        if not ok:
            x={'shortname':n,'name':row.get('name'),'reason':why,'status':'SKIP_PREFLIGHT','time':stamp()}
            cp['skips'].append(x); persist(cp); continue
        if not rom.is_file():
            cp['skips'].append({'shortname':n,'name':row.get('name'),'reason':'ZIP_NOT_FOUND','status':'SKIP_PREFLIGHT','time':stamp()}); persist(cp); continue
        # Per-game config backup and protected-state fingerprint precede temporary override.
        folder=STATE/n; folder.mkdir(parents=True,exist_ok=True)
        conf_before=folder/'batocera.conf.before'
        shutil.copy2(CONF,conf_before)
        conf_hash=sha_file(conf_before); rom_hash=sha_file(rom)
        pre_state=sr.snapshot_all(); pre_nonconf=canonical_state_hash(state_without_conf(pre_state))
        pilot.idle_check(baseline)
        started_game=stamp(); start_dmesg=sr.read_dmesg(); start_es=sr.es_pids()
        print(f'[{index}/{len(SELECTED)}] START {n} {row.get("name")}',flush=True)
        state={'kept_overrides':[],'reverted_overrides':[]}
        try:
            result=pilot.run_game(n,row,bp,baseline,state)
        except Exception as e:
            cp['phase']='PAUSED_SAFETY'; cp['error']=f'{type(e).__name__}: {e}'; cp['stopped_at']=stamp()
            cp['overrides_after']=active_overrides(); persist(cp)
            print('BATCH3_PAUSED',cp['error'],flush=True)
            break
        post_state=sr.snapshot_all(); post_nonconf=canonical_state_hash(state_without_conf(post_state))
        restore_ok=(result.get('restore')=='VERIFIED' and pre_nonconf==post_nonconf and
                    sha_file(rom)==rom_hash and sha_file(conf_before)==conf_hash)
        result_record={'shortname':n,'name':row.get('name'),'source':'USE_MAME_CORE_X; MAME078PLUS driver rejection; no prior MAME-current launch',
          'core_default':'mame078plus','core_test':'mame current libretro','core_path':result.get('core_path'),
          'started_at':started_game,'pid':result.get('health_pid'),'duration_seconds':result.get('duration'),
          'exit_code':result.get('exit_code'),'retroarch_result':result.get('health_status'),
          'mame_result':classify(result),'boot_status':result.get('boot'),'override':result.get('override'),
          'override_diff':result.get('override_diff'),'restore_verified':'YES' if restore_ok else 'NO',
          'restore_delta':{'before_nonconfig_sha256':pre_nonconf,'after_nonconfig_sha256':post_nonconf},
          'rom_sha256_before':rom_hash,'rom_unchanged':sha_file(rom)==rom_hash,
          'config_backup':str(conf_before),'config_sha256_before':conf_hash,
          'detail':result.get('detail',''),'health_core':result.get('health_core'),
          'health_emulator':result.get('health_emulator'),'health_status':result.get('health_status'),
          'players':row.get('players'),'buttons':row.get('buttons'),'control_type':row.get('control_type'),
          'input_class':result.get('input'),'tested_at':result.get('tested_at') or stamp(),
          'cleanup':result.get('cleanup'),'source_crc':row.get('romset_status')}
        cp['launches'].append(result_record); cp['restore_required_count']+=1
        if restore_ok: cp['restore_verified_count']+=1
        if result_record['boot_status']=='BOOT_OK' and result_record['restore_verified']=='YES' and result_record['cleanup']=='CLEANUP_OK':
            result_record['classification']='BOOT_PASS_SPECIAL_CONTROL' if result.get('input')=='SPECIAL_CONTROL' else 'BOOT_PASS'
            if result_record['players'] and int(result_record['players'])>=3:
                result_record['multiplayer_physical_test']='REQUIRED'
            if 'fight' in result_record['name'].lower() or 'kinst' in n:
                try:
                    if int(result_record['buttons'])<=6: result_record['fighting_physical_test']='REQUIRED'
                except (TypeError,ValueError): pass
            if result_record['classification']=='BOOT_PASS_SPECIAL_CONTROL':
                result_record['control_certification']='PENDING'
            cp['passes'].append(result_record)
        else:
            result_record['classification']=classify(result); cp['failures'].append(result_record)
        if result_record['override']=='KEPT': cp['overrides_added'].append(n)
        elif result_record['override']=='REVERTED': cp['overrides_removed'].append(n)
        cp['overrides_after']=active_overrides(); cp['last_completed']=n
        # Matrix update records only evidence from the B1/B2 reports and this actual launch.
        update_matrix(cp['launches'],backup_info)
        persist(cp)
        print(f'[{index}/{len(SELECTED)}] {result_record["classification"]} restore={restore_ok} cleanup={result_record["cleanup"]} detail={result_record["detail"][:200]}',flush=True)
        if not restore_ok:
            cp['phase']='PAUSED_SAFETY'; cp['error']='RESTORE_VERIFIED_NO'; cp['stopped_at']=stamp(); persist(cp); break
        if index%5==0:
            try:
                cp['system_checkpoints'].append(health_checkpoint(dmesg0,es0)); persist(cp)
            except Exception as e:
                cp['phase']='PAUSED_SAFETY'; cp['error']=f'HEALTH_REGRESSION: {type(e).__name__}: {e}'; cp['stopped_at']=stamp(); persist(cp); break
    if cp['phase']=='IN_PROGRESS': cp['phase']='COMPLETE'
    cp['finished_at']=stamp(); cp['overrides_after']=active_overrides()
    # Exact config delta: only per-game overrides for BOOT_PASS results may remain.
    expected=initial_conf
    for x in cp['passes']:
        line=f'mame["{x["shortname"]}.zip"].core=mame\n'.encode()
        if expected and not expected.endswith(b'\n'): expected+=b'\n'
        expected+=line
    cp['global_core_unchanged']=('<core default="true">mame078plus</core>' in escfg and b'mame.core=' not in CONF.read_bytes())
    cp['config_delta_exact']=CONF.read_bytes()==expected
    if not cp['config_delta_exact']:
        cp['phase']='PAUSED_SAFETY'; cp['error']='UNEXPECTED_BATOCERA_CONF_DELTA'
    try:
        final_health=pilot.host_health(dmesg0,es0)
        final_procs=[p for p in sr.proc_list() if p['comm'].lower() in ('retroarch','mame','emulatorlauncher','controller_dispatcher','selector_controles')]
        if final_procs: raise RuntimeError('FINAL_ORPHAN_OR_DUPLICATE_PROCESS:'+repr(final_procs))
        cp['system_after']={'es_pids':sr.es_pids(),'api_idle':sr.api_idle(),'api_game':sr.api_game(),
          'target_processes':pilot.active_pilot_processes(),'cpu_temp_c':sr.cpu_temp_max(),
          'mem_available_mb':mem_available_mb(),'mapping':json_profile_check(),
          'health_gate':'PASS','final_health_temp_c':final_health,'launch_processes':final_procs,
          'global_core':'mame078plus' if cp['global_core_unchanged'] else 'REGRESSION'}
    except Exception as e:
        cp['phase']='PAUSED_SAFETY'; cp['error']='FINAL_HEALTH_CHECK_FAILED:'+str(e)
    update_matrix(cp['launches'],backup_info); persist(cp)
    write_report(cp)
    print(json.dumps({'phase':cp['phase'],'pool':cp['pool_target_core_untested'],'preflight_pass':cp['preflight_pass'],
      'skipped_preflight':len(cp['skip_preflight']),'launched':len(cp['launches']),'pass':len(cp['passes']),
      'fail':len(cp['failures']),'restore':f'{cp["restore_verified_count"]}/{cp["restore_required_count"]}',
      'overrides_after':cp['overrides_after'],'config_delta_exact':cp['config_delta_exact']},ensure_ascii=False),flush=True)
def write_report(cp):
    lines=['# MAME Batch 3 — pruebas por override individual','',f'- Inicio: {cp["started_at"]}',f'- Fin: {cp["finished_at"]}',
      '- Core global: `mame078plus`, sin cambios. Core objetivo: `/usr/lib/libretro/mame_libretro.so` (MAME actual).',
      '- Ruta: EmulationStation → controller_dispatcher → launcher oficial → RetroArch. Sin input inyectado.',
      '- Corrección aplicada: intento con `mame078plus` cuenta como `TESTED_DEFAULT_CORE`, pero no como `TESTED_MAME_CURRENT`.',
      f'- Pool reconciliado `USE_MAME_CORE_X`: {len(cp["pool_shortnames"])+5}; ya probados con MAME actual excluidos: B1 5, B2 10; pool sin prueba target: {cp["pool_target_core_untested"]}.',
      f'- Preflight MAME 0.285: {cp["preflight_considered"]} considerados; {cp["preflight_pass"]} `-verifyroms` PASS; {len(cp["skip_preflight"])} omitidos por contenido/no dump.',
      f'- Selección: {len(cp["selected"])} (los candidatos normales pasaron primero; se añaden juegos reales con control especial porque no hay 20 candidatos normales).',
      f'- Backup saves/NVRAM/config protegido: `{cp["baseline"]["backup_path"]}`; baseline y `MANIFEST_SHA256.txt` verificados.',
      '', '## Preflight omitidos']
    for x in cp['skip_preflight']:
      lines.append(f'- `{x["shortname"]}` — {x["reason"]}')
    lines+=['','## Resultados de lanzamientos','',
      '| Shortname | Nombre | Inicio | PID | s | Exit | RetroArch | MAME/clasificación | Override | Restore | Evidencia |',
      '|---|---|---|---:|---:|---:|---|---|---|---|---|']
    for x in cp['launches']:
      lines.append(f'| {x["shortname"]} | {x["name"]} | {x["started_at"]} | {x["pid"]} | {x["duration_seconds"]} | {x["exit_code"]} | {x["retroarch_result"]} | {x["mame_result"]}/{x["classification"]} | {x["override"]} | {x["restore_verified"]} | {x["detail"].replace("|","/")[:240]} |')
    lines+=['','## Resumen',f'- PASS: {len(cp["passes"])}; FAIL: {len(cp["failures"])}; lanzados: {len(cp["launches"])}.',
      f'- Overrides nuevos retenidos: {", ".join(cp["overrides_added"]) or "ninguno"}. Fallidos revertidos: {", ".join(cp["overrides_removed"]) or "ninguno"}.',
      f'- Restore: {cp["restore_verified_count"]}/{cp["restore_required_count"]}. P1-P4 mapping verificado; esto no certifica controles físicos.',
      f'- Estado final: {cp["phase"]}; core global sin cambio: {cp["global_core_unchanged"]}; diff de configuración limitado a PASS: {cp["config_delta_exact"]}.',
      '- Los juegos especiales quedan como `BOOT_PASS_SPECIAL_CONTROL` cuando pasen; no implican compatibilidad con la botonera estándar.',
      '- Multijugador físico y controles de pelea permanecen pendientes. No se declara `CONTROL_CERTIFIED`.',
      '- No se inició BATCH 4.','']
    REPORT.write_text('\n'.join(lines),encoding='utf-8')
if __name__=='__main__': main()
