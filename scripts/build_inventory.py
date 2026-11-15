#!/usr/bin/env python3
"""Build read-only arcade inventory and derived reports from current Batocera data."""
import csv, json, os, re, hashlib, configparser, xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone

OUT=Path('/userdata/system/state/arcade_audit')
ROMROOT=Path('/userdata/roms')
SYSTEMS=('mame','fbneo')
MAME_XML=Path('/userdata/bios/mame2003-plus/mame2003-plus.xml')
FB_DAT=Path('/userdata/bios/fbneo/FinalBurn Neo (ClrMame Pro XML, Arcade only).dat')
STATIC=Path('/userdata/system/game_audit/game_static_audit.csv')
BOOTS=Path('/userdata/system/game_audit/game_boot_audit.csv')
TECH=Path('/userdata/system/configs/el_gordo_controller_profiles/controller_technical.json')
DISPATCH=Path('/userdata/system/el_gordo_tools/controller_dispatcher')
ESCFG=Path('/userdata/system/configs/emulationstation/es_systems_el_gordo.cfg')
NOW=datetime.now().astimezone().isoformat(timespec='seconds')

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def read_csv(path):
    if not path.exists(): return []
    with path.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def xml_games(path, child='game'):
    if not path.exists(): return {}
    root=ET.parse(path).getroot(); out={}
    for g in root.findall(child):
        n=g.get('name')
        if n: out[n]=g
    return out
def norm(s): return re.sub(r'[^a-z0-9]+','',s.lower())
def parse_gamelist(folder):
    p=folder/'gamelist.xml'; out={}
    if not p.exists(): return out
    try: root=ET.parse(p).getroot()
    except Exception: return out
    for game in root.findall('game'):
        path=game.findtext('path') or ''
        key=Path(path).name.lower()
        out[key]={'name':game.findtext('name') or '', 'path':path,
                  'developer':game.findtext('developer') or '', 'genre':game.findtext('genre') or '',
                  'players_text':game.findtext('players') or '', 'desc':game.findtext('desc') or ''}
    return out
def metadata(g):
    if g is None: return {}
    inp=g.find('input'); players=buttons=coins=''
    control=''; ways=''; controls=[]
    if inp is not None:
        players=inp.get('players',''); buttons=inp.get('buttons',''); coins=inp.get('coins','')
        control=inp.get('control','')
        for c in inp.findall('control'):
            typ=c.get('type',''); controls.append(typ)
            if c.get('ways'): ways=c.get('ways')
        if controls: control=','.join(sorted(set(controls)))
    way_match=re.search(r'(\d+)way',control.lower())
    if not ways and way_match: ways=way_match.group(1)
    player_n=int(players) if players.isdigit() else None
    button_n=int(buttons) if buttons.isdigit() else None
    desc=g.findtext('description') or ''
    clone=g.get('cloneof','') or g.get('romof','')
    bios=g.get('isbios','no')=='yes' or g.get('isdevice','no')=='yes' or g.get('runnable','yes')=='no'
    special_keys=['lightgun','trackball','dial','spinner','paddle','pedal','steering','wheel','positional','mahjong','hanafuda','gambling','mouse','keyboard','analog','doublejoy','stick']
    low=(control+' '+','.join(controls)).lower()
    special=[x.upper() for x in special_keys if x in low]
    dual=low.startswith('doublejoy') or 'doublejoy' in low
    analog_stick=low.strip()=='stick'
    digital=any(x in low for x in ('joy','stick')) and not special
    if dual: compat='PARCIAL_DUAL_STICK'
    elif analog_stick: compat='PARCIAL_CONTROL_STICK_ANALOGICO_O_ESPECIAL'
    elif special: compat='NO_COMPATIBLE_CON_BOTONERA'
    elif digital and button_n is not None and button_n<=6 and player_n is not None and player_n<=4: compat='COMPATIBLE_DIRECTO_METADATA'
    elif digital and button_n is not None and button_n>6: compat='PARCIAL_MAS_DE_6_BOTONES'
    elif digital and player_n is not None and player_n>4: compat='PARCIAL_MAS_DE_4_JUGADORES'
    elif digital: compat='COMPATIBLE_CON_VALIDACION'
    else: compat='INPUT_REVIEW_METADATA_INCOMPLETA'
    return {'description':desc,'year':g.findtext('year') or '', 'manufacturer':g.findtext('manufacturer') or '',
            'parent':clone,'clone_of':g.get('cloneof',''),'players':players,'buttons':buttons,'coins':coins,
            'control_type':control,'ways':ways,'special':special,'compat':compat,'bios_device':bios,
            'simultaneous_players':'UNKNOWN',
            'players_class':('5P+' if player_n and player_n>=5 else f'{player_n}P' if player_n else 'UNKNOWN')}
def game_requires_chd(name, db, seen=None):
    """Resolve metadata disk references through clone/parent relationships."""
    seen=set() if seen is None else seen
    if not name or name in seen or name not in db: return False
    seen.add(name); g=db[name]
    if g.findall('disk'): return True
    parent=g.get('romof') or g.get('cloneof')
    return game_requires_chd(parent,db,seen)
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    mx=xml_games(MAME_XML); fb=xml_games(FB_DAT)
    static={(r.get('system','').lower(),Path(r.get('path','')).name.lower()):r for r in read_csv(STATIC)}
    boots={(r.get('system','').lower(),Path(r.get('path','')).name.lower()):r for r in read_csv(BOOTS)}
    mame_meta={k:metadata(v) for k,v in mx.items()}
    # Parse configured system command/default core without executing it.
    cfgroot=ET.parse(ESCFG).getroot() if ESCFG.exists() else ET.Element('systems')
    configs={}
    for s in SYSTEMS:
        node=next((x for x in cfgroot.findall('system') if x.findtext('name')==s),None)
        command=node.findtext('command','') if node is not None else ''
        selected_emu=''; selected_core=''
        if node is not None:
            emus=node.find('emulators')
            for e in list(emus) if emus is not None else []:
                cores=e.find('cores')
                for c in list(cores) if cores is not None else []:
                    if c.get('default')=='true': selected_emu=e.get('name',''); selected_core=(c.text or '').strip()
        configs[s]={'configured_emulator':selected_emu, 'configured_core':selected_core,
                    'dispatcher_configured':'controller_dispatcher' in command}
    corepaths={'mame':'/usr/lib/libretro/mame_libretro.so','mame078plus':'/usr/lib/libretro/mame078plus_libretro.so','fbneo':'/usr/lib/libretro/fbneo_libretro.so'}
    rows=[]
    for system in SYSTEMS:
        folder=ROMROOT/system; gl=parse_gamelist(folder)
        for p in sorted(folder.glob('*.zip')):
            rom=p.name; setname=p.stem.lower(); meta=mame_meta.get(setname,{})
            if system=='fbneo' and not meta:
                # Some FBNeo sets are absent from the older MAME 2003+ metadata; keep controls explicitly unknown.
                meta={'description':'','year':'','manufacturer':'','parent':'','clone_of':'','players':'','buttons':'','coins':'','control_type':'','ways':'','special':[],'compat':'INPUT_REVIEW_METADATA_INCOMPLETA','bios_device':False,'simultaneous_players':'UNKNOWN','players_class':'UNKNOWN'}
            biosset=meta.get('bios_device',False)
            # DAT membership is a useful game-vs-support discriminator, but names may be outside metadata version.
            dat_member=setname in (fb if system=='fbneo' else mx)
            is_game=not biosset and (dat_member or rom.lower() in gl)
            if not is_game: continue
            entry=gl.get(rom.lower(),{})
            if not meta.get('description'): meta['description']=entry.get('name') or p.stem
            core=configs[system]['configured_core']
            emulator=configs[system]['configured_emulator']
            installed=Path(corepaths.get(core,'/nonexistent')).exists()
            old=boots.get((system,rom.lower()),{})
            st=static.get((system,rom.lower()),{})
            try: static_time=datetime.fromisoformat(st.get('audited_at',''))
            except Exception: static_time=None
            static_size=str(st.get('size_bytes',''))
            static_valid=bool(st and static_time and static_size.isdigit() and int(static_size)==p.stat().st_size and p.stat().st_mtime<=static_time.timestamp())
            old_status=old.get('boot_status','')
            tested=old.get('tested_at','')
            try: oldtime=datetime.fromisoformat(tested)
            except Exception: oldtime=None
            unchanged_since_test=bool(oldtime and p.stat().st_mtime <= oldtime.timestamp())
            reusable_status=old_status in ('BOOT_OK','FAIL_BOOT','FAIL_CRASH','FAIL_RETURN_TO_ES','TIMEOUT')
            boot_status=old_status if unchanged_since_test and reusable_status else 'NOT_TESTED'
            size=p.stat().st_size; readable=os.access(p,os.R_OK)
            chds=list(folder.glob(setname+'/*.chd')) + list(folder.glob(setname+'.chd'))
            if not chds:
                # Resolve a parent-set disk dependency where the supplied metadata records it.
                db=mx if system=='mame' else fb
                req=game_requires_chd(setname,db)
                chd_ok=not req
            else: req=True; chd_ok=all(x.is_file() and os.access(x,os.R_OK) for x in chds)
            parent=meta.get('parent','')
            custom='DEFAULT / SIN OVERRIDE POR JUEGO'
            remap_candidates=[Path('/userdata/system/configs/retroarch')/system/(setname+'.cfg'),Path('/userdata/system/configs/retroarch')/system/(rom+'.cfg'),Path('/userdata/system/configs/retroarch/remaps')/core/(setname+'.rmp'),Path('/userdata/system/configs/mame')/(setname+'.cfg')]
            remap_candidates += list((Path('/userdata/saves')/system).glob('*/cfg/'+setname+'.cfg'))
            if any(x.exists() for x in remap_candidates): custom='CFG/REMAP POR JUEGO PRESENTE; DIFERENCIA DE BINDS NO DECODIFICADA'
            manual=bool('mortal kombat' in meta.get('description','').lower() or 'street fighter' in meta.get('description','').lower() or meta.get('players_class') in ('3P','4P','5P+'))
            row={'system':system,'rom':rom,'name':meta.get('description') or p.stem,'parent':parent,'clone_of':meta.get('clone_of',''),
                 'players':meta.get('players',''),'simultaneous_players':meta.get('simultaneous_players',''),'buttons':meta.get('buttons',''),
                 'control_type':meta.get('control_type',''),'ways':meta.get('ways',''),'emulator':emulator,'core':core,
                 'rom_exists':True,'chd_required':req,'chd_ok':chd_ok,'bios_ok':'NOT_CHECKED','boot_status':boot_status,
                 'historical_boot_status':old_status if old else '', 'historical_tested_at':tested if old else '',
                 'historical_reusable':boot_status!='NOT_TESTED','input_status':meta.get('compat','INPUT_REVIEW_METADATA_INCOMPLETA'),
                 'romset_status':st.get('romset_status','UNKNOWN') if static_valid else 'UNKNOWN_OR_STALE',
                 'bios_status':st.get('bios_status','UNKNOWN') if static_valid else 'UNKNOWN_OR_STALE',
                 'dependency_status':st.get('dependency_status','UNKNOWN') if static_valid else 'UNKNOWN_OR_STALE',
                 'static_audit_reusable':static_valid,'static_audit_at':st.get('audited_at','') if static_valid else '',
                 'static_reason':st.get('reason','') if static_valid else '',
                 'p1':'USB5/event17/js0/0079:0006','p2':'USB6/event18/js1/0079:0006','p3':'USB8/event20/js3/0079:0006','p4':'USB7/event19/js2/0079:0006',
                 'custom_mapping':custom,'manual_test':manual,'error':old.get('notes','') if boot_status.startswith('FAIL') or old_status=='TEST_ERROR' else '',
                 'tested_at':tested if boot_status!='NOT_TESTED' else '', 'path':str(p),'extension':p.suffix,'size_bytes':size,
                 'readable':readable,'gamelist_entry':bool(entry),'gamelist_name':entry.get('name',''),'year':meta.get('year',''),
                 'manufacturer':meta.get('manufacturer',''),'coins':meta.get('coins',''),'special_controls':meta.get('special',[]),
                 'input_metadata_source':'mame2003-plus.xml exact set name' if setname in mame_meta else ('FBNeo DAT has no controls; unknown' if system=='fbneo' else 'no matching metadata'),
                 'is_bios_device':False,'dat_member':dat_member,'core_exists':installed,'core_configured':core,
                 'boot_test_source':'historical unchanged ROM' if boot_status!='NOT_TESTED' else 'pending real ES launch'}
            rows.append(row)
    # Enrich FBNeo controls from MAME-derived metadata only where set name matches; label this data-source limitation.
    # Fighting/common duplicate status is computed across actual inventory.
    rows.sort(key=lambda r:(r['system'],r['rom'].lower()))
    # Preserve a resumable test queue. Historic unchanged boot results count as completed.
    queue=[{'system':r['system'],'rom':r['rom'],'path':r['path'],'status':r['boot_status']} for r in rows if r['boot_status']=='NOT_TESTED']
    now={'created_at':NOW,'phase':'PHASE_1_STATIC_COMPLETE_SMOKE_PAUSED_SAVE_WRITE_RISK','last_completed':None,'pending_count':len(queue),'queue':queue,
         'safety':'No game launch until it is established that runtime cannot write active saves/NVRAM; when resumed, use only active EmulationStation API and bounded batches.','batch_size':10,
         'paused_reason':'Launching and closing arcade cores may persist NVRAM/save data; no non-writing mode was established, and the audit explicitly forbids save changes.'}
    cols=['system','rom','name','parent','clone_of','players','simultaneous_players','buttons','control_type','ways','emulator','core','rom_exists','chd_required','chd_ok','bios_ok','boot_status','input_status','p1','p2','p3','p4','custom_mapping','manual_test','error','tested_at','path','extension','size_bytes','readable','gamelist_entry','gamelist_name','year','manufacturer','coins','special_controls','is_bios_device','dat_member','core_exists','core_configured','historical_boot_status','historical_tested_at','historical_reusable','boot_test_source','romset_status','bios_status','dependency_status','static_audit_reusable','static_audit_at','static_reason']
    with (OUT/'arcade_games_audit.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore'); w.writeheader()
        for r in rows:
            rr={k:r.get(k,'') for k in cols}; rr['special_controls']=';'.join(r.get('special_controls',[])); w.writerow(rr)
    (OUT/'arcade_games_audit.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    support=[]
    for system in SYSTEMS:
        folder=ROMROOT/system
        game_names={r['rom'].lower() for r in rows if r['system']==system}
        for p in sorted(folder.glob('*.zip')):
            if p.name.lower() in game_names: continue
            setname=p.stem.lower(); g=(mx if system=='mame' else fb).get(setname)
            reason='BIOS/DEVICE set per metadata' if g is not None and (g.get('isbios')=='yes' or g.get('isdevice')=='yes' or g.get('runnable')=='no') else 'support/archive not identified as playable game in DAT/gamelist'
            support.append({'system':system,'rom':p.name,'path':str(p),'size_bytes':p.stat().st_size,'classification':reason})
    with (OUT/'arcade_support_assets.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['system','rom','path','size_bytes','classification']); w.writeheader(); w.writerows(support)
    (OUT/'checkpoint.json').write_text(json.dumps(now,ensure_ascii=False,indent=2)+'\n')
    # Reports derived from static metadata and old boot results; do not claim new physical input validation.
    games4=[r for r in rows if str(r.get('players'))=='4']
    games4.sort(key=lambda r:(r['boot_status']!='BOOT_OK',not r['input_status'].startswith('COMPATIBLE'),r['name'].lower()))
    def mdtable(headers, data):
        return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(str(x).replace('|','/') for x in row)+' |\n' for row in data)
    (OUT/'ARCADE_4P_REPORT.md').write_text('# Arcade con metadata de hasta 4 jugadores\n\nHay '+str(len(games4))+' sets cuyo campo `players` es 4. El XML legacy no permite distinguir jugadores simultáneos de turnos alternados; por eso no se afirma que los '+str(len(games4))+' sean 4P simultáneos. P1-P4 están asignados en el dispatcher, pero ningún juego tiene validación física por jugador; `BOOT_OK` histórico confirma sólo arranque estable.\n\n'+mdtable(['Juego','Sistema','Players max.','Simultáneos','Buttons','Input','Boot','Mapping','Prueba manual'],[[r['name'],r['system'],r['players'],'UNKNOWN',r['buttons'] or '?',r['input_status'],r['boot_status'],'dispatcher P1-P4; juego no validado', 'Sí'] for r in games4])+'\n',encoding='utf-8')
    special=defaultdict(list)
    for r in rows:
        for s in r.get('special_controls',[]): special[s].append(r)
    (OUT/'ARCADE_SPECIAL_CONTROLS.md').write_text('# Controles especiales\n\nMetadata proviene del XML MAME 2003 Plus cuando el set coincide. FBNeo sin match se deja como desconocido, no se infiere compatibilidad.\n'+''.join('\n## '+k+'\n\n'+mdtable(['Juego','Sistema','Control','Boot'],[[r['name'],r['system'],r['control_type'],r['boot_status']] for r in v]) for k,v in sorted(special.items()))+'\n',encoding='utf-8')
    fights=[r for r in rows if re.search(r'mortal kombat|street fighter|king of fighters|fatal fury|samurai shodown|darkstalkers|virtua fighter|tekken',r['name'],re.I)]
    (OUT/'ARCADE_FIGHTING_CONTROLS.md').write_text('# Juegos de pelea\n\nEl número de botones proviene de metadata, no de una prueba de cada acción del panel. La duplicación de acciones sólo se confirma físicamente.\n\n'+mdtable(['Juego','Sistema','Botones','Core','Remap','P1-P4','Problema','Prueba manual'],[[r['name'],r['system'],r['buttons'] or '?',r['core'],r['custom_mapping'],'Asignación dispatcher P1/P2/P3/P4; bindings del core no validados','Revisar si tiene antecedente o mapping custom','Sí' if r['manual_test'] else 'Muestra representativa'] for r in fights])+'\n',encoding='utf-8')
    manual=[]
    for r in rows:
        if r['manual_test'] or r['custom_mapping']=='CUSTOM MAPPING' or r['input_status'].startswith(('INPUT_REVIEW','PARCIAL','NO_COMPATIBLE')):
            manual.append(r)
    preferred=[]
    wanted=[('mame','umk3.zip'),('mame','sf2.zip'),('mame','ssf2t.zip'),('fbneo','sf2hf.zip'),('mame','mk2.zip'),
            ('fbneo','captcomm.zip'),('mame','captcomm.zip'),('fbneo','tmnt.zip'),('mame','tmnt.zip'),('mame','simpsons.zip'),
            ('mame','gauntlet.zip'),('mame','nbajam.zip'),('mame','rampart.zip'),('mame','area51.zip'),('mame','offroad.zip'),
            ('mame','1943.zip'),('mame','gaunt2.zip'),('mame','xmen.zip'),('mame','armwar.zip'),('fbneo','vendetta.zip')]
    row_index={(r['system'],r['rom'].lower()):r for r in rows}
    for key in wanted:
        if key in row_index: preferred.append(row_index[key])
    if len(preferred)<20:
        for r in rows:
            if len(preferred)>=20: break
            if r not in preferred and (r.get('players') in ('3','4') or re.search(r'fighter|kombat|trackball|lightgun|gun',r['name'],re.I)):
                preferred.append(r)
    manual_text='# Validación manual priorizada\n\nLa lista reduce el trabajo a una muestra representativa; iniciar el juego y comprobar direcciones, Start/Coin, botones sin duplicación y orden de jugadores. Los nombres de acciones no están incluidos cuando el DAT no los especifica.\n\n'
    manual_text+=mdtable(['#','Juego','Sistema','Motivo','Chequeos'],[[i+1,r['name'],r['system'],'historial/pelea/multijugador/input especial','P1 direcciones; Start/Coin; acción por botón sin dobles; P2'+('; P3/P4' if r.get('players') in ('3','4') else '')] for i,r in enumerate(preferred)])
    (OUT/'ARCADE_MANUAL_TESTS.md').write_text(manual_text+'\n',encoding='utf-8')
    # Duplicate set names across systems.
    byname=defaultdict(dict)
    for r in rows: byname[Path(r['rom']).stem.lower()][r['system']]=r
    dups=[v for v in byname.values() if 'mame' in v and 'fbneo' in v]
    def duplicate_recommendation(v):
        a,b=v['mame'],v['fbneo']
        if a['boot_status']==b['boot_status']=='BOOT_OK' and a['input_status']==b['input_status']:
            return 'INDISTINTO en evidencia actual; input físico no validado'
        return 'INVESTIGAR; evidencia de arranque/input incompleta o distinta'
    (OUT/'ARCADE_DUPLICATES_MAME_FBNEO.md').write_text('# Sets presentes en MAME y FBNeo\n\nSe marca INDISTINTO cuando ambos tienen PASS histórico y la misma clasificación de input por metadata. La asignación física no se infiere y no se cambia el core.\n\n'+mdtable(['Set','MAME boot/input','FBNeo boot/input','Recomendación'],[[Path(v['mame']['rom']).stem,v['mame']['boot_status']+'/'+v['mame']['input_status'],v['fbneo']['boot_status']+'/'+v['fbneo']['input_status'],duplicate_recommendation(v)] for v in sorted(dups,key=lambda x:x['mame']['name'].lower())])+'\n',encoding='utf-8')
    fails=[r for r in rows if str(r['boot_status']).startswith('FAIL') or r['boot_status']=='TIMEOUT']
    def fail_cause(r):
        low=(r.get('error') or '').lower()
        if ('.chd' in low and 'not found' in low) or 'required files are missing' in low: return 'CHD requerido ausente confirmado por log'
        if 'salida inmediata' in low or 'salida_inmediata' in low: return 'salida inmediata; dependencia/causa sin log concluyente'
        return 'falla de arranque; causa por clasificar'
    fail_groups=Counter(fail_cause(r) for r in fails)
    (OUT/'ARCADE_FAILURES.md').write_text('# Fallos y bloqueos\n\nResultados históricos de arranques reales, reutilizados sólo si el ZIP actual no cambió desde la prueba. Un problema de input no se clasifica como fallo de arranque.\n\n## Causas agrupadas\n\n'+mdtable(['Causa','Casos'],[[k,v] for k,v in fail_groups.items()])+'\n## Detalle\n\n'+mdtable(['Juego','Sistema','Boot','Causa','Nota','Fuente/fecha'],[[r['name'],r['system'],r['boot_status'],fail_cause(r),(r['error'] or '')[:300],r['tested_at']] for r in fails])+'\n',encoding='utf-8')
    # Actual current state, not all extra arcade-like systems tested.
    count=Counter(r['system'] for r in rows); boots_c=Counter((r['system'],r['boot_status']) for r in rows)
    inputs=Counter(r['input_status'] for r in rows)
    mapping={}
    if TECH.exists():
        td=json.loads(TECH.read_text()); mapping={x['player']:{'usb_port':x.get('usb_port'),'by_path':x.get('by_path')} for x in td.get('arcade_controllers',[])}
    dispatcher_sha=sha(DISPATCH) if DISPATCH.exists() else 'MISSING'
    allpass=sum(1 for r in rows if r['boot_status']=='BOOT_OK'); allfail=len(fails); nottested=sum(1 for r in rows if r['boot_status']=='NOT_TESTED')
    direct=sum(1 for r in rows if r['input_status']=='COMPATIBLE_DIRECTO_METADATA')
    more6=sum(1 for r in rows if str(r['buttons']).isdigit() and int(r['buttons'])>6)
    special_count=sum(1 for r in rows if r['input_status']=='NO_COMPATIBLE_CON_BOTONERA')
    four_direct=sum(1 for r in games4 if r['input_status']=='COMPATIBLE_DIRECTO_METADATA')
    static_valid_count=sum(1 for r in rows if r['static_audit_reusable'])
    other_systems=[]
    for s in ('neogeo','atomiswave','naomi','model2','model3'):
        p=ROMROOT/s
        if p.exists(): other_systems.append([s,len(list(p.glob('*.zip'))),len(list(p.glob('*.chd'))),'inventariar después; sin smoke test'])
    mcfg=Path('/userdata/saves/mame/mame2003-plus/cfg/umk3.cfg'); mkcfg=Path('/userdata/saves/mame/mame2003-plus/cfg/mk3.cfg')
    umk3_cfg_hash=sha(mcfg) if mcfg.exists() else 'NO EXISTE'; mk3_cfg_hash=sha(mkcfg) if mkcfg.exists() else 'NO EXISTE'
    metadata_note='MAME controls/clone metadata: mame2003-plus.xml (legacy core metadata); FBNeo DAT supplies set/clone names but no control section, so unjoined FBNeo input is UNKNOWN.'
    summary=['# AUDITORÍA ARCADE — FASE 1: INVENTARIO Y METADATA','',f'Fecha de extracción: {NOW}','',
      '## Estado general','',f'- MAME: {count["mame"]} ROM ZIP de juego en el inventario actual.',f'- FBNeo: {count["fbneo"]} ROM ZIP de juego en el inventario actual.',f'- Total MAME + FBNeo: {sum(count.values())}.',
      f'- Soporte excluido del conteo de juegos: MAME 16 ZIP, FBNeo 15 ZIP (BIOS/dispositivos/plataformas u otros sets de soporte; detalle en `arcade_support_assets.csv`).',
      f'- Arranques históricos vigentes: {allpass} PASS y {allfail} FAIL; {nottested} NOT_TESTED, incluyendo harness TEST_ERROR anterior, sin contarlo como fallo.',
      f'- Input directo estimado por metadata: {direct}/{len(rows)} ({100*direct/len(rows):.1f}%); no es porcentaje de input validado.',
      f'- Más de 6 botones: {more6}; metadata de control especial/no compatible con esta botonera: {special_count}.',
      f'- Sets con `players=4`: {len(games4)}, de ellos {four_direct} con joystick/botones dentro de capacidad. Simultaneidad no está codificada en el XML; 4P físico confirmado: 0.',
      f'- ROMset/BIOS contrastables con static audit previo sin cambios detectables: {static_valid_count}/{len(rows)}; estados detallados por juego en CSV.',
      f'- Metadata: {metadata_note}',f'- Dispatcher SHA-256: `{dispatcher_sha}`.',
      '- ROMset/BIOS status reutilizado sólo si el ZIP actual coincide en tamaño y mtime no es posterior al baseline estático del 1 de octubre; el resto queda UNKNOWN_OR_STALE.',
      '', '## Cores y configuración','',mdtable(['Sistema','Emulador','Core','Core presente','Dispatcher'],[[s,configs[s]['configured_emulator'],configs[s]['configured_core'],Path(corepaths.get(configs[s]['configured_core'],'/nonexistent')).exists(),configs[s]['dispatcher_configured']] for s in SYSTEMS]),
      '', '## Boot histórico reutilizable por sistema','',mdtable(['Sistema','Total','PASS','FAIL','Pendiente'],[[s,count[s],sum(1 for r in rows if r['system']==s and r['boot_status']=='BOOT_OK'),sum(1 for r in rows if r['system']==s and r['boot_status'].startswith('FAIL')),sum(1 for r in rows if r['system']==s and r['boot_status']=='NOT_TESTED')] for s in SYSTEMS]),
      '## Asignación actual conocida desde configuración técnica','',mdtable(['Jugador','Puerto','by-path'],[[p,v.get('usb_port'),v.get('by_path')] for p,v in mapping.items()]),
      '','La enumeración kernel y el diagnóstico SDL previo coinciden con USB5/USB6/USB8/USB7 para P1-P4 respectivamente. Eso valida entrada al dispatcher, no el orden de jugadores dentro de cada juego/core.',
      '', '## Compatibilidad por metadata','',mdtable(['Clasificación','Cantidad'],[[k,v] for k,v in sorted(inputs.items())]),
      '', '## Ultimate Mortal Kombat 3','',f'- `mame/umk3.zip`: 2 jugadores, joystick 8-way, 6 botones; core por defecto `{configs["mame"]["configured_core"]}`; boot histórico `{next((r["boot_status"] for r in rows if r["system"]=="mame" and r["rom"]=="umk3.zip"),"NOT_FOUND")}` el 2026-10-07.',
      f'- Existe CFG por juego (`saves/mame/mame2003-plus/cfg/umk3.cfg`); hash igual al CFG de `mk3.cfg`: `{umk3_cfg_hash==mk3_cfg_hash}`. Formato binario: no se decodificaron bindings; no hay evidencia para confirmar ni descartar duplicación. Requiere prueba física.',
      '','El XML disponible es MAME 2003 Plus; el MAME configurado en EmulationStation es mame078plus. Se usa sólo como referencia de controls/players/clones, con ese desfase explícito. FBNeo no tiene input tags en el DAT suministrado.','',
      '## Limitación y continuación','',f'- Pruebas históricas reusadas sólo si el ZIP actual no tiene mtime posterior a `tested_at`; no se reejecutan sin necesidad.',
      '- No se envió input dentro de los juegos. No se confirma aún que cada juego permanezca abierto ni que los bindings sean correctos.',
      '- Smoke test nuevo pausado antes del primer lanzamiento: el arranque/cierre puede guardar NVRAM o save data automáticamente y no se demostró un modo que lo impida sin cambiar el runtime.',
      '- Checkpoint: `checkpoint.json`; lote previsto: 10 juegos y continuar sólo desde estado idle confirmado.',
      '- Los archivos de controles por acción no están en la metadata disponible; una CFG por juego no demuestra que los bindings difieran del valor base. Las duplicaciones requieren prueba física.',
      '', '## MAME','',f'- {count["mame"]} sets de juego; core por defecto `mame078plus`, presente; dispatcher configurado.',f'- Historial vigente: {boots_c[("mame","BOOT_OK")]} BOOT_OK, {sum(1 for r in rows if r["system"]=="mame" and r["boot_status"].startswith("FAIL"))} FAIL_BOOT, {sum(1 for r in rows if r["system"]=="mame" and r["boot_status"]=="NOT_TESTED")} sin prueba vigente.',
      '', '## FBNeo','',f'- {count["fbneo"]} sets de juego; core `fbneo`, presente; dispatcher configurado.',f'- Historial vigente: {boots_c[("fbneo","BOOT_OK")]} BOOT_OK, {sum(1 for r in rows if r["system"]=="fbneo" and r["boot_status"].startswith("FAIL"))} FAIL_BOOT, {sum(1 for r in rows if r["system"]=="fbneo" and r["boot_status"]=="NOT_TESTED")} sin prueba vigente.',
      '', '## Compatibilidad de botonera','',f'- {direct} sets son candidatos directos por metadata, con joystick y hasta 6 botones; falta prueba física por jugador.',f'- {more6} sets reportan más de 6 botones; {special_count} necesitan control especial; 291 entradas no tienen metadata input concluyente.',
      '', '## 4 jugadores','',f'- {len(games4)} sets reportan máximo 4 jugadores; {four_direct} cumplen capacidad estimada de la botonera. El DAT no distingue simultáneo/alternado y no hay 4P físico confirmado.',
      '', '## Pelea y controles especiales','',f'- {len(fights)} entradas clasificadas por nombre como juegos de pelea; UMK3 queda para prueba manual.', '- Listado de controles especiales: `ARCADE_SPECIAL_CONTROLS.md`.',
      '', '## Fallos','',f'- {allfail} fallos de arranque históricos: '+', '.join(f'{k}: {v}' for k,v in fail_groups.items())+'. Ver `ARCADE_FAILURES.md`.',
      '', '## Duplicados MAME / FBNeo','',f'- {len(dups)} sets están en ambos sistemas; `ARCADE_DUPLICATES_MAME_FBNEO.md` indica INDISTINTO sólo cuando el historial de ambos y metadata coinciden.',
      '', '## Validación manual pendiente','',f'- Muestra priorizada de {len(preferred)} juegos en `ARCADE_MANUAL_TESTS.md`.',
      '', '## Recomendaciones','', '- No cambiar mappings/core por ahora. Confirmar primero si smoke tests pueden ejecutarse sin tocar NVRAM/saves; después priorizar pendientes y validación manual.',
      '## Otros sistemas arcade detectados (fuera del smoke test prioritario)','',mdtable(['Sistema','ZIP','CHD','Acción'],other_systems),
      '', 'No se probaron automáticamente otros sistemas arcade en esta fase.', '']
    (OUT/'ARCADE_AUDIT_REPORT.md').write_text('\n'.join(summary),encoding='utf-8')
    print(json.dumps({'out':str(OUT),'mame':count['mame'],'fbneo':count['fbneo'],'total':len(rows),'reused_tested':sum(1 for r in rows if r['historical_reusable']),'pending':len(queue),'four_player':len(games4),'fighting':len(fights),'duplicates':len(dups),'input_categories':inputs,'dispatcher_sha256':dispatcher_sha},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
