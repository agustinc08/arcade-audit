#!/usr/bin/env python3
"""Instrument the single authorized BATCH 3 positive control (altair)."""
import hashlib
import json
import os
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path('/userdata/system/state/arcade_audit')
sys.path.insert(0, str(OUT))
import smoke_runner as sr
import smoke_pilot_batch2 as pilot
sys.path.insert(0, '/userdata/system/el_gordo_tools')
from marker_ownership import create_exclusive as create_owned_marker, remove_if_owned as remove_owned_marker

RESUME = OUT / 'mame_batch3_resume_checkpoint.json'
ORIGINAL = OUT / 'mame_batch3_checkpoint.json'
CONF = Path('/userdata/system/batocera.conf')
DISPATCHER = Path('/userdata/system/el_gordo_tools/controller_dispatcher')
ESCFG = Path('/userdata/system/configs/emulationstation/es_systems_el_gordo.cfg')
PROFILE = Path('/userdata/system/configs/el_gordo_controller_profiles/controller_technical.json')
ROM = Path('/userdata/roms/mame/altair.zip')
CORE = Path('/usr/lib/libretro/mame_libretro.so')
CMD = Path('/var/run/cmdfiles/altair.cmd')
API = 'http://127.0.0.1:1234'
LOGS = [Path('/userdata/system/logs/controller_selector.log'), Path('/userdata/system/logs/es_launch_stderr.log')]

def stamp():
    return datetime.now().astimezone().isoformat(timespec='milliseconds')

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def overrides():
    return sorted(x.decode() for x in set(re.findall(rb'^mame\["([^\"]+)"\]\.core=mame\s*$', CONF.read_bytes(), re.M)))

def raw_get(path, timeout=2):
    with urllib.request.urlopen(API + path, timeout=timeout) as r:
        body = r.read().decode('utf-8', 'replace')
        return {'status': r.status, 'body': body}

def parse_game(raw):
    try:
        v = json.loads(raw['body'])
        return None if isinstance(v, dict) and v.get('msg') == 'NO GAME RUNNING' else v
    except Exception:
        return {'unparsed': raw['body']}

def proc_records():
    records = []
    own = {os.getpid()}
    try:
        ppid = os.getppid()
        own.add(ppid)
        pp = Path(f'/proc/{ppid}/stat').read_text().rsplit(')', 1)[1].split()
        if len(pp) > 1:
            own.add(int(pp[1]))
    except Exception:
        pass
    for p in Path('/proc').iterdir():
        if not p.name.isdigit() or int(p.name) in own:
            continue
        try:
            pid = int(p.name)
            cmd = (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode('utf-8', 'replace').strip()
            exe = os.readlink(p / 'exe')
            comm = (p / 'comm').read_text(errors='replace').strip()
            if not cmd:
                cmd = comm
            records.append({'pid': pid, 'exe': exe, 'comm': comm, 'cmd': cmd})
        except (OSError, ProcessLookupError):
            pass
    return records

def launch_processes(records=None):
    records = records if records is not None else proc_records()
    tokens = ('retroarch', 'controller_dispatcher', 'selector_controles', 'emulatorlauncher', '/usr/bin/mame')
    return [p for p in records if any(t in (p['exe'] + ' ' + p['cmd']).lower() for t in tokens)]

def target_ra(records=None):
    records = records if records is not None else proc_records()
    return [p for p in records if p['exe'].endswith('/retroarch') and str(CORE) in p['cmd'] and str(CMD) in p['cmd']]

def health_row(after_id):
    db = Path('/userdata/system/state/game_health.sqlite')
    try:
        c = sqlite3.connect('file:' + str(db) + '?mode=ro', uri=True, timeout=2)
        c.row_factory = sqlite3.Row
        row = c.execute('SELECT * FROM launch_events WHERE system=? AND rom=? AND id>? ORDER BY id DESC LIMIT 1',
                         ('mame', str(ROM), after_id)).fetchone()
        c.close()
        return dict(row) if row else None
    except Exception as e:
        return {'read_error': repr(e)}

def add_event(cp, key, detail=None):
    if not any(e['event'] == key for e in cp['control_altair']['events']):
        cp['control_altair']['events'].append({'event': key, 'time': stamp(), 'detail': detail})
        RESUME.write_text(json.dumps(cp, ensure_ascii=False, indent=2) + '\n')

def main():
    cp = json.loads(RESUME.read_text(encoding='utf-8'))
    if cp.get('phase') != 'PRE_CONTROL_DIAGNOSTICS_COMPLETE' or cp.get('control_altair', {}).get('status') != 'AUTHORIZED_NOT_YET_RUN':
        raise SystemExit('RESUME_CHECKPOINT_NOT_READY')
    if json.loads(ORIGINAL.read_text(encoding='utf-8')).get('phase') != 'PAUSED_SAFETY':
        raise SystemExit('ORIGINAL_CHECKPOINT_CHANGED')
    if sr.MARKER.exists():
        raise SystemExit('ONE_SHOT_MARKER_EXISTS')
    if not ROM.is_file() or not CORE.is_file():
        raise SystemExit('ALTair_ROM_OR_CORE_MISSING')
    if overrides() != cp['pre_control_system']['overrides']:
        raise SystemExit('OVERRIDE_SET_CHANGED')
    if sr.api_idle() is not True or sr.api_game() is not None or not sr.es_pids():
        raise SystemExit('ES_NOT_READY')
    # Exclude this observer and its shell from process checks; test only the real launch chain.
    if launch_processes():
        raise SystemExit('PREEXISTING_LAUNCH_PROCESS:' + repr(launch_processes()))
    _, backup, baseline = sr.ensure_backup_valid()
    pre = sr.snapshot_all()
    base_snap = baseline['protected_snapshot']
    if any(pre.get(k) != v for k, v in base_snap.items() if k != str(CONF)) or any(base_snap.get(k) != v for k, v in pre.items() if k != str(CONF)):
        raise SystemExit('PROTECTED_STATE_DRIFT_BEFORE_CONTROL')
    with urllib.request.urlopen(API + '/systems/mame/games', timeout=10) as r:
        games = json.loads(r.read())
    matches = [g for g in games if g.get('path') == str(ROM)]
    if len(matches) != 1:
        raise SystemExit('ALTair_NOT_UNIQUE_IN_LOADED_ES_COLLECTION')
    for path in LOGS:
        if not path.is_file():
            raise SystemExit('EXPECTED_LAUNCH_LOG_MISSING:' + str(path))
    # Per-game checkpoint copy plus full metadata snapshot; no ROM payload is copied.
    state_dir = OUT / 'mame_batch3_resume_runtime' / 'altair'
    state_dir.mkdir(parents=True, exist_ok=True)
    conf_copy = state_dir / 'batocera.conf.pretest'
    shutil.copy2(CONF, conf_copy)
    pre_snapshot_path = state_dir / 'snapshot.pretest.json'
    pre_snapshot_path.write_text(json.dumps(pre, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    pre_snapshot_hash = sha(pre_snapshot_path)
    db = sqlite3.connect('file:/userdata/system/state/game_health.sqlite?mode=ro', uri=True, timeout=2)
    before_id = db.execute('SELECT COALESCE(MAX(id),0) FROM launch_events').fetchone()[0]
    db.close()
    log_before = {str(p): {'size': p.stat().st_size, 'mtime_ns': p.stat().st_mtime_ns} for p in LOGS}
    cmd_before = {'exists': CMD.exists(), 'mtime_ns': CMD.stat().st_mtime_ns if CMD.exists() else None,
                  'size': CMD.stat().st_size if CMD.exists() else None}
    initial_idle = raw_get('/isIdle')
    initial_game = raw_get('/runningGame')
    cp['phase'] = 'ALTair_CONTROL_RUNNING'
    cp['control_altair'].update({'status': 'RUNNING', 'started_at': stamp(), 'pre_snapshot': str(pre_snapshot_path),
        'pre_snapshot_sha256': pre_snapshot_hash, 'pre_snapshot_item_count': len(pre), 'config_copy': str(conf_copy),
        'game_health_max_id_before': before_id, 'log_metadata_before': log_before, 'cmdfile_before': cmd_before,
        'initial_api': {'isIdle': initial_idle, 'runningGame': initial_game}, 'rom_sha256_before': sha(ROM),
        'core_path': str(CORE), 'override_set_before': overrides()})
    RESUME.write_text(json.dumps(cp, ensure_ascii=False, indent=2) + '\n')

    try:
        marker = create_owned_marker('mame', str(ROM), 'mame_batch3_resume_control',
                                    f'mame-batch3:{os.getpid()}:{time.time_ns()}', path=sr.MARKER)
    except FileExistsError as exc:
        raise RuntimeError('MARKER_ALREADY_EXISTS') from exc
    cp['control_altair']['marker'] = marker
    add_event(cp, 'T0_MARKER_CREATED', {'path': str(sr.MARKER), 'value': marker})

    stop = threading.Event()
    state = {'idle': True, 'game': None, 'marker_exists': True, 'cmdfile': cmd_before,
             'health_id': before_id, 'records': [], 'api_errors': []}
    def observe():
        while not stop.is_set():
            try:
                idle_raw = raw_get('/isIdle')
                idle_val = json.loads(idle_raw['body'])[0]
                game_raw = raw_get('/runningGame')
                game_val = parse_game(game_raw)
                records = proc_records()
                now_marker = sr.MARKER.exists()
                cmd_now = {'exists': CMD.exists(), 'mtime_ns': CMD.stat().st_mtime_ns if CMD.exists() else None,
                           'size': CMD.stat().st_size if CMD.exists() else None}
                h = health_row(before_id)
                h_id = h.get('id', before_id) if h else before_id
                if state['idle'] is True and idle_val is not True: add_event(cp, 'T2_ISIDLE_CHANGED', idle_raw)
                if state['game'] is None and game_val is not None: add_event(cp, 'T3_RUNNINGGAME_CHANGED', {'raw': game_raw, 'parsed': game_val})
                if state['marker_exists'] and not now_marker: add_event(cp, 'T4_MARKER_CONSUMED', None)
                if not state.get('dispatcher') and any('controller_dispatcher' in p['cmd'] for p in records):
                    state['dispatcher'] = True; add_event(cp, 'T5_CONTROLLER_DISPATCHER_SEEN', None)
                if not state.get('emulatorlauncher') and any('emulatorlauncher' in p['cmd'].lower() for p in records):
                    state['emulatorlauncher'] = True; add_event(cp, 'T6_EMULATORLAUNCHER_SEEN', None)
                ra = target_ra(records)
                if not state.get('retroarch') and ra:
                    state['retroarch'] = ra[0]['pid']; add_event(cp, 'T7_RETROARCH_TARGET_CORE_SEEN', ra[0])
                if cmd_now['exists'] and (not cmd_before['exists'] or cmd_now != cmd_before) and not state.get('cmdfile_seen'):
                    state['cmdfile_seen'] = True; add_event(cp, 'T8_ALTAIR_CMD_CREATED_OR_CHANGED', cmd_now)
                if h and h.get('id', 0) > before_id and not state.get('health'):
                    state['health'] = h; add_event(cp, 'T9_GAME_HEALTH_EVENT', h)
                state.update({'idle': idle_val, 'game': game_val, 'marker_exists': now_marker, 'cmdfile': cmd_now,
                              'health_id': h_id, 'records': records})
            except Exception as e:
                state['api_errors'].append({'time': stamp(), 'error': repr(e)})
            stop.wait(0.1)

    watcher = threading.Thread(target=observe, daemon=True)
    watcher.start()
    started_epoch = time.time()
    cp['control_altair']['launch_start_epoch'] = started_epoch
    add_event(cp, 'T1_POST_SENT', {'url': API + '/launch', 'body_utf8': str(ROM),
                                   'content_type': 'application/x-www-form-urlencoded', 'timeout_seconds': 8})
    status = 'LAUNCH_CHAIN_RUNTIME_FAILURE'
    post = None
    target = None
    details = None
    try:
        request = urllib.request.Request(API + '/launch', data=str(ROM).encode('utf-8'), method='POST',
                                         headers={'Content-Type': 'application/x-www-form-urlencoded'})
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                post = {'status': response.status, 'headers': dict(response.headers.items()),
                        'body': response.read().decode('utf-8', 'replace')}
        except urllib.error.HTTPError as e:
            post = {'status': e.code, 'headers': dict(e.headers.items()) if e.headers else {},
                    'body': e.read().decode('utf-8', 'replace')}
        cp['control_altair']['post_response'] = post
        RESUME.write_text(json.dumps(cp, ensure_ascii=False, indent=2) + '\n')
        deadline = started_epoch + 30
        while time.time() < deadline:
            ra = target_ra()
            if ra:
                target = ra[0]
                break
            time.sleep(0.1)
        if post.get('status') == 200 and target:
            if str(CORE) not in target['cmd'] or str(CMD) not in target['cmd']:
                details = 'RetroArch argv no coincide con core actual/cmdfile altair: ' + target['cmd']
                status = 'CONTROL_LAUNCH_FAIL'
            else:
                end_stable = time.time() + 20
                status = 'CONTROL_LAUNCH_PASS'
                while time.time() < end_stable:
                    current = target_ra()
                    if len(current) != 1 or current[0]['pid'] != target['pid']:
                        status = 'CONTROL_LAUNCH_FAIL'; details = 'RetroArch terminó durante ventana de estabilidad'; break
                    if sr.api_idle() is True or sr.api_game() is None:
                        status = 'CONTROL_LAUNCH_FAIL'; details = 'ES informó idle/sin juego mientras RetroArch seguía activo'; break
                    time.sleep(0.25)
                if status == 'CONTROL_LAUNCH_PASS':
                    current = target_ra()
                    if len(current) != 1 or current[0]['pid'] != target['pid']:
                        status = 'CONTROL_LAUNCH_FAIL'; details = 'PID target no único al cerrar'
                    else:
                        os.kill(target['pid'], signal.SIGTERM)
                        stop_deadline = time.time() + 20
                        while time.time() < stop_deadline and any(p['pid'] == target['pid'] for p in proc_records()):
                            time.sleep(0.2)
                        if any(p['pid'] == target['pid'] for p in proc_records()):
                            status = 'CONTROL_LAUNCH_FAIL'; details = 'RetroArch no cerró con SIGTERM dentro de 20s'
        else:
            details = 'POST/dispatch no inició RetroArch con MAME actual dentro de 30s'
    finally:
        stop.set(); watcher.join(timeout=3)
        try:
            removed = remove_owned_marker(marker['transaction_id'], owner='mame_batch3_resume_control',
                                          audit_id=marker.get('audit_id'), path=sr.MARKER)
            if removed: cp['control_altair']['marker_cleanup'] = 'REMOVED_OWN_UNCONSUMED_MARKER'
        except Exception as e:
            cp['control_altair']['marker_cleanup'] = 'FAILED:' + repr(e)
        # Wait for the official launcher to return to ES before restoring monitored per-game state.
        deadline = time.time() + 30
        while time.time() < deadline:
            if sr.api_idle() is True and sr.api_game() is None and not launch_processes():
                break
            time.sleep(0.25)
        post_snapshot = sr.snapshot_all()
        try:
            made, changed, removed = pilot.restore_files(pre, post_snapshot, backup, baseline, conf_copy)
            restore = {'verified': sr.snapshot_all() == pre, 'created': made, 'changed': changed, 'removed': removed,
                       'snapshot_sha256_after': sha(pre_snapshot_path)}
        except Exception as e:
            restore = {'verified': False, 'error': repr(e)}
        db_after = health_row(before_id)
        final_processes = launch_processes()
        final_idle = {'isIdle': raw_get('/isIdle'), 'runningGame': raw_get('/runningGame')}
        cp['control_altair'].update({'status': status, 'detail': details, 'ended_at': stamp(),
            'events': cp['control_altair']['events'], 'observer_final': state,
            'game_health_event': db_after, 'restore': restore, 'restore_verified': restore.get('verified', False),
            'final_api': final_idle, 'final_launch_processes': final_processes, 'rom_unchanged': sha(ROM) == cp['control_altair']['rom_sha256_before'],
            'override_set_after': overrides(), 'log_metadata_after': {str(p): {'size': p.stat().st_size, 'mtime_ns': p.stat().st_mtime_ns} for p in LOGS}})
        cp['phase'] = 'CONTROL_PASS' if status == 'CONTROL_LAUNCH_PASS' and restore.get('verified') else 'PAUSED_SAFETY'
        cp['kinstb_retry'] = 'AUTHORIZED_PENDING_CONTROL_PASS' if cp['phase'] == 'CONTROL_PASS' else 'NOT_RUN'
        cp['system_after_control'] = {'es_pids': sr.es_pids(), 'api_idle': sr.api_idle(), 'api_game': sr.api_game(),
            'launch_processes': final_processes, 'global_core': 'mame078plus', 'overrides': overrides(),
            'p1_p4_diagnostic': 'see pre-control record; no mapping writes were made'}
        RESUME.write_text(json.dumps(cp, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(cp['control_altair'], ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
