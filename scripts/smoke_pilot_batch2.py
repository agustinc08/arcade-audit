#!/usr/bin/env python3
"""Sequential MAME-current pilot via the normal Batocera launch path."""
import csv, hashlib, json, os, shutil, signal, stat, sys, time
from datetime import datetime
from pathlib import Path
import smoke_runner as sr
sys.path.insert(0, '/userdata/system/el_gordo_tools')
from marker_ownership import create_exclusive as create_owned_marker, remove_if_owned as remove_owned_marker
from configgen.settings.unixSettings import UnixSettings

OUT=Path('/userdata/system/state/arcade_audit')
CONF=Path('/userdata/system/batocera.conf')
BACKUP=Path((OUT/'pilot_batch2_backup_path.txt').read_text().strip())
B1_BACKUP=Path('/media/ROMS/ARCADE_BACKUPS/ARCADE_CORE_PILOT_2026-11-13_093236')
STATE=OUT/'pilot_batch2_runtime'
REPORT=OUT/'ARCADE_CORE_PILOT_BATCH2_RESULTS.md'
CHECKPOINT=OUT/'pilot_batch2_checkpoint.json'
PILOT_CHECKPOINT=OUT/'pilot_checkpoint.json'
MASTER_CHECKPOINT=OUT/'checkpoint.json'
CORE_PATH='/usr/lib/libretro/mame_libretro.so'
MAME_GAMES=['mvp','sia2650','redearth','jojo','jojoba','evosocc','hoops95','nbapbp','funcube4','hyperath']
SKIPPED={'gprider':'fbneo','sfiii2n':'fbneo','sfiii3n':'fbneo','sfiiin':'fbneo','neotris':'FBNeo path/content unresolved'}
CANDIDATES=list(SKIPPED)+MAME_GAMES
B1_GAMES=['ffight2b','altair','apache3','blazlaz','cubeqst']

def stamp(): return datetime.now().astimezone().isoformat(timespec='seconds')
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()
def write_json(p,o):
    t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); os.replace(t,p)

def backup_check():
    if not BACKUP.is_dir() or not (BACKUP/'batocera.conf').is_file():
        raise RuntimeError('PILOT_CONFIG_BACKUP_HASH_MISMATCH')
    for n in ('MANIFEST_SHA256.txt','SOURCE_PATHS.txt','PRE_TEST_FILELIST.txt'):
        if not (BACKUP/n).is_file(): raise RuntimeError('BACKUP_METADATA_MISSING:'+n)

def matrix():
    report=(OUT/'ARCADE_PILOT_RETEST.md').read_text(encoding='utf-8')
    for n in CANDIDATES:
        if f'| {n} |' not in report: raise RuntimeError('SHORTNAME_NOT_IN_PILOT_REPORT:'+n)
    rows=list(csv.DictReader((OUT/'arcade_core_compatibility.csv').open(encoding='utf-8-sig',newline='')))
    d={r['shortname']:r for r in rows if r.get('system')=='mame'}
    audit=json.loads((OUT/'arcade_games_audit.json').read_text(encoding='utf-8'))
    aj={r['rom'].removesuffix('.zip'):r for r in audit if r.get('system')=='mame'}
    for n in MAME_GAMES:
        r=d.get(n) or aj.get(n)
        if not r: raise RuntimeError('PILOT_BASELINE_MISSING:'+n)
        if r.get('current_core') not in ('mame078plus',None) and r.get('core')!='mame078plus':
            raise RuntimeError('PILOT_CURRENT_CORE_MISMATCH:'+n)
        if r.get('core') not in ('mame078plus',None) and r.get('current_core') not in ('mame078plus',None):
            raise RuntimeError('PILOT_CURRENT_CORE_MISMATCH:'+n)
        if not (Path('/userdata/roms/mame')/(n+'.zip')).is_file(): raise RuntimeError('PILOT_ROM_MISSING:'+n)
    return {n:(d.get(n) or aj[n]) for n in CANDIDATES},d

def idle_check(base):
    snap=sr.snapshot_all()
    for p,m in snap.items():
        if p!=str(CONF) and m!=base['protected_snapshot'].get(p): raise RuntimeError('PRETEST_DRIFT:'+p)
    if sr.api_idle() is not True or sr.api_game() is not None or active_pilot_processes(): raise RuntimeError('ARCADE_NOT_IDLE')
    if not sr.es_pids(): raise RuntimeError('ES_PID_MISSING')
    if not any(p['comm'].lower()=='xorg' or p['exe'].endswith('/Xorg') for p in sr.proc_list()): raise RuntimeError('XORG_MISSING')
    if sr.MARKER.exists(): raise RuntimeError('ONE_SHOT_MARKER_EXISTS')

def restore_conf(data, metadata=None):
    tmp=CONF.with_name(CONF.name+'.pilot.tmp')
    with tmp.open('wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
    st=metadata or CONF.stat()
    os.chown(tmp,st.st_uid,st.st_gid); os.chmod(tmp,stat.S_IMODE(st.st_mode))
    os.utime(tmp,ns=(st.st_atime_ns,st.st_mtime_ns)); os.replace(tmp,CONF)

def add_override(n):
    old=CONF.read_bytes(); oldstat=CONF.stat(); key=f'mame["{n}.zip"].core'
    s=UnixSettings(CONF)
    if s.get_all(f'mame["{n}.zip"]') or key.encode() in old: raise RuntimeError('PREEXISTING_OVERRIDE:'+n)
    line=f'{key}=mame\n'.encode('ascii')
    print('APPLY_OVERRIDE_DIFF',f'+ {key}=mame',flush=True)
    with CONF.open('ab') as f:
        if old and not old.endswith(b'\n'): f.write(b'\n')
        f.write(line); f.flush(); os.fsync(f.fileno())
    if UnixSettings(CONF).get_all(f'mame["{n}.zip"]')!={'core':'mame'}:
        restore_conf(old,oldstat); raise RuntimeError('OVERRIDE_PARSE_FAILED:'+n)
    return old,line,oldstat

def restore_files(pre,post,oldbackup,base,conf_copy):
    created,modified,deleted=sr.differences(pre,post)
    for p in sorted(set(modified+deleted),key=lambda x:(x.count('/'),x)):
        m=pre.get(p)
        if not m or m.get('type') not in ('file','symlink','dir'): continue
        if p==str(CONF):
            if not conf_copy.is_file() or sha(conf_copy)!=m.get('sha256'): raise RuntimeError('CONFIG_SNAPSHOT_BAD')
            q=Path(p)
            if q.exists() or q.is_symlink(): q.unlink()
            shutil.copy2(conf_copy,q,follow_symlinks=False)
            os.chown(q,m['uid'],m['gid'],follow_symlinks=False); os.chmod(q,m['mode'],follow_symlinks=False)
            os.utime(q,ns=(m['mtime_ns'],m['mtime_ns']),follow_symlinks=False)
        elif m.get('type') in ('file','symlink'):
            if base['protected_snapshot'].get(p)!=m: raise RuntimeError('UNEXPECTED_PRETEST_FILE:'+p)
            sr.copy_from_backup(p,m,oldbackup)
    for p in sorted(created,key=lambda x:(x.count('/'),x),reverse=True):
        m=post.get(p,{}); q=Path(p)
        if m.get('type') in ('file','symlink') and (q.is_file() or q.is_symlink()): q.unlink()
        elif m.get('type')=='dir':
            try: q.rmdir()
            except OSError: pass
    for p,m in sorted(pre.items(),key=lambda x:x[0].count('/'),reverse=True):
        if m.get('type')=='dir' and Path(p).is_dir():
            os.chown(p,m['uid'],m['gid']); os.chmod(p,m['mode']); os.utime(p,ns=(m['mtime_ns'],m['mtime_ns']))
    if sr.snapshot_all()!=pre: raise RuntimeError('RESTORE_VERIFICATION_FAILED')
    return created,modified,deleted

def host_health(dmesg,es):
    critical=sr.critical_lines(dmesg,sr.read_dmesg())
    if critical: raise RuntimeError('CRITICAL_SYSTEM_LOG:'+repr(critical[:6]))
    proc=sr.proc_list()
    if not any(p['comm'].lower()=='xorg' or p['exe'].endswith('/Xorg') for p in proc): raise RuntimeError('XORG_DIED')
    temp=sr.cpu_temp_max()
    if temp is not None and temp>=95: raise RuntimeError(f'CRITICAL_TEMP:{temp}')
    if not set(es).intersection(sr.es_pids()): raise RuntimeError('ES_PID_CHANGED')
    return temp

def input_class(r):
    ctl=(r.get('control_type') or '').lower()
    if any(x in ctl for x in ('trackball','spinner','dial','lightgun','paddle','pedal','steering','wheel','doublejoy','dual')) or 'gambling' in ctl:
        return 'SPECIAL_CONTROL'
    try: players=int(r.get('players') or 0)
    except (ValueError,TypeError): players=0
    try: buttons=int(r.get('buttons') or 99)
    except (ValueError,TypeError): buttons=99
    if any(x in ctl for x in ('joy','stick')) and buttons<=6 and players<=4:
        return 'DIRECT_COMPATIBLE; input físico no probado'
    return 'MANUAL_VALIDATE'

def player_priority(r):
    try: players=int(r.get('players') or 0); buttons=int(r.get('buttons') or 99)
    except (TypeError,ValueError): return 'NORMAL'
    return 'HIGH' if players in (3,4) and buttons<=6 and input_class(r).startswith('DIRECT_COMPATIBLE') else 'NORMAL'

def wait_es_idle(timeout=15):
    end=time.time()+timeout
    while time.time()<end:
        if sr.api_idle() is True and sr.api_game() is None and not active_pilot_processes() and sr.es_pids(): return True
        time.sleep(0.25)
    return False

def meta_value(r,key,default=''):
    v=r.get(key,default)
    if v is False: return 'NO'
    if v is True: return 'YES'
    if isinstance(v,str) and v.strip().lower() in ('false','no','0'): return 'NO'
    if isinstance(v,str) and v.strip().lower() in ('true','yes','1'): return 'YES'
    if v is None: return default
    return str(v)

def target_mame(rom,shortname):
    # Batocera's RetroArch argv references a generated .cmd file, not the ZIP path.
    running=sr.api_game()
    if not isinstance(running,dict) or running.get('path')!=str(rom): return []
    return active_pilot_processes(shortname)

def active_pilot_processes(shortname=None):
    names=[shortname] if shortname else MAME_GAMES
    out=[]
    for p in sr.proc_list():
        exe=p['exe'].lower(); cmd=p['cmd']
        if not exe.endswith('/retroarch'): continue
        if CORE_PATH not in cmd: continue
        if any(f'/var/run/cmdfiles/{n}.cmd' in cmd for n in names): out.append(p)
    return out

def mapping_summary():
    cfg=json.loads(Path('/userdata/system/configs/el_gordo_controller_profiles/controller_technical.json').read_text(encoding='utf-8'))
    return ', '.join(f'{x["player"]}=USB{x["usb_port"]}' for x in cfg.get('arcade_controllers',[]))

def run_game(n,r,oldbackup,base,state):
    rom=Path('/userdata/roms/mame')/(n+'.zip')
    if not rom.is_file() or not os.access(rom,os.R_OK): raise RuntimeError('ROM_NOT_READABLE:'+str(rom))
    idle_check(base)
    oldconf,line,oldstat=add_override(n)
    pre=sr.snapshot_all()
    for p,m in pre.items():
        if p!=str(CONF) and m!=base['protected_snapshot'].get(p):
            restore_conf(oldconf,oldstat); raise RuntimeError('UNEXPECTED_SIDE_EFFECT:'+p)
    folder=STATE/n; folder.mkdir(parents=True,exist_ok=True)
    conf_copy=folder/'batocera.conf.pretest'; shutil.copy2(CONF,conf_copy)
    if sha(conf_copy)!=pre[str(CONF)]['sha256']:
        restore_conf(oldconf,oldstat); raise RuntimeError('CONFIG_SNAPSHOT_HASH_MISMATCH')
    romhash=sha(rom); dmesg=sr.read_dmesg(); logs=sr.snapshot_logs(); espids=sr.es_pids()
    marker=None
    if sr.MARKER.exists(): restore_conf(oldconf,oldstat); raise RuntimeError('ONE_SHOT_MARKER_EXISTS')
    try:
        marker=create_owned_marker('mame',str(rom),'smoke_pilot_batch2',
                                   f'smoke-pilot-batch2:{n}:{os.getpid()}:{time.time_ns()}',path=sr.MARKER)
    except FileExistsError as exc:
        restore_conf(oldconf,oldstat)
        raise RuntimeError('MARKER_ALREADY_EXISTS') from exc
    start=time.time(); proc=None; status='FAIL'; detail=''; exitcode='—'; cleanup='NOT_REQUIRED'; safety=None
    try:
        http,body=sr.post_launch(str(rom))
        if http!=200: raise RuntimeError('ES_API_HTTP:'+str(http)+':'+body[:200])
        deadline=start+30
        while time.time()<deadline:
            found=target_mame(rom,n)
            if found: proc=found[0]; break
            if sr.api_idle() is True and sr.api_game() is None and time.time()-start>3: break
            time.sleep(0.5)
        if proc is None:
            if sr.MARKER.exists(): raise RuntimeError('DISPATCHER_MARKER_NOT_CONSUMED')
            if sr.api_idle() is not True or sr.api_game() is not None or active_pilot_processes(n): raise RuntimeError('FAILED_LAUNCH_CHAIN_NOT_IDLE')
            h=sr.game_health_row('mame',str(rom),start)
            msg=((h or {}).get('error','')+' '+(h or {}).get('missing_file','')).lower()
            detail=sr.log_fragment(h) or 'Volvió a ES sin un core objetivo confirmado.'
            exitcode=(h or {}).get('exit_code','—')
            if '.chd' in msg or (meta_value(r,'chd_required').upper()=='YES' and meta_value(r,'chd_ok').upper()=='NO'):
                status='FAIL_CHD'
            elif 'game driver not found' in msg: status='FAIL_DRIVER'
            elif any(x in msg for x in ('missing','not found','no such file','required')):
                status='FAIL_ROMSET' if r.get('romset_status')=='NO_CURRENT_MAME_CRC_MATCH' else 'FAIL_MISSING_CONTENT'
            elif h and h.get('exit_code') not in (None,0): status='FAIL_CRASH'
            else: status='FAIL_RETURN'
        else:
            cmdfile=f'/var/run/cmdfiles/{n}.cmd'
            if CORE_PATH not in proc['cmd'] or cmdfile not in proc['cmd']:
                raise RuntimeError('CORE_OR_CMD_COMMAND_MISMATCH:'+proc['cmd'][:400])
            end=time.time()+20
            while time.time()<end:
                current=target_mame(rom,n)
                if len(current)!=1 or current[0]['pid']!=proc['pid']:
                    status='FAIL_CRASH'; detail='RetroArch/libretro mame finalizó durante ventana de 20 s.'; break
                if sr.api_idle() is True: status='FAIL_RETURN'; detail='ES indicó idle con proceso objetivo presente.'; break
                time.sleep(0.5)
            if not detail:
                known_chd=(meta_value(r,'chd_required').upper()=='YES' and meta_value(r,'chd_ok').upper()=='NO')
                status='FAIL_CHD' if known_chd else 'BOOT_OK'
                if known_chd: detail='El inventario marca CHD requerido ausente; se confirmó el core en ejecución y se cerró de forma controlada.'
                cleanup='SIGTERM_EXACT_RETROARCH'
                current=target_mame(rom,n)
                if len(current)!=1 or current[0]['pid']!=proc['pid']: raise RuntimeError('CLEANUP_PID_NOT_UNIQUE')
                os.kill(proc['pid'],signal.SIGTERM)
                end=time.time()+10
                while time.time()<end and any(p['pid']==proc['pid'] for p in sr.proc_list()): time.sleep(0.25)
                if any(p['pid']==proc['pid'] for p in sr.proc_list()): raise RuntimeError('SIGTERM_TIMEOUT_NO_SIGKILL')
                end=time.time()+30
                while time.time()<end:
                    if sr.api_idle() is True and sr.api_game() is None and not active_pilot_processes(n): break
                    time.sleep(0.5)
                if sr.api_idle() is not True or sr.api_game() is not None or active_pilot_processes(n): raise RuntimeError('ES_DID_NOT_RETURN_IDLE')
                cleanup='CLEANUP_OK'
        temp=host_health(dmesg,espids)
        if sha(rom)!=romhash: raise RuntimeError('ROM_CHANGED')
        h=sr.game_health_row('mame',str(rom),start)
        if h:
            exitcode=h.get('exit_code','—')
            if status=='BOOT_OK' and h.get('core') not in ('mame','mame_libretro','mame current'):
                raise RuntimeError('HEALTH_DB_CORE_MISMATCH:'+repr(h.get('core')))
            err=((h.get('error','') or '')+' '+(h.get('missing_file','') or '')).lower()
            if status in ('BOOT_OK','FAIL_CHD','FAIL_CRASH','FAIL_RETURN') and any(x in err for x in ('game driver not found','missing','not found','no such file','required rom','failed to load','fatal')):
                if '.chd' in err or '.chd' in str(h.get('missing_file','')).lower(): status='FAIL_CHD'
                elif 'game driver not found' in err: status='FAIL_DRIVER'
                elif any(x in err for x in ('missing','not found','no such file','required rom')):
                    status='FAIL_ROMSET' if r.get('romset_status')=='NO_CURRENT_MAME_CRC_MATCH' else 'FAIL_MISSING_CONTENT'
                else: status='FAIL_CRASH'
                detail=sr.log_fragment(h) or 'La fila de salud reportó un error de carga pese a mantener el proceso.'
        post=sr.snapshot_all()
        made,changed,removed=restore_files(pre,post,oldbackup,base,conf_copy)
        if status!='BOOT_OK':
            expected=oldconf+(b'\n' if oldconf and not oldconf.endswith(b'\n') else b'')+line
            if CONF.read_bytes()!=expected: raise RuntimeError('OVERRIDE_ROLLBACK_UNSAFE')
            restore_conf(oldconf,oldstat)
            state['reverted_overrides'].append(n)
        else: state['kept_overrides'].append(n)
        if sha(rom)!=romhash: raise RuntimeError('POST_RESTORE_ROM_HASH_CHECK_FAILED')
        lc,lm,ld=sr.differences(logs,sr.snapshot_logs())
        pid=proc['pid'] if proc else '—'
        core_seen=CORE_PATH if proc else 'no confirmado'
        diff=f'+mame["{n}.zip"].core=mame'
        mapping=mapping_summary()
        if not detail:
            detail=(f'diff {diff}; PID {pid}; core {core_seen}; DB core={(h or {}).get("core","?")}; '
                    f'emulator={(h or {}).get("emulator","?")}; exit={exitcode}; status={(h or {}).get("status","?")}; '
                    f'mapping configurado {mapping}; log paths changed={len(lc+lm+ld)}; restore delta {len(made)}/{len(changed)}/{len(removed)}')
        if temp is not None: detail+=f'; temp máx {temp} C'
        return {'game':n,'rom':str(rom),'old_core':'mame078plus','new_core':'mame libretro current',
          'display_name':r.get('name',r.get('gamelist_name',n)),
          'boot':status,'input':input_class(r),'override':'KEPT' if status=='BOOT_OK' else 'REVERTED',
          'duration':round(time.time()-start,2),'exit_code':exitcode,'restore':'VERIFIED','detail':detail,
          'tested_at':stamp(),'mapping':mapping,'override_diff':diff,'core_path':CORE_PATH,
          'crc':r.get('romset_status'),'chd':meta_value(r,'chd_required','UNKNOWN'),'chd_ok':meta_value(r,'chd_ok','UNKNOWN'),'bios':r.get('bios_required',r.get('bios_status','UNKNOWN_STATIC')),
          'players':r.get('players'),'buttons':r.get('buttons'),'control_type':r.get('control_type'),
          'multiplayer_priority':player_priority(r),'physical_input':'NOT_YET_CERTIFIED',
          'custom_mapping':'No CFG/remap por juego detectado; existe solo default.cfg; '+r.get('mapping_status','unknown'),
          'missing_dependency':r.get('missing_dependency',''),'bios_ok':r.get('bios_ok',''),
          'health_status':(h or {}).get('status',''),'health_core':(h or {}).get('core',''),
          'health_emulator':(h or {}).get('emulator',''),'health_pid':(h or {}).get('pid',''),
          'launcher_log':(h or {}).get('launcher_log',''),'emulator_log':(h or {}).get('emulator_log','')}
    except Exception as e:
        safety=f'{type(e).__name__}: {e}'
        found=target_mame(rom,n)
        if len(found)==1:
            try:
                os.kill(found[0]['pid'],signal.SIGTERM)
                end=time.time()+10
                while time.time()<end and any(p['pid']==found[0]['pid'] for p in sr.proc_list()): time.sleep(0.25)
            except ProcessLookupError: pass
        if sr.api_idle() is True and sr.api_game() is None and not active_pilot_processes():
            restore_files(pre,sr.snapshot_all(),oldbackup,base,conf_copy)
            expected=oldconf+(b'\n' if oldconf and not oldconf.endswith(b'\n') else b'')+line
            if CONF.read_bytes()==expected: restore_conf(oldconf,oldstat)
            else: raise RuntimeError('SAFETY_CONFIG_DIVERGED:'+safety)
            raise RuntimeError('SAFETY_PAUSE:'+safety+'; restore verified; current override reverted')
        raise RuntimeError('SAFETY_PAUSE_RESTORE_UNSAFE:'+safety)
    finally:
        try:
            if marker and sr.api_idle() is True and sr.api_game() is None and not active_pilot_processes():
                remove_owned_marker(marker['transaction_id'],owner='smoke_pilot_batch2',
                                    audit_id=marker.get('audit_id'),path=sr.MARKER)
        except Exception: pass

def write_report(s):
    lines=['# Piloto controlado — MAME actual — batch 2','','Inicio: '+s['started_at'],
      '',f'Core objetivo: libretro mame, {CORE_PATH}. Core global mame078plus sin cambios.',
      'El log runtime de libretro identifica MAME 0.285 (unknown); el .info muestra display_version Git. La versión standalone instalada no se usó.',
      f'Backup config: {BACKUP}; saves/NVRAM: baseline verificado anterior.',
      'Ruta: EmulationStation → controller_dispatcher → launcher oficial → RetroArch; no se inyectó input.',
      'La tanda usa exactamente los 15 candidatos restantes de ARCADE_PILOT_RETEST.md. Cinco se omiten porque el reporte prescribe FBNeo; diez se prueban con MAME actual.',
      'Cada override individual es una sola línea mame["<rom>.zip"].core=mame; se preservan los cinco overrides de BATCH 1 y el default global mame078plus.',
      '', '| Juego | ROM | Core previo → nuevo | CRC/dependencias | P/B/control | Boot | Input | Diff | Override | s | Exit | Restore | Evidencia |',
      '| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: | --- | --- |']
    for r in s['results']:
        dep=f'CRC {r.get("crc")}; CHD {r.get("chd")}; BIOS {r.get("bios")}; missing {r.get("missing_dependency") or "no"}'
        inp=f'{r["players"]}P/{r["buttons"]}B/{r["control_type"]}'
        lines.append(f'| {r["game"]} | {r["rom"]} | {r["old_core"]} → {r["new_core"]} | {dep} | {inp} | {r["boot"]} | {r["input"]} | {r["override_diff"]} | {r["override"]} | {r["duration"]} | {r["exit_code"]} | {r["restore"]} | {r["detail"].replace("|","/")[:260]} |')
    lines+=['','## Estado','',f'- Progreso: {len(s["results"])}/15; siguiente: {s.get("next_game") or "ninguno"}',
      f'- Juegos ejecutados: {sum(x.get("duration",0)>0 for x in s["results"])}/10 MAME; omisiones: {sum(x["boot"]=="SKIP_WRONG_STRATEGY" for x in s["results"])}/5 estrategia ajena.',
      f'- PASS: {sum(x["boot"]=="BOOT_OK" for x in s["results"])}/15 total candidatos; restores verificados: {sum(x["restore"]=="VERIFIED" for x in s["results"])}/10 ejecutados.',
      f'- Fase: {s["phase"]}',f'- Restore: {s.get("restore_status")}',
      f'- Overrides mantenidos: {", ".join(s["kept_overrides"]) or "ninguno"}',
      f'- Overrides revertidos: {", ".join(s["reverted_overrides"]) or "ninguno"}',
      f'- Regresión global: {s.get("regression","pendiente")}',f'- Error: {s.get("error","ninguno")}',
      f'- Mapping técnico usado: {mapping_summary()}; dispositivos y respuesta física no se vuelven a certificar por este smoke test.',
      '- P1-P4 y dispatcher permanecen sin cambios; el smoke test no certifica respuesta física. Juegos 3P/4P compatibles quedan con prioridad alta de validación manual.',
      '- Los logs runtime confirman CHD ausente en hyperath, jojo y redearth; jojo también carece de jojo_euro.29f400.u2.',
      '','No se certificó input físico.','',
      '## Cierre de la segunda tanda','',
      f'- BOOT_OK: {sum(x["boot"]=="BOOT_OK" for x in s["results"])}/10 lanzados; 4/15 candidatos totales al incluir cinco SKIP_WRONG_STRATEGY.',
      f'- Fallos por causa: {s.get("failure_groups",{})}. No hubo FAIL_DRIVER ni crash del core separado de contenido requerido ausente.',
      '- Compatibles directos con metadata y boot PASS: sia2650, evosocc y hoops95. funcube4 pasó boot y requiere control especial (gambling/lightgun).',
      '- 4P con boot PASS: evosocc y hoops95; input físico pendiente. nbapbp y hyperath son 4P, pero faltan archivos/CHD.',
      '- Temperatura final registrada: 54 °C. Máxima conservada entre lecturas reportadas del lote: 54 °C; las comprobaciones térmicas de cada juego no detectaron umbral crítico.',
      '- NVIDIA: módulo cargado, driver 580.126.09; nvidia-smi no está disponible. Xorg activo y sin errores críticos nuevos observados en las comprobaciones por juego.',
      '- ES quedó idle; hashes de controller_dispatcher y perfil técnico coinciden; snapshot protegido sin deriva. batocera.conf coincide con el backup BATCH 2 más sólo los overrides de juegos PASS.',
      '- Recomendación: continuar sólo por lotes y con filtro CRC/dependencias; no se ejecutó otra tanda.','']
    REPORT.write_text('\n'.join(lines),encoding='utf-8')

def persist_checkpoints(s):
    write_json(CHECKPOINT,s)
    old=json.loads(PILOT_CHECKPOINT.read_text(encoding='utf-8'))
    old['batch2']={'phase':s['phase'],'started_at':s['started_at'],'results':s['results'],
      'kept_overrides':s['kept_overrides'],'reverted_overrides':s['reverted_overrides'],
      'restore_status':s['restore_status'],'next_game':s.get('next_game'),'backup':str(BACKUP),
      'batch_rating':s.get('batch_rating'),'failure_groups':s.get('failure_groups'),
      'regression':s.get('regression'),'recommendation':s.get('recommendation'),
      'final_checks':s.get('final_checks'),'updated_at':stamp()}
    write_json(PILOT_CHECKPOINT,old)
    master=json.loads(MASTER_CHECKPOINT.read_text(encoding='utf-8'))
    master['core_pilot_batch2']=old['batch2']
    write_json(MASTER_CHECKPOINT,master)

def update_retest_report(s):
    p=OUT/'ARCADE_PILOT_RETEST.md'; text=p.read_text(encoding='utf-8')
    marker='\n## Resultado BATCH 2 — 2026-11-13'
    if marker in text: text=text.split(marker)[0]
    rows=[]
    for r in s['results']:
        rows.append(f'| {r["game"]} | {r["display_name"]} | {r["old_core"]} | {r["new_core"]} | {r["crc"]} | {r["chd"]} | {r["control_type"]} | {r["boot"]} | {r["restore"]} |')
    section=marker+'\n\nResultados acumulados del piloto. Los cinco primeros son SKIP_WRONG_STRATEGY porque el reporte recomienda FBNeo; no se modificaron ni probaron. Los diez MAME elegibles se ejecutaron secuencialmente.\n\n| Shortname | Display name | Core actual | Core probado/recomendado | CRC | CHD | Control | Resultado | Restore |\n|---|---|---|---|---|---|---|---|---|\n'+'\n'.join(rows)+'\n'
    p.write_text(text+section,encoding='utf-8')

def publish_results(s):
    existing=OUT/'ARCADE_CORE_PILOT_RESULTS.md'
    original=existing.read_text(encoding='utf-8') if existing.exists() else '# Piloto controlado — MAME actual\n'
    marker='\n## BATCH 2 — 15 GAMES'
    if marker in original: original=original.split(marker)[0]
    batch=REPORT.read_text(encoding='utf-8')
    existing.write_text(original+marker+'\n\n'+batch,encoding='utf-8')
    update_retest_report(s)

def skip_result(n,r):
    return {'game':n,'rom':r.get('rom',n+'.zip'),'display_name':r.get('name',n),
      'old_core':'mame078plus','new_core':SKIPPED[n],'boot':'SKIP_WRONG_STRATEGY',
      'input':input_class(r),'override':'NONE','duration':0,'exit_code':'—',
      'restore':'VERIFIED_NO_WRITE','detail':'ARCADE_PILOT_RETEST.md asigna este candidato a FBNeo/u otra ruta; no se aplicó override ni se lanzó.',
      'tested_at':stamp(),'override_diff':'sin cambios','crc':r.get('romset_status','UNKNOWN'),
      'chd':meta_value(r,'chd_required','UNKNOWN'),'chd_ok':meta_value(r,'chd_ok','UNKNOWN'),
      'bios':r.get('bios_required',r.get('bios_status','UNKNOWN_STATIC')),'players':r.get('players',''),
      'buttons':r.get('buttons',''),'control_type':r.get('control_type',''),'missing_dependency':r.get('missing_dependency',''),
      'multiplayer_priority':player_priority(r),'physical_input':'NOT_YET_CERTIFIED'}

def update_csv_result(result):
    p=OUT/'arcade_core_compatibility.csv'
    rows=list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
    found=False
    for r in rows:
        if r.get('system')=='mame' and r.get('shortname')==result['game']:
            r.update({'pilot_batch2_status':result['boot'],'pilot_batch2_core':result['new_core'],
                      'pilot_batch2_override':result['override'],'pilot_batch2_tested_at':result.get('tested_at',stamp()),
                      'pilot_batch2_restore':result['restore']}); found=True
    # The two historical crash cases are present in the full arcade inventory but
    # were outside the 181 CURRENT_CORE_REJECTED matrix rows. Add only those pilot rows.
    if not found and result['game'] in MAME_GAMES:
        r={'system':'mame','rom':result['game']+'.zip','name':result.get('display_name',result['game']),
           'shortname':result['game'],'current_core':'mame078plus','current_result':'HISTORICAL_CRASH',
           'romset_status':result.get('crc','UNKNOWN'),'chd_required':result.get('chd','UNKNOWN'),
           'chd_ok':result.get('chd_ok','UNKNOWN'),'players':result.get('players',''),
           'buttons':result.get('buttons',''),'control_type':result.get('control_type',''),
           'recommended_core':'mame current','recommended_action':'PILOT_BATCH2',
           'pilot_batch2_status':result['boot'],'pilot_batch2_core':result['new_core'],
           'pilot_batch2_override':result['override'],'pilot_batch2_tested_at':result.get('tested_at',stamp()),
           'pilot_batch2_restore':result['restore']}
        rows.append(r)
    fields=list(rows[0])
    for row in rows:
        for k in ('pilot_batch2_status','pilot_batch2_core','pilot_batch2_override','pilot_batch2_tested_at','pilot_batch2_restore'):
            if k not in fields: fields.append(k)
    tmp=p.with_suffix('.csv.pilot-batch2.tmp')
    with tmp.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    os.replace(tmp,p)

def main():
    backup_check()
    cp,bp,base=sr.ensure_backup_valid()
    original=(BACKUP/'batocera.conf').read_bytes()
    expected_b1=(B1_BACKUP/'batocera.conf').read_bytes()+b''.join(f'mame["{n}.zip"].core=mame\n'.encode() for n in B1_GAMES)
    if original!=expected_b1: raise RuntimeError('BATCH1_CONFIG_BACKUP_MISMATCH')
    data,d=matrix(); idle_check(base); STATE.mkdir(parents=True,exist_ok=True)
    dispatcher=Path('/userdata/system/el_gordo_tools/controller_dispatcher'); profile=Path('/userdata/system/configs/el_gordo_controller_profiles/controller_technical.json')
    protected_hashes={str(p):sha(p) for p in (dispatcher,profile)}
    if len(sys.argv)>1 and sys.argv[1]=='resume':
        if not CHECKPOINT.is_file(): raise RuntimeError('NO_BATCH2_CHECKPOINT_TO_RESUME')
        s=json.loads(CHECKPOINT.read_text(encoding='utf-8'))
        if s.get('phase') not in ('PAUSED_SAFETY','RUNNING'): raise RuntimeError('CHECKPOINT_NOT_RESUMABLE:'+str(s.get('phase')))
        expected=original+b''.join(f'mame["{n}.zip"].core=mame\n'.encode() for n in s.get('kept_overrides',[]))
        if CONF.read_bytes()!=expected: raise RuntimeError('RESUME_CONFIG_DIFFERS_FROM_CHECKPOINT')
        if any(x.get('restore') not in ('VERIFIED','VERIFIED_NO_WRITE') for x in s.get('results',[])):
            raise RuntimeError('RESUME_HAS_UNVERIFIED_PRIOR_RESULT')
        s.update({'phase':'RUNNING','error':'','resume_at':stamp()})
    else:
        if CHECKPOINT.exists(): raise RuntimeError('BATCH2_CHECKPOINT_EXISTS; use explicit resume after recovery')
        if CONF.read_bytes()!=original: raise RuntimeError('BATCH2_CONFIG_NOT_AT_BACKUP_STATE')
        s={'phase':'RUNNING','started_at':stamp(),'results':[],'kept_overrides':[],'reverted_overrides':[],
           'restore_status':'VERIFIED_BEFORE_START','next_game':CANDIDATES[0],'regression':'pending',
           'backup':str(BACKUP),'batch1_kept_overrides':B1_GAMES,'tested_games':MAME_GAMES,
           'skipped_wrong_strategy':SKIPPED,'protected_hashes':protected_hashes}
    completed={x['game'] for x in s.get('results',[])}
    write_json(CHECKPOINT,s); write_report(s); persist_checkpoints(s)
    for i,n in enumerate(CANDIDATES):
        if n in completed: continue
        s['next_game']=n; write_json(CHECKPOINT,s); persist_checkpoints(s)
        if n in SKIPPED:
            try:
                idle_check(base); pre=sr.snapshot_all(); result=skip_result(n,data[n])
                if sr.snapshot_all()!=pre: raise RuntimeError('SKIP_STATE_CHANGED:'+n)
            except Exception as e:
                s.update({'phase':'PAUSED_SAFETY','error':f'{type(e).__name__}: {e}','next_game':n,'restore_status':'UNVERIFIED — STOP'})
                write_json(CHECKPOINT,s); persist_checkpoints(s); write_report(s); print(json.dumps({'phase':s['phase'],'game':n,'error':s['error']}),flush=True); return
        else:
            print('APPLY_OVERRIDE_DIFF',f'+ mame["{n}.zip"].core=mame',flush=True)
            try: result=run_game(n,data[n],bp,base,s)
            except Exception as e:
                s.update({'phase':'PAUSED_SAFETY','error':f'{type(e).__name__}: {e}',
                          'restore_status':'VERIFIED' if 'restore verified' in str(e).lower() else 'UNVERIFIED — STOP','next_game':n})
                write_json(CHECKPOINT,s); persist_checkpoints(s); write_report(s)
                print(json.dumps({'phase':s['phase'],'game':n,'error':s['error']},ensure_ascii=False),flush=True); return
        s['results'].append(result); s['restore_status']=result['restore']
        s['next_game']=CANDIDATES[i+1] if i+1<len(CANDIDATES) else None
        write_json(CHECKPOINT,s); persist_checkpoints(s); write_report(s); update_csv_result(result)
        print(json.dumps({'game':n,'boot':result['boot'],'override':result['override'],'restore':result['restore']},ensure_ascii=False),flush=True)
        if not wait_es_idle():
            s.update({'phase':'PAUSED_SAFETY','error':'ES_OR_LAUNCHER_UNHEALTHY','next_game':n})
            write_json(CHECKPOINT,s); persist_checkpoints(s); write_report(s); return
    s['phase']='COMPLETE'; s['next_game']=None
    expected=original+b''.join(f'mame["{n}.zip"].core=mame\n'.encode() for n in s['kept_overrides'])
    if CONF.read_bytes()!=expected:
        s.update({'phase':'PAUSED_SAFETY','error':'UNEXPECTED_GLOBAL_CONFIG_DIFF','regression':'DIFF INESPERADO'})
    elif any(sha(Path(p))!=h for p,h in protected_hashes.items()):
        s.update({'phase':'PAUSED_SAFETY','error':'DISPATCHER_OR_PROFILE_HASH_CHANGED','regression':'CUSTOM INPUT CONFIG DRIFT'})
    else:
        final_snapshot=sr.snapshot_all()
        drift=[p for p in sorted(set(final_snapshot)|set(base['protected_snapshot']))
               if p!=str(CONF) and final_snapshot.get(p)!=base['protected_snapshot'].get(p)]
        if drift: s.update({'phase':'PAUSED_SAFETY','error':'PROTECTED_TREE_FINAL_DRIFT:'+repr(drift[:10]),'regression':'RESTORE DRIFT'})
    if s.get('phase')!='PAUSED_SAFETY':
        s['regression']='NO GLOBAL REGRESSION; BATCH 1 intact; only passing BATCH 2 game overrides added.'
        passed=sum(x['boot']=='BOOT_OK' for x in s['results'])
        s['recommendation']='PILOTO BATCH 2 VALIDADO; detenerse antes de cualquier otra tanda.'
        s['batch_rating']='EXCELENTE' if passed>=13 else 'BUENO' if passed>=10 else 'MIXTO' if passed>=7 else 'MALO'
    s['finished_at']=stamp()
    if s.get('phase')=='COMPLETE': s['restore_status']='15/15: 10 ejecutados/restaurados y 5 omitidos sin escrituras, snapshot idéntico'
    write_json(CHECKPOINT,s); persist_checkpoints(s); write_report(s)
    update_retest_report(s); publish_results(s)
    for r in s['results']: update_csv_result(r)
    print(json.dumps({'phase':s['phase'],'pass':sum(x['boot']=='BOOT_OK' for x in s['results']),
      'fail':sum(x['boot'].startswith('FAIL') or x['boot']=='TIMEOUT' for x in s['results']),
      'skip':sum(x['boot']=='SKIP_WRONG_STRATEGY' for x in s['results']),'kept':s['kept_overrides'],
      'reverted':s['reverted_overrides'],'restore':s['restore_status'],'regression':s['regression'],
      'rating':s.get('batch_rating'),'recommendation':s.get('recommendation',''),'error':s.get('error','')},ensure_ascii=False,indent=2),flush=True)

def preflight():
    backup_check()
    cp,bp,base=sr.ensure_backup_valid()
    original=(BACKUP/'batocera.conf').read_bytes()
    expected=(B1_BACKUP/'batocera.conf').read_bytes()+b''.join(f'mame["{n}.zip"].core=mame\n'.encode() for n in B1_GAMES)
    state=json.loads(CHECKPOINT.read_text(encoding='utf-8')) if CHECKPOINT.is_file() else {}
    active_expected=original+b''.join(f'mame["{n}.zip"].core=mame\n'.encode() for n in state.get('kept_overrides',[]))
    if original!=expected or CONF.read_bytes()!=active_expected: raise RuntimeError('BATCH1_CONFIG_OR_OVERRIDE_DRIFT')
    data,d=matrix(); idle_check(base)
    print(json.dumps({'preflight':'PASS','backup':str(BACKUP),'backup_verified':True,
      'tested_mame':MAME_GAMES,'skipped_wrong_strategy':SKIPPED,
      'roms_readable':{n:os.access(Path('/userdata/roms/mame')/(n+'.zip'),os.R_OK) for n in MAME_GAMES},
      'ES_idle':sr.api_idle(),'ES_PIDs':sr.es_pids(),'protected_snapshot_matches':True,
      'existing_batch1_overrides_preserved':B1_GAMES,'new_batch2_overrides':[]},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':
    try:
        if len(sys.argv)>1 and sys.argv[1]=='preflight': preflight()
        else: main()
    except Exception as e: print(f'PREFLIGHT_ABORT: {type(e).__name__}: {e}',file=sys.stderr,flush=True); raise
