#!/usr/bin/env python3
"""Build read-only certification/media/multiplayer inventories from ES metadata."""
import csv, json, os, re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path('/userdata/system/state/arcade_audit')
ROMROOT=Path('/userdata/roms')
SYSTEMS=ROOT/'console_system_inventory.csv'
ARCADE=ROOT/'arcade_games_audit.csv'
OLD_CERT=ROOT/'game_certification.csv'
COMPAT=ROOT/'arcade_core_compatibility.csv'
OUT_CERT=ROOT/'full_game_certification.csv'
OUT_MEDIA=ROOT/'media_audit.csv'
OUT_MULTI=ROOT/'multiplayer_games.csv'
OUT_PARTY=ROOT/'TOP_PARTY_GAMES.md'
OUT_8P=ROOT/'GAMES_5_TO_8_PLAYERS.md'
OUT_SUMMARY=ROOT/'FULL_GAME_CERTIFICATION_SUMMARY.md'
OUT_REG=ROOT/'regression_suite.csv'

def csvread(p):
    with p.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def writecsv(p,fields,rows):
    tmp=p.with_suffix(p.suffix+'.tmp')
    with tmp.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    os.replace(tmp,p)
def exists_path(base,value):
    if not value: return 'NO'
    p=Path(value)
    if not p.is_absolute(): p=base/p
    return 'YES' if p.exists() else 'NO'
def number_players(value):
    if not value: return None
    nums=[int(x) for x in re.findall(r'\d+',value)]
    return max(nums) if nums else None
def rom_status(system,rom):
    p=Path(rom)
    if not p.is_absolute(): p=ROMROOT/system/p
    return ('YES' if p.is_file() else 'NO',str(p))
def main():
    systems={x['system']:x for x in csvread(SYSTEMS)}
    prior_cert={(r.get('system',''),Path(r.get('rom','')).name.lower()):r for r in csvread(OLD_CERT)} if OLD_CERT.exists() else {}
    games={}; media=[]; multi=[]; count=Counter(); orphans=[]
    # Existing gamelist XML is only parsed; no ROM/media writes or content hashes.
    for sysname,meta in systems.items():
        base=Path(meta.get('configured_path') or (ROMROOT/sysname))
        gl=base/'gamelist.xml'
        if not gl.is_file(): continue
        try: tree=ET.parse(gl)
        except (ET.ParseError,OSError): count['gamelist_parse_error']+=1; continue
        refs=set()
        for node in tree.getroot().findall('game'):
            def val(tag):
                e=node.find(tag); return (e.text or '').strip() if e is not None else ''
            rom=val('path')
            if not rom: continue
            name=val('name') or Path(rom).stem
            absrom=Path(rom); absrom=absrom if absrom.is_absolute() else (base/absrom).resolve(strict=False)
            rel=absrom.name
            images={k:val(k) for k in ('image','thumbnail','video','fanart')}
            statuses={k:exists_path(base,v) for k,v in images.items()}
            media.append({'system':sysname,'rom':str(absrom),'name':name,**images,
                          'image_exists':statuses['image'],'thumbnail_exists':statuses['thumbnail'],
                          'video_exists':statuses['video'],'fanart_exists':statuses['fanart'],
                          'missing_count':sum(v=='NO' for v in statuses.values()),
                          'guest_importance':'UNRANKED','media_note':'Metadata/reference presence only; no visual quality claim'})
            refs.update(str((base/(v[2:] if v.startswith('./') else v)).resolve(strict=False)) for v in images.values() if v)
            exists='YES' if absrom.is_file() else 'NO'
            key=(sysname,rel.lower())
            games[key]={'system':sysname,'rom':str(absrom),'name':name,'installed':exists,'static_validated':'NOT_TESTED',
                        'boot_status':'NOT_TESTED','boot_core':'','auto_certification':'NOT_TESTED',
                        'control_mode':'OTHER','recommended_control':'UNKNOWN','control_certification':'MANUAL_REQUIRED',
                        'input_software_status':'NOT_TESTED','input_physical_status':'NOT_TESTED',
                        'players_metadata':val('players'),'players_certified':'NOT_TESTED',
                        'exit_certification':'NOT_TESTED','audio_certification':'NOT_TESTED',
                        'video_sanity':'NOT_TESTED','special_control':'UNKNOWN','guest_ready':'NO',
                        'last_test':'','issue':'','notes':'EmulationStation gamelist metadata; not runtime-certified',
                        'playcount':val('playcount'),'lastplayed':val('lastplayed'),'gametime':val('gametime'),
                        'core_candidates':meta.get('configured_cores','')}
            prior=prior_cert.get(key)
            prior=prior or {}
            if prior:
                for src,dst in [('control_mode','control_mode'),('players_metadata','players_metadata'),
                                ('special_control','special_control'),('issue','issue'),('notes','notes')]:
                    if prior.get(src): games[key][dst]=prior[src]
            mode=prior.get('control_mode','')
            if mode in ('BOTONERA','JOYSTICK_RECOMMENDED','JOYSTICK_REQUIRED','SPECIAL_CONTROL','KEYBOARD_MOUSE','DUAL_STICK'):
                games[key]['recommended_control']=mode
            special=(prior.get('special_control','')+' '+val('special_control')).lower()
            if 'lightgun' in special or 'light gun' in special: games[key]['control_mode']='LIGHTGUN_REQUIRED';games[key]['recommended_control']='LIGHTGUN_REQUIRED'
            elif any(k in special for k in ('wheel','volante','pedal')): games[key]['control_mode']='WHEEL_REQUIRED';games[key]['recommended_control']='WHEEL_REQUIRED'
            elif any(k in special for k in ('trackball','spinner','paddle','mouse')): games[key]['control_mode']='SPECIAL_CONTROL';games[key]['recommended_control']='SPECIAL_CONTROL'
            elif 'dual-stick' in special or 'dual stick' in special: games[key]['control_mode']='DUAL_STICK';games[key]['recommended_control']='DUAL_STICK'
            elif mode=='SPECIAL_CONTROL': games[key]['recommended_control']='SPECIAL_CONTROL'
            players=number_players(val('players'))
            if players and players>=2 and not name.lower().startswith('zzz(notgame'):
                multi.append({'system':sysname,'rom':str(absrom),'name':name,'players_metadata':val('players'),
                              'players_supported_runtime':'NOT_TESTED','players_physically_certified':'NOT_TESTED',
                              'control_type':'UNKNOWN','guest_ready':'NO','multitap_or_adapter':'UNKNOWN',
                              'max_players_metadata':players,'source':'gamelist.xml; metadata only'})
            count['gamelist_entries']+=1
        # Orphan detection records only count/path; never deletes anything.
        for folder in ('images','videos'):
            d=base/folder
            if not d.is_dir(): continue
            for parent,dirs,files in os.walk(d,followlinks=False):
                dirs[:]=[x for x in dirs if not (Path(parent)/x).is_symlink()]
                for filename in files:
                    f=str((Path(parent)/filename).resolve(strict=False))
                    if f not in refs: orphans.append({'system':sysname,'path':f,'kind':folder[:-1],
                                                      'classification':'ORPHAN_CANDIDATE','action':'REVIEW_ONLY'})
    # Preserve historic arcade boot evidence separately from new certification evidence.
    for r in csvread(ARCADE):
        system=r['system']; rom=r['rom']; key=(system,Path(rom).name.lower())
        if key not in games:
            name=r.get('gamelist_name') or r.get('name') or Path(rom).stem
            games[key]={'system':system,'rom':r.get('path','') or str(ROMROOT/system/rom),'name':name,
                        'installed':'YES' if r.get('rom_exists','').lower() in ('true','yes') else 'NO',
                        'static_validated':'NOT_TESTED','boot_status':'NOT_TESTED','boot_core':'',
                        'auto_certification':'NOT_TESTED','control_mode':'UNKNOWN','recommended_control':'UNKNOWN',
                        'control_certification':'MANUAL_REQUIRED','input_software_status':'NOT_TESTED',
                        'input_physical_status':'NOT_TESTED','players_metadata':r.get('players',''),
                        'players_certified':'NOT_TESTED','exit_certification':'NOT_TESTED',
                        'audio_certification':'NOT_TESTED','video_sanity':'NOT_TESTED',
                        'special_control':r.get('special_controls','') or 'UNKNOWN','guest_ready':'NO',
                        'last_test':r.get('tested_at',''),'issue':r.get('error',''),
                        'notes':'Arcade inventory; historic BOOT status kept separate from AUTO_CERTIFIED',
                        'playcount':'','lastplayed':'','gametime':'','core_candidates':r.get('core','')}
        g=games[key]
        prior=prior_cert.get(key)
        if prior:
            for src,dst in [('control_mode','control_mode'),('players_metadata','players_metadata'),
                            ('special_control','special_control'),('issue','issue'),('notes','notes')]:
                if prior.get(src): g[dst]=prior[src]
        b=r.get('boot_status','')
        if b:
            g['boot_status']=b
            if b in ('BOOT_OK','BOOT_OK_DEFAULT_CORE','BOOT_OK_FBNEO','BOOT_OK_MAME_CURRENT'):
                g['boot_core']=r.get('core','') or r.get('emulator','')
            elif r.get('error'):
                g['issue']=r['error']
            g['last_test']=r.get('tested_at','')
        if r.get('players'):
            g['players_metadata']=r['players']
            pn=number_players(r['players'])
            if pn and pn>=2:
                if not any(x['system']==system and Path(x['rom']).name.lower()==Path(rom).name.lower() for x in multi):
                    multi.append({'system':system,'rom':g['rom'],'name':g['name'],'players_metadata':r['players'],
                                  'players_supported_runtime':'NOT_TESTED','players_physically_certified':'NOT_TESTED',
                                  'control_type':r.get('control_type','UNKNOWN'),'guest_ready':'NO','multitap_or_adapter':'UNKNOWN',
                                  'max_players_metadata':pn,'source':'arcade_games_audit.csv; metadata only'})
    # Merge the independent MAME-current evidence source; do not double count default-core rows.
    for r in csvread(COMPAT):
        if r.get('system')!='mame' or r.get('tested_mame_current')!='YES': continue
        key=('mame',Path(r.get('rom','')).name.lower());g=games.get(key)
        if not g:continue
        outcome=r.get('mame_current_result','')
        g['mame_current_historical_result']=outcome
        if outcome in ('BOOT_OK','BOOT_PASS'):
            g['boot_status']='BOOT_OK_MAME_CURRENT';g['boot_core']='mame current libretro';g['last_test']=r.get('mame_current_tested_at','')
        elif outcome:
            g['issue']=(g.get('issue','')+'; ' if g.get('issue') else '')+'MAME_CURRENT:'+outcome
    rows=list(games.values())
    fields=['system','rom','name','installed','lifecycle_state','static_validated','boot_status','boot_core','mame_current_historical_result','auto_certification',
            'control_mode','recommended_control','control_certification','input_software_status','input_physical_status',
            'players_metadata','players_certified','exit_certification','audio_certification','video_sanity',
            'special_control','guest_ready','last_test','issue','notes','playcount','lastplayed','gametime','core_candidates']
    for g in rows:
        g['lifecycle_state']='INSTALLED' if g['installed']=='YES' else 'NOT_TESTED'
        if g['installed']=='NO': g['static_validated']='FAIL'
    writecsv(OUT_CERT,fields,rows)
    mfields=['system','rom','name','image','image_exists','thumbnail','thumbnail_exists','video','video_exists','fanart','fanart_exists','missing_count','guest_importance','media_note']
    writecsv(OUT_MEDIA,mfields,media)
    pfields=['system','rom','name','players_metadata','max_players_metadata','players_supported_runtime','players_physically_certified','control_type','multitap_or_adapter','guest_ready','source']
    writecsv(OUT_MULTI,pfields,multi)
    # 5-8 players are metadata-only and must not imply runtime or physical capability.
    large=[x for x in multi if 5<=x['max_players_metadata']<=8]
    over8=[x for x in multi if x['max_players_metadata']>8]
    def mdlist(items):
        return '\n'.join(f"- `{x['system']}/{Path(x['rom']).name}` — {x['name']} (metadata: {x['players_metadata']}; runtime: NOT_TESTED; físico: NOT_TESTED)" for x in items) or '- Ningún candidato instalado identificado por metadata.'
    OUT_8P.write_text('# Juegos de 5 a 8 jugadores — estado de auditoría\n\nLa metadata de jugadores no certifica soporte runtime ni controles físicos.\n\n## Instalados según gamelist/inventario (metadata 5–8)\n\n'+mdlist(large)+'\n\n## Metadata superior a 8 (no contada como 5–8)\n\n'+mdlist(over8)+'\n\n## AUTO_CERTIFIED / CONTROL_CERTIFIED / GUEST_READY\n\n- Ninguno certificado por esta fase.\n\n## Requisitos pendientes\n\n- Validar límite real del core/emulador, multitap/adaptadores y número de dispositivos.\n- Certificación física requiere controles reales para cada plaza.\n',encoding='utf-8')
    # Transparent provisional party score; no popularity claims beyond play history/metadata.
    scored=[]
    for x in multi:
        name=x['name'].lower(); n=x['max_players_metadata']; score=min(n,8)*8
        score+=20 if x['players_supported_runtime']=='PASS' else 0
        score+=25 if x['guest_ready']=='YES' else 0
        score+=10 if any(k in name for k in ('turtles','simpsons','x-men','gauntlet','nba jam','capcom sports','party')) else 0
        scored.append((score,x))
    top=sorted(scored,key=lambda y:(-y[0],y[1]['name']))[:100]
    OUT_PARTY.write_text('# Candidatos party — ranking provisional\n\n`PARTY_SCORE` provisional: metadata de jugadores (8 puntos por plaza, tope 64) + soporte runtime certificado (+20) + GUEST_READY (+25) + coincidencia de títulos comunitariamente conocidos (+10). Este ranking **no demuestra popularidad ni jugabilidad**; todos los runtime/control/GUEST_READY no medidos se mantienen así.\n\n'+''.join(f"{i}. **{x['name']}** — `{x['system']}/{Path(x['rom']).name}` · PARTY_SCORE {score} · {x['players_metadata']} · runtime NOT_TESTED · Guest NO\n" for i,(score,x) in enumerate(top,1)),encoding='utf-8')
    # Small representative regression suite; all entries remain NOT_RUN.
    suite=[]
    for x in rows:
        nam=x['name'].lower(); sys=x['system']
        bucket=None
        if sys in ('mame','fbneo') and any(k in nam for k in ('street fighter','mortal kombat','tekken','king of fighters')): bucket='FIGHTING'
        elif sys in ('mame','fbneo') and any(k in nam for k in ('final fight','cadillacs','turtles','simpsons','captain commando')): bucket='BEAT_EM_UP'
        elif sys in ('mame','fbneo') and number_players(x['players_metadata'] or '') and number_players(x['players_metadata'] or '')>=4: bucket='4P'
        elif sys in ('psx','ps1'): bucket='PS1'
        elif sys=='ps2': bucket='PS2'
        elif sys=='dreamcast': bucket='DREAMCAST'
        elif sys=='n64': bucket='N64'
        if bucket and len([q for q in suite if q['category']==bucket])<5:
            suite.append({'category':bucket,'system':sys,'rom':Path(x['rom']).name,'name':x['name'],'status':'NOT_RUN','reason':'Representative regression candidate; launch blocked pending safe current baseline'})
    writecsv(OUT_REG,['category','system','rom','name','status','reason'],suite)
    missing=sum(1 for x in media if x['image_exists']=='NO')
    summary=Counter(x['auto_certification'] for x in rows)
    OUT_SUMMARY.write_text('# Certificación juego por juego — resumen inicial\n\n'
        f"- Fecha: {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n- Sistemas con entradas gamelist: {len(set(x['system'] for x in media))}; juegos/registros deduplicados: {len(rows)}\n"
        f"- STATIC_VALIDATED: 0 (la presencia del path no valida dependencias ni contenido completo)\n- AUTO_CERTIFIED: {summary.get('AUTO_CERTIFIED',0)}\n"
        f"- NOT_TESTED: {summary.get('NOT_TESTED',0)}; FAIL confirmado: 0 en esta nueva pasada; FAIL históricos se conservan en arcade_games_audit.csv\n"
        f"- CONTROL_CERTIFIED: 0; GUEST_READY: 0\n- Multiplayer metadata >=2: {len(multi)}; metadata 5-8P: {len(large)} (runtime y físico NOT_TESTED)\n"
        f"- Multimedia: {len(media)} entradas con gamelist; sin imagen: {missing}; huérfanos candidatos: {len(orphans)}\n- Regresión: {len(suite)} candidatos, todos NOT_RUN\n\n"
        'La clasificación previa BOOT_OK es evidencia histórica separada. No se convierte en AUTO_CERTIFIED porque esta fase todavía no validó en tiempo real audio, pantalla, identidad, estabilidad y restore bajo un baseline actual. La preflight del runner anterior encontró exclusivamente un delta de 18 overrides autorizados en `batocera.conf`; su restaurador usaría una copia antigua y por eso el lanzamiento está bloqueado hasta crear un baseline transaccional vigente. No se modificó el runtime ni se lanzaron juegos.\n',encoding='utf-8')
    writecsv(ROOT/'media_orphan_candidates.csv',['system','path','kind','classification','action'],orphans)
    print(json.dumps({'certification_rows':len(rows),'gamelist_media_rows':len(media),'multiplayer_metadata_rows':len(multi),
                      'five_to_eight_metadata_rows':len(large),'orphan_media_candidates':len(orphans),
                      'missing_primary_images':missing,'regression_suite_rows':len(suite)},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
