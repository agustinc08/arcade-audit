#!/usr/bin/env python3
"""Sequential MAME-current pilot via the normal Batocera launch path."""
import csv, hashlib, json, os, shutil, signal, stat, sys, time
from datetime import datetime
from pathlib import Path
import smoke_runner as sr
from configgen.settings.unixSettings import UnixSettings

OUT=Path('/userdata/system/state/arcade_audit')
CONF=Path('/userdata/system/batocera.conf')
BACKUP=Path('/media/ROMS/ARCADE_BACKUPS/ARCADE_CORE_PILOT_2026-11-13_093236')
STATE=OUT/'pilot_runtime'
REPORT=OUT/'ARCADE_CORE_PILOT_RESULTS.md'
CHECKPOINT=OUT/'pilot_checkpoint.json'
CORE_PATH='/usr/lib/libretro/mame_libretro.so'
GAMES=['ffight2b','altair','apache3','blazlaz','cubeqst']

def stamp(): return datetime.now().astimezone().isoformat(timespec='seconds')
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()
def write_json(p,o):
    t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); os.replace(t,p)

def backup_check():
    if not (BACKUP/'batocera.conf').is_file() or sha(CONF)!=sha(BACKUP/'batocera.conf'):
        raise RuntimeError('PILOT_CONFIG_BACKUP_HASH_MISMATCH')
    for n in ('MANIFEST_SHA256.txt','SOURCE_PATHS.txt','PRE_TEST_FILELIST.txt'):
        if not (BACKUP/n).is_file(): raise RuntimeError('BACKUP_METADATA_MISSING:'+n)

def matrix():
    rows=list(csv.DictReader((OUT/'arcade_core_compatibility.csv').open(encoding='utf-8-sig',newline='')))
    d={r['shortname']:r for r in rows if r['system']=='mame'}
    for n in GAMES:
        r=d.get(n)
        if not r or r['current_core']!='mame078plus' or r['current_result']!='GAME_DRIVER_NOT_FOUND':
            raise RuntimeError('PILOT_BASELINE_MISMATCH:'+n)
        if r['romset_status']!='FULL_CRC_MATCH_MAME_CURRENT' or r['chd_required']!='NO' or r['missing_dependency']:
            raise RuntimeError('PILOT_PREREQUISITE_MISMATCH:'+n)
    return d

def idle_check(base):
    snap=sr.snapshot_all()
    for p,m in snap.items():
        if p!=str(CONF) and m!=base['protected_snapshot'].get(p): raise RuntimeError('PRETEST_DRIFT:'+p)
    if sr.api_idle() is not True or sr.api_game() is not None or sr.launcher_processes(): raise RuntimeError('ARCADE_NOT_IDLE')
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
    if 'trackball' in r.get('control_type','').lower() or r['shortname']=='cubeqst': return 'SPECIAL_CONTROL_TRACKBALL'
    if r.get('input_compatibility')=='DIRECT_COMPATIBLE': return 'DIRECT_COMPATIBLE; input físico no probado'
    return 'MANUAL_VALIDATE'

def target_mame(rom,shortname):
    # Batocera's RetroArch argv references a generated .cmd file, not the ZIP path.
    running=sr.api_game()
    if not isinstance(running,dict) or running.get('path')!=str(rom): return []
    cmdfile=f'/var/run/cmdfiles/{shortname}.cmd'
    return [p for p in sr.proc_list()
            if 'retroarch' in (p['exe']+' '+p['cmd']).lower()
            and CORE_PATH in p['cmd'] and cmdfile in p['cmd']]

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
    marker=sr.marker_value('mame',str(rom))
    if sr.MARKER.exists(): restore_conf(oldconf,oldstat); raise RuntimeError('ONE_SHOT_MARKER_EXISTS')
    with sr.MARKER.open('x',encoding='utf-8') as f: json.dump(marker,f); f.flush(); os.fsync(f.fileno())
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
            if sr.api_idle() is not True or sr.api_game() is not None or sr.launcher_processes(): raise RuntimeError('FAILED_LAUNCH_CHAIN_NOT_IDLE')
            h=sr.game_health_row('mame',str(rom),start)
            msg=((h or {}).get('error','')+' '+(h or {}).get('missing_file','')).lower()
            detail=sr.log_fragment(h) or 'Volvió a ES sin un core objetivo confirmado.'
            exitcode=(h or {}).get('exit_code','—')
            status='MISSING_CONTENT' if any(x in msg for x in ('missing','not found','no such file','required')) else ('CRASH' if h and h.get('exit_code') not in (None,0) else 'FAIL')
        else:
            cmdfile=f'/var/run/cmdfiles/{n}.cmd'
            if CORE_PATH not in proc['cmd'] or cmdfile not in proc['cmd']:
                raise RuntimeError('CORE_OR_CMD_COMMAND_MISMATCH:'+proc['cmd'][:400])
            end=time.time()+20
            while time.time()<end:
                current=target_mame(rom,n)
                if len(current)!=1 or current[0]['pid']!=proc['pid']:
                    status='CRASH'; detail='RetroArch/libretro mame finalizó durante ventana de 20 s.'; break
                if sr.api_idle() is True: status='FAIL'; detail='ES indicó idle con proceso objetivo presente.'; break
                time.sleep(0.5)
            if not detail:
                status='BOOT_OK'; cleanup='SIGTERM_EXACT_RETROARCH'
                current=target_mame(rom,n)
                if len(current)!=1 or current[0]['pid']!=proc['pid']: raise RuntimeError('CLEANUP_PID_NOT_UNIQUE')
                os.kill(proc['pid'],signal.SIGTERM)
                end=time.time()+10
                while time.time()<end and any(p['pid']==proc['pid'] for p in sr.proc_list()): time.sleep(0.25)
                if any(p['pid']==proc['pid'] for p in sr.proc_list()): raise RuntimeError('SIGTERM_TIMEOUT_NO_SIGKILL')
                end=time.time()+30
                while time.time()<end:
                    if sr.api_idle() is True and sr.api_game() is None and not sr.launcher_processes(): break
                    time.sleep(0.5)
                if sr.api_idle() is not True or sr.api_game() is not None or sr.launcher_processes(): raise RuntimeError('ES_DID_NOT_RETURN_IDLE')
                cleanup='CLEANUP_OK'
        temp=host_health(dmesg,espids)
        if sha(rom)!=romhash: raise RuntimeError('ROM_CHANGED')
        h=sr.game_health_row('mame',str(rom),start)
        if h:
            exitcode=h.get('exit_code','—')
            if status=='BOOT_OK' and h.get('core') not in ('mame','mame_libretro','mame current'):
                raise RuntimeError('HEALTH_DB_CORE_MISMATCH:'+repr(h.get('core')))
            err=((h.get('error','') or '')+' '+(h.get('missing_file','') or '')).lower()
            if status=='BOOT_OK' and any(x in err for x in ('game driver not found','missing','not found','no such file','required rom','failed to load','fatal')):
                status='MISSING_CONTENT' if any(x in err for x in ('missing','not found','no such file','required rom')) else 'FAIL'
                detail=sr.log_fragment(h) or 'La fila de salud reportó un error de carga pese a mantener el proceso.'
        post=sr.snapshot_all()
        made,changed,removed=restore_files(pre,post,oldbackup,base,conf_copy)
        if status!='BOOT_OK':
            expected=oldconf+(b'\n' if oldconf and not oldconf.endswith(b'\n') else b'')+line+b'\n'
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
          'boot':status,'input':input_class(r),'override':'KEPT' if status=='BOOT_OK' else 'REVERTED',
          'duration':round(time.time()-start,2),'exit_code':exitcode,'restore':'VERIFIED','detail':detail,
          'tested_at':stamp(),'mapping':mapping,'override_diff':diff,'core_path':CORE_PATH,
          'crc':r.get('romset_status'),'chd':r.get('chd_required'),'bios':r.get('bios_required'),
          'players':r.get('players'),'buttons':r.get('buttons'),'control_type':r.get('control_type'),
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
        if sr.api_idle() is True and sr.api_game() is None and not sr.launcher_processes():
            restore_files(pre,sr.snapshot_all(),oldbackup,base,conf_copy)
            expected=oldconf+(b'\n' if oldconf and not oldconf.endswith(b'\n') else b'')+line+b'\n'
            if CONF.read_bytes()==expected: restore_conf(oldconf,oldstat)
            else: raise RuntimeError('SAFETY_CONFIG_DIVERGED:'+safety)
            raise RuntimeError('SAFETY_PAUSE:'+safety+'; restore verified; current override reverted')
        raise RuntimeError('SAFETY_PAUSE_RESTORE_UNSAFE:'+safety)
    finally:
        try:
            if sr.MARKER.exists() and sr.api_idle() is True and sr.api_game() is None and not sr.launcher_processes():
                m=json.loads(sr.MARKER.read_text(encoding='utf-8'))
                if m.get('audit_id')==marker.get('audit_id'): sr.MARKER.unlink()
        except Exception: pass

def write_report(s):
    lines=['# Piloto controlado — MAME actual','','Inicio: '+s['started_at'],
      '',f'Core objetivo: libretro mame, {CORE_PATH}. Core global mame078plus sin cambios.',
      'Metadata libretro mame: display_version Git; MAME standalone consultado en la auditoría: v0.285. Driver del target core se confirma además por el argv real en cada PASS.',
      f'Backup config: {BACKUP}; saves/NVRAM: baseline verificado anterior.',
      'Ruta: EmulationStation → controller_dispatcher → launcher oficial → RetroArch; no se inyectó input.',
      'El override individual esperado es una sola línea mame["<rom>.zip"].core=mame; se preserva el default libretro/mame078plus.',
      '', '| Juego | ROM | Core previo → nuevo | CRC/dependencias | P/B/control | Boot | Input | Diff | Override | s | Exit | Restore | Evidencia |',
      '| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: | --- | --- |']
    for r in s['results']:
        dep=f'CRC {r["crc"]}; CHD {r["chd"]}; BIOS {r["bios"]}; missing {r["missing_dependency"] or "no"}'
        inp=f'{r["players"]}P/{r["buttons"]}B/{r["control_type"]}'
        lines.append(f'| {r["game"]} | {r["rom"]} | {r["old_core"]} → {r["new_core"]} | {dep} | {inp} | {r["boot"]} | {r["input"]} | {r["override_diff"]} | {r["override"]} | {r["duration"]} | {r["exit_code"]} | {r["restore"]} | {r["detail"].replace("|","/")[:260]} |')
    lines+=['','## Estado','',f'- Progreso: {len(s["results"])}/5; siguiente: {s.get("next_game") or "ninguno"}',
      f'- Fase: {s["phase"]}',f'- Restore: {s.get("restore_status")}',
      f'- Overrides mantenidos: {", ".join(s["kept_overrides"]) or "ninguno"}',
      f'- Overrides revertidos: {", ".join(s["reverted_overrides"]) or "ninguno"}',
      f'- Regresión global: {s.get("regression","pendiente")}',f'- Error: {s.get("error","ninguno")}',
      f'- Mapping técnico usado: {mapping_summary()}; dispositivos y respuesta física no se vuelven a certificar por este smoke test.',
      '- No se encontraron CFG/remaps por juego para los cinco; solo existe configs/mame/cfg/default.cfg.',
      '- Intento inicial ffight2b: game_health registró libretro/mame, PID 28272, 86,72 s, exit 0 e INICIO_SOSTENIDO. No se contabilizó porque el matcher buscaba el ZIP en argv; Batocera usa /var/run/cmdfiles/ffight2b.cmd. El proceso se cerró con SIGTERM y el restore del baseline pasó. Se repite con matcher corregido.',
      '','No se certificó P1-P4 físicamente. cubeqst conserva clasificación de trackball.','']
    REPORT.write_text('\n'.join(lines),encoding='utf-8')

def update_csv(passed):
    if not passed: return
    p=OUT/'arcade_core_compatibility.csv'
    rows=list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
    for r in rows:
        if r['system']=='mame' and r['shortname'] in passed:
            r.update({'pilot_boot_status':'PILOT_BOOT_OK','pilot_core':'mame libretro current','pilot_override':'KEPT','pilot_tested_at':stamp()})
    fields=list(rows[0])
    for k in ('pilot_boot_status','pilot_core','pilot_override','pilot_tested_at'):
        if k not in fields: fields.append(k)
    tmp=p.with_suffix('.csv.pilot.tmp')
    with tmp.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    os.replace(tmp,p)

def main():
    backup_check()
    cp,bp,base=sr.ensure_backup_valid()
    if sha(CONF)!=base['protected_snapshot'][str(CONF)]['sha256']: raise RuntimeError('SAVE_BASELINE_CONFIG_DRIFT')
    data=matrix(); idle_check(base); STATE.mkdir(parents=True,exist_ok=True)
    s={'phase':'RUNNING','started_at':stamp(),'results':[],'kept_overrides':[],'reverted_overrides':[],
       'restore_status':'VERIFIED_BEFORE_START','next_game':GAMES[0],'regression':'pending',
       'harness_note':'Intento inicial ffight2b observado en health DB: core mame, PID 28272, 86.72 s, exit 0, INICIO_SOSTENIDO; no contado porque el matcher del harness buscó el ZIP en argv. El argv real usa /var/run/cmdfiles/ffight2b.cmd. SIGTERM controlado y restore verificado; se retesta.'}
    write_json(CHECKPOINT,s); write_report(s)
    for i,n in enumerate(GAMES):
        s['next_game']=n; write_json(CHECKPOINT,s); write_report(s)
        try: r=run_game(n,data[n],bp,base,s)
        except Exception as e:
            s.update({'phase':'PAUSED_SAFETY','error':f'{type(e).__name__}: {e}',
                      'restore_status':'VERIFIED' if 'restore verified' in str(e).lower() else 'UNVERIFIED — STOP',
                      'next_game':n})
            write_json(CHECKPOINT,s); write_report(s)
            print(json.dumps({'phase':s['phase'],'game':n,'error':s['error']},ensure_ascii=False),flush=True); return
        s['results'].append(r); s['restore_status']=r['restore']
        s['next_game']=GAMES[i+1] if i+1<len(GAMES) else None
        write_json(CHECKPOINT,s); write_report(s); update_csv(s['kept_overrides'])
        print(json.dumps({'game':n,'boot':r['boot'],'override':r['override'],'restore':r['restore']},ensure_ascii=False),flush=True)
        if sr.api_idle() is not True or sr.api_game() is not None or sr.launcher_processes() or not sr.es_pids():
            s.update({'phase':'PAUSED_SAFETY','error':'ES_OR_LAUNCHER_UNHEALTHY'})
            write_json(CHECKPOINT,s); write_report(s); return
        if sum(x['boot']!='BOOT_OK' for x in s['results'])>=3:
            s.update({'phase':'STOPPED_AFTER_3_FAILURES','error':'Tres o más pilotos fallaron; los restantes no se lanzan.'})
            s['next_game']=GAMES[i+1] if i+1<len(GAMES) else None
            s['restore_status']='VERIFIED'; write_json(CHECKPOINT,s); write_report(s); return
        if sum(x['boot']!='BOOT_OK' for x in s['results'])>=3:
            s.update({'phase':'STOPPED_AFTER_3_FAILURES','error':'Tres o más pilotos fallaron; no se lanzan los restantes.'})
            s['next_game']=GAMES[i+1] if i+1<len(GAMES) else None
            s['restore_status']='VERIFIED'; write_json(CHECKPOINT,s); write_report(s); return
    s['phase']='COMPLETE'; s['next_game']=None
    original=(BACKUP/'batocera.conf').read_bytes()
    expected=original+(b'\n' if original and not original.endswith(b'\n') and s['kept_overrides'] else b'')
    expected+=b''.join(f'mame["{n}.zip"].core=mame\n'.encode('ascii') for n in s['kept_overrides'])
    if CONF.read_bytes()!=expected:
        s.update({'phase':'PAUSED_SAFETY','error':'UNEXPECTED_GLOBAL_CONFIG_DIFF','regression':'DIFF INESPERADO'})
    else:
        s['regression']='NO GLOBAL REGRESSION; solo overrides de juegos piloto pasados; global mame078plus.'
        s['recommendation']='PILOTO INICIAL VALIDADO; detenerse antes de la segunda tanda.' if sum(x['boot']=='BOOT_OK' for x in s['results'])>=4 else 'DETENERSE; analizar fallos antes de ampliar.'
    s['finished_at']=stamp(); write_json(CHECKPOINT,s); write_report(s); update_csv(s['kept_overrides'])
    print(json.dumps({'phase':s['phase'],'pass':sum(x['boot']=='BOOT_OK' for x in s['results']),
      'fail':sum(x['boot']!='BOOT_OK' for x in s['results']),'kept':s['kept_overrides'],
      'reverted':s['reverted_overrides'],'restore':s['restore_status'],'regression':s['regression'],
      'recommendation':s.get('recommendation',''),'error':s.get('error','')},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':
    try: main()
    except Exception as e: print(f'PREFLIGHT_ABORT: {type(e).__name__}: {e}',file=sys.stderr,flush=True); raise
