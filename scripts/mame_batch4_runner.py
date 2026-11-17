#!/usr/bin/env python3
"""Guarded MAME BATCH 4 runner: ES restart already done; altair gates all games."""
import csv
import hashlib
import json
import os
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

OUT = Path('/userdata/system/state/arcade_audit')
sys.path.insert(0, str(OUT))
import smoke_runner as sr
import smoke_pilot_batch2 as pilot
import smoke_pilot_batch3 as batch3
sys.path.insert(0, '/userdata/system/el_gordo_tools')
from marker_ownership import create_exclusive as create_owned_marker, remove_if_owned as remove_owned_marker

CPFILE = OUT / 'mame_batch4_checkpoint.json'
REPORT = OUT / 'ARCADE_MAME_BATCH4_RESULTS.md'
CONF = Path('/userdata/system/batocera.conf')
CORE = Path('/usr/lib/libretro/mame_libretro.so')
MAME = Path('/usr/bin/mame/mame')
DISPATCHER = Path('/userdata/system/el_gordo_tools/controller_dispatcher')
PROFILE = Path('/userdata/system/configs/el_gordo_controller_profiles/controller_technical.json')
ESCFG = Path('/userdata/system/configs/emulationstation/es_systems_el_gordo.cfg')
API = 'http://127.0.0.1:1234'
LOG_PATHS = [Path('/userdata/system/logs/controller_selector.log'),
             Path('/userdata/system/logs/es_launch_stdout.log'),
             Path('/userdata/system/logs/es_launch_stderr.log'),
             Path('/userdata/system/logs/emulog.txt')]
GAMES = ['lbgrande', 'sws98', 'tenkomor', 'multigam', 'multigm3', 'nratechu', 'ertictac']
CORE_EXPECTED = 'mame078plus'
EXPECTED_OVERRIDES = ['altair.zip', 'apache3.zip', 'blazlaz.zip', 'cubeqst.zip', 'evosocc.zip',
                      'ffight2b.zip', 'funcube4.zip', 'hoops95.zip', 'sia2650.zip']

def stamp():
    return datetime.now().astimezone().isoformat(timespec='milliseconds')

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def save(cp):
    tmp = CPFILE.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(cp, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, CPFILE)

def active_overrides():
    return sorted(x.decode() for x in set(re.findall(rb'^mame\["([^\"]+)"\]\.core=mame\s*$', CONF.read_bytes(), re.M)))

def raw_get(path, timeout=2):
    with urllib.request.urlopen(API + path, timeout=timeout) as r:
        return {'status': r.status, 'body': r.read().decode('utf-8', 'replace')}

def api_state():
    idle = raw_get('/isIdle')
    game = raw_get('/runningGame')
    try: idle_value = json.loads(idle['body'])[0]
    except Exception: idle_value = None
    try:
        data = json.loads(game['body'])
        if isinstance(data, dict) and data.get('msg') == 'NO GAME RUNNING': data = None
    except Exception: data = {'unparsed': game['body']}
    return {'idle_raw': idle, 'idle': idle_value, 'game_raw': game, 'game': data}

def process_records():
    out = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit(): continue
        try:
            pid = int(p.name)
            cmd = (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode('utf-8', 'replace').strip()
            exe = os.readlink(p / 'exe')
            comm = (p / 'comm').read_text(errors='replace').strip()
            fields = (p / 'stat').read_text().rsplit(')', 1)[1].split()
            if not cmd: cmd = comm
            out.append({'pid': pid, 'ppid': int(fields[1]), 'exe': exe, 'comm': comm, 'cmd': cmd})
        except (OSError, ValueError, IndexError): pass
    return out

def chain_processes(records=None):
    records = records if records is not None else process_records()
    tokens = ('retroarch', 'controller_dispatcher', 'selector_controles', 'emulatorlauncher', '/usr/bin/mame/mame')
    return [p for p in records if any(t in (p['exe'] + ' ' + p['cmd']).lower() for t in tokens)]

def flag_value(argv_text, flag):
    parts = argv_text.split()
    try: return parts[parts.index(flag) + 1]
    except (ValueError, IndexError): return None

def new_dispatchers(before_pids, records=None):
    records = records if records is not None else process_records()
    return [p for p in records if p['pid'] not in before_pids and 'controller_dispatcher' in p['cmd']
            and '-system' in p['cmd'] and '-rom' in p['cmd']]

def target_retroarch(n, records=None):
    records = records if records is not None else process_records()
    cmdfile = f'/var/run/cmdfiles/{n}.cmd'
    return [p for p in records if p['exe'].endswith('/retroarch') and cmdfile in p['cmd']]

def db_max_id():
    with sqlite3.connect('file:/userdata/system/state/game_health.sqlite?mode=ro', uri=True, timeout=3) as c:
        return c.execute('SELECT COALESCE(MAX(id),0) FROM launch_events').fetchone()[0]

def health_after(system, rom, after_id):
    with sqlite3.connect('file:/userdata/system/state/game_health.sqlite?mode=ro', uri=True, timeout=3) as c:
        c.row_factory = sqlite3.Row
        row = c.execute('SELECT * FROM launch_events WHERE system=? AND rom=? AND id>? ORDER BY id DESC LIMIT 1',
                        (system, str(rom), after_id)).fetchone()
        return dict(row) if row else None

def copy_logs(game, phase):
    dest = OUT / 'mame_batch4_runtime' / game / ('logs_' + phase)
    dest.mkdir(parents=True, exist_ok=True)
    result = {}
    for p in LOG_PATHS:
        if p.is_file():
            q = dest / p.name
            shutil.copy2(p, q)
            result[str(p)] = {'copy': str(q), 'size': p.stat().st_size, 'sha256': sha(q)}
        else: result[str(p)] = {'exists': False}
    return result

def marker_for(rom):
    return create_owned_marker('mame', str(rom), 'mame_batch4_runner',
                               f'mame-batch4:{os.getpid()}:{time.time_ns()}', path=sr.MARKER)

def fresh_preflight(n):
    rom = Path('/userdata/roms/mame') / (n + '.zip')
    if not rom.is_file() or not os.access(rom, os.R_OK): return {'status': 'SKIP_PREFLIGHT', 'reason': 'ROM_NOT_PRESENT_OR_READABLE'}
    if not MAME.is_file() or not CORE.is_file(): return {'status': 'SKIP_PREFLIGHT', 'reason': 'MAME_CURRENT_BINARY_OR_CORE_MISSING'}
    ok, reason = batch3.mame_preflight(n)
    if not ok: return {'status': 'SKIP_PREFLIGHT', 'reason': reason}
    p = OUT / 'mame_batch3_preflight.json'
    prior = json.loads(p.read_text(encoding='utf-8'))['preflight']
    meta = next((r for r in prior if r.get('shortname') == n), None)
    if n == 'altair' and meta is None:
        return {'status': 'PASS', 'reason': 'fresh MAME listxml/verifyroms PASS; historical positive control is intentionally outside candidate preflight table',
                'fresh_verifyroms': 'PASS', 'fresh_listxml': 'PASS', 'metadata': None,
                'rom_sha256': sha(rom), 'rom_size': rom.stat().st_size, 'historical_positive_control': True}
    if not meta or meta.get('verify') != 'PASS' or meta.get('crc') != 'FULL_CRC_MATCH_MAME_CURRENT':
        return {'status': 'SKIP_PREFLIGHT', 'reason': 'STATIC_PREFLIGHT_OR_FULL_CRC_EVIDENCE_MISSING'}
    return {'status': 'PASS', 'reason': '', 'fresh_verifyroms': 'PASS', 'fresh_listxml': 'PASS',
            'metadata': meta, 'rom_sha256': sha(rom), 'rom_size': rom.stat().st_size}

def profile_check():
    q = subprocess.run([str(DISPATCHER), '--diagnose'], capture_output=True, text=True, timeout=20)
    if q.returncode: raise RuntimeError('P1_P4_DIAGNOSE_FAILED:' + q.stderr[-300:])
    prof = json.loads(q.stdout).get('profiles', {}).get('arcade', {})
    actual = {x['arcade_player']: (x.get('usb_port'), x.get('path')) for x in prof.get('players', [])}
    expected = {'P1': ('5', '/dev/input/event17'), 'P2': ('6', '/dev/input/event18'),
                'P3': ('8', '/dev/input/event20'), 'P4': ('7', '/dev/input/event19')}
    s = subprocess.run(['sdl2-jstest', '--list'], capture_output=True, text=True, timeout=20)
    paths = re.findall(r"Joystick Path:\s+'([^']+)'", s.stdout)
    if prof.get('duplicates') or actual != expected or s.returncode or paths != [
            '/dev/input/event17', '/dev/input/event18', '/dev/input/event19', '/dev/input/event20']:
        raise RuntimeError('P1_P4_MAPPING_REGRESSION:' + repr({'players': actual, 'paths': paths}))
    return {'players': actual, 'sdl_paths': paths, 'duplicates': False}

def restore_mismatch_launch(game, before_pids):
    records = process_records()
    # Stop only processes created by this request, after validating their target identity.
    ras = [p for p in records if p['pid'] not in before_pids and p['exe'].endswith('/retroarch')]
    for p in ras:
        try: os.kill(p['pid'], signal.SIGTERM)
        except ProcessLookupError: pass
    # Cancel the selector first; it is the only potentially blocking child before launcher.
    selectors = [p for p in records if p['pid'] not in before_pids and 'selector_controles' in p['cmd']]
    for p in selectors:
        try: os.kill(p['pid'], signal.SIGTERM)
        except ProcessLookupError: pass
    time.sleep(0.3)
    records = process_records()
    for p in new_dispatchers(before_pids, records):
        got = flag_value(p['cmd'], '-rom')
        if got and got != str(Path('/userdata/roms/mame') / (game + '.zip')):
            try: os.kill(p['pid'], signal.SIGTERM)
            except ProcessLookupError: pass

def marker_consumption_log_match(game, logs_pre, logs_post):
    path = '/userdata/system/logs/controller_selector.log'
    pre = logs_pre.get(path, {})
    post = logs_post.get(path, {})
    copied = post.get('copy')
    if not copied or not Path(copied).is_file(): return False
    try:
        lines = Path(copied).read_text(errors='replace').splitlines()
        offset = pre.get('size', 0)
        full = Path(copied).read_text(errors='replace')
        # The copied post log contains the full append-only log; byte offset indexes its pretest tail.
        tail = full.encode('utf-8', 'replace')[offset:].decode('utf-8', 'replace').splitlines()
        for line in tail:
            try: row = json.loads(line)
            except Exception: continue
            if (row.get('event') == 'boot_audit_auto_choice' and row.get('one_shot_consumed') is True
                    and row.get('system') == 'mame' and row.get('rom') == '/userdata/roms/mame/' + game + '.zip'):
                return True
    except Exception: pass
    return False

def emulatorlauncher_log_match(game, copied_logs):
    rom = '/userdata/roms/mame/' + game + '.zip'
    for source, meta in copied_logs.items():
        copied = meta.get('copy') if isinstance(meta, dict) else None
        if not copied or not Path(copied).is_file(): continue
        try:
            lines = Path(copied).read_text(errors='replace').splitlines()
        except OSError: continue
        if any('emulatorlauncher.py' in line and ('start_rom' in line or 'runCommand' in line)
               for line in lines) and any(rom in line for line in lines):
            return {'source': source, 'copy': copied, 'game_path_present': True,
                    'emulatorlauncher_trace_present': True}
    return None

def classify_mame_failure(h, duration, proc_seen):
    text = ''
    if h:
        text = ((h.get('relevant_error') or '') + ' ' + (h.get('missing_file') or '') + ' ' + (h.get('status') or '')).lower()
    if 'chd' in text: return 'MISSING_CHD'
    if 'bios' in text or 'key' in text and ('missing' in text or 'not found' in text): return 'MISSING_BIOS'
    if 'parent' in text and ('missing' in text or 'not found' in text): return 'MISSING_PARENT'
    if any(x in text for x in ('missing', 'not found', 'no such file', 'required rom', 'rom missing')): return 'MISSING_ROM_MEMBER'
    if h and h.get('signal') == 11: return 'SIGSEGV'
    if h and h.get('exit_code') not in (None, 0) and duration < 3: return 'IMMEDIATE_EXIT'
    if h and any(x in text for x in ('fatal', 'failed to load', 'game driver not found')): return 'MAME_FATAL'
    if not proc_seen: return 'LAUNCH_CHAIN_FAILURE'
    return 'UNKNOWN'

def update_matrix(game, status, tested_at):
    path = OUT / 'arcade_core_compatibility.csv'
    backup_dir = OUT / 'mame_batch4_backups'; backup_dir.mkdir(exist_ok=True)
    backup = backup_dir / 'arcade_core_compatibility.csv.pre_batch4'
    if not backup.exists(): shutil.copy2(path, backup)
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f); fields = reader.fieldnames; rows = list(reader)
    target = next((r for r in rows if r.get('system') == 'mame' and r.get('rom') == game + '.zip'), None)
    if not target: raise RuntimeError('MATRIX_ROW_MISSING:' + game)
    target['tested_mame_current'] = 'YES'
    target['not_tested_target_core'] = 'NO'
    target['mame_current_result'] = status
    target['mame_current_tested_at'] = tested_at
    target['mame_current_restore'] = 'VERIFIED'
    tmp = path.with_suffix('.csv.batch4.tmp')
    with tmp.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    os.replace(tmp, path)

def gamelist_hashes():
    result = {}
    for p in Path('/userdata/roms').glob('*/gamelist.xml'):
        result[str(p)] = sha(p)
    return result

def check_post_gamelist(before, game, health):
    after = gamelist_hashes(); changed = []
    for p in sorted(set(before) | set(after)):
        if before.get(p) != after.get(p): changed.append(p)
    if not changed: return {'changed_files': [], 'status': 'NONE'}
    expected = str(Path('/userdata/roms/mame/gamelist.xml'))
    if changed != [expected]: return {'changed_files': changed, 'status': 'UNEXPECTED_OTHER_SYSTEM_GAMELIST_CHANGE'}
    # Restrict this session's change to the launched entry's run-history fields.
    return {'changed_files': changed, 'status': 'MAME_GAMELIST_CHANGED_AFTER_LAUNCH',
            'game_health_event_id': (health or {}).get('id'), 'game': game}

def one_game(game, is_control, cp, backup, baseline):
    rom = Path('/userdata/roms/mame') / (game + '.zip')
    if sr.MARKER.exists(): raise RuntimeError('ONE_SHOT_MARKER_EXISTS')
    if sr.api_idle() is not True or sr.api_game() is not None or not sr.es_pids(): raise RuntimeError('ES_NOT_CLEAN_BEFORE:'+game)
    if chain_processes(): raise RuntimeError('LAUNCH_PROCESS_PREEXISTS:'+repr(chain_processes()))
    pf = fresh_preflight(game)
    cp.setdefault('preflights', {})[game] = pf; save(cp)
    if pf.get('status') != 'PASS':
        cp['skips'].append({'shortname': game, 'cause': pf.get('reason', 'PREFLIGHT_FAILED')}); save(cp)
        return {'result': 'SKIP_PREFLIGHT', 'cause': pf.get('reason')}
    rom_sha = sha(rom)
    current = sr.snapshot_all()
    protected = baseline['protected_snapshot']
    if any(current.get(k) != v for k, v in protected.items() if k != str(CONF)) or any(
            protected.get(k) != v for k, v in current.items() if k != str(CONF)):
        raise RuntimeError('PROTECTED_STATE_DRIFT_BEFORE:' + game)
    oldconf = CONF.read_bytes(); oldstat = CONF.stat(); line = b''
    # Resolve the exact ES entry before writing a temporary override. If the API
    # collection is stale or ambiguous, leave the active configuration untouched.
    with urllib.request.urlopen(API + '/systems/mame/games', timeout=10) as r:
        entries = json.loads(r.read())
    matches = [x for x in entries if x.get('path') == str(rom)]
    if len(matches) != 1:
        raise RuntimeError('ES_COLLECTION_PATH_NOT_UNIQUE:' + game)
    game_entry = matches[0]
    state_dir = OUT / 'mame_batch4_runtime' / game; state_dir.mkdir(parents=True, exist_ok=True)
    global_conf_copy = state_dir / 'batocera.conf.global_before'
    shutil.copy2(CONF, global_conf_copy)
    if not is_control:
        key = f'mame["{game}.zip"].core'
        if f'{game}.zip' in active_overrides() or key.encode() in oldconf: raise RuntimeError('OVERRIDE_ALREADY_ACTIVE:' + game)
        line = f'{key}=mame\n'.encode('ascii')
        with CONF.open('ab') as f:
            if oldconf and not oldconf.endswith(b'\n'): f.write(b'\n')
            f.write(line); f.flush(); os.fsync(f.fileno())
        if f'{game}.zip' not in active_overrides(): raise RuntimeError('OVERRIDE_NOT_ACTIVE_AFTER_WRITE:' + game)
    confcopy = state_dir / 'batocera.conf.pretest'; shutil.copy2(CONF, confcopy)
    pre = sr.snapshot_all()
    pre_snapshot_file = state_dir / 'snapshot.pretest.json'
    pre_snapshot_file.write_text(json.dumps(pre, sort_keys=True, ensure_ascii=False, indent=2) + '\n')
    log_backup = copy_logs(game, 'pre')
    temp_xml = Path('/tmp/game.xml')
    temp_before = {'exists': temp_xml.exists(), 'sha256': sha(temp_xml) if temp_xml.is_file() else None,
                   'mtime_ns': temp_xml.stat().st_mtime_ns if temp_xml.exists() else None}
    if temp_xml.is_file(): shutil.copy2(temp_xml, state_dir / 'game.xml.pretest')
    before_id = db_max_id(); before_pids = {p['pid'] for p in process_records()}
    cmdfile = Path('/var/run/cmdfiles') / f'{game}.cmd'
    cmd_before = {'exists': cmdfile.exists(), 'mtime_ns': cmdfile.stat().st_mtime_ns if cmdfile.exists() else None,
                  'size': cmdfile.stat().st_size if cmdfile.exists() else None}
    marker = marker_for(rom)
    started = time.time()
    result = {'shortname': game, 'name': game_entry.get('name'), 'control': is_control,
              'requested_rom': str(rom), 'core_default': CORE_EXPECTED, 'core_test': 'mame current',
              'preflight': pf, 'started_at': stamp(), 'start_epoch': started, 'marker': marker,
              'logs_pre': log_backup, 'game_xml_pre': temp_before, 'cmdfile_pre': cmd_before,
              'game_health_max_id_before': before_id, 'config_copy': str(confcopy),
              'pre_snapshot': str(pre_snapshot_file), 'rom_sha256_before': rom_sha,
              'retroarch_pid': None, 'dispatcher': [], 'events': [], 'post_response': None,
              'classification': None, 'restore_verified': False}
    cp['current_game'] = result; save(cp)
    def event(name, detail=None):
        if not any(x['event'] == name for x in result['events']):
            result['events'].append({'event': name, 'time': stamp(), 'detail': detail}); cp['current_game'] = result; save(cp)
    event('T0_MARKER_CREATED', {'path': str(sr.MARKER), 'value': marker})
    event('T1_POST_SENT', {'url': API + '/launch', 'body': str(rom), 'content_type': 'application/x-www-form-urlencoded'})
    req = urllib.request.Request(API + '/launch', data=str(rom).encode('utf-8'), method='POST',
                                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            post = {'status': r.status, 'headers': dict(r.headers.items()), 'body': r.read().decode('utf-8', 'replace')}
    except urllib.error.HTTPError as e:
        post = {'status': e.code, 'headers': dict(e.headers.items()) if e.headers else {}, 'body': e.read().decode('utf-8', 'replace')}
    except Exception as e:
        post = {'status': None, 'headers': {}, 'body': '', 'transport_error': repr(e)}
    result['post_response'] = post; save(cp)
    deadline = started + 30; target = None; wrong = None; observed_dispatchers = {}
    last_idle = True; last_game = None; proc_seen = False
    while time.time() < deadline:
        state = api_state(); records = process_records()
        running_game = state['game']
        if last_idle is True and state['idle'] is not True: event('T2_ISIDLE_CHANGED', state['idle_raw'])
        if last_game is None and running_game is not None: event('T3_RUNNINGGAME_CHANGED', running_game)
        if running_game is not None:
            seen_path = running_game.get('path') if isinstance(running_game, dict) else None
            if seen_path != str(rom):
                wrong = {'requested': str(rom), 'es_running_game': seen_path, 'full': running_game}
                result['wrong_game'] = wrong; result['classification'] = 'ES_WRONG_GAME_DISPATCH'; event('STOP_WRONG_RUNNING_GAME', wrong)
                break
        for p in new_dispatchers(before_pids, records):
            got_system = flag_value(p['cmd'], '-system'); got_rom = flag_value(p['cmd'], '-rom')
            observed_dispatchers[p['pid']] = {'pid': p['pid'], 'ppid': p['ppid'], 'argv': p['cmd'], 'system': got_system, 'rom': got_rom}
            if got_rom and got_rom != str(rom):
                wrong = {'requested': str(rom), 'dispatcher_rom': got_rom, 'dispatcher_pid': p['pid'], 'argv': p['cmd']}
                result['wrong_game'] = wrong; result['classification'] = 'ES_WRONG_GAME_DISPATCH'; event('STOP_WRONG_DISPATCHER_ROM', wrong)
                break
            if got_system == 'mame' and got_rom == str(rom) and not proc_seen:
                proc_seen = True; event('T5_CONTROLLER_DISPATCHER_ARGV', observed_dispatchers[p['pid']])
        if wrong: break
        if not sr.MARKER.exists(): event('T4_MARKER_CONSUMED', {'audit_id': marker['audit_id']})
        if any('emulatorlauncher' in p['cmd'].lower() for p in records): event('T6_EMULATORLAUNCHER_SEEN')
        cm = {'exists': cmdfile.exists(), 'mtime_ns': cmdfile.stat().st_mtime_ns if cmdfile.exists() else None,
              'size': cmdfile.stat().st_size if cmdfile.exists() else None}
        if cm['exists'] and (not cmd_before['exists'] or cm != cmd_before): event('T7_CMD_FILE', cm)
        found = target_retroarch(game, records)
        if found:
            if str(rom) not in str((running_game or {}).get('path', '')):
                wrong = {'requested': str(rom), 'es_running_game': (running_game or {}).get('path'), 'retroarch': found[0]}; result['wrong_game'] = wrong
                result['classification'] = 'ES_WRONG_GAME_DISPATCH'; event('STOP_WRONG_RETROARCH_CONTENT', wrong); break
            target = found[0]; result['retroarch_pid'] = target['pid']; result['retroarch_argv'] = target['cmd']
            event('T8_RETROARCH_SEEN', target)
            if str(CORE) not in target['cmd']:
                result['classification'] = 'LAUNCH_CHAIN_FAILURE'; result['core_mismatch'] = target['cmd']
                try: os.kill(target['pid'], signal.SIGTERM)
                except ProcessLookupError: pass
                break
            event('T9_MAME_CURRENT_CORE', str(CORE))
        h = health_after('mame', rom, before_id)
        if h and h.get('id', 0) > before_id: result['game_health_live'] = h; event('T10_GAME_HEALTH', {'id': h.get('id'), 'core': h.get('core'), 'status': h.get('status')})
        last_idle = state['idle']; last_game = running_game
        if target: break
        # A clean idle return after dispatch is recorded for 30s so a short race cannot hide.
        time.sleep(0.05)
    if wrong:
        restore_mismatch_launch(game, before_pids)
    elif target and post.get('status') == 200 and str(CORE) in target['cmd']:
        result['reached_mame_current'] = True
        observed_logs = copy_logs(game, 'observed')
        result['marker_consumed_log_match'] = marker_consumption_log_match(game, log_backup, observed_logs)
        launcher_log = emulatorlauncher_log_match(game, observed_logs)
        result['emulatorlauncher_log_evidence'] = launcher_log
        if launcher_log and not any(x['event'] == 'T6_EMULATORLAUNCHER_SEEN' for x in result['events']):
            event('T6_EMULATORLAUNCHER_SEEN', {'source': 'runtime log evidence', **launcher_log})
        required = {'T4_MARKER_CONSUMED', 'T5_CONTROLLER_DISPATCHER_ARGV', 'T6_EMULATORLAUNCHER_SEEN',
                    'T7_CMD_FILE', 'T8_RETROARCH_SEEN', 'T9_MAME_CURRENT_CORE'}
        observed = {x['event'] for x in result['events']}
        if not required.issubset(observed) or not result['marker_consumed_log_match']:
            # We have the exact process; close only this PID, but never call it a core/ROM failure.
            result['classification'] = 'LAUNCH_CHAIN_FAILURE'
            result['missing_chain_evidence'] = sorted(required - observed)
            result['stable_20s'] = False
            try: os.kill(target['pid'], signal.SIGTERM)
            except ProcessLookupError: pass
        else:
            result['stability_started_at'] = stamp(); end = time.time() + 20; stable = True
            while time.time() < end:
                state = api_state(); current = target_retroarch(game)
                if len(current) != 1 or current[0]['pid'] != target['pid']:
                    stable = False; result['stability_failure'] = 'RETROARCH_EXITED_OR_PID_CHANGED'; break
                if state['idle'] is not False or not isinstance(state['game'], dict) or state['game'].get('path') != str(rom):
                    stable = False; result['stability_failure'] = {'idle': state['idle'], 'game': state['game']}; break
                h = health_after('mame', rom, before_id)
                if h:
                    text = ((h.get('relevant_error') or '') + ' ' + (h.get('missing_file') or '')).lower()
                    if any(w in text for w in ('fatal', 'missing', 'not found', 'failed to load', 'game driver not found')):
                        stable = False; result['stability_failure'] = 'MAME_FATAL:' + (h.get('relevant_error') or h.get('missing_file') or ''); break
                time.sleep(0.25)
            result['stable_20s'] = stable
            if stable:
                current = target_retroarch(game)
                if len(current) != 1 or current[0]['pid'] != target['pid']:
                    stable = False; result['stability_failure'] = 'PID_NOT_UNIQUE_AT_CLOSE'
                else:
                    os.kill(target['pid'], signal.SIGTERM); result['close_method'] = 'SIGTERM_EXACT_RETROARCH_PID'
                    end = time.time() + 20
                    while time.time() < end and any(p['pid'] == target['pid'] for p in process_records()): time.sleep(0.2)
                    if any(p['pid'] == target['pid'] for p in process_records()):
                        stable = False; result['stability_failure'] = 'SIGTERM_TIMEOUT'
            result['stable_20s'] = stable
            if stable: result['classification'] = 'BOOT_PASS'
            else:
                h = health_after('mame', rom, before_id)
                result['classification'] = classify_mame_failure(h, (h or {}).get('duration_seconds') or 0, True)
    elif target and str(CORE) in target['cmd']:
        # Core process exists, but API response was invalid. Close safely and preserve a chain failure.
        result['reached_mame_current'] = True
        result['classification'] = 'LAUNCH_CHAIN_FAILURE'
        try: os.kill(target['pid'], signal.SIGTERM)
        except ProcessLookupError: pass
    elif not result.get('classification'):
        h = health_after('mame', rom, before_id)
        result['game_health_live'] = h
        result['classification'] = 'LAUNCH_CHAIN_FAILURE'
        result['chain_failure'] = 'No RetroArch with requested content/current core appeared within 30 seconds.'
        if h: result['classification'] = classify_mame_failure(h, h.get('duration_seconds') or 0, proc_seen)
    # If a core did start and the process ended before 20s, classify from the game-health event.
    if result['classification'] not in ('BOOT_PASS', 'ES_WRONG_GAME_DISPATCH', 'LAUNCH_CHAIN_FAILURE') and not target:
        result['classification'] = result.get('classification') or 'UNKNOWN'
    # Copy post-launch diagnostics before cleanup can rotate/change them.
    result['logs_post'] = copy_logs(game, 'post')
    result['dispatcher_observed'] = list(observed_dispatchers.values())
    result['cmdfile_post'] = {'exists': cmdfile.exists(), 'mtime_ns': cmdfile.stat().st_mtime_ns if cmdfile.exists() else None,
                              'size': cmdfile.stat().st_size if cmdfile.exists() else None}
    result['game_health_event'] = health_after('mame', rom, before_id)
    if result['game_health_event'] and result['game_health_event'].get('id', 0) > before_id:
        event('T10_GAME_HEALTH', {'id': result['game_health_event'].get('id'), 'core': result['game_health_event'].get('core'),
                                  'exit_code': result['game_health_event'].get('exit_code'), 'status': result['game_health_event'].get('status')})
    if result['classification'] == 'BOOT_PASS':
        h = result['game_health_event']
        if not h:
            result['classification'] = 'UNKNOWN'
            result['pass_rejected_reason'] = 'GAME_HEALTH_EXIT_EVENT_MISSING'
        elif h.get('core') != 'mame' or h.get('exit_code') != 0 or h.get('signal') not in (None, 0) or (h.get('duration_seconds') or 0) < 20:
            result['classification'] = 'MAME_FATAL'
            result['pass_rejected_reason'] = {'core': h.get('core'), 'exit_code': h.get('exit_code'),
                                              'signal': h.get('signal'), 'duration_seconds': h.get('duration_seconds')}
        else:
            fatal_text = ' '.join(str(h.get(k) or '') for k in ('relevant_error','missing_file','status','diagnosis')).lower()
            if any(token in fatal_text for token in ('missing chd','missing bios','missing parent','missing rom',
                                                       'not found','failed to load','game driver not found','fatal error')):
                result['classification'] = classify_mame_failure(h, h.get('duration_seconds') or 0, True)
                result['pass_rejected_reason'] = 'FATAL_MAME_EVIDENCE_IN_GAME_HEALTH'
    result['game_xml_post'] = {'exists': temp_xml.exists(), 'sha256': sha(temp_xml) if temp_xml.is_file() else None,
                               'content_matches': (f'<path>{rom}</path>' in temp_xml.read_text(errors='replace')) if temp_xml.is_file() else False}
    # Ensure ES returned idle and remove only our own still-present marker.
    deadline = time.time() + 30
    while time.time() < deadline:
        if sr.api_idle() is True and sr.api_game() is None and not chain_processes(): break
        time.sleep(0.25)
    try:
        if remove_owned_marker(marker['transaction_id'], owner='mame_batch4_runner',
                               audit_id=marker.get('audit_id'), path=sr.MARKER):
            result['marker_cleanup'] = 'REMOVED_OWN_UNCONSUMED_MARKER'
    except Exception as e: result['marker_cleanup'] = 'FAILED:' + repr(e)
    result['api_after_close'] = api_state()
    result['processes_after_close'] = chain_processes()
    # Restore monitored persistent user state. Logs/game_health are audit evidence and intentionally excluded.
    post = sr.snapshot_all()
    try:
        made, changed, removed = pilot.restore_files(pre, post, backup, baseline, confcopy)
        restore_ok = sr.snapshot_all() == pre
        result['restore_delta'] = {'created': made, 'changed': changed, 'removed': removed}
    except Exception as e:
        restore_ok = False; result['restore_error'] = repr(e)
    # Failed results must remove a newly-created per-game override. Control altair's historic override is untouched.
    if not is_control and result['classification'] != 'BOOT_PASS':
        expected = oldconf + (b'\n' if oldconf and not oldconf.endswith(b'\n') else b'') + line
        if CONF.read_bytes() != expected: raise RuntimeError('OVERRIDE_ROLLBACK_UNSAFE:' + game)
        pilot.restore_conf(oldconf, oldstat)
        result['override'] = 'REVERTED'
    elif not is_control:
        result['override'] = 'KEPT'
    else: result['override'] = 'UNCHANGED_HISTORIC'
    result['restore_verified'] = restore_ok
    result['rom_unchanged'] = sha(rom) == rom_sha
    result['ended_at'] = stamp()
    result['api_idle_after'] = sr.api_idle() is True
    result['running_game_none_after'] = sr.api_game() is None
    result['marker_absent_after'] = not sr.MARKER.exists()
    result['launch_processes_zero_after'] = not chain_processes()
    result['p1_p4_after'] = profile_check()
    result['global_core_after'] = '<core default="true">mame078plus</core>' in ESCFG.read_text(errors='replace')
    result['overrides_after'] = active_overrides()
    result['gamelist_hashes_after'] = gamelist_hashes()
    expected_after = sorted(EXPECTED_OVERRIDES + ([] if is_control or result['classification'] != 'BOOT_PASS' else [game + '.zip']))
    result['expected_overrides_after'] = expected_after
    overrides_ok = result['overrides_after'] == expected_after
    result['overrides_verified'] = overrides_ok
    result['dispatcher_sha_after'] = sha(DISPATCHER)
    if not (restore_ok and result['rom_unchanged'] and result['api_idle_after'] and result['running_game_none_after']
            and result['marker_absent_after'] and result['launch_processes_zero_after'] and result['p1_p4_after']
            and result['global_core_after'] and overrides_ok
            and result['dispatcher_sha_after'] == 'a60be89fb45ea27ec4f7c3f546e088c7ff3da140bccfe1c6a37e5b14ec581c45'):
        result['safety_gate'] = 'FAIL'
    else: result['safety_gate'] = 'PASS'
    cp['current_game'] = result; save(cp)
    # Only target-core evidence updates the compatibility matrix; altair is a historic positive control.
    if not is_control and result['safety_gate'] == 'PASS' and result.get('reached_mame_current') and result['classification'] in ('BOOT_PASS', 'MISSING_CHD', 'MISSING_BIOS', 'MISSING_PARENT',
            'MISSING_ROM_MEMBER', 'ROMSET_MISMATCH', 'MAME_FATAL', 'SIGSEGV', 'IMMEDIATE_EXIT', 'TIMEOUT', 'UNKNOWN'):
        update_matrix(game, result['classification'], result['ended_at'])
        result['matrix_updated'] = True
    if result['classification'] == 'BOOT_PASS':
        cp['passes'].append(result); 
        if not is_control: cp['new_overrides'].append(game)
    elif result['classification'] == 'ES_WRONG_GAME_DISPATCH':
        cp['failures'].append(result); cp['phase'] = 'PAUSED_SAFETY_WRONG_GAME'
    elif is_control:
        cp['altair_control'] = {'status': 'FAIL', 'result': result}; cp['phase'] = 'PAUSED_SAFETY_CONTROL_FAIL'
    else:
        cp['failures'].append(result)
    cp['restore_results'].append({'shortname': game, 'verified': restore_ok, 'type': 'CONTROL' if is_control else 'GAME'})
    cp['current_game'] = None
    save(cp)
    return result

def main():
    cp = json.loads(CPFILE.read_text(encoding='utf-8'))
    phase = cp.get('phase')
    if phase not in ('ALTair_CONTROL_READY', 'ALTair_CONTROL_PASS'):
        raise SystemExit('BATCH4_NOT_READY:' + str(phase))
    if not cp.get('gamelist_diff', {}).get('semantic_summary', {}).get('only_runtime_history_fields'):
        raise SystemExit('GAMELIST_DIFF_NOT_RECONCILED')
    if not cp.get('historical_artifacts_unchanged_at_test_ready', {}).get('mame_batch3_checkpoint.json'):
        raise SystemExit('BATCH3_HISTORY_HASH_CHANGED')
    if active_overrides() != EXPECTED_OVERRIDES: raise SystemExit('ACTIVE_OVERRIDE_SET_CHANGED')
    if '<core default="true">mame078plus</core>' not in ESCFG.read_text(errors='replace'): raise SystemExit('GLOBAL_CORE_CHANGED')
    if sha(DISPATCHER) != 'a60be89fb45ea27ec4f7c3f546e088c7ff3da140bccfe1c6a37e5b14ec581c45': raise SystemExit('DISPATCHER_SHA_CHANGED')
    if sr.MARKER.exists() or sr.api_idle() is not True or sr.api_game() is not None or not sr.es_pids() or chain_processes(): raise SystemExit('ES_NOT_CLEAN')
    _, backup, baseline = sr.ensure_backup_valid()
    # Protect the resumed tests from any unrelated change to saves/configs since the audited baseline.
    current = sr.snapshot_all()
    if any(current.get(k) != v for k, v in baseline['protected_snapshot'].items() if k != str(CONF)):
        raise SystemExit('PROTECTED_STATE_DRIFT_BEFORE_BATCH4')
    # This file captures the post-restart gamelist baseline; do not put ROM data here.
    game_dir = OUT / 'mame_batch4_runtime'; game_dir.mkdir(exist_ok=True)
    games_before = gamelist_hashes()
    (game_dir / 'gamelist_hashes_after_restart.json').write_text(json.dumps(games_before, indent=2) + '\n')
    cp['gamelists_after_restart_hashes'] = games_before
    if phase == 'ALTair_CONTROL_READY':
        cp['phase'] = 'ALTair_CONTROL_RUNNING'; cp['launched'] = []; cp['passes'] = []; cp['failures'] = []
        cp['skips'] = []; cp['new_overrides'] = []; cp['restore_results'] = []; save(cp)
        # Mandatory control gate: no candidate runs unless altair fully passes.
        control = one_game('altair', True, cp, backup, baseline)
        if control.get('result') == 'SKIP_PREFLIGHT':
            cp['altair_control'] = {'status': 'NOT_RUN_PREFLIGHT', 'result': control}
            cp['phase'] = 'PAUSED_SAFETY_CONTROL_PREFLIGHT'; cp['stop_reason'] = 'Altair fresh preflight did not pass; no candidate launched.'; save(cp)
            return
        if control['classification'] != 'BOOT_PASS' or control['safety_gate'] != 'PASS':
            cp['altair_control'] = {'status': 'FAIL', 'result': control}
            cp['phase'] = 'PAUSED_SAFETY_CONTROL_FAIL'; cp['stop_reason'] = 'Altair control did not fully pass; no candidate launched.'; save(cp)
            return
        cp['altair_control'] = {'status': 'PASS', 'result': control}
        cp['phase'] = 'ALTair_CONTROL_PASS'; save(cp)
    cp['phase'] = 'CANDIDATES_RUNNING'; save(cp)
    for game in GAMES:
        if cp['phase'] != 'CANDIDATES_RUNNING': break
        if game in cp.get('launched', []): continue
        result = one_game(game, False, cp, backup, baseline)
        if result.get('post_response') is not None: cp['launched'].append(game)
        if result.get('classification') == 'SKIP_PREFLIGHT': continue
        if result['safety_gate'] != 'PASS':
            cp['phase'] = 'PAUSED_SAFETY_RESTORE_OR_SYSTEM'; cp['stop_reason'] = 'Post-game safety gate failed.'; save(cp); break
        if result['classification'] in ('ES_WRONG_GAME_DISPATCH', 'LAUNCH_CHAIN_FAILURE'):
            cp['stop_reason'] = 'ES/dispatcher received a different ROM; remaining candidates stopped.'; save(cp); break
    if cp['phase'] == 'CANDIDATES_RUNNING': cp['phase'] = 'COMPLETE'
    cp['finished_at'] = stamp(); save(cp)

if __name__ == '__main__':
    main()
