#!/usr/bin/env python3
"""Explicit, detached supervisor for the arcade full-game certifier."""
import fcntl
import gzip
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

TOOLS = Path('/userdata/system/el_gordo_tools')
AUDIT = Path('/userdata/system/state/arcade_audit')
JOBS = Path('/userdata/system/state/arcade_audit/jobs')
META = JOBS / 'certifier_job.json'
PIDFILE = JOBS / 'certifier_job.pid'
LOG = JOBS / 'certifier_job.log'
LOCK = JOBS / '.certifier_job.lock'
CERTIFIER = TOOLS / 'full_game_certifier.py'
AUTOPILOT_STATE = AUDIT / 'autopilot_state.json'


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def autopilot_owns_start():
    state = read_json(AUTOPILOT_STATE, {}) or {}
    if state.get('status') not in ('STARTING', 'RUNNING'):
        return True
    run_id = state.get('run_id')
    pid = state.get('pid')
    if not run_id or os.environ.get('ARCADE_AUTOPILOT_RUN_ID') != run_id or not isinstance(pid, int):
        return False
    if os.getppid() != pid:
        return False
    try:
        proc = Path(f'/proc/{pid}')
        cmdline = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode('utf-8', 'replace')
        fields = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
        start_ticks = int(fields[19])
        return ('arcade_autopilot.py' in cmdline and '--worker' in cmdline and run_id in cmdline and
                start_ticks == state.get('process_start_ticks'))
    except (OSError, ValueError, IndexError):
        return False


def atomic_json(path, value):
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    fd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def read_json(path, fallback=None):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return fallback


def proc_info(pid):
    try:
        raw = Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
        stat = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return {'cmdline': raw, 'ppid': int(stat[1]), 'pgid': int(stat[2]), 'sid': int(stat[3])}
    except (OSError, ValueError, IndexError):
        return None


def active_certifiers():
    found = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        info = proc_info(int(entry.name))
        if info and str(CERTIFIER) in info['cmdline']:
            found.append((int(entry.name), info))
    return found


def active_job(meta):
    if not isinstance(meta, dict):
        return False
    for key in ('pid', 'worker_pid'):
        pid = meta.get(key)
        if isinstance(pid, int) and proc_info(pid):
            return True
    return False


def validate_start(batch_size):
    if not 1 <= batch_size <= 100:
        raise RuntimeError('BATCH_SIZE_MUST_BE_1_TO_100')
    if active_certifiers():
        raise RuntimeError('CERTIFIER_ALREADY_RUNNING')
    if not autopilot_owns_start():
        raise RuntimeError('AUTOPILOT_ALREADY_RUNNING')
    old = read_json(META)
    if active_job(old):
        raise RuntimeError('CERTIFIER_ALREADY_RUNNING')

    sys.path.insert(0, str(TOOLS))
    import full_game_certifier as cert

    cp = read_json(cert.STATE)
    if not cp:
        raise RuntimeError('CHECKPOINT_UNAVAILABLE')
    safe_resume = cp.get('status') == 'STOPPED_SAFE' and not cp.get('blocked_reason') and isinstance(cp.get('batch_in_progress'), dict)
    clean_complete = cp.get('status') == 'COMPLETE' and not cp.get('blocked_reason') and not cp.get('batch_in_progress')
    if not (clean_complete or safe_resume):
        raise RuntimeError('CHECKPOINT_NOT_RECONCILED:' + str(cp.get('status')) + ':' + str(cp.get('blocked_reason')))
    rows, _ = cert.load_rows()
    systems = cert.ad.live_systems()
    cert.assert_reconciled_queue(rows, cp, systems)
    metrics = cert.certification_metrics(rows, cp)
    if metrics.get('engine_fail_active'):
        raise RuntimeError('ACTIVE_ENGINE_FAILURES')
    next_game = cert.next_cursor(rows, systems)
    if not next_game:
        raise RuntimeError('NO_NOT_TESTED_GAME')
    baseline = cert.safety_baseline()
    # safety_baseline checks ES/API idle, marker absence, no launch processes,
    # EmulationStation, P1-P4 mapping, HDMI audio and global config hashes.
    if baseline.get('audio_default') != cert.HDMI:
        raise RuntimeError('HDMI_GATE_FAILED')
    if safe_resume:
        progress = cp['batch_in_progress']
        remaining = int(progress.get('considered', 0)) - int(progress.get('launched', 0))
        if remaining < 1:
            raise RuntimeError('SAFE_STOP_BATCH_BOUNDARY_INCONSISTENT')
        return next_game, min(batch_size, remaining)
    return next_game, batch_size


def rotate_successful_log():
    old = read_json(META)
    old_log = Path(old.get('log_path', str(LOG))) if old else LOG
    if not old_log.is_file() or not old:
        return
    if old.get('status') == 'FAILED':
        return
    archive = JOBS / 'logs'
    archive.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = archive / (str(old.get('job_id', 'previous')) + '.log.gz')
    if destination.exists():
        return
    with old_log.open('rb') as src, destination.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as dst:
            shutil.copyfileobj(src, dst)
    os.chmod(destination, 0o600)
    # Remove only the uncompressed duplicate after the compressed archive is readable.
    with gzip.open(destination, 'rb') as archived:
        while archived.read(1024 * 1024):
            pass
    if old_log.parent == (JOBS / 'logs') and old_log.name.endswith('.log'):
        old_log.unlink()


def acquire_lock():
    JOBS.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(str(LOCK), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        raise RuntimeError('CERTIFIER_ALREADY_RUNNING')
    return fd


def start(batch_size):
    lock_fd = acquire_lock()
    try:
        next_game, effective_batch_size = validate_start(batch_size)
        rotate_successful_log()
        job_id = datetime.now().strftime('%Y%m%dT%H%M%S') + '_' + uuid.uuid4().hex[:8]
        job_log = JOBS / 'logs' / (job_id + '.log')
        job_log.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if LOG.exists() and not LOG.is_symlink():
            raise RuntimeError('LOG_PATH_UNEXPECTED; preserve and inspect before proceeding')
        link_tmp = JOBS / '.certifier_job.log.new'
        try:
            link_tmp.unlink()
        except FileNotFoundError:
            pass
        link_tmp.symlink_to(Path('logs') / (job_id + '.log'))
        os.replace(link_tmp, LOG)
        argv = [sys.executable, str(CERTIFIER), '--batch', str(effective_batch_size)]
        meta = {
            'job_id': job_id, 'pid': None, 'worker_pid': None,
            'started_at': now(), 'finished_at': None, 'batch_size': effective_batch_size,
            'requested_batch_size': batch_size,
            'starting_game': next_game, 'command': argv, 'status': 'STARTING',
            'exit_code': None, 'log_path': str(job_log), 'stop_request': None,
        }
        atomic_json(META, meta)
        # Open the per-job log before detaching so all worker output is persistent.
        with job_log.open('ab', buffering=0) as output:
            proc = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), '--worker', job_id,
                 str(effective_batch_size), next_game, str(job_log)],
                stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                close_fds=True, start_new_session=True,
            )
        meta['worker_pid'] = proc.pid
        meta['pid'] = proc.pid
        meta['status'] = 'RUNNING'
        atomic_json(META, meta)
        PIDFILE.write_text(str(proc.pid) + '\n', encoding='ascii')
        os.chmod(PIDFILE, 0o600)
        print('STARTED')
        print(json.dumps(meta, ensure_ascii=False, indent=2))
    finally:
        os.close(lock_fd)


def worker(job_id, batch_size, starting_game, log_path):
    deadline = time.monotonic() + 10
    meta = {}
    while time.monotonic() < deadline:
        meta = read_json(META, {})
        if meta.get('job_id') == job_id and meta.get('worker_pid') == os.getpid():
            break
        time.sleep(0.02)
    else:
        return 70
    stop_file = JOBS / (job_id + '.stop')
    env = os.environ.copy()
    env['ARCADE_CERTIFIER_STOP_FILE'] = str(stop_file)
    command = [sys.executable, str(CERTIFIER), '--batch', str(batch_size)]
    proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, close_fds=True, env=env, text=True,
                            bufsize=1, start_new_session=False)
    meta.update({'pid': proc.pid, 'worker_pid': os.getpid(), 'command': command,
                 'status': 'RUNNING', 'starting_game': starting_game})
    atomic_json(META, meta)
    PIDFILE.write_text(str(proc.pid) + '\n', encoding='ascii')
    os.chmod(PIDFILE, 0o600)
    with open(log_path, 'a', encoding='utf-8', buffering=1) as log:
        for line in proc.stdout:
            log.write(line)
    code = proc.wait()
    cp = read_json(AUDIT / 'full_game_certification_checkpoint.json', {})
    safe_stopped = cp.get('status') == 'STOPPED_SAFE'
    status = 'COMPLETE' if safe_stopped or (code == 0 and cp.get('status') == 'COMPLETE') else 'FAILED'
    meta.update({'exit_code': code, 'finished_at': now(), 'status': status,
                 'completion_reason': 'SAFE_STOP_AT_GAME_BOUNDARY' if safe_stopped else None,
                 'checkpoint_status': cp.get('status'), 'next_game': cp.get('next_untested')})
    atomic_json(META, meta)
    return code


def status():
    meta = read_json(META)
    if not meta:
        print('NOT_RUNNING')
        return 0
    pid = meta.get('pid')
    info = proc_info(pid) if isinstance(pid, int) else None
    running = bool(info and (str(CERTIFIER) in info['cmdline'] or meta.get('worker_pid') == pid))
    state = meta.get('status')
    if running:
        state = 'RUNNING'
    elif meta.get('finished_at') and state in ('COMPLETE', 'FAILED'):
        state = meta['status']
    else:
        cp = read_json(AUDIT / 'full_game_certification_checkpoint.json', {})
        state = 'COMPLETE' if cp.get('status') == 'COMPLETE' and not cp.get('batch_in_progress') else 'FAILED'
    try:
        started = datetime.fromisoformat(meta['started_at'].replace('Z', '+00:00')).timestamp()
        elapsed = max(0, int(time.time() - started))
    except (KeyError, ValueError, TypeError):
        elapsed = None
    cp = read_json(AUDIT / 'full_game_certification_checkpoint.json', {})
    batch = cp.get('batch_in_progress') or cp.get('latest_batch') or {}
    result = {
        'status': state, 'pid': pid, 'worker_pid': meta.get('worker_pid'),
        'elapsed_seconds': elapsed, 'current_game': cp.get('current_test'),
        'processed': batch.get('launched', 0), 'AUTO_PASS': batch.get('auto_pass', 0),
        'GAME_FAIL': batch.get('game_fail', 0), 'RESTORES': batch.get('restore_verified', 0),
        'NEXT_GAME': cp.get('next_untested'), 'job_id': meta.get('job_id'),
        'exit_code': meta.get('exit_code'), 'session_id': info.get('sid') if info else None,
        'process_group': info.get('pgid') if info else None,
        'log': meta.get('log_path'),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def show_log(lines=50):
    if not 1 <= lines <= 1000:
        raise RuntimeError('LOG_LINES_MUST_BE_1_TO_1000')
    meta = read_json(META, {})
    path = LOG if LOG.exists() else Path(meta.get('log_path', str(LOG)))
    if not path.is_file():
        path = LOG
    if not path.is_file():
        print('NO_LOG')
        return 0
    with path.open('r', encoding='utf-8', errors='replace') as stream:
        from collections import deque
        for line in deque(stream, maxlen=lines):
            print(line, end='')
    return 0


def stop_safe():
    meta = read_json(META)
    if not meta or not active_job(meta):
        print('NOT_RUNNING')
        return 0
    job_id = meta.get('job_id')
    stop_file = JOBS / (str(job_id) + '.stop')
    # O_EXCL prevents a stale or misdirected request from silently replacing data.
    fd = os.open(str(stop_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w', encoding='ascii') as stream:
        stream.write(now() + '\n')
    meta['stop_request'] = str(stop_file)
    meta['stop_requested_at'] = now()
    atomic_json(META, meta)
    print('SAFE_STOP_REQUESTED; current transaction will finish restore before stopping')
    return 0


def main(argv):
    JOBS.mkdir(parents=True, exist_ok=True, mode=0o700)
    if argv and argv[0] == '--worker':
        return worker(argv[1], int(argv[2]), argv[3], argv[4])
    if not argv:
        raise RuntimeError('USAGE: arcade_certifier_job.sh start N|status|log [N]|stop-safe')
    if argv[0] == 'start' and len(argv) == 2:
        start(int(argv[1])); return 0
    if argv[0] == 'status' and len(argv) == 1:
        return status()
    if argv[0] == 'log' and len(argv) <= 2:
        return show_log(int(argv[1]) if len(argv) == 2 else 50)
    if argv[0] == 'stop-safe' and len(argv) == 1:
        return stop_safe()
    raise RuntimeError('USAGE: arcade_certifier_job.sh start N|status|log [N]|stop-safe')


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        if str(exc).startswith('CERTIFIER_ALREADY_RUNNING'):
            print('CERTIFIER_ALREADY_RUNNING', file=sys.stderr)
        sys.exit(1)
