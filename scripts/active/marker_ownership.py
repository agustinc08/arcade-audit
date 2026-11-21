#!/usr/bin/env python3
"""Shared, conservative ownership protocol for the one-shot launch marker."""
import fcntl
import json
import os
import stat
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

MARKER = Path('/userdata/system/state/boot_audit_once.json')
LOCK = Path('/userdata/system/state/boot_audit_once.lock')


@contextmanager
def marker_lock(path=None):
    if path is None: path = LOCK
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def read_marker(path=MARKER):
    path = Path(path)
    fd = None
    try:
        fd = os.open(str(path), os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return None
        with os.fdopen(fd, 'r', encoding='utf-8') as stream:
            fd = None
            value = json.load(stream)
        return value if isinstance(value, dict) else None
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    finally:
        if fd is not None:
            os.close(fd)


def classify_marker(value, transaction_id=None, *, recovery_evidence=None):
    if not isinstance(value, dict):
        return 'FOREIGN_UNKNOWN'
    if transaction_id and value.get('transaction_id') == transaction_id and value.get('owner') == 'full_game_certifier':
        return 'OWNED_BY_CURRENT_TRANSACTION'
    pid = value.get('pid')
    if isinstance(pid, int) and pid > 1 and isinstance(value.get('process_start_ticks'), int):
        try:
            proc = Path(f'/proc/{pid}')
            fields = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
            start_ticks = int(fields[19])
            argv = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode('utf-8', 'replace').lower()
            expected = {
                'full_game_certifier': 'full_game_certifier.py',
                'smoke_runner': 'smoke_runner.py',
                'smoke_pilot_runner': 'smoke_pilot_runner.py',
                'smoke_pilot_batch2': 'smoke_pilot_batch2.py',
                'mame_batch3_resume_control': 'mame_batch3_resume_control.py',
                'mame_batch4_runner': 'mame_batch4_runner.py',
                'mame_batch5_runner': 'mame_batch5_runner.py',
            }.get(value.get('owner'))
            if expected and start_ticks == value['process_start_ticks'] and expected in argv:
                return 'OWNED_BY_ACTIVE_PROCESS'
        except OSError:
            pass
        except (ValueError, IndexError):
            pass
    if _stale_proven(value, recovery_evidence):
        return 'STALE_PROVEN'
    # Staleness needs transaction/checkpoint and runtime evidence. A timestamp alone is insufficient.
    return 'FOREIGN_UNKNOWN'


def _stale_proven(value, evidence):
    required = ('transaction_finalized', 'es_idle', 'no_launch_processes',
                'no_selector_dispatcher_certifier', 'metadata_compatible')
    if not isinstance(value, dict) or not isinstance(evidence, dict):
        return False
    if any(evidence.get(key) is not True for key in required):
        return False
    if (value.get('schema_version') != 1 or value.get('owner') not in ('full_game_certifier', 'smoke_runner',
            'smoke_pilot_runner', 'smoke_pilot_batch2', 'mame_batch3_resume_control',
            'mame_batch4_runner', 'mame_batch5_runner')
            or not value.get('transaction_id') or not isinstance(value.get('pid'), int)
            or not isinstance(value.get('process_start_ticks'), int)):
        return False
    created = value.get('created_at')
    if not isinstance(created, (int, float)) or created <= 0 or created > time.time() + 60:
        return False
    if time.time() - created > 24 * 60 * 60:
        return False
    try:
        fields = Path(f"/proc/{value['pid']}/stat").read_text().rsplit(')', 1)[1].split()
        current_start_ticks = int(fields[19])
    except (OSError, ValueError, IndexError):
        return True
    return current_start_ticks != value['process_start_ticks']


def create_exclusive(system, rom, owner, transaction_id, *, choice='BOTONERA', path=MARKER):
    """Create a compatible one-shot marker without replacing any existing file."""
    if choice not in ('BOTONERA', 'JOYSTICKS'):
        raise ValueError('INVALID_AUTOMATIC_SELECTOR_CHOICE')
    now = time.time()
    value = {
        'enabled': True,
        'system': system,
        'rom': rom,
        'choice': choice,
        'created_at': now,
        'expires_at': now + 55,
        'audit_id': f'{system}:{Path(rom).name}:{now:.6f}',
        'schema_version': 1,
        'owner': owner,
        'transaction_id': transaction_id,
        'pid': os.getpid(),
        'process_start_ticks': _process_start_ticks(os.getpid()),
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'requested_system': system,
        'requested_rom': rom,
    }
    data = (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')
    with marker_lock():
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        created_stat = os.fstat(fd)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            directory_fd = os.open(str(Path(path).parent), os.O_RDONLY)
            try: os.fsync(directory_fd)
            finally: os.close(directory_fd)
        except Exception:
            # Only remove the inode we just created; do not unlink a replacement.
            try:
                current = Path(path).stat()
                if current.st_dev == created_stat.st_dev and current.st_ino == created_stat.st_ino:
                    Path(path).unlink()
            except (OSError, ValueError):
                pass
            raise
    return value


def _process_start_ticks(pid):
    try:
        return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19])
    except (OSError, ValueError, IndexError):
        return None


def remove_if_owned(transaction_id, *, owner='full_game_certifier', audit_id=None, path=MARKER):
    with marker_lock():
        if Path(path).is_symlink() or not Path(path).is_file():
            return False
        value = read_marker(path)
        if not value or value.get('owner') != owner or value.get('transaction_id') != transaction_id:
            return False
        if audit_id is not None and value.get('audit_id') != audit_id:
            return False
        Path(path).unlink()
        return True
