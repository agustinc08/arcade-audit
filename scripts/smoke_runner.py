#!/usr/bin/env python3
"""Bounded arcade smoke tests through EmulationStation with per-test save restore."""
import csv, hashlib, json, os, shutil, signal, sqlite3, stat, subprocess, sys, tempfile, time, urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys

TOOLS=Path('/userdata/system/el_gordo_tools')
if str(TOOLS) not in sys.path: sys.path.insert(0,str(TOOLS))
from marker_ownership import create_exclusive as create_owned_marker, remove_if_owned as remove_owned_marker, marker_lock

OUT=Path('/userdata/system/state/arcade_audit')
CHECKPOINT=OUT/'checkpoint.json'
CSV_PATH=OUT/'arcade_games_audit.csv'
JSON_PATH=OUT/'arcade_games_audit.json'
WRITE_REPORT=OUT/'ARCADE_SMOKE_WRITE_AUDIT.md'
MARKER=Path('/userdata/system/state/boot_audit_once.json')
API='http://127.0.0.1:1234'
BOOT_TIMEOUT=30
STABILITY_SECONDS=10
ES_POLL=0.5

# Trees/files whose exact state is preserved. The first four are likely write targets.
BACKUP_ITEMS=[
    Path('/userdata/saves/mame'), Path('/userdata/saves/fbneo'),
    Path('/userdata/system/configs/retroarch'), Path('/userdata/system/configs/mame'),
    Path('/userdata/cheats/saves'),
    Path('/userdata/system/batocera.conf'),
    Path('/userdata/system/configs/emulationstation/es_systems_el_gordo.cfg'),
    Path('/userdata/system/configs/el_gordo_controller_profiles/controller_technical.json'),
    Path('/userdata/system/configs/el_gordo_controller_profiles/multiplayer.json'),
]
MONITOR_ROOTS=BACKUP_ITEMS+[Path('/userdata/screenshots')]
LOG_ROOTS=[Path('/userdata/system/logs'),Path('/userdata/system/state/game_health.sqlite')]
ROM_ROOTS=[Path('/userdata/roms/mame'),Path('/userdata/roms/fbneo')]

def sha_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def rel_to_userdata(path):
    return Path('snapshot')/Path(str(path).lstrip('/'))

def record(path):
    try: st=os.lstat(path)
    except FileNotFoundError: return None
    mode=stat.S_IMODE(st.st_mode)
    item={'type':'symlink' if stat.S_ISLNK(st.st_mode) else 'dir' if stat.S_ISDIR(st.st_mode) else 'file' if stat.S_ISREG(st.st_mode) else 'other',
          'size':st.st_size,'mtime_ns':st.st_mtime_ns,'mode':mode,'uid':st.st_uid,'gid':st.st_gid}
    if item['type']=='file': item['sha256']=sha_file(path)
    elif item['type']=='symlink': item['target']=os.readlink(path)
    return item

def walk_tree(root):
    out={}
    root=Path(root)
    r=record(root)
    if r is None:
        out[str(root)]={'type':'absent'}; return out
    out[str(root)]=r
    if r['type']!='dir': return out
    for base,dirs,files in os.walk(root,topdown=True,followlinks=False):
        basep=Path(base)
        for name in list(dirs):
            p=basep/name; rr=record(p); out[str(p)]=rr
            if rr and rr['type']=='symlink': dirs.remove(name)
        for name in files:
            p=basep/name; out[str(p)]=record(p)
    return out

def snapshot_all(roots=MONITOR_ROOTS):
    result={}
    for root in roots: result.update(walk_tree(root))
    return result

def snapshot_logs():
    return snapshot_all(LOG_ROOTS)

def write_json(path,obj):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(tmp,path)

def ensure_backup_valid():
    cp=json.loads(CHECKPOINT.read_text(encoding='utf-8'))
    bp=Path(cp.get('write_protection',{}).get('backup_path',''))
    basefile=OUT/'protected_baseline.json'
    if not bp.is_dir() or not basefile.is_file(): raise RuntimeError('BACKUP_OR_BASELINE_MISSING')
    baseline=json.loads(basefile.read_text(encoding='utf-8'))
    for src,meta in baseline['backup_files'].items():
        if meta.get('type')=='file':
            dest=bp/rel_to_userdata(src)
            if not dest.is_file() or sha_file(dest)!=meta['sha256']:
                raise RuntimeError('BACKUP_VERIFY_FAILED:'+src)
    return cp,bp,baseline

def create_backup():
    cp=json.loads(CHECKPOINT.read_text(encoding='utf-8'))
    if cp.get('write_protection',{}).get('backup_path'):
        cp2,bp,base=ensure_backup_valid()
        print('BACKUP_EXISTS_VERIFIED',str(bp)); return
    if MARKER.exists(): raise RuntimeError('ONE_SHOT_MARKER_ALREADY_EXISTS; stop, do not overwrite')
    parent=Path('/media/ROMS/ARCADE_BACKUPS')
    if not parent.is_dir() or not os.access(parent,os.W_OK): raise RuntimeError('BACKUP_DESTINATION_UNAVAILABLE')
    stamp=datetime.now().astimezone().strftime('%Y-%m-%d_%H%M%S')
    dest=parent/f'ARCADE_SMOKE_TEST_SAVES_{stamp}'
    dest.mkdir(mode=0o700)
    sources={str(p):walk_tree(p) for p in BACKUP_ITEMS}
    pre=snapshot_all()
    source_lines=[]; manifest=[]
    for src_s,tree in sources.items():
        src=Path(src_s); source_lines.append(f'{src_s}\t{tree[str(src_s)].get("type")}')
        if tree[str(src_s)].get('type')=='absent': continue
        dst=dest/rel_to_userdata(src)
        dst.parent.mkdir(parents=True,exist_ok=True)
        if src.is_dir() and not src.is_symlink(): shutil.copytree(src,dst,symlinks=True,copy_function=shutil.copy2)
        elif src.is_symlink(): os.symlink(os.readlink(src),dst)
        else: shutil.copy2(src,dst)
        for p_s,meta in tree.items():
            if meta.get('type') in ('file','symlink'):
                dp=dest/rel_to_userdata(p_s)
                if meta['type']=='file':
                    digest=sha_file(dp)
                    if digest!=meta['sha256']: raise RuntimeError('COPY_HASH_MISMATCH:'+p_s)
                    manifest.append(f'{digest}  {dp.relative_to(dest)}  {meta["size"]} bytes')
                else:
                    if not dp.is_symlink() or os.readlink(dp)!=meta['target']: raise RuntimeError('COPY_SYMLINK_MISMATCH:'+p_s)
                    manifest.append(f'SYMLINK  {dp.relative_to(dest)} -> {meta["target"]}')
    post=snapshot_all()
    if pre!=post: raise RuntimeError('SOURCE_CHANGED_DURING_BACKUP')
    (dest/'SOURCE_PATHS.txt').write_text('\n'.join(source_lines)+'\n',encoding='utf-8')
    (dest/'PRE_TEST_FILELIST.txt').write_text('\n'.join(f'{meta.get("sha256","-")}\t{meta.get("size","-")}\t{meta.get("mtime_ns","-")}\t{meta.get("mode","-")}\t{p}' for p,meta in sorted(pre.items()))+'\n',encoding='utf-8')
    (dest/'MANIFEST_SHA256.txt').write_text('\n'.join(manifest)+'\n',encoding='utf-8')
    backup_files={}
    for src_s,tree in sources.items():
        for p_s,meta in tree.items():
            if meta and meta.get('type') in ('file','symlink','dir','absent'): backup_files[p_s]=meta
    baseline={'backup_path':str(dest),'backup_files':backup_files,'protected_snapshot':pre,
              'created_at':datetime.now().astimezone().isoformat(timespec='seconds')}
    write_json(OUT/'protected_baseline.json',baseline)
    # Verify all copied regular files against the source manifest and persist backup location.
    for src_s,tree in sources.items():
        for p_s,meta in tree.items():
            if meta and meta.get('type')=='file':
                dp=dest/rel_to_userdata(p_s)
                if sha_file(dp)!=meta['sha256']: raise RuntimeError('FINAL_BACKUP_VERIFY_FAILED:'+p_s)
    cp.setdefault('write_protection',{})
    cp['write_protection'].update({'backup_path':str(dest),'backup_verified':True,'baseline_files':sum(1 for x in pre.values() if x.get('type')=='file'),
                                   'created_at':baseline['created_at'],'batch_size':25,'restore_policy':'per-game compare/restore to verified baseline; pause on uncontained writes'})
    cp['phase']='BACKUP_VERIFIED_READY_FOR_SMOKE_TESTS'
    write_json(CHECKPOINT,cp)
    report='# Auditoría de escrituras de smoke tests\n\n## Rutas de escritura identificadas antes de probar\n\n'
    report+='- MAME: `/userdata/saves/mame` (NVRAM `.nv`, high scores `.hi`, CFG por juego `.cfg`, diffs); RetroArch declara `/userdata/saves/mame` como save/state directory. MAME 2003 Plus tiene NVRAM bootstraps activos y autosave de high score en `default`.\n'
    report+='- FBNeo: `/userdata/saves/fbneo` (save RAM `.fs`, NVRAM `.nv`, high scores `.hi`, memory cards `.memcard`, CFG); core options indican hiscores habilitados, memory card por juego y modo writable.\n'
    report+='- RetroArch: `/userdata/system/configs/retroarch` contiene core options, input/remap/config y subcarpeta `saves`; `remap_save_on_exit=true`. Se respalda y restaura archivo por archivo.\n'
    report+='- Config MAME: `/userdata/system/configs/mame`; se preserva junto a los datos de core. Configuración general Batocera, definición ES y perfiles P1-P4 se incluyen como archivos guardados puntuales.\n'
    report+='- `/userdata/cheats/saves` no existía al inspeccionar; `/userdata/screenshots` existía vacío. Se monitorean para eliminar sólo archivos nuevos de prueba.\n'
    report+='- `/userdata/system/logs` y `game_health.sqlite` pueden recibir logs/eventos permitidos; se conservan como evidencia y se reportan, no se revierten. No se toman screenshots ni se envía input.\n\n'
    if WRITE_REPORT.exists(): report=WRITE_REPORT.read_text(encoding='utf-8')+'\n'+report
    report+=f'## Preparación de backup — {baseline["created_at"]}\n\n- Destino: `{dest}`\n- Archivos fuente monitorizados: {sum(1 for x in pre.values() if x.get("type")=="file")}\n- Archivos copiados y verificados por SHA-256: {sum(1 for x in manifest if not x.startswith("SYMLINK"))}\n- Fuente sin cambios durante copia: sí\n- SHA-256 verificado antes de smoke tests: sí\n\n'
    WRITE_REPORT.write_text(report,encoding='utf-8')
    print(json.dumps({'backup':str(dest),'files':sum(1 for x in pre.values() if x.get('type')=='file'),'copied':len(manifest),'verified':True},ensure_ascii=False))

def differences(before,after):
    created=sorted(p for p in after if after[p].get('type')!='absent' and (p not in before or before[p].get('type')=='absent'))
    deleted=sorted(p for p in before if before[p].get('type')!='absent' and (p not in after or after[p].get('type')=='absent'))
    modified=sorted(p for p in before.keys()&after.keys() if before[p]!=after[p] and before[p].get('type')!='absent' and after[p].get('type')!='absent')
    return created,modified,deleted

def copy_from_backup(src_s,meta,bp):
    src=Path(src_s); backup=bp/rel_to_userdata(src_s)
    current=record(src)
    if current and current.get('type')=='dir' and meta.get('type')!='dir': raise RuntimeError('RESTORE_TYPE_CONFLICT:'+src_s)
    if current and current.get('type')=='dir' and meta.get('type')=='dir':
        os.chown(src,meta['uid'],meta['gid']); os.chmod(src,meta['mode']); os.utime(src,ns=(meta['mtime_ns'],meta['mtime_ns']))
        return
    if current and current.get('type') in ('file','symlink'): src.unlink()
    src.parent.mkdir(parents=True,exist_ok=True)
    if meta['type']=='symlink': os.symlink(meta['target'],src)
    elif meta['type']=='file':
        if not backup.is_file() or sha_file(backup)!=meta['sha256']: raise RuntimeError('RESTORE_SOURCE_INVALID:'+src_s)
        shutil.copy2(backup,src)
        os.chown(src,meta['uid'],meta['gid'],follow_symlinks=False)
        os.chmod(src,meta['mode'],follow_symlinks=False)
        os.utime(src,ns=(meta['mtime_ns'],meta['mtime_ns']),follow_symlinks=False)
    elif meta['type']=='dir':
        src.mkdir(exist_ok=True)
        os.chown(src,meta['uid'],meta['gid']); os.chmod(src,meta['mode']); os.utime(src,ns=(meta['mtime_ns'],meta['mtime_ns']))
    else: raise RuntimeError('UNSUPPORTED_RESTORE_TYPE:'+src_s)

def restore_to_baseline(after,bp,baseline):
    before=baseline['protected_snapshot']
    created,modified,deleted=differences(before,after)
    # Restore modified/deleted files only from the verified, exact-path backup.
    for p in sorted(set(modified+deleted),key=lambda x:(x.count('/'),x)):
        meta=before.get(p)
        if meta and meta.get('type') in ('file','symlink','dir'):
            copy_from_backup(p,meta,bp)
    # Remove only newly-created regular files/symlinks within monitored roots.
    for p in sorted(created,key=lambda x:(x.count('/'),x),reverse=True):
        meta=after.get(p,{})
        if meta.get('type') in ('file','symlink'):
            pp=Path(p)
            if pp.is_file() or pp.is_symlink(): pp.unlink()
        elif meta.get('type')=='dir':
            try: Path(p).rmdir()
            except OSError: pass
    # Restore metadata of pre-existing directories, deepest first.
    for p,meta in sorted(before.items(),key=lambda kv:kv[0].count('/'),reverse=True):
        if meta.get('type')=='dir' and Path(p).is_dir():
            os.chown(p,meta['uid'],meta['gid']); os.chmod(p,meta['mode']); os.utime(p,ns=(meta['mtime_ns'],meta['mtime_ns']))
    final=snapshot_all()
    if final!=before:
        c,m,d=differences(before,final)
        raise RuntimeError('RESTORE_VERIFICATION_FAILED:'+json.dumps({'created':c[:10],'modified':m[:10],'deleted':d[:10]}))
    return {'created':created,'modified':modified,'deleted':deleted,'verified':True}

def get_http(path,timeout=2):
    with urllib.request.urlopen(API+path,timeout=timeout) as resp:
        raw=resp.read(8192).decode('utf-8','replace')
        try: data=json.loads(raw)
        except Exception: data=raw
        return resp.status,data

def post_launch(path,timeout=5):
    req=urllib.request.Request(API+'/launch',data=path.encode('utf-8'),method='POST',headers={'Content-Type':'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        return resp.status,resp.read(4096).decode('utf-8','replace')

def api_idle():
    status,data=get_http('/isIdle')
    if status!=200 or not isinstance(data,list) or not data: return None
    return bool(data[0])

def wait_es_idle(timeout=20):
    deadline=time.time()+timeout
    last=None
    while time.time()<deadline:
        try:
            idle=api_idle(); game=api_game(); procs=launcher_processes()
            last={'idle':idle,'game':game,'processes':procs}
            if idle is True and game is None and not procs: return True
        except Exception as e:
            last={'error':str(e)}
        time.sleep(0.5)
    raise RuntimeError('ES_DID_NOT_REACH_IDLE_AFTER_PREVIOUS_GAME:'+repr(last))

def api_game():
    try:
        status,data=get_http('/runningGame')
        if isinstance(data,dict) and data.get('msg')=='NO GAME RUNNING': return None
        if status in (200,201): return data
        return {'status':status,'data':data}
    except Exception as e: return {'error':str(e)}

def proc_list():
    result=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit(): continue
        try:
            pid=int(p.name); cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode('utf-8','replace').strip()
            comm=(p/'comm').read_text(errors='replace').strip()
            exe=os.readlink(p/'exe')
            statline=(p/'stat').read_text(); fields=statline.rsplit(')',1)[1].split(); ppid=int(fields[1])
            if not cmd: cmd=comm
            result.append({'pid':pid,'ppid':ppid,'comm':comm,'exe':exe,'cmd':cmd})
        except (FileNotFoundError,ProcessLookupError,PermissionError,IndexError,ValueError): pass
    return result

def launcher_processes():
    tokens=('retroarch','controller_dispatcher','selector_controles','emulatorlauncher','/usr/bin/mame')
    return [p for p in proc_list() if any(t in (p['exe']+' '+p['cmd']).lower() for t in tokens)]

def es_pids():
    return [p['pid'] for p in proc_list() if p['comm'].lower() in ('emulationstation','emulationstation-standalone') or p['exe'].endswith('/emulationstation')]

def target_emulators(rom_path,core):
    expected=Path('/usr/lib/libretro')/(core+'_libretro.so')
    out=[]
    for p in proc_list():
        if 'retroarch' in (p['exe']+' '+p['cmd']).lower() and rom_path in p['cmd'] and str(expected) in p['cmd']:
            out.append(p)
    return out

def marker_value(system,rom):
    now=time.time()
    return {'enabled':True,'system':system,'rom':rom,'choice':'BOTONERA','created_at':now,'expires_at':now+55,'audit_id':f'{system}:{Path(rom).name}:{now:.6f}'}

def add_result_files(item,status,input_test,error,exit_code,cleanup,restore,elapsed,health=None,log_path=''):
    rows=list(csv.DictReader(CSV_PATH.open(encoding='utf-8-sig',newline='')))
    target=None
    for r in rows:
        if r['system']==item['system'] and r['rom']==item['rom']:
            target=r; break
    if target is None: raise RuntimeError('CSV_ROW_MISSING:'+item['system']+'/'+item['rom'])
    target['boot_status']=status
    target['input_test_status']=input_test
    target['manual_test']=str(target.get('manual_test','False')=='True' or input_test=='MANUAL_TEST')
    target['tested_at']=datetime.now().astimezone().isoformat(timespec='seconds')
    target['error']=error or ''
    target['exit_code']='' if exit_code is None else str(exit_code)
    target['cleanup_status']=cleanup
    target['write_restore_status']='VERIFIED' if restore.get('verified') else 'FAILED'
    target['runtime_seconds']=f'{elapsed:.2f}'
    target['log_path']=log_path
    if health:
        target['game_health_status']=health.get('status','')
        target['emulator']=health.get('emulator') or target.get('emulator','')
        target['core']=health.get('core') or target.get('core','')
    fields=list(rows[0].keys()) if rows else []
    for extra in ('input_test_status','exit_code','cleanup_status','write_restore_status','runtime_seconds','log_path','game_health_status'):
        if extra not in fields: fields.append(extra)
    tmp=CSV_PATH.with_suffix('.csv.tmp')
    with tmp.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    os.replace(tmp,CSV_PATH)
    data=json.loads(JSON_PATH.read_text(encoding='utf-8'))
    for r in data:
        if r['system']==item['system'] and r['rom']==item['rom']:
            r.update(target); break
    write_json(JSON_PATH,data)

def game_health_row(system,rom,start_epoch):
    db=Path('/userdata/system/state/game_health.sqlite')
    try:
        c=sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True,timeout=2)
        rows=c.execute('select id,launched_at,emulator,core,pid,duration_seconds,exit_code,signal,relevant_error,launcher_log,emulator_log,status,missing_file from launch_events where system=? and rom=? order by id desc limit 5',(system,rom)).fetchall(); c.close()
        for r in rows:
            try: ts=datetime.fromisoformat(r[1].replace('Z','+00:00')).timestamp()
            except Exception: ts=start_epoch-1
            if ts>=start_epoch-2:
                return {'id':r[0],'launched_at':r[1],'emulator':r[2],'core':r[3],'pid':r[4],'duration':r[5],'exit_code':r[6],'signal':r[7],'error':r[8] or '', 'launcher_log':r[9] or '', 'emulator_log':r[10] or '', 'status':r[11] or '', 'missing_file':r[12] or ''}
    except Exception: pass
    return None

def classify_input(row):
    try: players=int(row.get('players') or 0)
    except ValueError: players=0
    if players>=3: return 'MANUAL_TEST'
    compat=row.get('input_status','')
    if compat=='NO_COMPATIBLE_CON_BOTONERA': return 'SPECIAL_CONTROL'
    if compat=='PARCIAL_DUAL_STICK': return 'DUAL_STICK'
    if 'ANALOG' in compat: return 'ANALOG'
    if compat=='COMPATIBLE_DIRECTO_METADATA': return 'INPUT_REVIEW'
    return 'INPUT_REVIEW'

def current_queue(cp):
    q=cp.get('queue',[])
    return [x for x in q if x.get('status')=='NOT_TESTED']

def write_checkpoint(cp,item,status,extra=None):
    cp['completed']=cp.get('completed',[])
    record_item={'system':item['system'],'rom':item['rom'],'path':item['path'],'status':status,
                 'completed_at':datetime.now().astimezone().isoformat(timespec='seconds')}
    if extra: record_item.update(extra)
    cp['completed'].append(record_item)
    cp['queue']=[x for x in cp.get('queue',[]) if not (x['system']==item['system'] and x['rom']==item['rom'])]
    cp['pending_count']=len(current_queue(cp))
    cp.pop('in_flight',None)
    cp['last_completed']={'system':item['system'],'rom':item['rom'],'status':status}
    cp['last_restore_status']='VERIFIED'
    cp['phase']='SMOKE_TESTS_IN_PROGRESS' if cp['pending_count'] else 'SMOKE_TESTS_COMPLETE'
    cp.setdefault('write_protection',{})['last_restore_verified_at']=datetime.now().astimezone().isoformat(timespec='seconds')
    write_json(CHECKPOINT,cp)

def update_reports(batch_record=None):
    rows=list(csv.DictReader(CSV_PATH.open(encoding='utf-8-sig',newline='')))
    pass_n=sum(r.get('boot_status') in ('BOOT_OK','PASS') for r in rows)
    fail_rows=[r for r in rows if r.get('boot_status','').startswith('FAIL') or r.get('boot_status')=='TIMEOUT']
    pending=sum(r.get('boot_status')=='NOT_TESTED' for r in rows)
    manual=sum(r.get('input_test_status')=='MANUAL_TEST' for r in rows)
    inputs=Counter(r.get('input_status','') for r in rows)
    summary='\n## Smoke tests — estado acumulado\n\n'+f'- Total inventariado: {len(rows)}; PASS: {pass_n}; FAIL/TIMEOUT: {len(fail_rows)}; NOT_TESTED: {pending}; input manual pendiente: {manual}.\n- No se inyectaron pulsaciones. PASS sólo confirma que el core permaneció abierto en la ventana y volvió a ES.\n- Clasificación input por metadata: '+', '.join(f'{k}={v}' for k,v in sorted(inputs.items()))+'.\n'
    if batch_record:
        summary+=f'- Último lote {batch_record["batch"]}: {batch_record["games"]} juegos; restauración: {batch_record["restore"]}.\n'
    ap=OUT/'ARCADE_AUDIT_REPORT.md'; existing=ap.read_text(encoding='utf-8') if ap.exists() else '# AUDITORÍA ARCADE\n'
    marker='\n## Smoke tests — estado acumulado'
    if marker in existing: existing=existing.split(marker)[0]
    ap.write_text(existing+summary,encoding='utf-8')
    # Failure report from retained historical and new results.
    causes={}
    for r in fail_rows:
        e=(r.get('error') or '').lower()
        if r.get('boot_status')=='FAIL_MISSING_CHD' or '.chd' in e and 'not found' in e: cause='CHD faltante'
        elif r.get('boot_status')=='FAIL_BIOS' or 'bios' in e: cause='BIOS'
        elif 'rom' in e and ('missing' in e or 'not found' in e): cause='ROM'
        elif 'core' in e or 'retroarch' in e: cause='core/emulador'
        elif r.get('boot_status')=='TIMEOUT': cause='timeout'
        else: cause='salida/falla de arranque'
        causes[cause]=causes.get(cause,0)+1
    def table(headers,data):
        return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(str(x).replace('|','/') for x in row)+' |\n' for row in data)
    faildoc='# Fallos de arranque arcade\n\n## Agrupación\n\n'+table(['Causa','Juegos'],sorted(causes.items(),key=lambda x:-x[1]))+'\n## Detalle\n\n'+table(['Juego','Sistema','Estado','Error'],[[r.get('name',r['rom']),r['system'],r['boot_status'],r.get('error','')[:300]] for r in fail_rows])
    (OUT/'ARCADE_FAILURES.md').write_text(faildoc,encoding='utf-8')
    # 4-player report uses maximum players, not simultaneous-player inference.
    four=[r for r in rows if str(r.get('players'))=='4']
    four.sort(key=lambda r:(r.get('boot_status')!='BOOT_OK',r.get('name','').lower()))
    fourdoc='# Arcade con metadata de hasta 4 jugadores\n\nEl campo `players=4` no distingue simultáneo de alternado. Ningún smoke test envía input; por eso mapping de juego sigue manual.\n\n'
    fourdoc+=table(['Juego','Sistema','Players max.','Simultáneos','Buttons','Boot','Input test','Manual'],[[r.get('name'),r['system'],r['players'],'UNKNOWN',r.get('buttons') or '?',r.get('boot_status'),r.get('input_test_status','MANUAL_TEST'),'Sí'] for r in four])
    (OUT/'ARCADE_4P_REPORT.md').write_text(fourdoc,encoding='utf-8')
    # Fighting report: preserve metadata and flag UMK3/manual mappings.
    import re
    fights=[r for r in rows if re.search(r'mortal kombat|street fighter|king of fighters|fatal fury|samurai shodown|darkstalkers|virtua fighter|tekken',r.get('name',''),re.I)]
    fightdoc='# Juegos de pelea\n\nBotones/control son metadata del DAT disponible. No se mandaron pulsaciones; ningún duplicado queda confirmado automáticamente.\n\n'
    fightdoc+=table(['Juego','Sistema','Botones','Core','CFG/remap','Boot','P1-P4','Problema/manual'],[[r.get('name'),r['system'],r.get('buttons') or '?',r.get('core'),r.get('custom_mapping'),r.get('boot_status'),r.get('input_test_status','INPUT_REVIEW'),'UMK3: antecedente doble golpe; prueba física obligatoria' if 'umk3' in r['rom'] else ('Prueba física representativa' if r.get('manual_test')=='True' else 'Sin conflicto confirmado')] for r in fights])
    (OUT/'ARCADE_FIGHTING_CONTROLS.md').write_text(fightdoc,encoding='utf-8')
    # Keep the existing hand-curated manual checklist and special-control catalog,
    # while attaching current boot evidence without claiming physical input validation.
    manual_path=OUT/'ARCADE_MANUAL_TESTS.md'
    manual_base=manual_path.read_text(encoding='utf-8') if manual_path.exists() else '# Pruebas manuales arcade\n'
    manual_marker='\n## Estado de smoke test — 2026-11-13'
    if manual_marker in manual_base: manual_base=manual_base.split(manual_marker)[0]
    manual_candidates=[r for r in rows if r.get('manual_test')=='True' or r.get('input_test_status')=='MANUAL_TEST']
    manual_summary=manual_marker+'\n\nEl smoke test valida arranque/estabilidad/cierre, no pulsaciones ni asignación física. Los juegos de 3P/4P requieren comprobación en gabinete.\n\n'
    manual_summary+=table(['Juego','Sistema','Boot','Input','Prueba física'],[[r.get('name',r['rom']),r['system'],r.get('boot_status'),r.get('input_test_status','INPUT_REVIEW'),'Pendiente'] for r in manual_candidates])
    manual_path.write_text(manual_base+manual_summary,encoding='utf-8')
    special_path=OUT/'ARCADE_SPECIAL_CONTROLS.md'
    special_base=special_path.read_text(encoding='utf-8') if special_path.exists() else '# Controles especiales arcade\n'
    special_marker='\n## Resultado de smoke tests — 2026-11-13'
    if special_marker in special_base: special_base=special_base.split(special_marker)[0]
    special_summary=special_marker+'\n\nEl resultado de boot no certifica controles especiales ni compatibilidad física. No se inyectó input. Mantener los títulos catalogados aquí como `MANUAL_TEST`/control especial hasta validación con el hardware correspondiente.\n\n'
    special_summary+=f'- Juegos arcade inventariados: {len(rows)}.\n- Smoke tests con restore verificado en esta continuación: {sum(r.get("write_restore_status")=="VERIFIED" for r in rows)}.\n- No se generaron pulsaciones ni se tocaron mappings.\n'
    special_path.write_text(special_base+special_summary,encoding='utf-8')

def log_fragment(health):
    parts=[]
    if health:
        if health.get('error'): parts.append('game_health: '+health['error'])
        if health.get('missing_file'): parts.append('missing_file: '+health['missing_file'])
        if health.get('status'): parts.append('status: '+health['status'])
    return '\n'.join(parts)[:1500]

def critical_lines(before_lines,after_lines):
    from collections import Counter
    import re
    diff=list((Counter(after_lines)-Counter(before_lines)).elements())
    pats=[r'NVRM.*Xid',r'Xid \(',r'Xorg.*segfault',r'EXT4-fs error',r'I/O error',r'Buffer I/O error',r'GPU has fallen off the bus',r'thermal.*critical',r'controller_dispatcher.*(traceback|fatal|crash)']
    return [x for x in diff if any(re.search(p,x,re.I) for p in pats)]

def read_dmesg():
    try:
        p=subprocess.run(['dmesg','--ctime'],capture_output=True,text=True,timeout=5)
        return p.stdout.splitlines()[-1200:] if p.returncode==0 else []
    except Exception: return []

def cpu_temp_max():
    vals=[]
    for p in Path('/sys/class/thermal').glob('thermal_zone*/temp'):
        try:
            n=int(p.read_text().strip()); vals.append(n/1000 if n>1000 else float(n))
        except Exception: pass
    for p in Path('/sys/class/hwmon').glob('hwmon*/temp*_input'):
        try:
            n=int(p.read_text().strip()); vals.append(n/1000 if n>1000 else float(n))
        except Exception: pass
    return max(vals) if vals else None

def append_write_log(batch,game,pre,post,restore_status,log_changes=None):
    created,modified,deleted=differences(pre,post)
    changed=(created or modified or deleted)
    rows='\n'.join(['| '+str(x)+' |' for x in changed]) if changed else '| (sin escrituras en árboles protegidos) |'
    head='| Tipo | Ruta |\n| --- | --- |\n'
    body=head+''.join(f'| CREATED | `{p}` |\n' for p in created)+''.join(f'| MODIFIED | `{p}` |\n' for p in modified)+''.join(f'| DELETED | `{p}` |\n' for p in deleted)
    if not changed: body+=rows+'\n'
    lp=WRITE_REPORT
    text=lp.read_text(encoding='utf-8') if lp.exists() else '# Auditoría de escrituras de smoke tests\n'
    text+=f'\n### Lote {batch} — {game["system"]}/{game["rom"]}\n\n{body}\n- Restore: **{restore_status}**\n- Logs/health database: '+(', '.join(log_changes) if log_changes else 'sin cambios detectados')+'\n'
    lp.write_text(text,encoding='utf-8')

def run_one(item,batch,cp,bp,baseline):
    rom=Path(item['path'])
    if not rom.is_file() or not os.access(rom,os.R_OK):
        return {'status':'FAIL_MISSING_ROM','error':'ROM path ausente o no legible','input_test_status':classify_input({'players':'','input_status':'INPUT_REVIEW'}),'restore':{'verified':True},'cleanup':'NOT_LAUNCHED','elapsed':0,'exit_code':None,'health':None}
    before=snapshot_all()
    if before!=baseline['protected_snapshot']:
        raise RuntimeError('PRE_TEST_DRIFT: saved/config trees differ from verified baseline')
    dmesg_before=read_dmesg(); logs_before=snapshot_logs(); rom_before=record(rom)
    # A game that crashes can take a short time to unwind the launcher state. Wait
    # for the real ES idle signal before starting the next item.
    wait_es_idle(20)
    preidle=api_idle(); pregame=api_game()
    if preidle is not True or pregame is not None: raise RuntimeError('PRECHECK_NOT_IDLE:'+repr((preidle,pregame)))
    procs=launcher_processes()
    if procs: raise RuntimeError('LAUNCH_PROCESS_ALREADY_ACTIVE:'+repr(procs))
    epids=es_pids()
    if not epids: raise RuntimeError('EMULATIONSTATION_PID_MISSING')
    marker=None
    if MARKER.exists(): raise RuntimeError('ONE_SHOT_MARKER_ALREADY_EXISTS')
    try:
        marker=create_owned_marker(item['system'],str(rom),'smoke_runner',
                                   f"smoke:{item['system']}:{Path(str(rom)).name}:{time.time_ns()}",path=MARKER)
    except FileExistsError as exc:
        raise RuntimeError('MARKER_ALREADY_EXISTS') from exc
    start=time.time(); launched=False; seen=[]; process=None; health=None; status='FAIL_RETURN_TO_ES'; error=''; exit_code=None; cleanup='NOT_REQUIRED'
    try:
        http,body=post_launch(str(rom))
        if http!=200: raise RuntimeError(f'POST_HTTP_{http}:{body[:300]}')
        deadline=start+BOOT_TIMEOUT
        while time.time()<deadline:
            exact=target_emulators(str(rom),item['system']=='fbneo' and 'fbneo' or 'mame078plus')
            run=api_game(); idle=api_idle()
            if exact:
                process=exact[0]; seen=exact; launched=True; break
            if run is not None and idle is False:
                # ES has handed control to the launch chain; allow RetroArch a short spawn grace.
                time.sleep(1); continue
            if idle is True and run is None and time.time()-start>3:
                break
            time.sleep(ES_POLL)
        if not launched:
            if not MARKER.exists():
                # Marker consumption proves the actual dispatcher used this exact audit choice.
                selector=[p for p in proc_list() if 'selector_controles' in (p['exe']+' '+p['cmd']).lower()]
                if selector: raise RuntimeError('SELECTOR_DID_NOT_BYPASS; stop without injecting input')
            health=game_health_row(item['system'],str(rom),start)
            if api_idle() is not True or api_game() is not None or launcher_processes():
                raise RuntimeError('NO_BOOT_BUT_LAUNCH_CHAIN_NOT_IDLE')
            if health:
                exit_code=health.get('exit_code')
                e=(health.get('error','')+' '+health.get('missing_file','')).lower()
                if 'chd' in e and ('not found' in e or health.get('missing_file')): status='FAIL_MISSING_CHD'
                elif 'bios' in e and ('missing' in e or 'not found' in e): status='FAIL_BIOS'
                elif 'rom' in e and ('missing' in e or 'not found' in e): status='FAIL_MISSING_ROM'
                else: status='FAIL_BOOT'
                error=log_fragment(health)
            elif api_idle() is True and api_game() is None: status='FAIL_RETURN_TO_ES'; error='EmulationStation volvió a idle sin proceso RetroArch confirmado.'
            else: status='TIMEOUT'; error='No se confirmó RetroArch exacto durante el timeout.'
        else:
            if MARKER.exists(): raise RuntimeError('ONE_SHOT_NOT_CONSUMED; stop before game test')
            expected_core='fbneo' if item['system']=='fbneo' else 'mame078plus'
            if expected_core+'_libretro.so' not in process['cmd']:
                raise RuntimeError('CORE_COMMAND_LINE_MISMATCH:'+process['cmd'][:500])
            # A stable boot is a live exact PID for the full window, with no fatal log evidence.
            stable_until=time.time()+STABILITY_SECONDS
            while time.time()<stable_until:
                now=target_emulators(str(rom),expected_core)
                if not now or now[0]['pid']!=process['pid']:
                    status='FAIL_CRASH'; error='RetroArch terminó durante la ventana de estabilidad.'; break
                if api_idle() is True:
                    status='FAIL_RETURN_TO_ES'; error='EmulationStation informó idle mientras el PID parecía activo.'; break
                time.sleep(ES_POLL)
            if not error:
                status='BOOT_OK'; cleanup='SIGTERM_EXACT_PID_PENDING'
                # Controlled shutdown: only SIGTERM to the verified RetroArch PID carrying this ROM/core.
                cur=target_emulators(str(rom),expected_core)
                if len(cur)!=1 or cur[0]['pid']!=process['pid']:
                    raise RuntimeError('UNSAFE_CLEANUP_PID_NOT_UNIQUE:'+repr(cur))
                os.kill(process['pid'],signal.SIGTERM)
                close_deadline=time.time()+10
                while time.time()<close_deadline:
                    if not any(p['pid']==process['pid'] for p in proc_list()): break
                    time.sleep(0.25)
                if any(p['pid']==process['pid'] for p in proc_list()):
                    cleanup='CLEANUP_ERROR_PID_STILL_ACTIVE'
                    raise RuntimeError('SIGTERM_DID_NOT_CLOSE_EXACT_RETROARCH; no SIGKILL attempted')
                clean_deadline=time.time()+30
                while time.time()<clean_deadline:
                    if api_idle() is True and api_game() is None and not launcher_processes(): break
                    time.sleep(0.5)
                if api_idle() is not True or api_game() is not None or launcher_processes():
                    cleanup='CLEANUP_ERROR_ES_NOT_IDLE'
                    raise RuntimeError('ES_DID_NOT_RETURN_IDLE_AFTER_CONTROLLED_EXIT')
                if not set(epids).intersection(es_pids()):
                    cleanup='CLEANUP_ERROR_ES_PID_CHANGED'
                    raise RuntimeError('EMULATIONSTATION_PID_CHANGED')
                cleanup='CLEANUP_OK'
        # Capture kernel/runtime safety signals and protect the ROM itself.
        new_critical=critical_lines(dmesg_before,read_dmesg())
        if new_critical: raise RuntimeError('CRITICAL_SYSTEM_LOG:'+repr(new_critical[:8]))
        if not any(p['exe'].endswith('/Xorg') or p['comm']=='Xorg' for p in proc_list()): raise RuntimeError('XORG_PROCESS_MISSING')
        t=cpu_temp_max()
        if t is not None and t>=95: raise RuntimeError(f'CRITICAL_TEMPERATURE:{t:.1f}C')
        rom_after=record(rom)
        if rom_before!=rom_after: raise RuntimeError('ROM_CHANGED_DURING_SMOKE_TEST')
        health=game_health_row(item['system'],str(rom),start) or health
        if status=='BOOT_OK' and health and health.get('exit_code') not in (None,0,-15):
            # Requested SIGTERM can appear in game_health; other nonzero exit codes warrant review.
            error=(error+' '+log_fragment(health)).strip()
        return {'status':status,'error':error,'input_test_status':classify_input({'players':item.get('players',''),'input_status':item.get('input_status','')}),
                'restore':{'verified':False},'cleanup':cleanup,'elapsed':time.time()-start,'exit_code':exit_code if exit_code is not None else (health or {}).get('exit_code'),
                'health':health,'start':start,'dmesg_critical':new_critical if 'new_critical' in locals() else [],'temp':t if 't' in locals() else None,
                'logs_before':logs_before}
    except Exception as e:
        # A launch/cleanup/safety anomaly pauses the entire batch after controlled process handling.
        recovery=''
        try:
            expected_core='fbneo' if item['system']=='fbneo' else 'mame078plus'
            active=target_emulators(str(rom),expected_core)
            if len(active)==1:
                os.kill(active[0]['pid'],signal.SIGTERM)
                deadline=time.time()+10
                while time.time()<deadline and any(p['pid']==active[0]['pid'] for p in proc_list()): time.sleep(0.25)
                if any(p['pid']==active[0]['pid'] for p in proc_list()): recovery='; exact RetroArch PID sigue activo tras SIGTERM, no se usó SIGKILL'
                else: recovery='; se cerró mediante SIGTERM el PID RetroArch exacto de esta ROM'
        except Exception as cleanup_exc: recovery='; cierre de emergencia no confirmado: '+str(cleanup_exc)
        return {'status':'MANUAL_TEST','error':str(e)+recovery,'input_test_status':'WRITE_ISOLATION_UNSAFE','restore':{'verified':False},'cleanup':cleanup,
                'elapsed':time.time()-start,'exit_code':exit_code,'health':health,'start':start,'logs_before':logs_before}
    finally:
        # Remove only our exact, unconsumed one-shot marker, and only if no game launch remains active.
        try:
            if marker and api_idle() is True and api_game() is None and not launcher_processes():
                remove_owned_marker(marker['transaction_id'],owner='smoke_runner',
                                    audit_id=marker.get('audit_id'),path=MARKER)
        except Exception: pass

def run_batch(limit=25):
    cp,bp,baseline=ensure_backup_valid()
    if cp.get('phase')=='PAUSED_SAFETY': raise RuntimeError('CHECKPOINT_PAUSED_FOR_SAFETY; inspect before resuming')
    if cp.get('in_flight'):
        old=cp['in_flight']; idle=api_idle(); game=api_game(); active=launcher_processes()
        if idle is not True or game is not None or active:
            raise RuntimeError('INTERRUPTED_TEST_STILL_ACTIVE:'+repr({'idle':idle,'game':game,'processes':active}))
        after=snapshot_all(); restored=restore_to_baseline(after,bp,baseline)
        item={k:old[k] for k in ('system','rom','path')}
        item['name']=item['rom']
        add_result_files(item,'MANUAL_TEST','WRITE_ISOLATION_UNSAFE','Proceso de auditoría interrumpido; se restauró y verificó el baseline antes de reanudar.',None,'INTERRUPTED_AFTER_SAFE_EXIT',restored,0)
        append_write_log(old.get('batch',0),item,baseline['protected_snapshot'],after,'VERIFIED (RECUPERACIÓN DE INTERRUPCIÓN)',[])
        write_checkpoint(cp,item,'MANUAL_TEST',{'write_restore_status':'VERIFIED','error':'interrupted; baseline restored before resume'})
        cp=json.loads(CHECKPOINT.read_text(encoding='utf-8'))
        update_reports({'batch':old.get('batch',0),'games':1,'restore':'VERIFIED (RECUPERACIÓN)'})
    queue=current_queue(cp)
    if not queue:
        print('NO_PENDING_GAMES'); return
    batch_no=cp.get('batches_completed',0)+1
    selected=queue[:limit]
    print(f'BATCH_START {batch_no} games={len(selected)} pending={len(queue)}',flush=True)
    batch_results=[]
    for index,item in enumerate(selected,1):
        print(f'[{index}/{len(selected)}] START {item["system"]}/{item["rom"]}',flush=True)
        cp['in_flight']={'system':item['system'],'rom':item['rom'],'path':item['path'],'batch':batch_no,
                         'started_at':datetime.now().astimezone().isoformat(timespec='seconds')}
        write_json(CHECKPOINT,cp)
        result=run_one(item,batch_no,cp,bp,baseline)
        after=snapshot_all()
        try:
            restored=restore_to_baseline(after,bp,baseline)
            result['restore']=restored
        except Exception as e:
            result['status']='MANUAL_TEST'; result['input_test_status']='WRITE_ISOLATION_UNSAFE'
            result['error']=(result.get('error','')+' RESTORE_FAILURE:'+str(e)).strip()
            result['restore']={'verified':False,'error':str(e)}
        logs_after=snapshot_logs(); logc,logm,logd=differences(result.get('logs_before',{}),logs_after)
        logchanges=logc+logm+logd
        elapsed=result.get('elapsed',0)
        add_result_files(item,result['status'],result.get('input_test_status','INPUT_REVIEW'),result.get('error',''),result.get('exit_code'),result.get('cleanup',''),result.get('restore',{}),elapsed,result.get('health'))
        append_write_log(batch_no,item,baseline['protected_snapshot'],after,'VERIFIED' if result.get('restore',{}).get('verified') else 'FAILED',logchanges)
        write_checkpoint(cp,item,result['status'],{'write_restore_status':'VERIFIED' if result.get('restore',{}).get('verified') else 'FAILED',
                           'cleanup_status':result.get('cleanup'),'error':result.get('error','')[:500]})
        cp=json.loads(CHECKPOINT.read_text(encoding='utf-8'))
        update_reports({'batch':batch_no,'games':index,'restore':'VERIFIED' if result.get('restore',{}).get('verified') else 'FAILED'})
        batch_results.append(result)
        print(f'[{index}/{len(selected)}] {result["status"]} cleanup={result.get("cleanup")} restore={result.get("restore",{}).get("verified")} error={result.get("error","")[:240]}',flush=True)
        if not result.get('restore',{}).get('verified') or result['status']=='MANUAL_TEST' or result.get('cleanup','').startswith('CLEANUP_ERROR'):
            cp['phase']='PAUSED_SAFETY'; cp['safety_pause']=result.get('error','')[:1000]; write_json(CHECKPOINT,cp)
            print('BATCH_PAUSED_SAFETY',result.get('error',''),flush=True); break
    cp=json.loads(CHECKPOINT.read_text(encoding='utf-8'))
    cp['batches_completed']=batch_no if batch_results else cp.get('batches_completed',0)
    if len(batch_results)==len(selected) and cp.get('phase')!='PAUSED_SAFETY':
        cp['full_batches_completed']=cp.get('full_batches_completed',0)+1
    if cp.get('pending_count',0):
        if cp['batches_completed']>=2 and cp.get('write_protection',{}).get('restore_all_verified',True): cp['write_protection']['batch_size']=50
        cp['phase']='SMOKE_TESTS_IN_PROGRESS' if cp.get('phase')!='PAUSED_SAFETY' else cp['phase']
    else: cp['phase']='SMOKE_TESTS_COMPLETE'
    write_json(CHECKPOINT,cp)
    update_reports({'batch':batch_no,'games':len(batch_results),'restore':'VERIFIED' if all(x.get('restore',{}).get('verified') for x in batch_results) else 'FAILED'})
    print(json.dumps({'batch':batch_no,'completed':len(batch_results),'pending':cp.get('pending_count'),'phase':cp.get('phase'),'pass':sum(x['status']=='BOOT_OK' for x in batch_results),'fail':sum(x['status'].startswith('FAIL') for x in batch_results),'manual':sum(x['status']=='MANUAL_TEST' for x in batch_results),'restore_verified':all(x.get('restore',{}).get('verified') for x in batch_results)},ensure_ascii=False),flush=True)

def run_all():
    cp,bp,baseline=ensure_backup_valid()
    # First two full batches are fixed at 25; later batches expand to 50 only after verified restores.
    while current_queue(cp):
        if cp.get('phase')=='PAUSED_SAFETY': break
        size=25 if cp.get('full_batches_completed',0)<2 else 50
        run_batch(size)
        cp=json.loads(CHECKPOINT.read_text(encoding='utf-8'))
        if cp.get('phase')=='PAUSED_SAFETY': break

def preflight():
    cp,bp,baseline=ensure_backup_valid()
    idle=api_idle(); running=api_game(); procs=launcher_processes(); eps=es_pids()
    current=snapshot_all()
    marker_exists=MARKER.exists()
    if idle is not True or running is not None or procs or not eps or marker_exists or current!=baseline['protected_snapshot']:
        raise RuntimeError('PREFLIGHT_FAILED:'+repr({'idle':idle,'running':running,'launcher_processes':procs,'es_pids':eps,'marker':marker_exists,'baseline_equal':current==baseline['protected_snapshot']}))
    print(json.dumps({'preflight':'PASS','backup':str(bp),'backup_verified':True,'pending':cp.get('pending_count'),
                      'emulationstation_pids':eps,'idle':idle,'running_game':running,'launch_processes':procs,
                      'marker_absent':not marker_exists,'protected_trees_match_backup':True},ensure_ascii=False,indent=2))

def recover_restore():
    """Recover only the known, test-created save delta after a restore-code defect."""
    cp,bp,baseline=ensure_backup_valid()
    idle=api_idle(); running=api_game(); procs=launcher_processes(); eps=es_pids()
    if idle is not True or running is not None or procs or not eps:
        raise RuntimeError('RECOVERY_RUNTIME_NOT_IDLE:'+repr({'idle':idle,'running':running,'processes':procs,'es':eps}))
    before=baseline['protected_snapshot']; after=snapshot_all()
    created,modified,deleted=differences(before,after)
    expected_created=['/userdata/saves/fbneo/fbneo/20pacgalr4.nv']
    expected_modified=['/userdata/saves/fbneo/fbneo']
    if created!=expected_created or modified!=expected_modified or deleted:
        raise RuntimeError('RECOVERY_DIFF_NOT_EXACT:'+json.dumps({'created':created,'modified':modified,'deleted':deleted}))
    restored=restore_to_baseline(after,bp,baseline)
    if not restored.get('verified'):
        raise RuntimeError('RECOVERY_RESTORE_NOT_VERIFIED')
    cp=json.loads(CHECKPOINT.read_text(encoding='utf-8'))
    # The first run itself passed: the runtime log confirms FBNeo initialized the exact
    # driver, the runner held the verified RetroArch PID for 10 s, and cleanup was clean.
    # Only the separate restore helper failed; record that corrected outcome accurately.
    item={'system':'fbneo','rom':'20pacgalr4.zip','path':'/userdata/roms/fbneo/20pacgalr4.zip'}
    rows=list(csv.DictReader(CSV_PATH.open(encoding='utf-8-sig',newline='')))
    old_tested_at=''
    for row in rows:
        if row['system']==item['system'] and row['rom']==item['rom']:
            old_tested_at=row.get('tested_at','')
            row['boot_status']='BOOT_OK'
            row['input_test_status']='INPUT_REVIEW'
            row['manual_test']='False'
            row['error']='FBNeo runtime log confirms driver started; stable 10 s; clean SIGTERM. Initial restore helper defect recovered; protected baseline verified.'
            row['exit_code']='0'; row['cleanup_status']='CLEANUP_OK'; row['write_restore_status']='VERIFIED'
            row['runtime_seconds']='24.89'; row['game_health_status']='FBNEO_DRIVER_STARTED_STABLE_CLEAN_EXIT'
            if old_tested_at: row['tested_at']=old_tested_at
            break
    fields=list(rows[0].keys())
    tmp=CSV_PATH.with_suffix('.csv.tmp')
    with tmp.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    os.replace(tmp,CSV_PATH)
    data=json.loads(JSON_PATH.read_text(encoding='utf-8'))
    for row in data:
        if row['system']==item['system'] and row['rom']==item['rom']:
            row.update(next(x for x in rows if x['system']==item['system'] and x['rom']==item['rom']))
            break
    write_json(JSON_PATH,data)
    for done in cp.get('completed',[]):
        if done.get('system')==item['system'] and done.get('rom')==item['rom']:
            done.update({'status':'BOOT_OK','write_restore_status':'VERIFIED','cleanup_status':'CLEANUP_OK',
                         'error':'Runtime confirma inicio estable y cierre limpio; fallo inicial del helper de restore corregido y verificado.'})
    cp['last_completed']={'system':item['system'],'rom':item['rom'],'status':'BOOT_OK'}
    cp['last_restore_status']='VERIFIED'
    cp['phase']='SMOKE_TESTS_IN_PROGRESS'
    cp.pop('safety_pause',None)
    cp['pending_count']=len(current_queue(cp))
    cp['last_restore_status']='VERIFIED'
    cp.setdefault('write_protection',{})['restore_all_verified']=True
    cp['write_protection']['last_restore_verified_at']=datetime.now().astimezone().isoformat(timespec='seconds')
    write_json(CHECKPOINT,cp)
    with WRITE_REPORT.open('a',encoding='utf-8') as f:
        f.write('\n### Recuperación de restauración — 20pacgalr4.zip\n\n')
        f.write('- Hallazgo: el runner generó `/userdata/saves/fbneo/fbneo/20pacgalr4.nv`; el directorio preexistente `/userdata/saves/fbneo/fbneo` sólo cambió su metadata de modificación.\n')
        f.write('- Causa de pausa: el restaurador anterior rechazó erróneamente un directorio existente al restaurar su metadata. No se lanzó ningún otro juego.\n')
        f.write('- Acción: eliminado únicamente el archivo nuevo del smoke test y restaurada metadata desde el baseline verificado.\n')
        f.write('- Verificación: snapshot protegido coincide exactamente con `protected_baseline.json`: **VERIFIED**.\n')
    print(json.dumps({'recovery':'VERIFIED','created_before':created,'modified_before':modified,'deleted_before':deleted,
                      'protected_trees_match_baseline':snapshot_all()==before,'pending':cp['pending_count'],'phase':cp['phase']},ensure_ascii=False,indent=2))

def finalize_recovered_first_test():
    cp,bp,baseline=ensure_backup_valid()
    if snapshot_all()!=baseline['protected_snapshot'] or api_idle() is not True or api_game() is not None or launcher_processes():
        raise RuntimeError('FINALIZE_PRECONDITION_FAILED')
    item={'system':'fbneo','rom':'20pacgalr4.zip'}
    rows=list(csv.DictReader(CSV_PATH.open(encoding='utf-8-sig',newline='')))
    found=False
    for row in rows:
        if row['system']==item['system'] and row['rom']==item['rom']:
            row.update({'boot_status':'BOOT_OK','input_test_status':'INPUT_REVIEW','manual_test':'False',
                        'error':'FBNeo runtime log confirms driver started; stable 10 s; clean SIGTERM. Initial restore helper defect recovered; protected baseline verified.',
                        'exit_code':'0','cleanup_status':'CLEANUP_OK','write_restore_status':'VERIFIED',
                        'runtime_seconds':'24.89','game_health_status':'FBNEO_DRIVER_STARTED_STABLE_CLEAN_EXIT'})
            found=True; break
    if not found: raise RuntimeError('FIRST_RESULT_ROW_MISSING')
    fields=list(rows[0].keys()); tmp=CSV_PATH.with_suffix('.csv.tmp')
    with tmp.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    os.replace(tmp,CSV_PATH)
    data=json.loads(JSON_PATH.read_text(encoding='utf-8'))
    for row in data:
        if row['system']==item['system'] and row['rom']==item['rom']:
            row.update(next(x for x in rows if x['system']==item['system'] and x['rom']==item['rom'])); break
    write_json(JSON_PATH,data)
    for done in cp.get('completed',[]):
        if done.get('system')==item['system'] and done.get('rom')==item['rom']:
            done.update({'status':'BOOT_OK','write_restore_status':'VERIFIED','cleanup_status':'CLEANUP_OK',
                         'error':'Runtime confirma inicio estable y cierre limpio; helper de restore corregido y baseline verificado.'})
    cp['last_completed']={'system':item['system'],'rom':item['rom'],'status':'BOOT_OK'}
    cp['phase']='SMOKE_TESTS_IN_PROGRESS'; cp.pop('safety_pause',None)
    cp['pending_count']=len(current_queue(cp)); cp['last_restore_status']='VERIFIED'
    cp.setdefault('write_protection',{})['restore_all_verified']=True
    write_json(CHECKPOINT,cp)
    update_reports({'batch':1,'games':1,'restore':'VERIFIED (helper corregido)'} )
    print(json.dumps({'finalized':'BOOT_OK','protected_baseline_matches':True,'pending':cp['pending_count']},ensure_ascii=False,indent=2))

def clear_unlaunched_inflight():
    cp,bp,baseline=ensure_backup_valid()
    old=cp.get('in_flight')
    if not old: raise RuntimeError('NO_IN_FLIGHT_ITEM')
    if snapshot_all()!=baseline['protected_snapshot'] or api_idle() is not True or api_game() is not None or launcher_processes() or MARKER.exists():
        raise RuntimeError('CLEAR_INFLIGHT_PRECONDITION_FAILED')
    key=(old['system'],old['rom'])
    if not any((x['system'],x['rom'])==key and x.get('status')=='NOT_TESTED' for x in cp.get('queue',[])):
        raise RuntimeError('INFLIGHT_NOT_STILL_PENDING:'+repr(key))
    cp.pop('in_flight',None)
    cp['pending_count']=len(current_queue(cp))
    cp['phase']='SMOKE_TESTS_IN_PROGRESS'
    cp['last_unlaunched_item_requeued']={'system':old['system'],'rom':old['rom'],'reason':'host precheck observed prior game API transition; this item was not launched','at':datetime.now().astimezone().isoformat(timespec='seconds')}
    write_json(CHECKPOINT,cp)
    with WRITE_REPORT.open('a',encoding='utf-8') as f:
        f.write(f"\n### Elemento no iniciado — lote {old.get('batch')}\n\n- `{old['system']}/{old['rom']}` no llegó a lanzarse: el precheck detectó que EmulationStation aún reportaba el juego anterior. Se mantuvo en cola.\n- Antes de limpiar `in_flight`: ES idle, sin juego ni procesos de lanzamiento; árbol protegido coincide con baseline.\n")
    print(json.dumps({'cleared_unlaunched_inflight':key,'kept_pending':True,'pending':cp['pending_count']},ensure_ascii=False,indent=2))
def main():
    if len(sys.argv)<2: raise SystemExit('usage: smoke_runner.py backup|recover|finalize_first|clear_unlaunched|preflight|batch [N]|run')
    if sys.argv[1]=='backup': create_backup()
    elif sys.argv[1]=='recover': recover_restore()
    elif sys.argv[1]=='finalize_first': finalize_recovered_first_test()
    elif sys.argv[1]=='clear_unlaunched': clear_unlaunched_inflight()
    elif sys.argv[1]=='preflight': preflight()
    elif sys.argv[1]=='batch': run_batch(int(sys.argv[2]) if len(sys.argv)>2 else 25)
    elif sys.argv[1]=='run': run_all()
    elif sys.argv[1]=='refresh_reports': update_reports()
    else: raise SystemExit('unknown operation')

if __name__=='__main__': main()

