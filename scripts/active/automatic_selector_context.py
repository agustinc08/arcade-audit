#!/usr/bin/python3
"""Transaction-scoped authorization for automated selector invocations.

This module does not change manual launches. Authorization requires a live
certifier identity, the same boot and EmulationStation process identity, the
canonical system/ROM, and an allowed transaction phase.
"""
from __future__ import annotations

import fcntl
import json
import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ACTIVE_CONTEXT = Path('/userdata/system/state/arcade_audit/jobs/automatic_selector_context.json')
CONTEXT_LOCK = ACTIVE_CONTEXT.with_suffix('.lock')
CERTIFIER = '/userdata/system/el_gordo_tools/full_game_certifier.py'
DISPATCHER = '/userdata/system/el_gordo_tools/controller_dispatcher'


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name(path.name + '.tmp')
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)
    dfd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)


@contextmanager
def _locked(path: Path = ACTIVE_CONTEXT):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = Path(path).with_suffix('.lock')
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def current_boot_id() -> str | None:
    try:
        return Path('/proc/sys/kernel/random/boot_id').read_text().strip() or None
    except OSError:
        return None


def process_identity(pid: int) -> dict | None:
    try:
        proc = Path(f'/proc/{pid}')
        fields = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
        cmdline = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode('utf-8', 'replace').strip()
        return {
            'pid': int(pid), 'ppid': int(fields[1]), 'start_ticks': int(fields[19]),
            'comm': (proc / 'comm').read_text().strip(),
            'exe': os.readlink(proc / 'exe'), 'cmdline': cmdline,
        }
    except (OSError, ValueError, IndexError):
        return None


def _canonical_rom(value: str) -> str:
    return os.path.realpath(os.path.abspath(value))


def create_context(*, transaction_id: str, system: str, rom: str,
                   certifier: dict, es_identity: dict, autopilot: dict | None,
                   path: Path = ACTIVE_CONTEXT, now: float | None = None) -> dict:
    if not transaction_id or not Path(rom).is_absolute():
        raise ValueError('AUTOMATIC_CONTEXT_IDENTITY_INVALID')
    if not isinstance(certifier, dict) or not isinstance(certifier.get('pid'), int) or not certifier.get('start_ticks'):
        raise ValueError('AUTOMATIC_CONTEXT_CERTIFIER_IDENTITY_INVALID')
    if not isinstance(es_identity, dict) or not isinstance(es_identity.get('pid'), int) or not es_identity.get('start_ticks'):
        raise ValueError('AUTOMATIC_CONTEXT_ES_IDENTITY_INVALID')
    boot = current_boot_id()
    if not boot:
        raise ValueError('AUTOMATIC_CONTEXT_BOOT_ID_UNAVAILABLE')
    stamp = time.time() if now is None else now
    value = {
        'schema_version': 1, 'state': 'ACTIVE', 'phase': 'PRE_LAUNCH',
        'transaction_id': transaction_id, 'boot_id': boot,
        'certifier': certifier, 'autopilot': autopilot,
        'system': system, 'rom': _canonical_rom(rom),
        'emulationstation': es_identity,
        'created_at_epoch': stamp,
        'created_at_utc': datetime.fromtimestamp(stamp, timezone.utc).isoformat(timespec='milliseconds'),
        'invocations': [], 'closed_at_utc': None, 'close_reason': None,
    }
    with _locked(path):
        if path.exists() or path.is_symlink():
            raise FileExistsError('AUTOMATIC_SELECTOR_CONTEXT_ALREADY_EXISTS')
        _atomic_json(path, value)
    return value


def read_context(path: Path = ACTIVE_CONTEXT) -> dict | None:
    try:
        if path.is_symlink() or not path.is_file():
            return None
        value = json.loads(path.read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else None
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def set_phase(transaction_id: str, phase: str, *, path: Path = ACTIVE_CONTEXT) -> bool:
    if phase not in ('PRE_LAUNCH', 'EMULATOR_RUNNING', 'POST_EMULATOR', 'CLEANUP'):
        raise ValueError('AUTOMATIC_CONTEXT_PHASE_INVALID')
    with _locked(path):
        value = read_context(path)
        if not value or value.get('state') != 'ACTIVE' or value.get('transaction_id') != transaction_id:
            return False
        value['phase'] = phase
        value['phase_updated_at_utc'] = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        _atomic_json(path, value)
        return True


def _ancestry_reaches_es(pid: int, expected_es: dict) -> bool:
    seen = set()
    current = pid
    for _ in range(32):
        if current in seen or current <= 1:
            return False
        seen.add(current)
        record = process_identity(current)
        if not record:
            return False
        if current == expected_es.get('pid'):
            return record.get('start_ticks') == expected_es.get('start_ticks') and \
                ('emulationstation' in record.get('comm', '').lower() or
                 'emulationstation' in record.get('exe', '').lower())
        current = record['ppid']
    return False


def _live_identity_matches(expected: dict, required_fragment: str) -> bool:
    if not isinstance(expected, dict):
        return False
    live = process_identity(expected.get('pid')) if isinstance(expected.get('pid'), int) else None
    return bool(live and live.get('start_ticks') == expected.get('start_ticks') and
                required_fragment in live.get('cmdline', ''))


def authorize_invocation(*, system: str, rom: str, dispatcher_pid: int,
                         ppid: int, path: Path = ACTIVE_CONTEXT,
                         boot_id: str | None = None) -> tuple[bool, str, dict | None]:
    """Authorize and atomically audit only a transaction-linked invocation."""
    with _locked(path):
        context = read_context(path)
        if not context:
            return False, 'CONTEXT_MISSING_OR_CORRUPT', None
        if (context.get('schema_version') != 1 or context.get('state') != 'ACTIVE' or
                context.get('boot_id') != (boot_id or current_boot_id())):
            return False, 'CONTEXT_INACTIVE_OR_WRONG_BOOT', None
        if context.get('system') != system or context.get('rom') != _canonical_rom(rom):
            return False, 'SYSTEM_OR_ROM_MISMATCH', None
        if not _live_identity_matches(context.get('certifier'), 'full_game_certifier.py'):
            return False, 'CERTIFIER_IDENTITY_NOT_LIVE', None
        if context.get('autopilot'):
            owner = context['autopilot']
            if not _live_identity_matches(owner, 'arcade_autopilot.py') or owner.get('run_id') not in owner.get('cmdline', ''):
                return False, 'AUTOPILOT_IDENTITY_NOT_LIVE', None
        dispatcher = process_identity(dispatcher_pid)
        if (not dispatcher or dispatcher.get('ppid') != ppid or
                DISPATCHER not in dispatcher.get('cmdline', '') or
                not _ancestry_reaches_es(dispatcher_pid, context.get('emulationstation', {}))):
            return False, 'EMULATIONSTATION_ANCESTRY_MISMATCH', None
        invocations = context.get('invocations')
        if not isinstance(invocations, list):
            return False, 'INVOCATION_LOG_CORRUPT', None
        pre = [x for x in invocations if x.get('phase') == 'PRE_LAUNCH' and x.get('automatic_context_match') is True]
        post = [x for x in invocations if x.get('phase') == 'POST_EMULATOR' and x.get('automatic_context_match') is True]
        phase = context.get('phase')
        if phase == 'PRE_LAUNCH' and len(pre) == 0 and len(post) == 0:
            pass
        elif phase == 'POST_EMULATOR' and len(pre) == 1 and len(post) == 0:
            pass
        else:
            return False, 'TRANSACTION_PHASE_OR_INVOCATION_AMBIGUOUS', None
        invocation = {
            'selector_invocation_id': uuid.uuid4().hex,
            'transaction_id': context['transaction_id'], 'system': system,
            'rom': _canonical_rom(rom), 'pid': dispatcher_pid, 'ppid': ppid,
            'dispatcher_start_ticks': dispatcher['start_ticks'],
            'emulationstation': context['emulationstation'],
            'automatic_context_match': True, 'choice': 'JOYSTICKS PRIMERO',
            'internal_choice': 'external', 'phase': phase,
            'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
        }
        context['invocations'].append(invocation)
        _atomic_json(path, context)
        return True, 'MATCH', invocation


def claim_emulator_launch(invocation: dict | None, *, system: str, rom: str,
                          dispatcher_pid: int, ppid: int,
                          path: Path = ACTIVE_CONTEXT,
                          boot_id: str | None = None) -> tuple[str, str]:
    """Atomically allow at most one emulator launch for an automatic transaction.

    Manual launches do not carry an invocation and remain unaffected. An
    invalid or ambiguous automatic context is refused; a second, otherwise
    valid invocation of the same transaction is suppressed before configgen.
    """
    if invocation is None:
        return 'ALLOW', 'MANUAL_LAUNCH'
    with _locked(path):
        context = read_context(path)
        if not context:
            return 'REFUSE', 'AUTOMATIC_CONTEXT_MISSING_OR_CORRUPT'
        expected_boot = boot_id or current_boot_id()
        if (context.get('schema_version') != 1 or context.get('state') != 'ACTIVE' or
                not expected_boot or context.get('boot_id') != expected_boot):
            return 'REFUSE', 'AUTOMATIC_CONTEXT_INACTIVE_OR_WRONG_BOOT'
        if (context.get('transaction_id') != invocation.get('transaction_id') or
                context.get('system') != system or context.get('rom') != _canonical_rom(rom) or
                invocation.get('system') != system or invocation.get('rom') != _canonical_rom(rom) or
                invocation.get('automatic_context_match') is not True):
            return 'REFUSE', 'AUTOMATIC_CONTEXT_IDENTITY_MISMATCH'
        if not _live_identity_matches(context.get('certifier'), 'full_game_certifier.py'):
            return 'REFUSE', 'CERTIFIER_IDENTITY_NOT_LIVE'
        if context.get('autopilot'):
            owner = context['autopilot']
            if (not _live_identity_matches(owner, 'arcade_autopilot.py') or
                    owner.get('run_id') not in owner.get('cmdline', '')):
                return 'REFUSE', 'AUTOPILOT_IDENTITY_NOT_LIVE'
        es_identity = context.get('emulationstation')
        dispatcher = process_identity(dispatcher_pid)
        if (not dispatcher or dispatcher.get('ppid') != ppid or
                DISPATCHER not in dispatcher.get('cmdline', '') or
                not _ancestry_reaches_es(dispatcher_pid, es_identity or {})):
            return 'REFUSE', 'EMULATIONSTATION_ANCESTRY_MISMATCH'
        invocations = context.get('invocations')
        if not isinstance(invocations, list):
            return 'REFUSE', 'INVOCATION_LOG_CORRUPT'
        record = next((item for item in invocations
                       if item.get('selector_invocation_id') == invocation.get('selector_invocation_id')), None)
        if (not record or record.get('pid') != dispatcher_pid or record.get('ppid') != ppid or
                record.get('dispatcher_start_ticks') != dispatcher.get('start_ticks') or
                record.get('transaction_id') != context.get('transaction_id') or
                record.get('automatic_context_match') is not True):
            return 'REFUSE', 'AUTOMATIC_INVOCATION_IDENTITY_MISMATCH'

        claim = context.get('emulator_launch_claim')
        if claim is None:
            context['emulator_launch_claim'] = {
                'state': 'CLAIMED',
                'transaction_id': context['transaction_id'],
                'boot_id': context['boot_id'],
                'system': system,
                'rom': _canonical_rom(rom),
                'emulationstation': es_identity,
                'selector_invocation_id': invocation['selector_invocation_id'],
                'dispatcher': {
                    'pid': dispatcher_pid,
                    'start_ticks': dispatcher['start_ticks'],
                    'ppid': ppid,
                },
                'claimed_at_utc': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
            }
            record['emulator_launch'] = 'ALLOWED'
            record['emulator_launch_reason'] = 'FIRST_LAUNCH_FOR_TRANSACTION'
            _atomic_json(path, context)
            return 'ALLOW', 'FIRST_LAUNCH_FOR_TRANSACTION'

        expected_identity = {
            'transaction_id': context['transaction_id'],
            'boot_id': context['boot_id'],
            'system': system,
            'rom': _canonical_rom(rom),
            'emulationstation': es_identity,
        }
        if (not isinstance(claim, dict) or claim.get('state') != 'CLAIMED' or
                any(claim.get(key) != value for key, value in expected_identity.items()) or
                not isinstance(claim.get('dispatcher'), dict) or
                not isinstance(claim.get('dispatcher', {}).get('pid'), int) or
                not isinstance(claim.get('dispatcher', {}).get('start_ticks'), int) or
                claim.get('selector_invocation_id') not in {
                    item.get('selector_invocation_id') for item in invocations
                    if item.get('emulator_launch') == 'ALLOWED'
                }):
            return 'REFUSE', 'AUTOMATIC_LAUNCH_CLAIM_CORRUPT_OR_AMBIGUOUS'
        record['emulator_launch'] = 'SUPPRESSED_DUPLICATE'
        record['emulator_launch_reason'] = 'DUPLICATE_LAUNCH_FOR_TRANSACTION'
        _atomic_json(path, context)
        return 'SUPPRESS', 'DUPLICATE_LAUNCH_FOR_TRANSACTION'


def close_context(transaction_id: str, *, archive_path: Path | None = None,
                  reason: str = 'TRANSACTION_FINISHED', path: Path = ACTIVE_CONTEXT) -> dict | None:
    with _locked(path):
        context = read_context(path)
        if not context or context.get('transaction_id') != transaction_id:
            return None
        context['state'] = 'CLOSED'
        context['phase'] = 'CLOSED'
        context['closed_at_utc'] = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        context['close_reason'] = reason
        if archive_path is not None:
            _atomic_json(archive_path, context)
        path.unlink()
        return context
