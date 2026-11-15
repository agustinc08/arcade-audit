#!/usr/bin/env python3
"""Read-only discovery and preflight helpers for the Batocera certifier."""
import csv, hashlib, json, os, re, subprocess, tempfile, urllib.request, xml.etree.ElementTree as ET, zipfile
from pathlib import Path

AUDIT=Path('/userdata/system/state/arcade_audit')
ESCFG=Path('/userdata/system/configs/emulationstation/es_systems_el_gordo.cfg')
DEFAULTS=Path('/usr/share/batocera/configgen/configgen-defaults.yml')
CONF=Path('/userdata/system/batocera.conf')
API='http://127.0.0.1:1234'
LIB='/usr/lib/libretro'
MAME='/usr/bin/mame/mame'
FBNEO_DAT=Path('/userdata/bios/fbneo/FinalBurn Neo (ClrMame Pro XML, Arcade only).dat')
MAX_ZIP_MEMBERS=20000

def sha_file(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def bounded_content_fingerprint(p):
    """Return a metadata-only fingerprint; never stream ROM payloads during candidate planning."""
    st=p.stat()
    return {'hash_scope':'STAT_ONLY','size':st.st_size,'mtime_ns':st.st_mtime_ns,'inode':st.st_ino}

def parse_defaults():
    out={}; current=None
    if not DEFAULTS.is_file(): return out
    for line in DEFAULTS.read_text(errors='replace').splitlines():
        m=re.match(r'^([A-Za-z0-9_-]+):\s*$',line)
        if m: current=m.group(1);out.setdefault(current,{})
        elif current:
            m=re.match(r'^\s+(emulator|core):\s*([^#\s]+)',line)
            if m:out[current][m.group(1)]=m.group(2)
    return out

def parse_es():
    root=ET.parse(ESCFG).getroot(); out={}
    for node in root.findall('system'):
        name=node.findtext('name')
        if not name:continue
        emulators={}
        ebox=node.find('emulators')
        if ebox is not None:
            for em in ebox.findall('emulator'):
                en=em.get('name'); cores=[]
                cbox=em.find('cores')
                if cbox is not None:
                    for c in cbox.findall('core'):
                        if c.text:cores.append({'name':c.text.strip(),'default':c.get('default')=='true'})
                emulators[en]=cores
        out[name]={'command':node.findtext('command') or '', 'emulators':emulators,
                   'extensions':node.findtext('extension') or ''}
    return out

def config_overrides():
    text=CONF.read_text(errors='replace') if CONF.is_file() else ''
    values={}
    for line in text.splitlines():
        m=re.match(r'^([A-Za-z0-9_-]+)\.(emulator|core)=(.*)$',line.strip())
        if m:values.setdefault(m.group(1),{})[m.group(2)]=m.group(3).strip().strip('"')
    per_game={}
    for m in re.finditer(r'^mame\["([^"]+)"\]\.core=(\S+)',text,re.M):per_game[m.group(1)]=m.group(2)
    return values,per_game

def live_systems():
    req=urllib.request.Request(API+'/systems',headers={'Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=8) as r: rows=json.load(r)
    es=parse_es(); defaults=parse_defaults(); overrides,pergame=config_overrides()
    found=[]
    for row in rows:
        name=row.get('name','')
        if not name or row.get('gamesystem')=='false' or row.get('collection')=='true':continue
        info=es.get(name,{})
        configured=defaults.get(name,{})
        emulator=overrides.get(name,{}).get('emulator',configured.get('emulator',''))
        choices=info.get('emulators',{}).get(emulator,[]) if emulator else []
        # Batocera's active system config can intentionally differ from configgen defaults.
        # Use explicit batocera.conf first, then the currently loaded ES system's default core.
        core=overrides.get(name,{}).get('core')
        if not core:core=next((c['name'] for c in choices if c['default']),choices[0]['name'] if choices else configured.get('core',''))
        command=info.get('command','')
        adapter='ADAPTER_NOT_READY'
        status='PENDING'
        if 'controller_dispatcher' not in command:
            why='ES_COMMAND_DOES_NOT_USE_CONTROLLER_DISPATCHER'
        elif name=='mame' and core=='mame':adapter='MAME_CURRENT';status='READY';why='individual/current MAME core'
        elif name=='mame' and core=='mame078plus':adapter='MAME078PLUS';status='READY';why='default MAME 0.78 Plus core'
        elif name=='fbneo' or (name=='neogeo' and core=='fbneo'):
            adapter='FBNEO';status='READY' if Path(LIB+'/fbneo_libretro.so').is_file() and FBNEO_DAT.is_file() else 'PENDING';why='FBNeo libretro with installed DAT' if status=='READY' else 'core or DAT unavailable'
        elif emulator=='libretro':
            adapter='RETROARCH_GENERIC';core_path=Path(LIB+'/'+core+'_libretro.so') if core else None
            status='READY' if core_path and core_path.is_file() else 'PENDING';why='RetroArch content identity + core argv' if status=='READY' else 'configured libretro core missing'
        elif emulator:
            adapter='STANDALONE_GENERIC';status='PENDING';why='standalone identity/restore profile not validated'
        else:why='configured emulator/core unresolved'
        found.append({'system':name,'rom_count':int(row.get('totalGames') or 0),'configured_emulator':emulator,
            'configured_core':core,'launcher_type':'controller_dispatcher+launcher' if 'controller_dispatcher' in command else 'other',
            'adapter':adapter,'adapter_status':status,'reason':why,'visible':row.get('visible')=='true',
            'emulator_override':name in overrides and 'emulator' in overrides[name],
            'core_override':name in overrides and 'core' in overrides[name],
            'active_mame_current_overrides':sorted(k for k,v in pergame.items() if v=='mame') if name=='mame' else []})
    return found

def system_game(system,rom):
    with urllib.request.urlopen(API+f'/systems/{system}/games',timeout=10) as r: entries=json.load(r)
    exact=[x for x in entries if x.get('path')==str(rom)]
    return exact[0] if len(exact)==1 else None

def parse_cue(path):
    missing=[]
    for line in path.read_text(errors='replace').splitlines():
        m=re.match(r'\s*FILE\s+["\']?([^"\']+)["\']?\s+',line,re.I)
        if m and not (path.parent/m.group(1)).is_file():missing.append(m.group(1))
    return missing

_dat_cache=None
_dat_version=None
def fbneo_dat():
    global _dat_cache,_dat_version
    if _dat_cache is not None:return _dat_cache
    _dat_cache={}
    _dat_version=None
    if not FBNEO_DAT.is_file():return _dat_cache
    root=ET.parse(FBNEO_DAT).getroot()
    _dat_version=root.findtext('./header/version') or ''
    nodes=root.findall('.//game') or root.findall('.//machine')
    for node in nodes:
        name=node.get('name')
        if not name:continue
        _dat_cache[name]={'cloneof':node.get('cloneof'),'romof':node.get('romof'),
          'roms':[{'name':x.get('name'),'crc':(x.get('crc') or '').lower(),'size':int(x.get('size') or 0),'status':x.get('status','good')}
                  for x in node.findall('rom')]}
    return _dat_cache

def preflight(system,rom,adapter,core,rom_entry=None):
    p=Path(rom)
    if not p.is_file() or not os.access(p,os.R_OK):return {'status':'STATIC_FAIL','reason':'ROM_NOT_PRESENT_OR_READABLE'}
    if rom_entry is None:rom_entry=system_game(system,p)
    if rom_entry is None:return {'status':'STATIC_FAIL','reason':'ES_GAME_PATH_NOT_UNIQUE_OR_NOT_LOADED'}
    if p.suffix.lower()=='.cue':
        missing=parse_cue(p)
        if missing:return {'status':'STATIC_FAIL','reason':'MISSING_ROM_MEMBER','missing':missing}
    archive_check='NOT_APPLICABLE'
    try:
        if p.suffix.lower()=='.zip':
            with zipfile.ZipFile(p) as z:
                infos=z.infolist()
                if len(infos)>MAX_ZIP_MEMBERS:
                    return {'status':'ADAPTER_NOT_READY','reason':'ZIP_MEMBER_COUNT_LIMIT','members':len(infos)}
                # CRC scanning decompresses every member and may stream GBs during planning.
                # MAME-current/FBNeo use dedicated metadata verification below; generic systems
                # validate the archive directory and defer payload checks to the real boot.
                archive_check='CENTRAL_DIRECTORY_ONLY'
    except (OSError,zipfile.BadZipFile):return {'status':'STATIC_FAIL','reason':'ROMSET_BAD'}
    fingerprint=bounded_content_fingerprint(p)
    result={'status':'PASS','reason':'content present; exact ES path; central-directory check plus adapter-specific verification',
            'content_fingerprint':fingerprint,'rom_size':p.stat().st_size,'archive_check':archive_check,'es_entry_id':rom_entry.get('id'),
            'es_name':rom_entry.get('name'),'adapter':adapter,'core':core}
    if adapter in ('MAME_CURRENT','MAME078PLUS'):
        core_path=Path(LIB+('/mame_libretro.so' if adapter=='MAME_CURRENT' else '/mame078plus_libretro.so'))
        if not core_path.is_file():return {'status':'ADAPTER_NOT_READY','reason':'MAME_CORE_MISSING'}
        if adapter=='MAME_CURRENT':
            short=p.stem
            if not Path(MAME).is_file():return {'status':'ADAPTER_NOT_READY','reason':'MAME_CURRENT_VERIFY_TOOL_MISSING'}
            with tempfile.TemporaryDirectory(prefix='cert_mame_verify_') as td:
                t=Path(td); dirs=[]
                for d in ('home','ini','cfg','nvram','input','state','snapshot','diff'):
                    q=t/d;q.mkdir();dirs.append(q)
                opts=['-noreadconfig','-rompath','/userdata/roms/mame;/userdata/bios','-homepath',str(dirs[0]),'-inipath',str(dirs[1]),
                      '-cfg_directory',str(dirs[2]),'-nvram_directory',str(dirs[3]),'-input_directory',str(dirs[4]),
                      '-state_directory',str(dirs[5]),'-snapshot_directory',str(dirs[6]),'-diff_directory',str(dirs[7])]
                env={**os.environ,'HOME':str(dirs[0]),'XDG_CONFIG_HOME':str(dirs[0]),'XDG_CACHE_HOME':str(dirs[0])}
                try:q=subprocess.run([MAME,*opts,'-verifyroms',short],cwd=td,env=env,capture_output=True,text=True,timeout=60)
                except subprocess.TimeoutExpired:return {'status':'ADAPTER_NOT_READY','reason':'MAME_VERIFY_TIMEOUT'}
            txt=q.stdout+'\n'+q.stderr
            result['verifyroms_exit']=q.returncode
            if not re.search(r'romset\s+"?'+re.escape(short)+r'"?(?:\s+\[[^\]]+\])?\s+is\s+good',txt,re.I):
                result['status']='STATIC_FAIL';result['reason']='MAME_VERIFYROMS_FAILED';result['verify_output']=txt[-3000:]
        result['core_path']=str(core_path)
    elif adapter=='FBNEO':
        dat=fbneo_dat(); short=p.stem
        if not dat:return {'status':'ADAPTER_NOT_READY','reason':'FBNEO_DAT_UNAVAILABLE'}
        if not Path(LIB+'/fbneo_libretro.so').is_file():return {'status':'ADAPTER_NOT_READY','reason':'FBNEO_CORE_MISSING'}
        if short not in dat:return {'status':'STATIC_FAIL','reason':'DAT_DRIVER_NOT_FOUND','dat_version':_dat_version}
        checked=[]; missing=[]; bad=[]; chain=[]; cur=short;seen=set()
        while cur and cur in dat and cur not in seen:
            seen.add(cur);chain.append(cur);row=dat[cur]
            zpath=Path('/userdata/roms')/system/(cur+'.zip')
            if not zpath.is_file():missing.append({'set':cur,'reason':'ZIP_MISSING'})
            else:
                with zipfile.ZipFile(zpath) as z:
                    zm={i.filename:(i.CRC,i.file_size) for i in z.infolist() if not i.is_dir()}
                for member in row['roms']:
                    if member['status']=='nodump':continue
                    val=zm.get(member['name'])
                    if val is None:missing.append({'set':cur,'member':member['name']})
                    elif val[0]!=int(member['crc'],16) or val[1]!=member['size']:
                        bad.append({'set':cur,'member':member['name'],'expected_crc':member['crc'],'actual_crc':f'{val[0]:08x}',
                                    'expected_size':member['size'],'actual_size':val[1]})
                checked.append(cur)
            cur=row.get('cloneof') or row.get('romof')
        result.update({'dat_version':_dat_version,'dat_sha256':sha_file(FBNEO_DAT),'dat_sets_checked':checked,'dependency_chain':chain})
        if missing or bad:
            result.update(status='STATIC_FAIL',reason='FBNEO_DAT_CONTENT_MISMATCH',missing_members=missing,bad_members=bad)
    else:
        lib=Path(LIB+'/'+core+'_libretro.so')
        if not lib.is_file():return {'status':'ADAPTER_NOT_READY','reason':'CONFIGURED_CORE_MISSING','core_path':str(lib)}
        result['core_path']=str(lib)
    return result

def game_adapter(system,rom,systems):
    base=next((x for x in systems if x['system']==system),None)
    if not base:return None
    info=dict(base)
    if system=='mame' and Path(rom).name in base.get('active_mame_current_overrides',[]):
        info['adapter']='MAME_CURRENT';info['configured_core']='mame';info['adapter_status']='READY';info['reason']='active per-game MAME-current override'
    info['core']=info.get('configured_core','')
    return info

def restore_scope(system,adapter,rom):
    paths=[Path('/userdata/system/batocera.conf'),Path('/userdata/system/state/boot_audit_once.json'),
           Path('/userdata/system/configs/retroarch'),Path('/userdata/system/configs/el_gordo_controller_profiles/controller_technical.json'),
           Path('/userdata/system/configs/el_gordo_controller_profiles/multiplayer.json'),
           Path('/userdata/roms')/system/'gamelist.xml',Path('/userdata/saves')/system]
    if adapter in ('MAME_CURRENT','MAME078PLUS','FBNEO'):
        paths.append(Path('/userdata/system/configs/mame'))
    cfg=Path('/userdata/system/configs')/system
    if cfg.exists():paths.append(cfg)
    if system=='mame':paths += [Path('/userdata/saves/mame/mame'),Path('/userdata/saves/mame/plugins')]
    paths=list(dict.fromkeys(paths)); checked=[]
    try:
        from certification_transaction import state, is_allowed
        for p in paths:
            if not is_allowed(p):return {'status':'ADAPTER_NOT_READY','reason':'RESTORE_PATH_NOT_ALLOWLISTED','path':str(p)}
            s=state(p)
            if s.get('size',0)>50*1024*1024:return {'status':'ADAPTER_NOT_READY','reason':'RESTORE_SCOPE_OVER_50_MIB','path':str(p),'size':s.get('size')}
            checked.append(str(p))
    except Exception as e:return {'status':'ADAPTER_NOT_READY','reason':'RESTORE_SCOPE_UNSAFE','detail':type(e).__name__+': '+str(e)}
    return {'status':'READY','paths':checked}

if __name__=='__main__':
    systems=live_systems()
    for x in systems:print(json.dumps(x,ensure_ascii=False))
