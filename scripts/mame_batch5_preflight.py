#!/usr/bin/env python3
"""Read-only MAME 0.285 preflight for normal, previously untested MAME games."""
import csv
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

OUT = Path('/userdata/system/state/arcade_audit')
CSV = OUT / 'arcade_core_compatibility.csv'
GAMES = Path('/userdata/roms/mame')
MAME = Path('/usr/bin/mame/mame')
ROMPATH = '/userdata/roms/mame;/userdata/bios'
RESERVED_FBNEO = {'gprider', 'sfiii2n', 'sfiii3n', 'sfiiin', 'neotris'}
EXCLUDED_KINSTB = {'kinstb'}
INTERESTING = {'mk4','kov2','kov2p','martmast','dynwar','ddux','gradius4','jockeygp',
               'misncrft','dacholer','gekisou','freezeat'}

def run(args, cwd, env):
    try:
        p = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True,
                           errors='replace', timeout=60)
        return {'rc': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr, 'timeout': False}
    except subprocess.TimeoutExpired as e:
        return {'rc': None, 'stdout': (e.stdout or '').decode(errors='replace') if isinstance(e.stdout, bytes) else (e.stdout or ''),
                'stderr': (e.stderr or '').decode(errors='replace') if isinstance(e.stderr, bytes) else (e.stderr or ''),
                'timeout': True}

def parse_machine(xml_text):
    at = xml_text.find('<?xml')
    if at < 0: return None, 'XML_DECLARATION_MISSING'
    try:
        root = ET.fromstring(xml_text[at:])
        machine = root.find('machine')
        if machine is None: return None, 'MACHINE_NODE_MISSING'
        driver = machine.find('driver')
        inputs = machine.find('input')
        return {
            'shortname': machine.get('name'), 'description': (machine.findtext('description') or '').strip(),
            'runnable': machine.get('runnable', 'yes'), 'cloneof': machine.get('cloneof'),
            'romof': machine.get('romof'), 'isbios': machine.get('isbios', 'no'),
            'driver_status': driver.get('status') if driver is not None else None,
            'driver_emulation': driver.get('emulation') if driver is not None else None,
            'players': inputs.get('players') if inputs is not None else None,
            'buttons': inputs.get('buttons') if inputs is not None else None,
            'control_type': inputs.get('control') if inputs is not None else None,
            'roms': [{'name': x.get('name'), 'size': x.get('size'), 'crc': x.get('crc'),
                      'sha1': x.get('sha1'), 'status': x.get('status'), 'optional': x.get('optional'),
                      'bios': x.get('bios'), 'merge': x.get('merge')} for x in machine.findall('rom')],
            'bios_sets': [{'name': x.get('name'), 'description': x.get('description'), 'default': x.get('default')}
                          for x in machine.findall('biosset')],
            'disks': [{'name': x.get('name'), 'sha1': x.get('sha1'), 'status': x.get('status'),
                       'optional': x.get('optional'), 'merge': x.get('merge')} for x in machine.findall('disk')],
        }, None
    except Exception as e:
        return None, 'XML_PARSE_ERROR:' + repr(e)

def main():
    if not MAME.is_file(): raise SystemExit('MAME_BINARY_MISSING')
    version = subprocess.run([str(MAME), '-version'], capture_output=True, text=True, timeout=15).stdout.strip()
    if not version.startswith('0.285'): raise SystemExit('MAME_VERSION_NOT_0.285:' + version)
    with CSV.open(encoding='utf-8-sig', newline='') as f: rows = list(csv.DictReader(f))
    tested = {'ffight2b','altair','apache3','blazlaz','cubeqst','mvp','sia2650','redearth','jojo',
              'jojoba','evosocc','hoops95','nbapbp','funcube4','hyperath','lbgrande','sws98',
              'tenkomor','multigam','multigm3','nratechu','ertictac'}
    all_unprobed = [r for r in rows if r.get('system') == 'mame' and r.get('tested_mame_current') != 'YES']
    target_pool = [r for r in all_unprobed if r.get('current_result') == 'GAME_DRIVER_NOT_FOUND'
                   and r.get('mame_standalone_support') == 'SUPPORTED' and r.get('entry_kind') == 'GAME']
    normal = []
    excluded = []
    for r in target_pool:
        n = r.get('shortname', '')
        name = r.get('name', '')
        control = (r.get('control_type') or '').lower()
        players = int(r['players']) if (r.get('players') or '').isdigit() else None
        buttons = int(r['buttons']) if (r.get('buttons') or '').isdigit() else None
        why = None
        if n in tested or r.get('tested_mame_current') == 'YES': why = 'ALREADY_TESTED_MAME_CURRENT_RUNTIME_EVIDENCE'
        elif n in RESERVED_FBNEO: why = 'RESERVED_FOR_FBNEO'
        elif n in EXCLUDED_KINSTB: why = 'EXCLUDE_ARCADE_PRIORITY_SNES_BOOTLEG'
        elif name.startswith('ZZZ(notgame)'): why = 'ZZZ_NOTGAME'
        elif r.get('input_compatibility') != 'DIRECT_COMPATIBLE': why = 'NOT_DIRECT_COMPATIBLE_METADATA'
        elif control != 'joy': why = 'SPECIAL_OR_NON_DIGITAL_CONTROL:' + control
        elif buttons is None or buttons > 6: why = 'MORE_THAN_6_OR_UNKNOWN_BUTTONS'
        elif players is None or players < 1 or players > 4: why = 'PLAYER_COUNT_UNKNOWN_OR_OUT_OF_RANGE'
        elif not (GAMES / (n + '.zip')).is_file(): why = 'ROM_ZIP_NOT_PRESENT'
        if why:
            excluded.append({'shortname': n, 'name': name, 'reason': why})
        else:
            normal.append(r)
    # Stable ordering: likely full CRC sets first; then 4P/3P, fighters/beat'em ups,
    # popular titles, followed by the remaining direct digital candidates.
    genre_words = ('fighter','fighting','mortal kombat','knights of valour','martial masters',
                   'dynasty wars','dynamite dux','gladiator','road of the sword','street fighter')
    def priority(r):
        n, name = r['shortname'], r.get('name','')
        try: p = int(r.get('players') or 0)
        except ValueError: p = 0
        full = r.get('romset_status') == 'FULL_CRC_MATCH_MAME_CURRENT'
        fight = any(x in name.lower() for x in genre_words) or n in {'mk4','kov2','kov2p','martmast','sfzch','svg'}
        beat = any(x in name.lower() for x in ('dynasty wars','dynamite dux','gladiator'))
        popularity = n in {'mk4','kov2','kov2p','martmast','gradius4','dynwar','ddux','sfzch','svg'}
        # Candidate order preserves practical choices; this is preflight ordering only.
        return (0 if full else 1, 0 if p >= 3 else 1, 0 if fight else 1,
                0 if beat else 1, 0 if popularity else 1, n)
    normal.sort(key=priority)

    root = Path(tempfile.mkdtemp(prefix='arcade_mame_batch5_preflight_'))
    writes = {k: str(root / k) for k in ('home','ini','cfg','nvram','input','state','snapshot','diff')}
    for p in writes.values(): Path(p).mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'HOME': writes['home'], 'XDG_CONFIG_HOME': writes['home'], 'XDG_CACHE_HOME': writes['home']}
    opts = ['-noreadconfig','-rompath',ROMPATH,'-homepath',writes['home'],'-inipath',writes['ini'],
            '-cfg_directory',writes['cfg'],'-nvram_directory',writes['nvram'],'-input_directory',writes['input'],
            '-state_directory',writes['state'],'-snapshot_directory',writes['snapshot'],'-diff_directory',writes['diff']]
    out = {'created_at': datetime.now().astimezone().isoformat(timespec='seconds'), 'mame_version': version,
           'mame_binary': str(MAME), 'rompath': ROMPATH, 'isolated_write_directories': writes,
           'preflight_is_read_only': True, 'summary': {'unprobed_matrix_rows': len(all_unprobed),
           'mame_current_supported_driver_target_pool': len(target_pool), 'normal_metadata_pool': len(normal),
           'excluded_before_runtime_preflight': len(excluded), 'verify_pass': 0, 'verify_fail': 0},
           'excluded': excluded, 'candidates': []}
    dest = OUT / 'mame_batch5_preflight.json'
    for i, r in enumerate(normal, 1):
        n = r['shortname']; rom = GAMES / (n + '.zip')
        size = rom.stat().st_size; mtime = rom.stat().st_mtime_ns
        listfull = run([str(MAME), *opts, '-listfull', n], root, env)
        listxml = run([str(MAME), *opts, '-listxml', n], root, env)
        machine, xml_error = parse_machine(listxml['stdout'])
        verify = run([str(MAME), *opts, '-verifyroms', n], root, env)
        verify_text = (verify['stdout'] + '\n' + verify['stderr']).strip()
        if verify['timeout']: verify_status = 'TIMEOUT'
        elif re.search(r'romset\s+"?' + re.escape(n) + r'"?(?:\s+\[[^\]]+\])?\s+is\s+good', verify_text, re.I): verify_status = 'PASS'
        elif re.search(r'romset\s+"?' + re.escape(n) + r'"?(?:\s+\[[^\]]+\])?\s+is\s+best available', verify_text, re.I): verify_status = 'NO_GOOD_DUMP_REQUIRED'
        elif re.search(r'not found|NOT FOUND|INCORRECT LENGTH|WRONG CHECKSUM|is bad|Required files are missing|Fatal error', verify_text, re.I): verify_status = 'FAIL'
        else: verify_status = 'UNKNOWN'
        desc = None
        for line in listfull['stdout'].splitlines():
            if line.strip().startswith(n): desc = line.strip()[len(n):].strip(' "'); break
        missing = sorted(set(re.findall(r'([^\s:]+(?:\.chd|\.bin|\.rom|\.u[0-9a-z]+|\.ic[0-9]+|\.key))\s*\([^\n]*?\)\s*-\s*(?:NOT FOUND|INCORRECT LENGTH|WRONG CHECKSUM)', verify_text, re.I)))
        if not missing:
            missing = sorted(set(re.findall(r'([A-Za-z0-9_.+-]+\.(?:chd|bin|rom|key))\s*:\s*(?:NOT FOUND|INCORRECT LENGTH|WRONG CHECKSUM)', verify_text, re.I)))
        drivers = (machine or {}).get('driver_status')
        runnable = (machine or {}).get('runnable')
        if verify_status == 'PASS' and listfull['rc'] == 0 and listxml['rc'] == 0 and machine and runnable == 'yes':
            final = 'PREFLIGHT_PASS'
            failure_categories = []
        else:
            # A failed read-only check always means SKIP_PREFLIGHT. Keep the
            # reason as a separate, possibly overlapping list of exact causes.
            final = 'SKIP_PREFLIGHT'
            failure_categories = []
            low_verify = verify_text.lower()
            if not machine or runnable != 'yes' or 'romset "' + n.lower() + '" not found' in low_verify:
                failure_categories.append('DRIVER_NOT_RUNNABLE')
            if verify_status == 'TIMEOUT' or verify_status == 'UNKNOWN':
                failure_categories.append('UNKNOWN_DEPENDENCY')
            if verify_status == 'NO_GOOD_DUMP_REQUIRED':
                failure_categories.append('NO_GOOD_DUMP_REQUIRED')
            if re.search(r'\bis bad\b|wrong checksum|incorrect length|needs redump', low_verify):
                failure_categories.append('ROMSET_BAD')
            if missing or re.search(r'not found|not found - no good dump known', low_verify):
                failure_categories.append('MISSING_ROM_MEMBER')
            if r.get('romof') and r.get('romof_archive_status') in ('NOT_FOUND', 'MISSING', 'NO'):
                failure_categories.append('MISSING_PARENT')
            if r.get('bios_required') not in ('NO', 'NOT_REQUIRED', None) and r.get('bios_ok') in ('NO', 'NOT_FOUND', 'MISSING'):
                failure_categories.append('MISSING_BIOS')
            if machine and any(z.get('name', '').lower().endswith('.chd') for z in machine.get('roms', [])):
                failure_categories.append('MISSING_CHD')
            if not failure_categories:
                failure_categories.append('UNKNOWN_DEPENDENCY')
        row = {
            'shortname': n, 'name': desc or r.get('name'), 'mame_name': (machine or {}).get('description'),
            'source': 'arcade_core_compatibility.csv + MAME 0.285 current read-only output',
            'core_default': 'mame078plus','tested_mame_current_before': r.get('tested_mame_current'),
            'static_recommended_action': r.get('recommended_action'), 'static_romset_status': r.get('romset_status'),
            'static_players': r.get('players'), 'static_buttons': r.get('buttons'), 'static_control_type': r.get('control_type'),
            'input_classification': r.get('input_compatibility'), 'cloneof': (machine or {}).get('cloneof'),
            'romof': (machine or {}).get('romof'), 'rom_zip': str(rom), 'rom_zip_present': rom.is_file(),
            'rom_zip_size': size, 'rom_zip_mtime_ns': mtime, 'listfull_rc': listfull['rc'],
            'listfull_output': listfull['stdout'].strip(), 'listxml_rc': listxml['rc'],
            'listxml_error': xml_error, 'mame_machine': machine, 'runnable': runnable == 'yes' if machine else False,
            'driver_status': drivers, 'verifyroms_status': verify_status, 'verifyroms_rc': verify['rc'],
            'verifyroms_output': verify_text, 'missing_files': missing, 'final_preflight': final,
            'preflight_failure_categories': failure_categories}
        out['candidates'].append(row)
        if final == 'PREFLIGHT_PASS': out['summary']['verify_pass'] += 1
        else: out['summary']['verify_fail'] += 1
        tmp = dest.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        os.replace(tmp, dest)
        print(f'PREFLIGHT {i}/{len(normal)} {n}: {final} ({verify_status})', flush=True)
    out['selection_order'] = [x['shortname'] for x in sorted(out['candidates'], key=lambda x: priority(next(r for r in normal if r['shortname']==x['shortname']))) if x['final_preflight']=='PREFLIGHT_PASS']
    tmp = dest.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, dest)
    print('PREFLIGHT_DONE', json.dumps(out['summary'], ensure_ascii=False), 'output', dest, flush=True)

if __name__ == '__main__': main()
