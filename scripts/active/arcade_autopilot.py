#!/usr/bin/env python3
"""Deterministic, fail-closed coordinator for the Arcade Audit workflow."""
import argparse
import csv
import datetime as dt
import shutil
import hashlib
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

TOOLS = Path('/userdata/system/el_gordo_tools')
AUDIT = Path('/userdata/system/state/arcade_audit')
DATA = AUDIT / 'data'
TASKS = DATA / 'autopilot_tasks.json'
STATE = AUDIT / 'autopilot_state.json'
PIDFILE = AUDIT / 'autopilot.pid'
LOCK = AUDIT / 'autopilot.lock'
LOG = AUDIT / 'logs' / 'autopilot.log'
EVENTS = DATA / 'autopilot_events.jsonl'
CODEX_HANDOFF = AUDIT / 'CODEX_NEXT_TASK.md'
MANUAL_HANDOFF = AUDIT / 'MANUAL_NEXT_TASK.md'
CERT_JOB = TOOLS / 'arcade_certifier_job.sh'
CERTIFIER = TOOLS / 'full_game_certifier.py'
PUBLISHER = TOOLS / 'publish_arcade_audit.sh'
SUMMARY_BUILDER = TOOLS / 'rebuild_certification_summary.py'
STATE_BUILDER = TOOLS / 'rebuild_arcade_current_state.py'
CERT_STATE = AUDIT / 'full_game_certification_checkpoint.json'
CERT_CSV = AUDIT / 'full_game_certification.csv'
MASTER = AUDIT / 'arcade_master_checkpoint.json'
MARKER = Path('/userdata/system/state/boot_audit_once.json')
MAX_BATCH_SIZE = 100
DEFAULT_BATCH_SIZE = 100
DEFAULT_MAX_BATCHES = 10
POLL_SECONDS = 60
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_KEEP = 3
MIN_FREE_BYTES = 1024 * 1024 * 1024
STOP_STATES = {'WRONG_GAME_DISPATCH', 'RESTORE_FAILURE', 'AUDIO_ROUTE_CHANGED',
               'BATOCERA_CONF_CHANGE', 'P1_P4_MAPPING_CHANGE', 'DISK_IO_ERROR',
               'TRANSACTION_CORRUPTION', 'UNRECOVERABLE_ES_STATE'}
TASK_STATUSES = {'PENDING', 'READY', 'RUNNING', 'COMPLETE', 'FAILED', 'BLOCKED',
                 'CODEX_REQUIRED', 'MANUAL_REQUIRED', 'PAUSED_SAFETY', 'SKIPPED'}
AUTOPILOT_STATUSES = {'STOPPED', 'RUNNING', 'PAUSED', 'PAUSED_SAFETY', 'WAITING_CODEX',
                      'WAITING_MANUAL', 'COMPLETE', 'ERROR'}


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')


def read_json(path, fallback=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return fallback


def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name(path.name + '.tmp')
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(obj, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
        dfd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def append_event(event, **fields):
    EVENTS.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    item = {'at': now(), 'event': event, **fields}
    fd = os.open(str(EVENTS), os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.write(fd, (json.dumps(item, ensure_ascii=False, separators=(',', ':')) + '\n').encode())
        os.fsync(fd)
    finally:
        os.close(fd)


def log(message, **fields):
    LOG.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    rotate_log_if_needed()
    suffix = (' ' + json.dumps(fields, ensure_ascii=False, sort_keys=True)) if fields else ''
    with LOG.open('a', encoding='utf-8') as stream:
        stream.write(f'{now()} {message}{suffix}\n')
        stream.flush()
        os.fsync(stream.fileno())


def rotate_log_if_needed():
    if not LOG.exists() or LOG.stat().st_size < LOG_MAX_BYTES:
        return
    oldest = LOG.with_name(LOG.name + f'.{LOG_KEEP}')
    try:
        oldest.unlink()
    except FileNotFoundError:
        pass
    for n in range(LOG_KEEP - 1, 0, -1):
        src = LOG.with_name(LOG.name + f'.{n}')
        if src.exists():
            os.replace(src, LOG.with_name(LOG.name + f'.{n + 1}'))
    os.replace(LOG, LOG.with_name(LOG.name + '.1'))


def task(task_id, kind, title, status, priority, *, source='ARCADE_MASTER', reason='',
         automatic=False, codex=False, manual=False, depends=(), attempts=0, max_attempts=3,
         next_action='', evidence=(), files=(), do_not_change=(), success='', after=''):
    stamp = now()
    return {
        'id': task_id, 'type': kind, 'title': title, 'status': status, 'priority': priority,
        'created_at': stamp, 'updated_at': stamp, 'source': source, 'reason': reason,
        'automatic': bool(automatic), 'requires_codex': bool(codex), 'requires_manual': bool(manual),
        'depends_on': list(depends), 'attempts': attempts, 'max_attempts': max_attempts,
        'last_error': None, 'next_action': next_action, 'evidence': list(evidence),
        'files': list(files), 'do_not_change': list(do_not_change),
        'success_criteria': success, 'after_completion': after,
    }


def seed_tasks(checkpoint=None, master=None):
    cp = checkpoint or {}
    latest = cp.get('batch_in_progress') or cp.get('latest_batch') or {}
    batch_name = latest.get('name', 'priority_batch_10')
    match = re.search(r'(\d+)$', batch_name)
    batch_no = int(match.group(1)) if match else 11
    batch_id = f'CERT-BATCH-{batch_no:04d}'
    blocked = cp.get('status') != 'COMPLETE' or bool(cp.get('blocked_reason')) or bool(cp.get('engine_fail_active'))
    batch_status = 'PAUSED_SAFETY' if blocked else 'READY'
    out = [task(
        batch_id, 'CERTIFICATION_BATCH', f'Continuar {batch_name}', batch_status, 10,
        source='full_game_certification_checkpoint.json',
        reason=cp.get('blocked_reason') or 'Siguiente batch de la queue vigente.',
        automatic=True, next_action='Resolver bloqueo de seguridad y reconciliar checkpoint antes de llamar al job runner.',
        evidence=[str(CERT_STATE), str(CERT_CSV)],
        files=[str(CERT_STATE), str(CERT_CSV), str(CERT_JOB)],
        do_not_change=['Resultados históricos', 'MAME global', 'overrides', 'P1-P4', 'ROM/BIOS'],
        success='Batch limitado completado, restore verificado por juego y fuentes locales reconciliadas.',
        after='Rebuild summary/current state, publicar y recalcular NEXT_GAME.'
    )]
    out.append(task(
        'REPAIR-CERTIFIER-MARKER-COLLISION', 'REPAIR_CODEX', 'Resolver colisión del marker de certificación',
        'CODEX_REQUIRED', 1, source='CERT-007',
        reason='Un marker ausente en PRE_STATE apareció en POST_STATE; el contenido/escritor no se preservó ni identificó.',
        codex=True, next_action='Investigar todos los escritores del marker e implementar exclusión mutua/abort seguro con prueba aislada sin juego.',
        evidence=['arcade_master_checkpoint.json: CERT-007', 'reports/PRIORITY_CERTIFICATION_BATCH_11.md',
                  'runtime/20261116T232721_823ec5e49e/manifest.json'],
        files=[str(CERTIFIER), '/userdata/system/state/arcade_audit/scripts/active/certification_transaction.py'],
        do_not_change=['No relanzar xmultipl', 'No reintentar Batch 11', 'No eliminar marker ajeno',
                       'No cambiar controles ni configuración global'],
        success='Writer identificado o exclusión mutua demostrada; abort no modifica marker ajeno; runtime y transaction pasan prueba aislada.',
        after='Reconciliar el registro pre-launch sin borrar evidencia y habilitar sólo el cursor elegible siguiente.'
    ))
    out.extend([
        task('REGRESSION-HEALTH-001', 'REGRESSION_CHECK', 'Health review antes de modificar runtime',
             'READY', 8, automatic=True,
             reason='Validar configuración, runtime, disco y reconciliación antes de certificar.',
             next_action='Ejecutar comprobaciones read-only; cualquier discrepancia pausa la cola.',
             evidence=['checkpoint', 'batocera.conf', 'P1-P4', 'HDMI', 'EmulationStation'],
             success='Safety gates PASS sin mutaciones.'),
        task('CHECKPOINT-RECONCILIATION-0011', 'CHECKPOINT_RECONCILIATION', 'Verificar reconciliación Batch 11 parcial',
             'COMPLETE', 15, source='local CSV/checkpoint/master/summary', automatic=True,
             reason='Los agregados locales y GitHub reflejan 919 transacciones; el lote queda bloqueado por ENGINE_FAIL activo.',
             next_action='Repetir únicamente lectura de invariantes al reanudar; no reconstruir ni sobreescribir evidencia.',
             evidence=['full_game_certification.csv', 'full_game_certification_checkpoint.json',
                       'arcade_master_checkpoint.json', 'FULL_GAME_CERTIFICATION_SUMMARY.md'],
             success='Métricas, records, cursor y CSV concuerdan sin cambiar resultados.'),
        task('REPORT-REBUILD-0011', 'REPORT_REBUILD', 'Regenerar reportes derivados tras la pausa',
             'COMPLETE', 16, automatic=True, reason='Summary y ARCADE_CURRENT_STATE reflejan estado bloqueado actual.',
             evidence=['FULL_GAME_CERTIFICATION_SUMMARY.md', 'ARCADE_CURRENT_STATE.md'],
             next_action='Regenerar tras cada batch estable.'),
        task('GITHUB-PUBLISH-AUTOPILOT', 'GITHUB_PUBLISH', 'Publicar Autopilot después de validación',
             'PENDING', 30, automatic=True, reason='Los nuevos archivos no están aún en el HEAD remoto verificado.',
             next_action='Ejecutar secret/payload scan y publisher existente; respetar límites y manifests exactos.',
             evidence=['github_publish_state.json', 'publisher dry-run pendiente'],
             files=[str(TOOLS / 'publish_arcade_audit_github.py')],
             do_not_change=['No incluir tokens', 'No saltar SECRET_SCAN/PAYLOAD_SCAN', 'No usar autorización one-time amplia'],
             success='Remote SHA nuevo verificado y export exacto coincide.'),
        task('VISUAL-BLACK-CAPTURE', 'VISUAL_DIAGNOSTIC', 'Investigar sospechas de captura negra',
             'CODEX_REQUIRED', 40, source='CERT-004', reason='19 casos BLACK_SCREEN_SUSPECT; el mecanismo de captura puede no representar salida visible.',
             codex=True, next_action='Correlacionar captura con proceso, framebuffer/backend y evidencia independiente; agrupar casos.',
             evidence=['arcade_master_checkpoint.json: CERT-004', 'reports/ROOT_CAUSES.md'],
             files=['full_game_certification_checkpoint.json', 'reports/ARCADE_VISUAL_MEDIA_AUDIT.md'],
             do_not_change=['No marcar BLACK_SCREEN_SUSPECT como GAME_FAIL automáticamente', 'No relanzar juegos masivamente'],
             success='Explicación aceptada, backend identificado o tarea manual de TV documentada.'),
        task('REPAIR-MVP', 'REPAIR_CODEX', 'Diagnosticar SIGSEGV aislado de Mvp',
             'CODEX_REQUIRED', 50, source='CERT-002', reason='SIGSEGV histórico aislado con transacción restaurada; requiere análisis antes de cualquier retest.',
             codex=True, next_action='Analizar logs/runtime y decidir si existe retry seguro basado en causa demostrada.',
             evidence=['game_repair_queue.csv: mame/mvp.zip'],
             files=['full_game_certification_checkpoint.json', 'reports/ROOT_CAUSES.md'],
             do_not_change=['No cambiar core global', 'No probar masivamente', 'No tocar ROM/BIOS'],
             success='Causa raíz o estado de reparación documentado con evidencia.'),
        task('REPAIR-CONTENT-ROOTS', 'REPAIR_CODEX', 'Resolver contenido/BIOS faltante por causas raíz',
             'CODEX_REQUIRED', 55, source='CERT-003/CERT-005', reason='CRC/BIOS/CHD faltantes requieren verificación de contenido apropiado; no se permiten descargas ni edición a ciegas.',
             codex=True, next_action='Verificar inventarios y documentación legal del set/BIOS; nunca modificar ZIP automáticamente.',
             evidence=['game_repair_queue.csv', 'arcade_issues.csv: CERT-003/CERT-005'],
             do_not_change=['No descargar ROM comercial', 'No editar ZIP', 'No sustituir BIOS arbitrariamente'],
             success='Contenido validado por evidencia y retest explícitamente autorizado.'),
    ])
    manual_count = 0
    manual_sample = {}
    manual_csv = AUDIT / 'manual_physical_test_queue.csv'
    if manual_csv.is_file():
        try:
            with manual_csv.open(encoding='utf-8-sig', newline='') as f:
                pending = [r for r in csv.DictReader(f) if r.get('status') == 'MANUAL_REQUIRED']
                manual_count = len(pending)
                manual_sample = pending[0] if pending else {}
        except OSError:
            pass
    out.extend([
        task('CTRL-REPRESENTATIVE-SAMPLE', 'CONTROL_PHYSICAL', 'Certificar muestra física representativa de controles',
             'MANUAL_REQUIRED', 70, source='manual_physical_test_queue.csv', reason=f'{manual_count} secuencias físicas siguen pendientes; no inferir control desde AUTO_PASS.',
             manual=True, next_action='Probar muestra acordada: P1/P2 fighter, MAME 4P, beat-em-up, deporte y joystick externo.',
             evidence=['manual_physical_test_queue.csv', 'reports/ARCADE_CONTROL_CERTIFICATION.md'],
             files=['manual_physical_test_queue.csv'],
             do_not_change=['No remapear P1-P4 durante la prueba', 'No declarar juegos físicos certificados sin observación'],
             success='Resultados humanos registrados por secuencia y controles/restore sin regresión.'),
        task('ADAPTER-IMPLEMENTATION', 'ADAPTER_IMPLEMENTATION', 'Implementar adapters para sistemas pendientes',
             'CODEX_REQUIRED', 80, source='detected_systems.csv', reason='El registry actual tiene sistemas PENDING; consultar el registry al seleccionar, no fijar el total histórico.',
             codex=True, next_action='Priorizar el primer adapter PENDING entre PS2, Dreamcast, PSP, N64, PSX, GameCube, Saturn, Mega CD, Xbox y Xbox360 según registry actual.',
             evidence=['data/detected_systems.csv', 'data/certifier_adapter_registry.csv'],
             files=['certifier_adapters.py', 'full_game_certifier.py'],
             do_not_change=['Mantener identidad/audio/restore/ES/disk/transaction gates', 'No modificar core global ni controles'],
             success='Adapter implementado, transaccional, auditado y habilitado sólo después de prueba focalizada.'),
        task('MEDIA-AUDIT-REFRESH', 'MEDIA_AUDIT', 'Actualizar auditoría de media sólo lectura',
             'COMPLETE', 90, automatic=True, reason='Existe media_audit.csv con verificación de referencias; no descargar en lote durante certificación.',
             evidence=['media_audit.csv', 'reports/ARCADE_VISUAL_MEDIA_AUDIT.md'],
             next_action='Refrescar sólo en ventana sin conflicto de recursos.'),
        task('FILESYSTEM-CANDIDATES', 'FILESYSTEM_CLEANUP', 'Inventariar candidatos de cleanup sin borrar',
             'BLOCKED', 95, source='filesystem audit', reason='Primera versión permite detectar/documentar; no autoriza borrar backups ni datos de usuario.',
             automatic=False, next_action='Generar candidatos con referencias, mount, tamaño y clasificación; cualquier borrado requiere revisión humana.',
             evidence=['reports/FILESYSTEM_MASTER_AUDIT.md', 'data/filesystem_cleanup_inventory.csv'],
             do_not_change=['No borrar ROMs/BIOS/saves/config/backups', 'No usar rm -rf'],
             success='Inventario read-only reconciliado y candidatos explícitamente clasificados.'),
        task('REPAIR-AUTO-RECIPE-QUEUE', 'REPAIR_AUTOMATIC', 'Evaluar recetas de reparación previamente aprobadas',
             'BLOCKED', 60, automatic=False, source='game_repair_queue.csv',
             reason='No hay receta automática revisada habilitada en la primera versión.',
             next_action='Registrar receta explícita retry-safe antes de habilitar esta tarea.',
             evidence=['game_repair_queue.csv', 'ROOT_CAUSES.md'],
             do_not_change=['No ROM/BIOS/CHD, core global, P1-P4 ni paquetes'],
             success='Sólo reparación permitida por receta auditada y retest explícito.'),
        task('GUEST_READY_BUILD', 'GUEST_READY_BUILD', 'Diseñar promoción Guest Mode basada en evidencia física',
             'BLOCKED', 100, source='control certification', reason='CONTROL_CERTIFIED=0; no promover juegos automáticamente.',
             depends=['CTRL-REPRESENTATIVE-SAMPLE'], automatic=False, codex=True,
             next_action='Esperar estrategia y muestra representativa de controles suficiente.',
             evidence=['reports/ARCADE_GUEST_READY_STATUS.md', 'reports/ARCADE_CONTROL_CERTIFICATION.md'],
             success='Reglas de elegibilidad inequívocas y sin promoción automática fuera de política.'),
    ])
    manual_task = next(x for x in out if x['id'] == 'CTRL-REPRESENTATIVE-SAMPLE')
    manual_task['manual_test'] = {key: manual_sample.get(key) for key in
                                  ('test_id', 'name', 'system', 'rom', 'test_goal')}
    pending_adapters = []
    systems_csv = DATA / 'detected_systems.csv'
    if systems_csv.is_file():
        try:
            with systems_csv.open(encoding='utf-8-sig', newline='') as f:
                pending_adapters = [r.get('system') for r in csv.DictReader(f)
                                    if r.get('adapter_status', '').upper() == 'PENDING']
        except OSError:
            pass
    adapter_task = next(x for x in out if x['id'] == 'ADAPTER-IMPLEMENTATION')
    adapter_task['evidence'].append('PENDING systems: ' + ', '.join(x for x in pending_adapters if x))
    return out


def load_tasks(create=False):
    obj = read_json(TASKS)
    if obj is None:
        if not create:
            cp = read_json(CERT_STATE, {}) or {}
            master = read_json(MASTER, {}) or {}
            return {'schema_version': 1, 'updated_at': now(), 'tasks': seed_tasks(cp, master)}
        cp = read_json(CERT_STATE, {}) or {}
        master = read_json(MASTER, {}) or {}
        obj = {'schema_version': 1, 'updated_at': now(), 'tasks': seed_tasks(cp, master)}
        atomic_json(TASKS, obj)
        write_handoffs(obj['tasks'])
    if not isinstance(obj, dict) or obj.get('schema_version') != 1 or not isinstance(obj.get('tasks'), list):
        raise RuntimeError('TASK_QUEUE_SCHEMA_INVALID')
    for item in obj['tasks']:
        if item.get('status') not in TASK_STATUSES:
            raise RuntimeError('TASK_STATUS_INVALID:' + str(item.get('id')))
    if create:
        known = {item.get('id') for item in obj['tasks']}
        cp = read_json(CERT_STATE, {}) or {}
        master = read_json(MASTER, {}) or {}
        new_items = [item for item in seed_tasks(cp, master) if item['id'] not in known]
        if new_items:
            obj['tasks'].extend(new_items)
            save_tasks(obj)
            write_handoffs(obj['tasks'])
    return obj


def save_tasks(obj):
    obj['updated_at'] = now()
    for item in obj['tasks']:
        item['updated_at'] = item.get('updated_at') or obj['updated_at']
    atomic_json(TASKS, obj)


def dependency_state(item, by_id):
    return all(dep in by_id and by_id[dep].get('status') == 'COMPLETE' for dep in item.get('depends_on', []))


def task_is_automatic_ready(item, by_id):
    retry_after = item.get('retry_after')
    if retry_after:
        try:
            if dt.datetime.fromisoformat(retry_after).timestamp() > time.time():
                return False
        except ValueError:
            return False
    return (item.get('automatic') is True and not item.get('requires_codex') and
            not item.get('requires_manual') and item.get('status') in ('PENDING', 'READY') and
            dependency_state(item, by_id) and int(item.get('attempts', 0)) < int(item.get('max_attempts', 1)))


def select_task(tasks):
    by_id = {x['id']: x for x in tasks}
    available = [x for x in tasks if task_is_automatic_ready(x, by_id)]
    return min(available, key=lambda x: (int(x.get('priority', 999)), x['id'])) if available else None


def pending_handoffs(tasks):
    by_id = {x['id']: x for x in tasks}
    codex = [x for x in tasks if x.get('requires_codex') and x.get('status') == 'CODEX_REQUIRED' and dependency_state(x, by_id)]
    manual = [x for x in tasks if x.get('requires_manual') and x.get('status') == 'MANUAL_REQUIRED' and dependency_state(x, by_id)]
    codex.sort(key=lambda x: (x['priority'], x['id']))
    manual.sort(key=lambda x: (x['priority'], x['id']))
    return codex, manual


def write_handoffs(tasks):
    codex, manual = pending_handoffs(tasks)
    if codex:
        t = codex[0]
        body = (f"# Próxima tarea requerida por Codex\n\nTASK: {t['id']} — {t['title']}\n\n"
                f"WHY:\n{t['reason']}\n\nEVIDENCE:\n" + '\n'.join(f'- {x}' for x in t.get('evidence', [])) +
                "\n\nFILES:\n" + '\n'.join(f'- {x}' for x in t.get('files', [])) +
                "\n\nDO NOT CHANGE:\n" + '\n'.join(f'- {x}' for x in t.get('do_not_change', [])) +
                f"\n\nSUCCESS CRITERIA:\n{t.get('success_criteria','')}\n\nAFTER COMPLETION:\n{t.get('after_completion','') }\n")
        atomic_text(CODEX_HANDOFF, body)
    else:
        atomic_text(CODEX_HANDOFF, '# No hay tarea CODEX_REQUIRED disponible.\n')
    if manual:
        t = manual[0]
        details = t.get('manual_test', {})
        body = (f"# Próxima tarea física\n\nTASK: {t['id']} — {t['title']}\n\nTEST:\n"
                f"{details.get('name', 'Muestra representativa de controles')}\n\n"
                f"GAME: {details.get('system', 'mame')}:{details.get('rom', 'seleccionado en la cola física')}\n\n"
                f"PRESS:\n{details.get('test_goal', t['next_action'])}\n\n"
                f"WHY:\n{t['reason']}\n\nSTEPS:\n{t['next_action']}\n\nEVIDENCE:\n" +
                '\n'.join(f'- {x}' for x in t.get('evidence', [])) +
                "\n\nDO NOT CHANGE:\n" + '\n'.join(f'- {x}' for x in t.get('do_not_change', [])) +
                f"\n\nEXPECTED:\n{t.get('success_criteria','')}\n")
        atomic_text(MANUAL_HANDOFF, body)
    else:
        atomic_text(MANUAL_HANDOFF, '# No hay tarea MANUAL_REQUIRED disponible.\n')


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name(path.name + '.tmp')
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        dfd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def proc_record(pid):
    try:
        p = Path(f'/proc/{pid}')
        cmd = p.joinpath('cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
        stat = p.joinpath('stat').read_text().rsplit(')', 1)[1].split()
        return {'cmdline': cmd, 'ppid': int(stat[1]), 'pgid': int(stat[2]), 'sid': int(stat[3]),
                'start_ticks': int(stat[19])}
    except (OSError, ValueError, IndexError):
        return None


def is_autopilot_process(pid, expected_ticks=None):
    rec = proc_record(pid)
    return bool(rec and str(Path(__file__).resolve()) in rec['cmdline'] and '--worker' in rec['cmdline'] and
                (expected_ticks is None or rec['start_ticks'] == expected_ticks))


def find_autopilot_process():
    state = read_json(STATE, {}) or {}
    pid = state.get('pid')
    if isinstance(pid, int) and is_autopilot_process(pid, state.get('process_start_ticks')):
        return pid, proc_record(pid)
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        rec = proc_record(int(entry.name))
        if rec and str(Path(__file__).resolve()) in rec['cmdline'] and '--worker' in rec['cmdline']:
            return int(entry.name), rec
    return None, None


def certifier_active():
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        rec = proc_record(int(entry.name))
        if not rec or str(CERTIFIER) not in rec['cmdline']:
            continue
        try:
            executable = Path(f'/proc/{entry.name}/exe').resolve().name
        except OSError:
            continue
        argv = rec['cmdline'].split()
        if executable.startswith('python') and str(CERTIFIER) in argv[1:]:
            return int(entry.name), rec
    return None, None


def current_global_overrides():
    conf = Path('/userdata/system/batocera.conf')
    try:
        raw = conf.read_text(encoding='utf-8', errors='replace')
    except OSError as exc:
        raise RuntimeError('BATOCERA_CONF_UNREADABLE') from exc
    # Batocera's effective global MAME core is selected in EmulationStation's
    # active system definition; per-game overrides live in batocera.conf.
    systems_xml = Path('/userdata/system/configs/emulationstation/es_systems_el_gordo.cfg')
    try:
        root = ET.parse(systems_xml).getroot()
        mame = next((item for item in root.findall('.//system')
                     if (item.findtext('name') or '').strip().lower() == 'mame'), None)
        libretro = next((item for item in mame.findall('./emulators/emulator')
                         if item.get('name') == 'libretro'), None) if mame is not None else None
        cores = libretro.findall('./cores/core') if libretro is not None else []
        selected = next((item for item in cores if item.get('default', '').lower() == 'true'),
                        cores[0] if cores else None)
        global_core = (selected.text or '').strip() if selected is not None else None
    except (OSError, ET.ParseError) as exc:
        raise RuntimeError('MAME_SYSTEM_CONFIG_UNREADABLE') from exc
    if not global_core:
        raise RuntimeError('MAME_GLOBAL_CORE_UNAVAILABLE')
    overrides = set()
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        match = re.match(r'^\+?mame\["([^"]+)"\]\.core=', stripped)
        if match:
            overrides.add(match.group(1))
    return global_core, len(overrides)


PROTECTED_CONF_KEYS = {
    'global.videooutput', 'global.videomode', 'audio.device', 'audio.driver',
    'audio.mode', 'audio.output'
}
CRITICAL_KEY_HINTS = ('video', 'audio', 'mame', 'core', 'emulator', 'controller',
                      'launcher', 'dispatcher', 'retroarch', 'input', 'player', 'p1', 'p2', 'p3', 'p4')


def parse_batocera_config(path):
    values = {}
    for raw in Path(path).read_text(encoding='utf-8', errors='replace').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip()
    return values


def is_protected_config_key(key):
    low = key.lower()
    return (low in PROTECTED_CONF_KEYS or low.startswith('mame.') or
            bool(re.fullmatch(r'mame\["[^"]+"\]\.core', low)) or
            bool(re.search(r'(^|[.\[])controllers?(?:[.\[]|$)', low)) or
            any(term in low for term in ('controller', 'launcher', 'dispatcher')))


def is_unknown_critical_config_key(key):
    low = key.lower()
    return any(hint in low for hint in CRITICAL_KEY_HINTS) and not is_protected_config_key(key) and low != 'audio.volume'


def protected_config_snapshot(path, global_mame_core=None, mame_override_count=None):
    values = parse_batocera_config(path)
    protected = {key: value for key, value in values.items() if is_protected_config_key(key)}
    if global_mame_core is not None:
        protected['@runtime.global_mame_core'] = global_mame_core
    if mame_override_count is not None:
        protected['@runtime.mame_override_count'] = int(mame_override_count)
    canonical = json.dumps(protected, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return {'keys': protected, 'fingerprint': hashlib.sha256(canonical).hexdigest()}


def compare_protected_config(expected_path, actual_path, expected_sha256=None):
    expected_file = Path(expected_path)
    actual_file = Path(actual_path)
    if not expected_file.is_file() or not actual_file.is_file():
        return {'matches': False, 'reason': 'CONFIG_FILE_MISSING'}
    if expected_sha256 and hashlib.sha256(expected_file.read_bytes()).hexdigest() != expected_sha256:
        return {'matches': False, 'reason': 'EXPECTED_CONFIG_BASELINE_UNAVAILABLE'}
    old, new = parse_batocera_config(expected_file), parse_batocera_config(actual_file)
    changed = {key for key in old.keys() | new.keys() if old.get(key) != new.get(key)}
    unknown = sorted(key for key in changed if is_unknown_critical_config_key(key))
    old_sem = protected_config_snapshot(expected_file)
    new_sem = protected_config_snapshot(actual_file)
    return {'matches': not unknown and old_sem['keys'] == new_sem['keys'],
            'expected_fingerprint': old_sem['fingerprint'],
            'actual_fingerprint': new_sem['fingerprint'],
            'unknown_critical_keys': unknown,
            'changed_protected_keys': sorted(key for key in changed if is_protected_config_key(key)),
            'whole_file_sha_changed': hashlib.sha256(expected_file.read_bytes()).hexdigest() !=
                                      hashlib.sha256(actual_file.read_bytes()).hexdigest()}


def disk_health():
    paths = ['/userdata', '/media/ROMS', '/media/BATOCERA_ROMS']
    records = []
    for raw in paths:
        p = Path(raw)
        if not p.exists() or not p.is_dir():
            return False, 'DISK_MOUNT_UNAVAILABLE:' + raw, records
        try:
            fs = os.statvfs(p)
        except OSError as exc:
            return False, 'DISK_IO_ERROR:' + raw + ':' + type(exc).__name__, records
        total = fs.f_blocks * fs.f_frsize
        free = fs.f_bavail * fs.f_frsize
        used_pct = int(100 * (total - free) / total) if total else 100
        records.append({'path': raw, 'free_bytes': free, 'used_percent': used_pct})
        if free < MIN_FREE_BYTES or used_pct >= 98:
            return False, 'DISK_SPACE_CRITICAL:' + raw, records
    return True, None, records


def max_temperature_c():
    found = []
    for p in Path('/sys/class/thermal').glob('thermal_zone*/temp'):
        try:
            value = int(p.read_text().strip())
            if value > 0:
                found.append(value / 1000.0 if value > 1000 else float(value))
        except (OSError, ValueError):
            pass
    return max(found) if found else None


def health_check(*, include_checkpoint=True, allow_self=False, allow_certifier_pid=None):
    checks = {'certifier_conflict': None, 'autopilot_conflict': None,
              'checkpoint': None, 'runtime': None, 'disk': None, 'marker': None,
              'temperature_c': max_temperature_c()}
    cert_pid, _ = certifier_active()
    checks['certifier_conflict'] = cert_pid if cert_pid != allow_certifier_pid else None
    own_pid, _ = find_autopilot_process()
    checks['autopilot_conflict'] = own_pid if own_pid and (not allow_self or own_pid != os.getpid()) else None
    if cert_pid and cert_pid != allow_certifier_pid:
        return False, 'UNEXPECTED_CONCURRENT_CERTIFIER', checks
    if checks['autopilot_conflict']:
        return False, 'UNEXPECTED_CONCURRENT_AUTOPILOT', checks
    ok, disk_reason, disk = disk_health()
    checks['disk'] = disk
    if not ok:
        return False, disk_reason, checks
    if checks['temperature_c'] is not None and checks['temperature_c'] >= 90:
        return False, 'TEMPERATURE_CRITICAL', checks
    if MARKER.exists():
        try:
            from marker_ownership import classify_marker, read_marker
            marker = read_marker(MARKER)
            checks['marker'] = {'exists': True, 'ownership': classify_marker(marker),
                                'owner': marker.get('owner') if marker else None,
                                'transaction_id': marker.get('transaction_id') if marker else None}
        except Exception:
            checks['marker'] = {'exists': True, 'ownership': 'FOREIGN_UNKNOWN'}
        return False, 'MARKER_FOREIGN_UNKNOWN', checks
    checks['marker'] = {'exists': False, 'ownership': None}
    if include_checkpoint:
        cp = read_json(CERT_STATE, {}) or {}
        checks['checkpoint'] = {k: cp.get(k) for k in ('status', 'blocked_reason', 'engine_fail_active', 'next_untested')}
        safe_resume = (cp.get('status') == 'STOPPED_SAFE' and not cp.get('blocked_reason') and
                       isinstance(cp.get('batch_in_progress'), dict))
        clean_complete = (cp.get('status') == 'COMPLETE' and not cp.get('blocked_reason') and
                          not cp.get('batch_in_progress'))
        if not (clean_complete or safe_resume) or int(cp.get('engine_fail_active', 0)):
            return False, 'CHECKPOINT_SAFETY_BLOCK:' + str(cp.get('status')) + ':' + str(cp.get('blocked_reason')), checks
        try:
            sys.path.insert(0, str(TOOLS))
            import full_game_certifier as cert
            rows, _ = cert.load_rows()
            systems = cert.ad.live_systems()
            cert.assert_reconciled_queue(rows, cp, systems)
            baseline = cert.safety_baseline()
            checks['runtime'] = {'ES_API': 'PASS', 'HDMI': baseline.get('audio_default'),
                                 'P1_P4': baseline.get('p1_p4'),
                                 'batocera_conf_sha256': baseline.get('batocera_conf_sha256')}
            core, count = current_global_overrides()
            checks['runtime']['MAME_GLOBAL_CORE'] = core
            checks['runtime']['MAME_OVERRIDES_COUNT'] = count
            if core != 'mame078plus' or count != 18:
                return False, 'PROTECTED_MAME_CONFIG_CHANGE', checks
        except Exception as exc:
            detail = str(exc).splitlines()[0][:180]
            return False, 'RUNTIME_HEALTH_FAIL:' + type(exc).__name__ + ':' + detail, checks
    return True, None, checks


RECOVERABLE_SAFETY_BLOCKERS = {'ES_NOT_IDLE', 'ES_IDLE_TIMEOUT', 'SELECTOR_NOT_CLOSED'}
POST_REBOOT_GAME = 'megacd:/userdata/roms/megacd/Final Fight CD (USA).chd'
POST_REBOOT_TX = '20261118T161913_0b1c456071'
POST_REBOOT_FAILED_JOB = '20261118T161901_df534fc7'
BATCH68_GAME = 'prboom:/userdata/roms/prboom/doom1_shareware.wad'
BATCH68_TX = '20261119T143935_d7d3a63e70'
BATCH68_RETRY_TX = '20261120T213050_7ed567f0ef'
BATCH69_GAME = 'mrboom:/userdata/roms/mrboom/MrBoom.libretro'
BATCH69_TX = '20261120T233918_99d5ee09e8'
BATCH69_JOB_ID = '20261120T233915_f921510e'


def current_boot_id():
    try:
        return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    except OSError:
        return None


def pid_matches_boot(pid, record_boot_id=None):
    """A stored PID is not evidence of a live process across a reboot."""
    boot_id = current_boot_id()
    if not isinstance(pid, int) or not boot_id:
        return False
    if record_boot_id and record_boot_id != boot_id:
        return False
    return proc_record(pid) is not None


def recovered_runtime_evidence(cp):
    """Collect fresh gates needed to reconcile only known post-ES blockers."""
    evidence = {'current_boot_id': current_boot_id(), 'checks': {}, 'passed': False}
    try:
        if not evidence['current_boot_id']:
            raise RuntimeError('BOOT_ID_UNAVAILABLE')
        job = read_json(AUDIT / 'jobs' / 'certifier_job.json', {}) or {}
        evidence['checks']['historical_failed_job_preserved'] = bool(
            job.get('job_id') == POST_REBOOT_FAILED_JOB and job.get('status') == 'FAILED')
        if not evidence['checks']['historical_failed_job_preserved']:
            raise RuntimeError('HISTORICAL_FAILED_JOB_MISMATCH')
        evidence['previous_boot_id'] = job.get('boot_id')
        evidence['certifier_pid'] = job.get('pid')
        evidence['certifier_pid_alive_this_boot'] = pid_matches_boot(
            job.get('pid'), job.get('boot_id'))
        if evidence['certifier_pid_alive_this_boot']:
            rec = proc_record(job['pid'])
            if rec and str(CERTIFIER) in rec.get('cmdline', ''):
                raise RuntimeError('CERTIFIER_STILL_ACTIVE')

        cp_status = cp.get('status')
        evidence['checks']['no_engine_fail'] = int(cp.get('engine_fail_active', 0)) == 0
        if not evidence['checks']['no_engine_fail']:
            raise RuntimeError('ENGINE_FAIL_ACTIVE')
        evidence['checks']['marker_absent'] = not MARKER.exists()
        if not evidence['checks']['marker_absent']:
            raise RuntimeError('MARKER_FOREIGN_UNKNOWN')

        sys.path.insert(0, str(TOOLS))
        import full_game_certifier as cert
        active = cert.pids()
        evidence['launch_processes'] = active
        evidence['checks']['launch_processes_absent'] = not active
        if active:
            raise RuntimeError('LAUNCH_PROCESS_ACTIVE')
        evidence['checks']['no_active_certifier'] = certifier_active()[0] is None
        if not evidence['checks']['no_active_certifier']:
            raise RuntimeError('CERTIFIER_STILL_ACTIVE')
        idle_observation = cert.wait_for_es_idle()
        evidence['es'] = idle_observation
        evidence['checks']['es_idle'] = idle_observation.get('isIdle') is True
        evidence['checks']['running_game_none'] = idle_observation.get('runningGame') is None
        if not evidence['checks']['es_idle']:
            raise RuntimeError('ES_NOT_IDLE')
        if not evidence['checks']['running_game_none']:
            raise RuntimeError('RUNNING_GAME_ACTIVE')

        before = next((x for x in cp.get('results', [])
                       if x.get('transaction_id') == POST_REBOOT_TX and
                       x.get('system') == 'fds' and
                       x.get('rom') == '/userdata/roms/fds/Super Mario Brothers (ESP).fds'), None)
        txdir = AUDIT / 'runtime' / POST_REBOOT_TX
        manifest = read_json(txdir / 'manifest.json', {}) or {}
        result = read_json(txdir / 'result.json', {}) or {}
        evidence['last_restored_transaction'] = POST_REBOOT_TX
        evidence['checks']['last_result_restore_verified'] = bool(
            before and before.get('result') == 'AUTO_PASS' and
            before.get('restore', {}).get('status') == 'RESTORE_VERIFIED' and
            before.get('restore', {}).get('transaction_id') == POST_REBOOT_TX)
        evidence['checks']['manifest_restore_verified'] = bool(
            manifest.get('transaction_id') == POST_REBOOT_TX and
            manifest.get('status') == 'RESTORE_VERIFIED')
        if not evidence['checks']['last_result_restore_verified'] or not evidence['checks']['manifest_restore_verified']:
            raise RuntimeError('LAST_TRANSACTION_NOT_RESTORE_VERIFIED')

        core, override_count = current_global_overrides()
        baseline = {
            'batocera_conf_sha256': hashlib.sha256(
                Path('/userdata/system/batocera.conf').read_bytes()).hexdigest(),
            'protected_config_fingerprint': protected_config_snapshot(
                '/userdata/system/batocera.conf', core, override_count)['fingerprint'],
            'global_mame_core': core,
            'mame_overrides_count': override_count,
            'p1_p4': cert.profile_state(),
            'audio_default': cert.get_default_sink(),
            'dispatcher_sha256': hashlib.sha256(Path(str(TOOLS / 'controller_dispatcher')).read_bytes()).hexdigest(),
            'profile_sha256': hashlib.sha256(Path('/userdata/system/configs/el_gordo_controller_profiles/controller_technical.json').read_bytes()).hexdigest(),
            'multiplayer_sha256': hashlib.sha256(Path('/userdata/system/configs/el_gordo_controller_profiles/multiplayer.json').read_bytes()).hexdigest(),
        }
        evidence['runtime_baseline'] = baseline
        tx_baseline = result.get('safety_before') or {}
        stable_mapping_ok = cert.stable_profile_matches(baseline['p1_p4'])
        evidence['checks']['logical_p1_p4_stable_identity'] = stable_mapping_ok
        if not stable_mapping_ok:
            raise RuntimeError('P1_P4_MAPPING_CHANGE')
        config_reference = AUDIT / 'certification_runtime' / 'batocera.conf.current'
        config_comparison = compare_protected_config(
            config_reference, '/userdata/system/batocera.conf',
            expected_sha256=tx_baseline.get('batocera_conf_sha256'))
        expected_fingerprint = protected_config_snapshot(
            config_reference, tx_baseline.get('global_mame_core'), 18)['fingerprint']
        actual_fingerprint = protected_config_snapshot(
            '/userdata/system/batocera.conf', core, override_count)['fingerprint']
        config_comparison['expected_fingerprint'] = expected_fingerprint
        config_comparison['actual_fingerprint'] = actual_fingerprint
        config_comparison['matches'] = (config_comparison.get('matches') is True and
                                        expected_fingerprint == actual_fingerprint)
        evidence['protected_config_semantic'] = config_comparison
        evidence['checks']['protected_semantic_config_matches'] = config_comparison.get('matches') is True
        evidence['protected_config'] = {
            key: {'expected': tx_baseline.get(key), 'actual': baseline.get(key),
                  'matches': tx_baseline.get(key) == baseline.get(key)}
            for key in ('global_mame_core', 'audio_default', 'dispatcher_sha256',
                        'profile_sha256', 'multiplayer_sha256')
        }
        evidence['checks']['protected_config_matches'] = all(
            item['expected'] is not None and item['matches']
            for item in evidence['protected_config'].values()) and stable_mapping_ok and \
            evidence['checks']['protected_semantic_config_matches']
        evidence['checks']['mame_overrides_expected'] = (
            baseline['global_mame_core'] == 'mame078plus' and
            baseline['mame_overrides_count'] == 18)
        if not evidence['checks']['mame_overrides_expected']:
            raise RuntimeError('PROTECTED_MAME_CONFIG_CHANGE')
        if not evidence['checks']['protected_config_matches']:
            raise RuntimeError('PROTECTED_CONFIG_MISMATCH')

        rows, _ = cert.load_rows()
        systems = cert.ad.live_systems()
        evidence['queue_reconciliation'] = cert.assert_reconciled_queue(rows, cp, systems)
        evidence['checks']['queue_checkpoint_reconciled'] = True
        evidence['passed'] = True
        return evidence
    except Exception as exc:
        evidence['failure'] = type(exc).__name__ + ':' + str(exc)[:180]
        return evidence


def recovered_safety_plan(cp, evidence):
    """Pure, deliberately narrow decision gate for post-reboot reconciliation."""
    if str(cp.get('blocked_reason') or '').strip() == 'ES_LAUNCH_PROCESS_ACTIVE':
        results = cp.get('results') if isinstance(cp.get('results'), list) else []
        latest = results[-1] if results else {}
        if latest.get('transaction_id') == BATCH69_TX:
            return batch69_recovered_safety_plan(cp, evidence)
        return batch68_recovered_safety_plan(cp, evidence)
    import re as _re
    reason = str(cp.get('blocked_reason') or '')
    blockers = _re.findall(r'(?<![A-Z0-9_])(ES_NOT_IDLE|ES_IDLE_TIMEOUT|SELECTOR_NOT_CLOSED)(?![A-Z0-9_])',
                           reason.upper())
    if cp.get('status') != 'PAUSED_SYSTEM_SAFETY_FAILURE' or len(blockers) != 1:
        return False, 'BLOCKER_NOT_RECOVERABLE', None
    if int(cp.get('engine_fail_active', 0)) != 0:
        return False, 'ENGINE_FAIL_ACTIVE', None
    batch = cp.get('batch_in_progress')
    if not isinstance(batch, dict) or batch.get('name') != 'priority_batch_59':
        return False, 'BATCH_59_CHECKPOINT_MISMATCH', None
    if (batch.get('considered') != 100 or batch.get('launched') != 1 or
            batch.get('auto_pass') != 1 or batch.get('game_fail') != 0 or
            batch.get('restore_verified') != 1 or batch.get('restore_failures') != 0 or
            cp.get('next_untested') != POST_REBOOT_GAME):
        return False, 'BATCH_59_PROGRESS_MISMATCH', None
    checks = evidence.get('checks', {}) if isinstance(evidence, dict) else {}
    required = ('no_engine_fail', 'marker_absent', 'launch_processes_absent',
                'no_active_certifier', 'es_idle', 'running_game_none',
                'historical_failed_job_preserved',
                'last_result_restore_verified', 'manifest_restore_verified',
                'protected_config_matches', 'protected_semantic_config_matches',
                'logical_p1_p4_stable_identity', 'mame_overrides_expected',
                'queue_checkpoint_reconciled')
    if (not evidence.get('passed') or not evidence.get('current_boot_id') or
            any(checks.get(key) is not True for key in required)):
        return False, evidence.get('failure', 'RUNTIME_RECOVERY_GATES_FAILED'), None
    if evidence.get('last_restored_transaction') != POST_REBOOT_TX:
        return False, 'LAST_TRANSACTION_ID_MISMATCH', None
    return True, blockers[0], {
        'recovered_at': now(),
        'previous_status': cp.get('status'),
        'previous_blocked_reason': cp.get('blocked_reason'),
        'current_boot_id': evidence['current_boot_id'],
        'previous_boot_id': evidence.get('previous_boot_id'),
        'runtime_checks': checks,
        'last_restored_transaction': POST_REBOOT_TX,
        'next_game': cp.get('next_untested'),
        'recovery_reason': 'POST_REBOOT_RUNTIME_CLEAN',
        'recovered_blocker': blockers[0],
    }


def batch68_recovered_safety_plan(cp, evidence):
    """Allow only the specifically recovered Batch 68 ES launch blocker."""
    if cp.get('status') != 'PAUSED_SYSTEM_SAFETY_FAILURE' or cp.get('blocked_reason') != 'ES_LAUNCH_PROCESS_ACTIVE':
        return False, 'BLOCKER_NOT_RECOVERABLE', None
    batch = cp.get('batch_in_progress')
    results = cp.get('results')
    latest_tx = results[-1].get('transaction_id') if isinstance(results, list) and results else None
    retry_case = latest_tx == BATCH68_RETRY_TX
    expected_tx = BATCH68_RETRY_TX if retry_case else BATCH68_TX
    expected_launched = 22 if retry_case else 21
    expected_restores = expected_launched
    expected_batch = {'name': 'priority_batch_68', 'considered': 41, 'launched': expected_launched,
                      'auto_pass': 20, 'game_fail': 0, 'restore_verified': expected_restores,
                      'restore_failures': 0}
    if not isinstance(batch, dict) or any(batch.get(k) != v for k, v in expected_batch.items()):
        return False, 'BATCH68_PROGRESS_MISMATCH', None
    if cp.get('next_untested') != BATCH68_GAME or cp.get('current_test'):
        return False, 'BATCH68_CURSOR_OR_ACTIVE_TRANSACTION_MISMATCH', None
    results = cp.get('results')
    if not isinstance(results, list) or len(results) < expected_launched:
        return False, 'BATCH68_RESULT_HISTORY_MISSING', None
    tail = results[-expected_launched:]
    tail_counts = {}
    for item in tail:
        tail_counts[item.get('result', 'UNKNOWN')] = tail_counts.get(item.get('result', 'UNKNOWN'), 0) + 1
    doom = tail[-1]
    expected_counts = {'AUTO_PASS': 20, 'SYSTEM_SAFETY_FAILURE': 2} if retry_case else {'AUTO_PASS': 20, 'SYSTEM_SAFETY_FAILURE': 1}
    if (tail_counts != expected_counts or
            doom.get('transaction_id') != expected_tx or doom.get('system') != 'prboom' or
            doom.get('rom') != '/userdata/roms/prboom/doom1_shareware.wad' or
            doom.get('result') != 'SYSTEM_SAFETY_FAILURE' or
            doom.get('failure_class') != 'ES_LAUNCH_PROCESS_ACTIVE' or
            doom.get('restore', {}).get('status') != 'RESTORE_VERIFIED' or
            any(not item.get('transaction_id') or item.get('restore', {}).get('status') != 'RESTORE_VERIFIED'
                for item in tail)):
        return False, 'BATCH68_RESULT_OR_RESTORE_MISMATCH', None
    result_sha = hashlib.sha256(json.dumps(results, ensure_ascii=False, sort_keys=True,
                                          separators=(',', ':')).encode()).hexdigest()
    batch_sha = hashlib.sha256(json.dumps(batch, ensure_ascii=False, sort_keys=True,
                                         separators=(',', ':')).encode()).hexdigest()
    if evidence.get('result_records_sha256') != result_sha:
        return False, 'BATCH68_RESULT_EVIDENCE_CHANGED', None
    if evidence.get('batch_progress_sha256') != batch_sha:
        return False, 'BATCH68_PROGRESS_EVIDENCE_CHANGED', None
    if doom.get('result') in ('AUTO_PASS', 'GAME_FAIL'):
        return False, 'DOOM_RESULT_ALREADY_TERMINAL', None
    checks = evidence.get('checks', {}) if isinstance(evidence, dict) else {}
    required = (
        'operator_confirmed_normal_selector_cancel', 'two_consecutive_clean_runtime_observations',
        'es_idle', 'running_game_none', 'marker_absent', 'selector_absent', 'launcher_absent',
        'emulator_absent', 'all_launch_and_emulator_processes_absent',
        'no_active_certifier', 'no_active_autopilot', 'no_partial_transaction', 'last_result_restore_verified',
        'transaction_record_consistent', 'manifest_restore_verified', 'restored_paths_match_pre_state', 'batch68_transactions_consistent',
        'previous_terminal_result_preserved', 'doom_csv_still_not_tested', 'cursor_matches_canonical_queue',
        'hdmi_pass', 'logical_p1_p4_stable_identity', 'protected_config_pass',
        'only_active_stop_is_reconciled_safety_incident', 'no_other_active_engine_failure',
        'result_evidence_unchanged', 'batch_progress_unchanged', 'no_game_terminal_result_for_doom',
    )
    if not evidence.get('passed') or not evidence.get('current_boot_id'):
        return False, evidence.get('failure', 'BATCH68_RUNTIME_GATES_FAILED'), None
    for key in required:
        if checks.get(key) is not True:
            return False, 'BATCH68_GATE_FAIL:' + key, None
    if evidence.get('transaction_id') != expected_tx or evidence.get('next_game') != BATCH68_GAME:
        return False, 'BATCH68_TRANSACTION_OR_CURSOR_MISMATCH', None
    # The existing counter includes this one SYSTEM_SAFETY_FAILURE because it
    # belongs to STOP_ENGINE. It is cleared only after this exact incident is
    # reconciled; all other active engine failures must already be absent.
    if cp.get('engine_fail_active') != 1 or evidence.get('active_stop_result_count') != 1:
        return False, 'ACTIVE_ENGINE_FAILURE_COUNT_MISMATCH', None
    return True, 'ES_LAUNCH_PROCESS_ACTIVE', {
        'recovered_at': now(),
        'previous_status': cp.get('status'),
        'previous_blocked_reason': cp.get('blocked_reason'),
        'current_boot_id': evidence['current_boot_id'],
        'transaction_id': expected_tx,
        'next_game': BATCH68_GAME,
        'recovery_reason': 'NORMAL_SELECTOR_CANCELLATION_AND_RUNTIME_CLEAN',
        'operator_confirmed_normal_selector_cancel': True,
        'runtime_checks': checks,
        'previous_active_engine_fail_count': cp.get('engine_fail_active'),
        'reconciled_engine_fail_active': 0,
        'result_records_sha256': evidence.get('result_records_sha256'),
        'batch_progress_sha256': evidence.get('batch_progress_sha256'),
        'csv_sha256': evidence.get('csv_sha256'),
    }


def batch69_recovered_safety_plan(cp, evidence):
    """Reconcile only the recorded MrBoom pre-launch stop after Doom's selector closed normally."""
    if cp.get('status') != 'PAUSED_SYSTEM_SAFETY_FAILURE' or cp.get('blocked_reason') != 'ES_LAUNCH_PROCESS_ACTIVE':
        return False, 'BLOCKER_NOT_RECOVERABLE', None
    batch = cp.get('batch_in_progress')
    expected_batch = {'name': 'priority_batch_69', 'considered': 1, 'launched': 1,
                      'processed': 1, 'auto_pass': 0, 'game_fail': 0, 'static_fail': 0,
                      'restore_verified': 1, 'restore_failures': 0}
    if not isinstance(batch, dict) or any(batch.get(k) != v for k, v in expected_batch.items()):
        return False, 'BATCH69_PROGRESS_MISMATCH', None
    results = cp.get('results')
    incident = results[-1] if isinstance(results, list) and results else {}
    if (not isinstance(results, list) or incident.get('transaction_id') != BATCH69_TX or
            incident.get('system') != 'mrboom' or incident.get('rom') != '/userdata/roms/mrboom/MrBoom.libretro' or
            incident.get('result') != 'SYSTEM_SAFETY_FAILURE' or
            incident.get('failure_class') != 'ES_LAUNCH_PROCESS_ACTIVE' or
            incident.get('restore', {}).get('status') != 'RESTORE_VERIFIED' or
            incident.get('restore', {}).get('transaction_id') != BATCH69_TX):
        return False, 'BATCH69_INCIDENT_OR_RESTORE_MISMATCH', None
    if cp.get('next_untested') != BATCH69_GAME or cp.get('current_test'):
        return False, 'BATCH69_CURSOR_OR_ACTIVE_TRANSACTION_MISMATCH', None
    checks = evidence.get('checks', {}) if isinstance(evidence, dict) else {}
    required = (
        'two_consecutive_clean_runtime_observations', 'es_idle', 'running_game_none',
        'marker_absent', 'selector_absent', 'launcher_absent', 'emulator_absent',
        'all_launch_and_emulator_processes_absent', 'no_active_certifier', 'no_active_autopilot',
        'no_partial_transaction', 'manifest_restore_verified', 'restored_paths_match_pre_state',
        'emulator_not_started', 'normal_selector_cancel_verified', 'batch69_transactions_consistent',
        'batch68_preserved', 'mrboom_csv_still_not_tested', 'cursor_matches_canonical_queue',
        'hdmi_pass', 'logical_p1_p4_stable_identity', 'protected_config_pass',
        'only_active_stop_is_reconciled_safety_incident', 'result_evidence_unchanged',
        'batch_progress_unchanged')
    if not evidence.get('passed') or not evidence.get('current_boot_id'):
        return False, evidence.get('failure', 'BATCH69_RUNTIME_GATES_FAILED'), None
    for key in required:
        if checks.get(key) is not True:
            return False, 'BATCH69_GATE_FAIL:' + key, None
    if evidence.get('transaction_id') != BATCH69_TX or evidence.get('next_game') != BATCH69_GAME:
        return False, 'BATCH69_TRANSACTION_OR_CURSOR_MISMATCH', None
    # The one active stop is this system-safety blocker. Its reconciliation
    # clears only the counter; the result and launch record remain untouched.
    if cp.get('engine_fail_active') != 1 or evidence.get('active_stop_result_count') != 1:
        return False, 'ACTIVE_ENGINE_FAILURE_COUNT_MISMATCH', None
    return True, 'ES_LAUNCH_PROCESS_ACTIVE', {
        'recovered_at': now(), 'previous_status': cp.get('status'),
        'previous_blocked_reason': cp.get('blocked_reason'),
        'current_boot_id': evidence['current_boot_id'], 'transaction_id': BATCH69_TX,
        'next_game': BATCH69_GAME,
        'recovery_reason': 'BATCH69_RESIDUAL_DOOM_SELECTOR_CLOSED_AND_RUNTIME_CLEAN',
        'runtime_checks': checks, 'previous_active_engine_fail_count': cp.get('engine_fail_active'),
        'reconciled_engine_fail_active': 0,
        'result_records_sha256': evidence.get('result_records_sha256'),
        'batch_progress_sha256': evidence.get('batch_progress_sha256'),
        'csv_sha256': evidence.get('csv_sha256'),
    }


def batch68_reconciled_incident_matches(cp, active_stops, csv_sha256):
    """Accept only the exact Batch 68 incident previously reconciled with clean runtime evidence."""
    import hashlib
    recovery = cp.get('safety_recovery') or {}
    runtime_checks = recovery.get('runtime_checks') or {}
    required_runtime_checks = (
        'operator_confirmed_normal_selector_cancel', 'two_consecutive_clean_runtime_observations',
        'es_idle', 'running_game_none', 'marker_absent', 'all_launch_and_emulator_processes_absent',
        'no_active_certifier', 'no_active_autopilot', 'no_partial_transaction',
        'last_result_restore_verified', 'manifest_restore_verified', 'restored_paths_match_pre_state',
        'batch68_transactions_consistent', 'previous_terminal_result_preserved',
        'doom_csv_still_not_tested', 'cursor_matches_canonical_queue', 'hdmi_pass',
        'logical_p1_p4_stable_identity', 'protected_config_pass', 'result_evidence_unchanged',
        'batch_progress_unchanged', 'no_game_terminal_result_for_doom',
    )
    if len(active_stops) != 1:
        return False
    incident = active_stops[0]
    recovered_tx = recovery.get('transaction_id')
    if recovered_tx not in (BATCH68_TX, BATCH68_RETRY_TX):
        return False
    results_digest = hashlib.sha256(json.dumps(
        cp.get('results', []), ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    batch_digest = hashlib.sha256(json.dumps(
        cp.get('batch_in_progress'), ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return bool(
        cp.get('status') == 'STOPPED_SAFE' and cp.get('blocked_reason') is None and
        cp.get('engine_fail_active') == 0 and cp.get('next_untested') == BATCH68_GAME and
        incident.get('transaction_id') == recovered_tx and
        incident.get('system') == 'prboom' and incident.get('rom') == '/userdata/roms/prboom/doom1_shareware.wad' and
        incident.get('result') == 'SYSTEM_SAFETY_FAILURE' and
        incident.get('failure_class') == 'ES_LAUNCH_PROCESS_ACTIVE' and
        incident.get('restore', {}).get('status') == 'RESTORE_VERIFIED' and
        incident.get('restore', {}).get('transaction_id') == recovered_tx and
        recovery.get('previous_blocked_reason') == 'ES_LAUNCH_PROCESS_ACTIVE' and
        recovery.get('recovery_reason') == 'NORMAL_SELECTOR_CANCELLATION_AND_RUNTIME_CLEAN' and
        recovery.get('operator_confirmed_normal_selector_cancel') is True and
        recovery.get('previous_active_engine_fail_count') == 1 and
        recovery.get('reconciled_engine_fail_active') == 0 and
        recovery.get('transaction_id') == recovered_tx and recovery.get('next_game') == BATCH68_GAME and
        all(runtime_checks.get(key) is True for key in required_runtime_checks) and
        recovery.get('result_records_sha256') == results_digest and
        recovery.get('batch_progress_sha256') == batch_digest and
        recovery.get('csv_sha256') == csv_sha256)


def batch68_retry_incident_pending_matches(cp, active_stops, transaction_id):
    """Permit one explicitly identified retry failure after the first recovery, once."""
    if transaction_id != BATCH68_RETRY_TX or len(active_stops) != 1:
        return False
    incident = active_stops[0]
    batch = cp.get('batch_in_progress') or {}
    results = cp.get('results') or []
    if (incident.get('transaction_id') != BATCH68_RETRY_TX or incident.get('system') != 'prboom' or
            incident.get('rom') != '/userdata/roms/prboom/doom1_shareware.wad' or
            incident.get('result') != 'SYSTEM_SAFETY_FAILURE' or
            incident.get('failure_class') != 'ES_LAUNCH_PROCESS_ACTIVE' or
            incident.get('restore', {}).get('status') != 'RESTORE_VERIFIED' or len(results) < 22):
        return False
    tail = results[-22:]
    counts = {}
    for item in tail:
        counts[item.get('result', 'UNKNOWN')] = counts.get(item.get('result', 'UNKNOWN'), 0) + 1
    if counts != {'AUTO_PASS': 20, 'SYSTEM_SAFETY_FAILURE': 2} or tail[-2].get('transaction_id') != BATCH68_TX:
        return False
    previous_recovery = cp.get('safety_recovery') or {}
    if (previous_recovery.get('transaction_id') != BATCH68_TX or
            previous_recovery.get('recovery_reason') != 'NORMAL_SELECTOR_CANCELLATION_AND_RUNTIME_CLEAN' or
            previous_recovery.get('reconciled_engine_fail_active') != 0):
        return False
    prefix = results[:-1]
    prefix_digest = hashlib.sha256(json.dumps(prefix, ensure_ascii=False, sort_keys=True,
        separators=(',', ':')).encode()).hexdigest()
    prior_batch = json.loads(json.dumps(batch))
    for key in ('launched', 'processed', 'restore_verified'):
        if not isinstance(prior_batch.get(key), int) or prior_batch[key] != 22:
            return False
        prior_batch[key] -= 1
    prior_batch_digest = hashlib.sha256(json.dumps(prior_batch, ensure_ascii=False, sort_keys=True,
        separators=(',', ':')).encode()).hexdigest()
    return bool(prefix_digest == previous_recovery.get('result_records_sha256') and
                prior_batch_digest == previous_recovery.get('batch_progress_sha256'))


def batch68_recovered_runtime_evidence(cp, *, operator_confirmed_normal_selector_cancel=False):
    """Capture fresh, read-only evidence for Batch 68 safety reconciliation."""
    import hashlib
    evidence = {'current_boot_id': current_boot_id(), 'checks': {}, 'observations': [], 'passed': False}
    checks = evidence['checks']
    try:
        batch = cp.get('batch_in_progress') or {}
        latest = cp.get('results')[-1] if isinstance(cp.get('results'), list) and cp.get('results') else {}
        txid = latest.get('transaction_id')
        if txid not in (BATCH68_TX, BATCH68_RETRY_TX):
            raise RuntimeError('BATCH68_INCIDENT_ID_NOT_ALLOWLISTED')
        retry_case = txid == BATCH68_RETRY_TX
        expected_launched = 22 if retry_case else 21
        expected_counts = {'AUTO_PASS': 20, 'SYSTEM_SAFETY_FAILURE': 2} if retry_case else {'AUTO_PASS': 20, 'SYSTEM_SAFETY_FAILURE': 1}
        if not evidence['current_boot_id']:
            raise RuntimeError('BOOT_ID_UNAVAILABLE')
        checks['operator_confirmed_normal_selector_cancel'] = bool(operator_confirmed_normal_selector_cancel)
        if not checks['operator_confirmed_normal_selector_cancel']:
            raise RuntimeError('NORMAL_SELECTOR_CANCELLATION_NOT_CONFIRMED')

        sys.path.insert(0, str(TOOLS))
        import full_game_certifier as cert
        # Two complete observations, separated by the existing one-second
        # safety polling interval; every observation checks ES, marker, the
        # certifier detector, and the broader emulator/launcher process set.
        relevant = {'retroarch', 'mame', 'flycast', 'prboom', 'gzdoom',
                    'emulatorlauncher', 'controller_dispatcher', 'selector_controles'}
        for index in range(2):
            idle, game = cert.api_state()
            detected = cert.pids()
            broad = []
            for entry in Path('/proc').iterdir():
                if not entry.name.isdigit():
                    continue
                try:
                    comm = (entry / 'comm').read_text().strip().lower()
                    exe = Path(f'/proc/{entry.name}/exe').resolve().name.lower()
                    argv = (entry / 'cmdline').read_bytes().replace(b'\\0', b' ').decode(errors='replace').strip()
                except OSError:
                    continue
                if comm in relevant or exe in relevant:
                    broad.append({'pid': int(entry.name), 'comm': comm, 'exe': exe, 'argv': argv[:500]})
            all_records = list(detected) + broad
            selector_active = [x for x in all_records if x.get('comm') in ('selector_controles', 'selector_contro') or
                               x.get('exe') == 'selector_controles' or '/userdata/system/el_gordo_tools/selector_controles' in x.get('argv', '')]
            launcher_active = [x for x in all_records if x.get('comm') in ('controller_dispatcher', 'controller_disp', 'emulatorlauncher') or
                               x.get('exe') in ('controller_dispatcher', 'emulatorlauncher') or
                               '/userdata/system/el_gordo_tools/controller_dispatcher' in x.get('argv', '') or
                               '/usr/bin/emulatorlauncher' in x.get('argv', '')]
            emulator_active = [x for x in all_records if x.get('comm') in ('retroarch', 'mame', 'flycast', 'prboom', 'gzdoom') or
                               x.get('exe') in ('retroarch', 'mame', 'flycast', 'prboom', 'gzdoom')]
            observation = {'index': index + 1, 'captured_at': now(), 'isIdle': idle,
                           'runningGame': game, 'pids': detected, 'other_relevant_processes': broad,
                           'selector_processes': selector_active, 'launcher_processes': launcher_active,
                           'emulator_processes': emulator_active,
                           'marker_absent': not MARKER.exists()}
            evidence['observations'].append(observation)
            if not idle or game is not None or detected or broad or MARKER.exists():
                raise RuntimeError('RUNTIME_NOT_CLEAN_OBSERVATION_' + str(index + 1))
            if index == 0:
                time.sleep(1)
        checks['two_consecutive_clean_runtime_observations'] = True
        checks['es_idle'] = all(x['isIdle'] is True for x in evidence['observations'])
        checks['running_game_none'] = all(x['runningGame'] is None for x in evidence['observations'])
        checks['marker_absent'] = all(x['marker_absent'] for x in evidence['observations'])
        checks['all_launch_and_emulator_processes_absent'] = all(
            not x['pids'] and not x['other_relevant_processes'] for x in evidence['observations'])
        checks['selector_absent'] = all(not x['selector_processes'] for x in evidence['observations'])
        checks['launcher_absent'] = all(not x['launcher_processes'] for x in evidence['observations'])
        checks['emulator_absent'] = all(not x['emulator_processes'] for x in evidence['observations'])

        cert_pid, cert_proc = certifier_active()
        evidence['certifier_pid'] = cert_pid
        evidence['certifier_process'] = cert_proc
        job = read_json(AUDIT / 'jobs' / 'certifier_job.json', {}) or {}
        evidence['certifier_job'] = {k: job.get(k) for k in ('job_id', 'status', 'pid', 'started_at', 'finished_at', 'boot_id')}
        checks['no_active_certifier'] = cert_pid is None and job.get('status') in ('FAILED', 'COMPLETE') and bool(job.get('finished_at'))
        if not checks['no_active_certifier']:
            raise RuntimeError('CERTIFIER_STILL_ACTIVE_OR_JOB_NOT_TERMINAL')
        autopilot_pid, _ = find_autopilot_process()
        checks['no_active_autopilot'] = autopilot_pid is None
        if not checks['no_active_autopilot']:
            raise RuntimeError('AUTOPILOT_STILL_ACTIVE')
        checks['no_partial_transaction'] = not cp.get('current_test')
        if not checks['no_partial_transaction']:
            raise RuntimeError('CHECKPOINT_TRANSACTION_STILL_ACTIVE')

        txdir = AUDIT / 'runtime' / txid
        manifest = read_json(txdir / 'manifest.json', {}) or {}
        result = read_json(txdir / 'result.json', {}) or {}
        evidence['transaction_id'] = txid
        doom = next((x for x in reversed(cp.get('results', []))
                     if x.get('transaction_id') == txid), None)
        checks['no_game_terminal_result_for_doom'] = bool(
            doom and doom.get('result') == 'SYSTEM_SAFETY_FAILURE' and
            doom.get('failure_class') == 'ES_LAUNCH_PROCESS_ACTIVE' and
            doom.get('system') == 'prboom' and doom.get('rom') == '/userdata/roms/prboom/doom1_shareware.wad')
        evidence['doom_result'] = {k: doom.get(k) for k in ('result', 'failure_class', 'transaction_id', 'finished_at')} if doom else None
        checks['last_result_restore_verified'] = bool(
            doom and doom.get('restore', {}).get('status') == 'RESTORE_VERIFIED' and
            doom.get('restore', {}).get('transaction_id') == txid and
            result.get('restore', {}).get('status') == 'RESTORE_VERIFIED' and
            result.get('restore', {}).get('transaction_id') == txid)
        checks['transaction_record_consistent'] = bool(
            result.get('transaction_id') == txid and result.get('system') == 'prboom' and
            result.get('rom') == '/userdata/roms/prboom/doom1_shareware.wad' and
            result.get('result') == 'SYSTEM_SAFETY_FAILURE' and
            result.get('failure_class') == 'ES_LAUNCH_PROCESS_ACTIVE' and
            result.get('finished_at') == (doom or {}).get('finished_at') and
            result.get('exit', {}).get('code') == 0 and
            result.get('restore', {}).get('paths') == 7 and
            not result.get('safety_after') and not result.get('safety_after_finally'))
        checks['manifest_restore_verified'] = bool(
            manifest.get('transaction_id') == txid and
            manifest.get('status') == 'RESTORE_VERIFIED' and len(manifest.get('entries', [])) == 7)
        if (not checks['last_result_restore_verified'] or not checks['transaction_record_consistent'] or
                not checks['manifest_restore_verified']):
            raise RuntimeError('BATCH68_TRANSACTION_NOT_RESTORE_VERIFIED')

        import certification_transaction as tx
        restore_checks = []
        for entry in manifest['entries']:
            current = tx.state(Path(entry['path']))
            restore_checks.append({'path': entry['path'], 'matches_pre_state': current == entry.get('before')})
        evidence['restored_paths'] = restore_checks
        checks['restored_paths_match_pre_state'] = all(x['matches_pre_state'] for x in restore_checks)
        if not checks['restored_paths_match_pre_state']:
            raise RuntimeError('RESTORED_PATH_DIFFERS_FROM_PRE_STATE')

        batch = cp.get('batch_in_progress') or {}
        tail = cp.get('results', [])[-int(batch.get('launched') or 0):]
        tail_counts = {}
        for item in tail:
            tail_counts[item.get('result', 'UNKNOWN')] = tail_counts.get(item.get('result', 'UNKNOWN'), 0) + 1
        evidence['batch68_tail_counts'] = tail_counts
        checks['batch68_transactions_consistent'] = bool(
            batch.get('name') == 'priority_batch_68' and batch.get('considered') == 41 and
            batch.get('launched') == expected_launched and batch.get('auto_pass') == 20 and batch.get('game_fail') == 0 and
            batch.get('restore_verified') == expected_launched and batch.get('restore_failures') == 0 and
            len(tail) == expected_launched and tail_counts == expected_counts and
            all(x.get('transaction_id') and x.get('restore', {}).get('status') == 'RESTORE_VERIFIED' for x in tail))
        if not checks['batch68_transactions_consistent']:
            raise RuntimeError('BATCH68_ACCOUNTING_MISMATCH')
        previous = next((x for x in reversed(tail[:-1]) if x.get('result') == 'AUTO_PASS'), None)
        checks['previous_terminal_result_preserved'] = bool(
            previous and previous.get('result') == 'AUTO_PASS' and
            previous.get('restore', {}).get('status') == 'RESTORE_VERIFIED' and
            previous.get('transaction_id'))
        if not checks['previous_terminal_result_preserved']:
            raise RuntimeError('PREVIOUS_BATCH68_RESULT_MISMATCH')

        rows, _ = cert.load_rows()
        doom_row = next((x for x in rows if x.get('system') == 'prboom' and
                         x.get('rom') == '/userdata/roms/prboom/doom1_shareware.wad'), None)
        checks['doom_csv_still_not_tested'] = bool(
            doom_row and doom_row.get('auto_certification') == 'NOT_TESTED' and
            doom_row.get('lifecycle_state') == 'NOT_TESTED' and
            doom_row.get('audio_certification') == 'NOT_TESTED' and
            doom_row.get('exit_certification') == 'NOT_TESTED')
        if not checks['doom_csv_still_not_tested']:
            raise RuntimeError('DOOM_CSV_IS_TERMINAL_OR_CHANGED')
        systems = cert.ad.live_systems()
        queue = cert.queue(rows, systems)
        canonical_next = f"{queue[0]['system']}:{queue[0]['rom']}" if queue else None
        evidence['next_game'] = cp.get('next_untested')
        checks['cursor_matches_canonical_queue'] = cp.get('next_untested') == BATCH68_GAME == canonical_next
        evidence['queue_reconciliation'] = cert.assert_reconciled_queue(rows, cp, systems)
        if not checks['cursor_matches_canonical_queue']:
            raise RuntimeError('BATCH68_CURSOR_MISMATCH')

        baseline = result.get('safety_before') or {}
        identity = cert.profile_state()
        checks['logical_p1_p4_stable_identity'] = cert.stable_profile_matches(identity)
        evidence['p1_p4'] = {p: {'physical_path': v['physical_path'], 'by_path': v['by_path'],
                                 'usb_port': v['usb_port'], 'device_identity': v['device_identity']}
                             for p, v in identity.items()}
        audio = cert.get_default_sink()
        checks['hdmi_pass'] = audio == cert.HDMI == baseline.get('audio_default')
        evidence['audio_default'] = audio
        core, override_count = current_global_overrides()
        current_dispatcher_sha = hashlib.sha256((TOOLS / 'controller_dispatcher').read_bytes()).hexdigest()
        reviewed_dispatcher = Path('/userdata/system/state/arcade_audit_git/scripts/active/controller_dispatcher.py')
        reviewed_dispatcher_sha = (hashlib.sha256(reviewed_dispatcher.read_bytes()).hexdigest()
                                   if reviewed_dispatcher.is_file() and not reviewed_dispatcher.is_symlink() else None)
        dispatcher_matches_baseline = current_dispatcher_sha == baseline.get('dispatcher_sha256')
        dispatcher_matches_reviewed_fix = bool(reviewed_dispatcher_sha and current_dispatcher_sha == reviewed_dispatcher_sha)
        evidence['dispatcher_identity'] = {
            'current_sha256': current_dispatcher_sha,
            'incident_baseline_sha256': baseline.get('dispatcher_sha256'),
            'reviewed_export_sha256': reviewed_dispatcher_sha,
            'matches_incident_baseline': dispatcher_matches_baseline,
            'matches_reviewed_export': dispatcher_matches_reviewed_fix,
        }
        checks['protected_config_pass'] = bool(
            hashlib.sha256(Path('/userdata/system/batocera.conf').read_bytes()).hexdigest() == baseline.get('batocera_conf_sha256') and
            core == baseline.get('global_mame_core') == 'mame078plus' and override_count == 18 and
            (dispatcher_matches_baseline or dispatcher_matches_reviewed_fix) and
            hashlib.sha256(Path('/userdata/system/configs/el_gordo_controller_profiles/controller_technical.json').read_bytes()).hexdigest() == baseline.get('profile_sha256') and
            hashlib.sha256(Path('/userdata/system/configs/el_gordo_controller_profiles/multiplayer.json').read_bytes()).hexdigest() == baseline.get('multiplayer_sha256'))
        if not checks['logical_p1_p4_stable_identity'] or not checks['hdmi_pass'] or not checks['protected_config_pass']:
            raise RuntimeError('BATCH68_PROTECTED_RUNTIME_GATE_FAIL')

        latest = {}
        for item in cp.get('results', []):
            latest[(item.get('system'), item.get('rom'))] = item
        active_stops = [x for x in latest.values() if x.get('result') in cert.STOP_ENGINE]
        evidence['csv_sha256'] = hashlib.sha256(CERT_CSV.read_bytes()).hexdigest()
        incident_only = (batch68_reconciled_incident_matches(cp, active_stops, evidence['csv_sha256']) or
                         batch68_retry_incident_pending_matches(cp, active_stops, txid))
        evidence['active_stop_result_count'] = len(active_stops)
        checks['only_active_stop_is_reconciled_safety_incident'] = incident_only
        checks['no_other_active_engine_failure'] = incident_only
        if not incident_only:
            raise RuntimeError('RECONCILED_BATCH68_INCIDENT_MISMATCH')

        evidence['result_records_sha256'] = hashlib.sha256(
            json.dumps(cp.get('results', []), ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        evidence['batch_progress_sha256'] = hashlib.sha256(
            json.dumps(batch, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        evidence['csv_sha256'] = hashlib.sha256(CERT_CSV.read_bytes()).hexdigest()
        checks['result_evidence_unchanged'] = True
        checks['batch_progress_unchanged'] = True
        evidence['passed'] = all(checks.get(k) is True for k in (
            'operator_confirmed_normal_selector_cancel', 'two_consecutive_clean_runtime_observations',
            'es_idle', 'running_game_none', 'marker_absent', 'selector_absent', 'launcher_absent',
            'emulator_absent', 'all_launch_and_emulator_processes_absent',
            'no_active_certifier', 'no_active_autopilot', 'no_partial_transaction', 'last_result_restore_verified',
            'transaction_record_consistent', 'manifest_restore_verified', 'restored_paths_match_pre_state', 'batch68_transactions_consistent',
            'previous_terminal_result_preserved', 'doom_csv_still_not_tested', 'cursor_matches_canonical_queue',
            'hdmi_pass', 'logical_p1_p4_stable_identity', 'protected_config_pass',
            'only_active_stop_is_reconciled_safety_incident', 'no_other_active_engine_failure',
            'result_evidence_unchanged', 'batch_progress_unchanged', 'no_game_terminal_result_for_doom'))
        if not evidence['passed']:
            raise RuntimeError('BATCH68_RUNTIME_GATES_FAILED')
        return evidence
    except Exception as exc:
        evidence['failure'] = type(exc).__name__ + ':' + str(exc)[:180]
        return evidence


def batch69_recovered_runtime_evidence(cp):
    """Capture fresh, read-only evidence for the one Batch 69 Doom-chain blocker."""
    evidence = {'current_boot_id': current_boot_id(), 'checks': {}, 'observations': [], 'passed': False}
    checks = evidence['checks']
    try:
        if not evidence['current_boot_id']:
            raise RuntimeError('BOOT_ID_UNAVAILABLE')
        batch = cp.get('batch_in_progress') or {}
        if (batch.get('name') != 'priority_batch_69' or batch.get('considered') != 1 or
                batch.get('launched') != 1 or batch.get('processed') != 1 or
                batch.get('auto_pass') != 0 or batch.get('game_fail') != 0 or
                batch.get('static_fail') != 0 or batch.get('restore_verified') != 1 or
                batch.get('restore_failures') != 0):
            raise RuntimeError('BATCH69_PROGRESS_MISMATCH')
        results = cp.get('results') if isinstance(cp.get('results'), list) else []
        incident = results[-1] if results else {}
        if (incident.get('transaction_id') != BATCH69_TX or incident.get('system') != 'mrboom' or
                incident.get('rom') != '/userdata/roms/mrboom/MrBoom.libretro' or
                incident.get('result') != 'SYSTEM_SAFETY_FAILURE' or
                incident.get('failure_class') != 'ES_LAUNCH_PROCESS_ACTIVE' or
                incident.get('restore', {}).get('status') != 'RESTORE_VERIFIED'):
            raise RuntimeError('BATCH69_INCIDENT_ID_NOT_ALLOWLISTED')
        evidence['transaction_id'] = BATCH69_TX

        sys.path.insert(0, str(TOOLS))
        import full_game_certifier as cert
        relevant = {'retroarch', 'mame', 'flycast', 'prboom', 'gzdoom',
                    'emulatorlauncher', 'controller_dispatcher', 'selector_controles'}
        for index in range(2):
            idle, game = cert.api_state()
            detected = cert.pids()
            broad = []
            for entry in Path('/proc').iterdir():
                if not entry.name.isdigit():
                    continue
                try:
                    comm = (entry / 'comm').read_text().strip().lower()
                    exe = Path(f'/proc/{entry.name}/exe').resolve().name.lower()
                    argv = (entry / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace').strip()
                except OSError:
                    continue
                if comm in relevant or exe in relevant:
                    broad.append({'pid': int(entry.name), 'comm': comm, 'exe': exe, 'argv': argv[:500]})
            observation = {'index': index + 1, 'captured_at': now(), 'isIdle': idle,
                           'runningGame': game, 'pids': detected, 'other_relevant_processes': broad,
                           'marker_absent': not MARKER.exists()}
            evidence['observations'].append(observation)
            if not idle or game is not None or detected or broad or MARKER.exists():
                raise RuntimeError('RUNTIME_NOT_CLEAN_OBSERVATION_' + str(index + 1))
            if index == 0:
                time.sleep(1)
        checks.update({
            'two_consecutive_clean_runtime_observations': True,
            'es_idle': all(x['isIdle'] is True for x in evidence['observations']),
            'running_game_none': all(x['runningGame'] is None for x in evidence['observations']),
            'marker_absent': all(x['marker_absent'] for x in evidence['observations']),
            'all_launch_and_emulator_processes_absent': all(
                not x['pids'] and not x['other_relevant_processes'] for x in evidence['observations']),
            'selector_absent': all(not x['pids'] and not x['other_relevant_processes'] for x in evidence['observations']),
            'launcher_absent': all(not x['pids'] and not x['other_relevant_processes'] for x in evidence['observations']),
            'emulator_absent': all(not x['pids'] and not x['other_relevant_processes'] for x in evidence['observations']),
        })
        job = read_json(AUDIT / 'jobs' / 'certifier_job.json', {}) or {}
        ap_state = read_json(STATE, {}) or {}
        evidence['certifier_job'] = {k: job.get(k) for k in ('job_id', 'status', 'pid', 'worker_pid', 'boot_id',
            'started_at', 'finished_at', 'exit_code', 'checkpoint_status', 'starting_game', 'autopilot_owner')}
        evidence['autopilot_state'] = {k: ap_state.get(k) for k in ('status', 'pid', 'process_start_ticks',
            'run_id', 'current_task', 'pause_reason')}
        cert_pid, _ = certifier_active()
        ap_pid, _ = find_autopilot_process()
        checks['no_active_certifier'] = cert_pid is None and job.get('job_id') == BATCH69_JOB_ID and job.get('status') == 'FAILED' and bool(job.get('finished_at'))
        checks['no_active_autopilot'] = ap_pid is None and ap_state.get('status') == 'PAUSED_SAFETY' and ap_state.get('current_task') == 'CERT-BATCH-0069'
        checks['no_partial_transaction'] = not cp.get('current_test')
        if not checks['no_active_certifier'] or not checks['no_active_autopilot'] or not checks['no_partial_transaction']:
            raise RuntimeError('WORKER_OR_TRANSACTION_STILL_ACTIVE')

        txdir = AUDIT / 'runtime' / BATCH69_TX
        manifest = read_json(txdir / 'manifest.json', {}) or {}
        result = read_json(txdir / 'result.json', {}) or {}
        evidence['manifest_status'] = manifest.get('status')
        evidence['result_identity_es_running_game'] = (result.get('identity') or {}).get('es', {}).get('es_running_game')
        checks['manifest_restore_verified'] = bool(manifest.get('transaction_id') == BATCH69_TX and
            manifest.get('status') == 'RESTORE_VERIFIED' and len(manifest.get('entries', [])) == 7)
        checks['emulator_not_started'] = bool(result.get('transaction_id') == BATCH69_TX and
            result.get('process') == {} and result.get('exit') == {} and result.get('failure_class') == 'ES_LAUNCH_PROCESS_ACTIVE' and
            (result.get('identity') or {}).get('es', {}).get('es_running_game') == '/userdata/roms/prboom/doom1_shareware.wad')
        import certification_transaction as transaction
        restored = []
        for entry in manifest.get('entries', []):
            restored.append(transaction.state(Path(entry['path'])) == entry.get('before'))
        checks['restored_paths_match_pre_state'] = bool(restored) and all(restored)
        checks['transaction_result_matches_checkpoint'] = bool(
            result.get('transaction_id') == BATCH69_TX and result.get('system') == 'mrboom' and
            result.get('rom') == '/userdata/roms/mrboom/MrBoom.libretro' and
            result.get('result') == 'SYSTEM_SAFETY_FAILURE' and
            result.get('restore', {}).get('status') == 'RESTORE_VERIFIED')
        if not all(checks.get(k) is True for k in ('manifest_restore_verified', 'emulator_not_started',
                'restored_paths_match_pre_state', 'transaction_result_matches_checkpoint')):
            raise RuntimeError('BATCH69_TRANSACTION_NOT_VERIFIED')

        # Require the exact logged late Doom selector and its normal cancellation.
        selector_log = Path('/userdata/system/logs/controller_selector.log')
        selector_events = []
        for line in selector_log.read_text(encoding='utf-8', errors='replace').splitlines():
            try:
                item = json.loads(line)
            except (ValueError, TypeError):
                continue
            if (item.get('system') in ('prboom', 'mrboom') and
                    item.get('rom') in ('/userdata/roms/prboom/doom1_shareware.wad',
                                        '/userdata/roms/mrboom/MrBoom.libretro') and
                    str(item.get('time', '')).startswith('2026-11-20T23:')):
                selector_events.append(item)
        doom_unmatched = any(x.get('event') == 'automatic_selector_context_no_match' and
            x.get('system') == 'prboom' and x.get('rom') == '/userdata/roms/prboom/doom1_shareware.wad' and
            x.get('reason') == 'SYSTEM_OR_ROM_MISMATCH' and x.get('time') == '2026-11-20T23:39:18-0300'
            for x in selector_events)
        doom_cancelled = any(x.get('event') == 'cancel' and x.get('system') == 'prboom' and
            x.get('rom') == '/userdata/roms/prboom/doom1_shareware.wad' and x.get('time') == '2026-11-20T23:43:08-0300'
            for x in selector_events)
        mrboom_cancelled = any(x.get('event') == 'cancel' and x.get('system') == 'mrboom' and
            x.get('rom') == '/userdata/roms/mrboom/MrBoom.libretro' and x.get('time') == '2026-11-20T23:46:03-0300'
            for x in selector_events)
        evidence['selector_events'] = selector_events
        checks['normal_selector_cancel_verified'] = doom_unmatched and doom_cancelled and mrboom_cancelled
        if not checks['normal_selector_cancel_verified']:
            raise RuntimeError('RESIDUAL_DOOM_SELECTOR_CANCELLATION_NOT_PROVEN')

        rows, _ = cert.load_rows()
        mrboom = next((x for x in rows if x.get('system') == 'mrboom' and x.get('rom') == '/userdata/roms/mrboom/MrBoom.libretro'), None)
        checks['mrboom_csv_still_not_tested'] = bool(mrboom and
            mrboom.get('auto_certification') == 'NOT_TESTED' and mrboom.get('lifecycle_state') == 'NOT_TESTED' and
            mrboom.get('test_id') == BATCH69_TX and mrboom.get('failure_class') == 'ES_LAUNCH_PROCESS_ACTIVE' and
            mrboom.get('restore_status') == 'RESTORE_VERIFIED')
        if not checks['mrboom_csv_still_not_tested']:
            raise RuntimeError('MRBOOM_CSV_TERMINAL_OR_INCONSISTENT')

        latest = {}
        for item in cp.get('results', []):
            latest[(item.get('system'), item.get('rom'))] = item
        active_stops = [x for x in latest.values() if x.get('result') in cert.STOP_ENGINE]
        metrics = cert.certification_metrics(rows, cp)
        evidence['active_stop_result_count'] = len(active_stops)
        evidence['engine_fail_active'] = metrics.get('engine_fail_active')
        checks['only_active_stop_is_reconciled_safety_incident'] = bool(
            len(active_stops) == 1 and active_stops[0].get('transaction_id') == BATCH69_TX and
            metrics.get('engine_fail_active') == cp.get('engine_fail_active') == 1)
        if not checks['only_active_stop_is_reconciled_safety_incident']:
            raise RuntimeError('OTHER_ACTIVE_ENGINE_FAILURE')

        latest_batch = cp.get('latest_batch') or {}
        batch68 = latest.get(('prboom', '/userdata/roms/prboom/doom1_shareware.wad'), {})
        checks['batch68_preserved'] = bool(latest_batch.get('name') == 'priority_batch_68' and
            latest_batch.get('considered') == 41 and latest_batch.get('launched') == 23 and
            latest_batch.get('auto_pass') == 21 and latest_batch.get('game_fail') == 0 and
            latest_batch.get('static_fail') == 0 and latest_batch.get('restore_verified') == '23/23' and
            latest_batch.get('restore_failures') == 0 and batch68.get('transaction_id') == '20261120T233733_b974e9791f' and
            batch68.get('result') == 'AUTO_PASS' and batch68.get('restore', {}).get('status') == 'RESTORE_VERIFIED')
        if not checks['batch68_preserved']:
            raise RuntimeError('BATCH68_CHANGED')

        systems = cert.ad.live_systems()
        queue = cert.queue(rows, systems)
        canonical_next = f"{queue[0]['system']}:{queue[0]['rom']}" if queue else None
        checks['cursor_matches_canonical_queue'] = cp.get('next_untested') == BATCH69_GAME == canonical_next
        evidence['next_game'] = cp.get('next_untested')
        if not checks['cursor_matches_canonical_queue']:
            raise RuntimeError('BATCH69_CURSOR_MISMATCH')

        baseline = result.get('safety_before') or {}
        identity = cert.profile_state()
        checks['logical_p1_p4_stable_identity'] = bool(cert.stable_profile_matches(identity) and
            cert.stable_profile_matches(baseline.get('p1_p4', {})) and
            all(identity[p].get(k) == baseline.get('p1_p4', {}).get(p, {}).get(k)
                for p in ('P1', 'P2', 'P3', 'P4') for k in ('physical_path', 'by_path', 'usb_port', 'device_identity')))
        checks['hdmi_pass'] = cert.get_default_sink() == cert.HDMI == baseline.get('audio_default')
        core, override_count = current_global_overrides()
        current_dispatcher = hashlib.sha256((TOOLS / 'controller_dispatcher').read_bytes()).hexdigest()
        current_profile = hashlib.sha256(Path('/userdata/system/configs/el_gordo_controller_profiles/controller_technical.json').read_bytes()).hexdigest()
        current_multi = hashlib.sha256(Path('/userdata/system/configs/el_gordo_controller_profiles/multiplayer.json').read_bytes()).hexdigest()
        current_conf = hashlib.sha256(Path('/userdata/system/batocera.conf').read_bytes()).hexdigest()
        checks['protected_config_pass'] = bool(current_conf == baseline.get('batocera_conf_sha256') and
            core == baseline.get('global_mame_core') == 'mame078plus' and override_count == 18 and
            current_dispatcher == baseline.get('dispatcher_sha256') and
            current_profile == baseline.get('profile_sha256') and current_multi == baseline.get('multiplayer_sha256'))
        if not checks['hdmi_pass'] or not checks['logical_p1_p4_stable_identity'] or not checks['protected_config_pass']:
            raise RuntimeError('BATCH69_PROTECTED_RUNTIME_GATE_FAIL')

        evidence['result_records_sha256'] = hashlib.sha256(json.dumps(results, ensure_ascii=False,
            sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        evidence['batch_progress_sha256'] = hashlib.sha256(json.dumps(batch, ensure_ascii=False,
            sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        evidence['csv_sha256'] = hashlib.sha256(CERT_CSV.read_bytes()).hexdigest()
        checks['result_evidence_unchanged'] = True
        checks['batch_progress_unchanged'] = True
        checks['batch69_transactions_consistent'] = bool(cp.get('launch_transactions') == 5689 and
            cp.get('result_records') == 6649 and batch.get('considered') == 1 and
            batch.get('launched') == 1 and batch.get('auto_pass') == 0 and batch.get('game_fail') == 0 and
            batch.get('restore_verified') == 1 and batch.get('restore_failures') == 0)
        evidence['passed'] = all(checks.get(k) is True for k in (
            'two_consecutive_clean_runtime_observations', 'es_idle', 'running_game_none', 'marker_absent',
            'selector_absent', 'launcher_absent', 'emulator_absent', 'all_launch_and_emulator_processes_absent',
            'no_active_certifier', 'no_active_autopilot', 'no_partial_transaction', 'manifest_restore_verified',
            'restored_paths_match_pre_state', 'emulator_not_started', 'normal_selector_cancel_verified',
            'batch69_transactions_consistent', 'batch68_preserved', 'mrboom_csv_still_not_tested',
            'cursor_matches_canonical_queue', 'hdmi_pass', 'logical_p1_p4_stable_identity',
            'protected_config_pass', 'only_active_stop_is_reconciled_safety_incident',
            'result_evidence_unchanged', 'batch_progress_unchanged'))
        if not evidence['passed']:
            raise RuntimeError('BATCH69_RUNTIME_GATES_FAILED')
        return evidence
    except Exception as exc:
        evidence['failure'] = type(exc).__name__ + ':' + str(exc)[:180]
        return evidence


def apply_recovered_checkpoint_metadata(cp, recovery):
    before = json.loads(json.dumps(cp))
    cp['status'] = 'STOPPED_SAFE'
    cp['blocked_reason'] = None
    cp['resume_reason'] = recovery['recovery_reason']
    cp['safety_recovery'] = recovery
    cp['updated_at'] = recovery['recovered_at']
    if recovery.get('reconciled_engine_fail_active') == 0:
        cp['engine_fail_active'] = 0
    progress_keys = ('batch_in_progress', 'latest_batch', 'next_untested', 'results',
                     'launch_transactions', 'unique_games_processed', 'result_records',
                     'auto_certified', 'game_fail', 'restore_failures')
    for key in progress_keys:
        if cp.get(key) != before.get(key):
            raise RuntimeError('RECOVERY_PROGRESS_MUTATION:' + key)
    if recovery.get('reconciled_engine_fail_active') != 0 and cp.get('engine_fail_active') != before.get('engine_fail_active'):
        raise RuntimeError('RECOVERY_PROGRESS_MUTATION:engine_fail_active')
    return cp


def reconcile_recovered_safety_block(*, operator_confirmed_normal_selector_cancel=False):
    cp = read_json(CERT_STATE, {}) or {}
    if cp.get('blocked_reason') == 'ES_LAUNCH_PROCESS_ACTIVE':
        results = cp.get('results') if isinstance(cp.get('results'), list) else []
        latest = results[-1] if results else {}
        if latest.get('transaction_id') == BATCH69_TX:
            evidence = batch69_recovered_runtime_evidence(cp)
        else:
            evidence = batch68_recovered_runtime_evidence(
                cp, operator_confirmed_normal_selector_cancel=operator_confirmed_normal_selector_cancel)
    else:
        evidence = recovered_runtime_evidence(cp)
    allowed, reason, recovery = recovered_safety_plan(cp, evidence)
    if not allowed:
        print('RECOVERY: FAIL:' + str(reason))
        print('EVIDENCE: ' + json.dumps(evidence, ensure_ascii=False, sort_keys=True))
        return 3
    stamp = dt.datetime.now().strftime('%Y%m%dT%H%M%S')
    backup_dir = AUDIT / 'recovery_backups' / ('safety_checkpoint_' + stamp)
    backup_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    shutil.copy2(CERT_STATE, backup_dir / CERT_STATE.name)
    cp = apply_recovered_checkpoint_metadata(cp, recovery)
    atomic_json(CERT_STATE, cp)
    append_event('RECOVERED_SAFETY_BLOCK_RECONCILED', **recovery,
                 checkpoint_backup=str(backup_dir / CERT_STATE.name))
    print('RECOVERY: PASS')
    print('CHECKPOINT: STOPPED_SAFE')
    print('BATCH: ' + str((cp.get('batch_in_progress') or {}).get('name')) + '; progress preserved')
    print('NEXT_GAME: ' + str(cp.get('next_untested')))
    print('LAST_RESTORE: RESTORE_VERIFIED:' + str(recovery.get('last_restored_transaction') or recovery.get('transaction_id') or POST_REBOOT_TX))
    return 0


def report_reconciled():
    cp = read_json(CERT_STATE, {}) or {}
    if cp.get('status') != 'COMPLETE' or cp.get('blocked_reason') or cp.get('batch_in_progress'):
        return False, 'CHECKPOINT_NOT_COMPLETE'
    try:
        sys.path.insert(0, str(TOOLS))
        import full_game_certifier as cert
        rows, _ = cert.load_rows()
        systems = cert.ad.live_systems()
        metrics = cert.assert_reconciled_queue(rows, cp, systems)
        return True, metrics
    except Exception as exc:
        return False, type(exc).__name__ + ':' + str(exc)[:180]


def get_cert_job_status():
    try:
        p = subprocess.run([str(CERT_JOB), 'status'], capture_output=True, text=True, timeout=8)
    except Exception as exc:
        return {'status': 'FAILED', 'error': type(exc).__name__}
    if p.returncode:
        return {'status': 'FAILED', 'error': p.stdout.strip()[-200:]}
    out = p.stdout.strip()
    if out == 'NOT_RUNNING':
        return {'status': 'NOT_RUNNING'}
    try:
        return json.loads(out)
    except ValueError:
        return {'status': 'UNKNOWN', 'detail': out[-200:]}


def _batch_index(value):
    match = re.search(r'(\d+)$', str(value or ''))
    return int(match.group(1)) if match else None


def _parse_time(value):
    try:
        return dt.datetime.fromisoformat(str(value).replace('Z', '+00:00')).astimezone(dt.timezone.utc)
    except (TypeError, ValueError):
        return None


def summary_matches_checkpoint(cp, path=None):
    path = Path(path or (AUDIT / 'FULL_GAME_CERTIFICATION_SUMMARY.md'))
    try:
        summary = path.read_text(encoding='utf-8')
    except OSError:
        return False
    expected = {
        'AUTO_CERTIFIED': cp.get('auto_certified'),
        'GAME_FAIL': cp.get('game_fail'),
        'STATIC_FAIL': cp.get('static_fail'),
        'NEEDS_REPAIR': cp.get('needs_repair'),
        'ENGINE_FAIL_ACTIVE': cp.get('engine_fail_active'),
        'NEXT_GAME': cp.get('next_untested') or 'NONE',
    }
    for key, value in expected.items():
        match = re.search(r'^\s*[-*]?\s*' + re.escape(key) + r'\s*:\s*(.*?)\s*$', summary, re.M)
        if not match or match.group(1).strip('`') != str(value):
            return False
    return True


def reconcile_report_recovery():
    """Close Batch 59 only when its failed job is proven to be post-processing-only."""
    autopilot_pid = find_autopilot_process()[0]
    certifier_pid = certifier_active()[0]
    if autopilot_pid or certifier_pid:
        raise RuntimeError('REPORT_RECOVERY_RUNTIME_PROCESS_ACTIVE:' +
                           str(autopilot_pid) + ':' + str(certifier_pid))
    cp = read_json(CERT_STATE, {}) or {}
    was_paused_for_reports = (cp.get('status') == 'PAUSED_REPORT_RECONCILIATION' and
                              cp.get('blocked_reason') == 'CURRENT_STATE_RECONCILIATION_FAIL')
    already_checkpoint_complete = (cp.get('status') == 'COMPLETE' and
                                   not cp.get('blocked_reason'))
    if (not (was_paused_for_reports or already_checkpoint_complete) or
            cp.get('batch_in_progress') or int(cp.get('engine_fail_active', 0)) or
            int(cp.get('restore_failures', 0))):
        raise RuntimeError('REPORT_RECOVERY_CHECKPOINT_STATE_MISMATCH')
    latest = cp.get('latest_batch') or {}
    expected = {'name': 'priority_batch_59', 'considered': 100, 'launched': 100,
                'auto_pass': 100, 'game_fail': 0, 'static_fail': 0,
                'restore_verified': '100/100', 'restore_failures': 0,
                'engine_failures_unresolved': 0}
    if any(latest.get(key) != value for key, value in expected.items()):
        raise RuntimeError('REPORT_RECOVERY_BATCH_TOTALS_MISMATCH')

    meta_path = AUDIT / 'jobs' / 'certifier_job.json'
    meta = read_json(meta_path, {}) or {}
    job_view = get_cert_job_status()
    if (meta.get('status') != 'FAILED' or meta.get('exit_code') != 5 or
            meta.get('checkpoint_status') != 'PAUSED_REPORT_RECONCILIATION' or
            job_view.get('status') != 'FAILED' or job_view.get('pid_state') != 'STALE'):
        raise RuntimeError('REPORT_RECOVERY_JOB_NOT_POSTPROCESS_FAILURE')
    log_path = Path(meta.get('log_path') or '')
    try:
        log_text = log_path.read_text(encoding='utf-8', errors='replace')
    except OSError as exc:
        raise RuntimeError('REPORT_RECOVERY_JOB_LOG_UNAVAILABLE') from exc
    if ('REPORT_RECONCILIATION_PASS' not in log_text or
            'CURRENT_STATE_RECONCILIATION_FAIL' not in log_text):
        raise RuntimeError('REPORT_RECOVERY_JOB_LOG_CAUSE_MISMATCH')

    sys.path.insert(0, str(TOOLS))
    import rebuild_priority_batch_report as batch_report
    import full_game_certifier as cert
    rows, _ = cert.load_rows()
    _, batch_results, _, _ = batch_report.batch_records(cp, rows)
    resume_started = _parse_time(meta.get('started_at'))
    pre_resume = sum(1 for item in batch_results
                     if _parse_time(item.get('finished_at')) and
                     _parse_time(item.get('finished_at')) < resume_started) if resume_started else -1
    resume_selected = len(batch_results) - pre_resume
    if (pre_resume != 1 or resume_selected != 99 or cp.get('selected_count') != 99 or
            meta.get('batch_size') != 99 or meta.get('requested_batch_size') != 100):
        raise RuntimeError('REPORT_RECOVERY_RESUME_ACCOUNTING_MISMATCH')
    report = AUDIT / 'reports' / 'PRIORITY_CERTIFICATION_BATCH_59.md'
    if report.read_text(encoding='utf-8') != batch_report.render_report(cp, rows):
        raise RuntimeError('REPORT_RECOVERY_BATCH_REPORT_STALE')
    if not summary_matches_checkpoint(cp):
        raise RuntimeError('REPORT_RECOVERY_SUMMARY_MISMATCH')
    summary = (AUDIT / 'FULL_GAME_CERTIFICATION_SUMMARY.md').read_text(encoding='utf-8')
    if ('CURRENT_INVOCATION_SELECTED_COUNT: 99' not in summary or
            'considerados 100; lanzados 100; AUTO_PASS 100; restore 100/100' not in summary):
        raise RuntimeError('REPORT_RECOVERY_INVOCATION_OR_BATCH_SEMANTICS_MISMATCH')
    current = (AUDIT / 'ARCADE_CURRENT_STATE.md').read_text(encoding='utf-8')
    live_identity = cert.profile_state()
    if not cert.stable_profile_matches(live_identity):
        raise RuntimeError('REPORT_RECOVERY_LIVE_CONTROLLER_IDENTITY_FAIL')
    for player, port in cert.EXPECTED_ARCADE_USB.items():
        item = live_identity[player]
        if (f'USB{port}' not in current or item.get('physical_path') not in current or
                item.get('by_path') not in current or item.get('event') not in current or
                item.get('js') not in current):
            raise RuntimeError('REPORT_RECOVERY_CURRENT_STATE_STALE:' + player)
    recovery = cp.get('safety_recovery') or {}
    checks = recovery.get('runtime_checks') or {}
    state = read_json(STATE, {}) or {}
    runtime = (state.get('last_safety_check') or {}).get('runtime') or {}
    if (checks.get('protected_semantic_config_matches') is not True or
            checks.get('protected_config_matches') is not True or
            runtime.get('HDMI') != 'alsa_output.pci-0000_01_00.1.hdmi-stereo'):
        raise RuntimeError('REPORT_RECOVERY_PROTECTED_CONFIG_OR_HDMI_NOT_VERIFIED')

    backup_dir = AUDIT / 'recovery_backups' / ('batch59_report_recovery_' +
                 dt.datetime.now().strftime('%Y%m%dT%H%M%S'))
    backup_dir.mkdir(parents=True, exist_ok=False)
    master_path = AUDIT / 'arcade_master_checkpoint.json'
    for path in (CERT_STATE, master_path, TASKS, STATE, meta_path):
        if path.is_file():
            shutil.copy2(path, backup_dir / path.name)

    if was_paused_for_reports:
        cp['status'] = 'COMPLETE'
        cp['blocked_reason'] = None
        master = read_json(master_path, {}) or {}
        phase = master.get('phases', {}).get('PHASE_14_FULL_GAME_CERTIFICATION', {})
        from certification_batch_accounting import phase_summary
        phase['summary'] = phase_summary(latest, cp.get('auto_certified'), cp.get('next_untested'))
        phase['updated_at'] = now()
        atomic_json(CERT_STATE, cp)
        atomic_json(master_path, master)

    task_obj = load_tasks(create=False)
    result = finish_batch(task_obj, 'CERT-BATCH-0059', state)
    if not result:
        raise RuntimeError('REPORT_RECOVERY_BATCH_FINALIZATION_FAILED')
    state.update({'status': 'STOPPED', 'pause_reason': None, 'current_task': None,
                  'pause_requested': False, 'stop_requested': False,
                  'next_action': 'Publicar Batch 59; Batch 60 sigue esperando el publish task.'})
    atomic_json(STATE, state)
    master = read_json(master_path, {}) or {}
    phase_summary_text = master.get('phases', {}).get('PHASE_14_FULL_GAME_CERTIFICATION', {}).get('summary', '')
    print('BATCH_59_REPORT_RECOVERY_PASS')
    print('CHECKPOINT: COMPLETE')
    print('BATCH_PRE_RESUME: ' + str(pre_resume))
    print('RESUME_INVOCATION_SELECTED: ' + str(resume_selected))
    print('PHASE_SUMMARY: ' + phase_summary_text)
    print('JOB: FAILED_POSTPROCESS_PRESERVED_UNTIL_PUBLISH')
    print('BACKUP: ' + str(backup_dir))
    return 0


def _batch_publication_artifact_hashes(batch_name):
    number = _batch_index(batch_name)
    if number is None:
        return None
    paths = {
        'checkpoint_hash': AUDIT / 'full_game_certification_checkpoint.json',
        'summary_hash': AUDIT / 'FULL_GAME_CERTIFICATION_SUMMARY.md',
        'batch_report_hash': AUDIT / 'reports' / f'PRIORITY_CERTIFICATION_BATCH_{number}.md',
    }
    result = {}
    for key, path in paths.items():
        try:
            result[key] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            return None
    return result


def write_publication_receipt(batch_name, remote_sha, published_at=None):
    """Persist local evidence tying a verified publisher commit to batch artifacts."""
    number = _batch_index(batch_name)
    hashes = _batch_publication_artifact_hashes(batch_name)
    if (not number or not hashes or not isinstance(remote_sha, str) or
            not re.fullmatch(r'[a-f0-9]{40}', remote_sha)):
        return False
    receipt = {
        'schema_version': 1,
        'batch_name': batch_name,
        'cert_task': f'CERT-BATCH-{number:04d}',
        'publish_task': f'GITHUB-PUBLISH-CERT-BATCH-{number:04d}',
        'remote_sha': remote_sha,
        'published_at': published_at or now(),
        **hashes,
        'verified': True,
    }
    path = AUDIT / 'jobs' / 'publications' / f'{batch_name}.json'
    atomic_json(path, receipt)
    return True


def batch68_prelaunch_queue_refusal_matches(task_id, job, cp, task_obj, log_text, csv_sha256):
    """Recognize only this reconciled Batch 68 job that failed before creating a transaction."""
    if task_id != 'CERT-BATCH-0068':
        return False
    tasks = task_obj.get('tasks', []) if isinstance(task_obj, dict) else []
    task = next((item for item in tasks if item.get('id') == task_id), {})
    authorization = task.get('recovery_retry_authorization') or {}
    import full_game_certifier as cert
    latest = {}
    for item in cp.get('results', []):
        latest[(item.get('system'), item.get('rom'))] = item
    active_stops = [item for item in latest.values() if item.get('result') in cert.STOP_ENGINE]
    recovery_ok = batch68_reconciled_incident_matches(cp, active_stops, csv_sha256)
    batch = cp.get('batch_in_progress') or {}
    return bool(
        recovery_ok and job.get('status') == 'COMPLETE' and job.get('exit_code') == 6 and
        job.get('completion_reason') == 'SAFE_STOP_AT_GAME_BOUNDARY' and
        job.get('checkpoint_status') == 'STOPPED_SAFE' and job.get('starting_game') == BATCH68_GAME and
        job.get('finished_at') and job.get('job_id') == authorization.get('job_id') and
        authorization.get('job_exit_code') == 6 and
        authorization.get('queue_invariant') == 'QUEUE_INVARIANT_FAIL: selected game already has a result' and
        authorization.get('starting_game') == BATCH68_GAME and
        authorization.get('launch_transactions_before') == cp.get('launch_transactions') == 5686 and
        authorization.get('result_records_before') == cp.get('result_records') == 6646 and
        task.get('max_attempts') == 5 and
        ((task.get('attempts') == 4 and task.get('status') == 'READY') or
         (task.get('attempts') == 5 and task.get('status') == 'RUNNING')) and
        authorization.get('allowed_additional_task_attempts') == 2 and
        authorization.get('allowed_new_game_transactions') == 1 and
        batch.get('name') == 'priority_batch_68' and batch.get('considered') == 41 and
        batch.get('launched') == 21 and batch.get('auto_pass') == 20 and batch.get('game_fail') == 0 and
        batch.get('restore_verified') == 21 and batch.get('restore_failures') == 0 and
        cp.get('current_test') is None and cp.get('next_untested') == BATCH68_GAME and
        'QUEUE_INVARIANT_FAIL: selected game already has a result' in log_text)


def previous_job_consumption_check(task_id, job, cp, task_obj, state, *, reconciled=None,
                                   summary_ok=None, publish_state=None, archive_path=None):
    """Validate historical completion before allowing the next batch through the job guard."""
    latest = cp.get('latest_batch') or {}
    batch_name = latest.get('name')
    batch_n = _batch_index(batch_name)
    current_n = _batch_index(task_id)
    if not batch_n or current_n != batch_n + 1:
        return False, 'NOT_IMMEDIATELY_PREVIOUS_BATCH'
    if job.get('status') == 'COMPLETE' and task_id == 'CERT-BATCH-0068':
        meta = read_json(AUDIT / 'jobs' / 'certifier_job.json', {}) or {}
        log_path = Path(meta.get('log_path') or '')
        try:
            log_text = log_path.read_text(encoding='utf-8', errors='replace') if log_path.parent == (AUDIT / 'jobs' / 'logs') else ''
        except OSError:
            log_text = ''
        csv_sha = hashlib.sha256(CERT_CSV.read_bytes()).hexdigest()
        try:
            import full_game_certifier as cert
            rows, _ = cert.load_rows()
            cert.assert_reconciled_queue(rows, cp, cert.ad.live_systems(), 1)
        except Exception:
            return False, 'BATCH68_QUEUE_NOT_RECONCILED'
        if batch68_prelaunch_queue_refusal_matches(task_id, meta, cp, task_obj, log_text, csv_sha):
            return True, 'BATCH68_PRELAUNCH_QUEUE_REFUSAL_RECONCILED'
    if (job.get('status') not in ('COMPLETE', 'CONSUMED') or
            cp.get('status') != 'COMPLETE' or cp.get('blocked_reason') or
            cp.get('batch_in_progress') or int(cp.get('engine_fail_active', 0))):
        return False, 'CHECKPOINT_NOT_CLEAN_COMPLETE'
    # ROM filenames may contain spaces (for example "Magical Pop'n.zip").
    # Reject control/newline characters while keeping the canonical queue cursor.
    if (cp.get('next_untested') not in (None, 'NONE') and
            not re.fullmatch(r'[a-z0-9_-]+:/userdata/roms/[^\r\n\x00]+', str(cp.get('next_untested')))):
        return False, 'NEXT_GAME_INVALID'
    job_id = job.get('job_id')
    if not isinstance(job_id, str) or not re.fullmatch(r'\d{8}T\d{6}_[a-f0-9]{8}', job_id):
        return False, 'JOB_ID_INVALID'
    meta = read_json(AUDIT / 'jobs' / 'certifier_job.json', {}) or {}
    recovered_postprocess = (
        meta.get('status') == 'CONSUMED' and meta.get('original_status') == 'FAILED' and
        meta.get('exit_code') == 5 and
        (meta.get('postprocess_reconciliation') or {}).get('verified') is True)
    normal_complete = (meta.get('status') in ('COMPLETE', 'CONSUMED') and
                       meta.get('exit_code') == 0)
    if (meta.get('job_id') != job_id or not (normal_complete or recovered_postprocess) or
            meta.get('checkpoint_status') != 'COMPLETE' or
            not isinstance(meta.get('pid'), int) or meta.get('pid') <= 1 or
            not isinstance(meta.get('worker_pid'), int) or meta.get('worker_pid') <= 1):
        return False, 'JOB_METADATA_INCOMPATIBLE'
    owner = meta.get('autopilot_owner')
    if (not isinstance(owner, dict) or not owner.get('run_id') or
            not isinstance(owner.get('pid'), int) or owner.get('pid') <= 1 or
            not isinstance(owner.get('process_start_ticks'), int) or owner.get('process_start_ticks') <= 0):
        return False, 'JOB_OWNER_IDENTITY_INVALID'
    state_job = (state or {}).get('certifier_job') or {}
    # certifier_job in autopilot_state is a runtime snapshot and can lag the
    # canonical job metadata after a detached worker completes. Cross-check its
    # identity only when it names a different concrete job.
    if state_job.get('job_id') not in (None, job_id):
        return False, 'JOB_STATE_IDENTITY_MISMATCH'
    job_cursor = job.get('NEXT_GAME') or meta.get('next_game')
    if (job_cursor not in (None, 'NONE') and
            not re.fullmatch(r'[a-z0-9_-]+:/userdata/roms/[^\r\n\x00]+', str(job_cursor))):
        return False, 'JOB_CURSOR_INVALID'
    if latest.get('next_game') not in (None, cp.get('next_untested')):
        return False, 'JOB_CURSOR_MISMATCH'
    if meta.get('batch_name') and meta.get('batch_name') != batch_name:
        return False, 'JOB_BATCH_MISMATCH'
    if not meta.get('batch_name'):
        started, finished = _parse_time(meta.get('started_at')), _parse_time(meta.get('finished_at'))
        batch_started, batch_finished = _parse_time(latest.get('started_at')), _parse_time(latest.get('finished_at'))
        if not all((started, finished, batch_started, batch_finished)) or started < batch_started or \
                finished < batch_finished or (finished - batch_finished).total_seconds() > 600:
            return False, 'JOB_BATCH_IDENTITY_UNPROVEN'
    cert_task = next((x for x in task_obj.get('tasks', []) if x.get('id') == f'CERT-BATCH-{batch_n:04d}'), None)
    publish_task = next((x for x in task_obj.get('tasks', [])
                         if x.get('id') == f'GITHUB-PUBLISH-CERT-BATCH-{batch_n:04d}'), None)
    if not cert_task or cert_task.get('status') != 'COMPLETE':
        return False, 'CERTIFICATION_TASK_NOT_COMPLETE'
    if not publish_task or publish_task.get('status') != 'COMPLETE':
        return False, 'PUBLISH_TASK_NOT_COMPLETE'
    if reconciled is None:
        reconciled, _ = report_reconciled()
    if not reconciled:
        return False, 'SUMMARY_NOT_RECONCILED'
    if summary_ok is None:
        summary_ok = summary_matches_checkpoint(cp)
    if not summary_ok:
        return False, 'SUMMARY_NOT_RECONCILED'
    pub = publish_state if publish_state is not None else (read_json(AUDIT / 'github_publish_state.json', {}) or {})
    remote_sha = pub.get('last_known_remote_sha')
    recorded_sha = (state or {}).get('last_github_sha')
    if (not isinstance(remote_sha, str) or not re.fullmatch(r'[a-f0-9]{40}', remote_sha) or
            remote_sha != pub.get('last_successful_publish_sha') or
            (recorded_sha is not None and not re.fullmatch(r'[a-f0-9]{40}', str(recorded_sha)))):
        return False, 'PUBLISH_SHA_UNVERIFIED'
    receipt_path = AUDIT / 'jobs' / 'publications' / f'{batch_name}.json'
    receipt = read_json(receipt_path, {}) or {}
    expected_hashes = _batch_publication_artifact_hashes(batch_name)
    if (not expected_hashes or receipt.get('batch_name') != batch_name or
            receipt.get('cert_task') != f'CERT-BATCH-{batch_n:04d}' or
            receipt.get('publish_task') != f'GITHUB-PUBLISH-CERT-BATCH-{batch_n:04d}' or
            receipt.get('remote_sha') != remote_sha or receipt.get('verified') is not True or
            any(receipt.get(k) != v for k, v in expected_hashes.items())):
        return False, 'PUBLICATION_RECEIPT_INVALID'
    if job.get('status') == 'CONSUMED':
        expected_archive = Path(archive_path or (AUDIT / 'jobs' / 'history' / f'{job_id}.json'))
        archived = read_json(expected_archive, {}) or {}
        expected_archive_status = 'FAILED' if recovered_postprocess else 'COMPLETE'
        expected_consumer = (f'GITHUB-PUBLISH-CERT-BATCH-{batch_n:04d}'
                             if recovered_postprocess else task_id)
        if (meta.get('consumed_by_task') != expected_consumer or
                meta.get('archive_path') != str(expected_archive) or
                archived.get('job_id') != job_id or archived.get('status') != expected_archive_status or
                (recovered_postprocess and
                 (archived.get('postprocess_reconciliation') or {}).get('verified') is not True)):
            return False, 'CONSUMED_JOB_ARCHIVE_INVALID'
    return True, 'PREVIOUS_JOB_COMPLETE_AND_CONSUMED'


def consume_previous_job(task_id, job, cp, task_obj, state):
    valid, reason = previous_job_consumption_check(task_id, job, cp, task_obj, state)
    if not valid:
        return False, reason
    if job.get('status') == 'CONSUMED':
        return True, reason
    meta_path = AUDIT / 'jobs' / 'certifier_job.json'
    meta = read_json(meta_path, {}) or {}
    history = AUDIT / 'jobs' / 'history'
    history.mkdir(parents=True, exist_ok=True, mode=0o700)
    archive = history / f"{meta['job_id']}.json"
    if archive.exists():
        existing = read_json(archive, {}) or {}
        if existing.get('job_id') != meta.get('job_id') or existing.get('status') != 'COMPLETE':
            return False, 'CONSUMED_JOB_ARCHIVE_CONFLICT'
    else:
        archived = dict(meta)
        archived['archived_at'] = now()
        archived['archived_as'] = 'PREVIOUS_JOB_COMPLETE_AND_CONSUMED'
        atomic_json(archive, archived)
    meta.update({'status': 'CONSUMED', 'consumed_at': now(), 'consumed_by_task': task_id,
                 'archive_path': str(archive)})
    atomic_json(meta_path, meta)
    append_event('CERTIFIER_JOB_CONSUMED', task_id=task_id, job_id=meta['job_id'],
                 batch=meta.get('batch_name') or (cp.get('latest_batch') or {}).get('name'),
                 archive_path=str(archive))
    return True, 'PREVIOUS_JOB_COMPLETE_AND_CONSUMED'


def update_task(obj, task_id, **changes):
    for item in obj['tasks']:
        if item['id'] == task_id:
            item.update(changes)
            item['updated_at'] = now()
            return item
    raise RuntimeError('TASK_NOT_FOUND:' + task_id)


def add_next_batch_task(obj, cp):
    batch = cp.get('latest_batch', {}).get('name', 'priority_batch_10')
    match = re.search(r'(\d+)$', batch)
    n = (int(match.group(1)) + 1) if match else 1
    tid = f'CERT-BATCH-{n:04d}'
    if any(x['id'] == tid for x in obj['tasks']):
        return
    obj['tasks'].append(task(tid, 'CERTIFICATION_BATCH', f'Certificar priority_batch_{n}', 'READY', 10,
        automatic=True, source='recalculated queue', reason='Tarea creada sólo después de batch estable y queue reconciliada.',
        next_action='arcade_certifier_job.sh start N', evidence=[str(CERT_STATE), str(CERT_CSV)],
        files=[str(CERT_JOB)], do_not_change=['No repetir identidades terminales', 'No relajar safety gates'],
        success='N juegos procesados o checkpoint de seguridad pausa.', after='Reconciliar reports y publicar.'))


def write_cycle_summary(task_obj, state):
    cp = read_json(CERT_STATE, {}) or {}
    batch = cp.get('latest_batch') or {}
    codex, manual = pending_handoffs(task_obj['tasks'])
    lines = [
        '# ARCADE AUTOPILOT — último ciclo', '',
        f'- Actualizado: {now()}', f'- Batch: {batch.get("name", "NONE")}',
        f'- Considerados: {batch.get("considered", 0)}', f'- Lanzados: {batch.get("launched", 0)}',
        f'- AUTO_PASS: {batch.get("auto_pass", 0)}', f'- GAME_FAIL: {batch.get("game_fail", 0)}',
        f'- STATIC_FAIL: {batch.get("static_fail", 0)}', f'- Restores: {batch.get("restore_verified", 0)}',
        f'- AUTO_CERTIFIED acumulado: {cp.get("auto_certified", 0)}',
        f'- Reparaciones automáticas realizadas: 0 (sin receta revisada)',
        f'- CODEX_REQUIRED pendientes: {len(codex)}', f'- MANUAL_REQUIRED pendientes: {len(manual)}',
        f'- NEXT_GAME: `{cp.get("next_untested", "NONE")}`',
        f'- Safety: {cp.get("status", "UNKNOWN")}; {cp.get("blocked_reason") or "sin bloqueo registrado"}',
        '- GitHub: gestionado por task separada del publisher; SHA verificado en `autopilot_state.json`.',
        f'- Próximo paso: {state.get("next_action", "consultar arcade_autopilot next")}', '',
    ]
    atomic_text(AUDIT / 'reports' / 'AUTOPILOT_STATUS.md', '\n'.join(lines))


def refresh_batch_task(obj, cp):
    """Make a prior fail-closed batch eligible only after canonical safety state is clean."""
    current = cp.get('batch_in_progress') or {}
    latest = cp.get('latest_batch') or {}
    if cp.get('status') == 'STOPPED_SAFE' and current.get('name'):
        batch_name = current['name']
    elif cp.get('status') == 'COMPLETE' and not cp.get('blocked_reason') and not int(cp.get('engine_fail_active', 0)):
        m = re.search(r'(\d+)$', latest.get('name', ''))
        batch_name = 'priority_batch_' + str(int(m.group(1)) + 1) if m else 'priority_batch_1'
    else:
        return
    m = re.search(r'(\d+)$', batch_name)
    tid = f'CERT-BATCH-{int(m.group(1)):04d}' if m else 'CERT-BATCH-UNKNOWN'
    found = next((x for x in obj['tasks'] if x.get('id') == tid), None)
    if found and found.get('status') == 'PAUSED_SAFETY':
        found.update({'status': 'READY', 'last_error': None, 'updated_at': now(),
                      'reason': 'Checkpoint canónico reconciliado y safety gates PASS; reanudación permitida.'})


def batch68_single_transaction_retry_authorized(task_obj, cp, remote_sha=None):
    """Narrow one-game Autopilot limit for the explicitly authorized Doom retry."""
    task = next((x for x in task_obj.get('tasks', []) if x.get('id') == 'CERT-BATCH-0068'), {})
    authorization = (task.get('recovery_retry_authorization') or {}).get('post_fix_retry') or {}
    if remote_sha is None:
        publisher = read_json(AUDIT / 'github_publish_state.json', {}) or {}
        remote_sha = publisher.get('last_known_remote_sha')
    batch = cp.get('batch_in_progress') or {}
    recovery = cp.get('safety_recovery') or {}
    refusals = authorization.get('prelaunch_refusals') or []
    expected_refusals = {
        ('20261120T231924_3dc310ae', 'ENGINE_FAIL_COUNTER_MISMATCH'),
        ('20261120T232753_83f95d7b', 'QUEUE_INVARIANT_FAIL: selected game already has a result'),
    }
    exact_prelaunch_refusal = (
        len(refusals) == len(expected_refusals) and
        {(item.get('run_id'), item.get('reason')) for item in refusals if isinstance(item, dict)} == expected_refusals and
        all(item.get('new_transactions') == 0 and item.get('game_transaction_started') is False
            for item in refusals if isinstance(item, dict)))
    return bool(
        task.get('attempts') == 7 and task.get('max_attempts') == 8 and
        authorization.get('additional_task_attempts') == 3 and exact_prelaunch_refusal and
        authorization.get('additional_game_transactions') == 1 and
        authorization.get('starting_game') == BATCH68_GAME and
        authorization.get('github_sha') == remote_sha and
        authorization.get('launch_transactions_before') == cp.get('launch_transactions') == 5687 and
        authorization.get('result_records_before') == cp.get('result_records') == 6647 and
        authorization.get('batch_launched_before') == batch.get('launched') == 22 and
        authorization.get('batch_auto_pass_before') == batch.get('auto_pass') == 20 and
        authorization.get('batch_game_fail_before') == batch.get('game_fail') == 0 and
        batch.get('name') == 'priority_batch_68' and batch.get('considered') == 41 and
        batch.get('restore_verified') == 22 and batch.get('restore_failures') == 0 and
        cp.get('status') == 'STOPPED_SAFE' and not cp.get('blocked_reason') and
        not cp.get('current_test') and cp.get('engine_fail_active') == 0 and
        cp.get('next_untested') == BATCH68_GAME and
        recovery.get('transaction_id') == BATCH68_RETRY_TX and
        recovery.get('reconciled_engine_fail_active') == 0)


def single_transaction_retry_publish_boundary(state, item):
    """Stop a one-game recovery run only after its own batch publication task."""
    return bool(
        state.get('single_transaction_retry') is True and
        int(state.get('batches_completed', 0)) >= 1 and
        item.get('type') == 'GITHUB_PUBLISH' and
        item.get('id') == 'GITHUB-PUBLISH-CERT-BATCH-0068' and
        item.get('source') == 'CERT-BATCH-0068')


def single_transaction_retry_completion_lock(state):
    return state.get('single_transaction_retry_completed') is True


def recover_unfinished_tasks(obj, job, cp, state):
    """Recover idempotent work; a completed certifier is finalized without relaunch."""
    if job.get('status') == 'RUNNING':
        return
    latest = cp.get('latest_batch') or {}
    match = re.search(r'(\d+)$', latest.get('name', ''))
    completed_id = f'CERT-BATCH-{int(match.group(1)):04d}' if match else None
    for item in obj['tasks']:
        if item.get('status') != 'RUNNING':
            continue
        kind = item.get('type')
        if kind == 'CERTIFICATION_BATCH':
            stopped = cp.get('batch_in_progress') or {}
            stop_match = re.search(r'(\d+)$', stopped.get('name', ''))
            stop_id = f'CERT-BATCH-{int(stop_match.group(1)):04d}' if stop_match else None
            next_batch_id = f'CERT-BATCH-{_batch_index(latest.get("name")) + 1:04d}' if _batch_index(latest.get('name')) else None
            if cp.get('status') == 'STOPPED_SAFE' and item.get('id') == stop_id:
                item.update({'status': 'READY', 'updated_at': now(), 'last_error': None,
                             'next_action': 'Retomar el batch desde el siguiente cursor; el helper calcula el remanente.'})
                continue
            if (job.get('status') == 'COMPLETE' and cp.get('status') == 'COMPLETE' and
                    not cp.get('batch_in_progress') and item.get('id') == completed_id):
                item.update({'status': 'READY', 'updated_at': now(), 'last_error': None,
                             'next_action': 'Finalizar reconcile/reports/publicación del job COMPLETE; no relanzar.'})
            elif (job.get('status') == 'CONSUMED' and cp.get('status') == 'COMPLETE' and
                  not cp.get('batch_in_progress') and item.get('id') == next_batch_id):
                item.update({'status': 'READY', 'updated_at': now(), 'last_error': None,
                             'next_action': 'Revalidar job consumido y continuar con el runner del batch siguiente.'})
            continue
        if kind in ('REPORT_REBUILD', 'GITHUB_PUBLISH', 'CHECKPOINT_RECONCILIATION'):
            item.update({'status': 'READY', 'updated_at': now(), 'last_error': None,
                         'next_action': 'Reintentar tarea idempotente interrumpida por caída del Autopilot.'})


def finish_batch(task_obj, tid, state):
    ok, evidence = report_reconciled()
    if not ok:
        update_task(task_obj, tid, status='PAUSED_SAFETY', last_error=evidence,
                    next_action='No iniciar batch siguiente; reconciliar discrepancia sin alterar resultados históricos.')
        save_tasks(task_obj)
        state.update({'status': 'PAUSED_SAFETY', 'pause_reason': 'CHECKPOINT_RECONCILIATION_FAIL:' + str(evidence),
                      'current_task': tid, 'next_action': 'Reconciliar fuentes canónicas y preservar evidencia.'})
        atomic_json(STATE, state)
        append_event('SAFETY_PAUSE', task_id=tid, reason=state['pause_reason'])
        return False
    try:
        for script in (SUMMARY_BUILDER, STATE_BUILDER):
            p = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=180)
            if p.returncode:
                raise RuntimeError(script.name + ':' + p.stdout[-500:] + p.stderr[-200:])
        completed_ids = list(state.get('completed_batch_ids', []))
        if tid not in completed_ids:
            state['completed_batch_ids'] = completed_ids + [tid]
            state['batches_completed'] = int(state.get('batches_completed', 0)) + 1
            state['games_processed_this_run'] = int(state.get('games_processed_this_run', 0)) + int(
                (read_json(CERT_STATE, {}) or {}).get('latest_batch', {}).get('launched', 0))
            # Persist the idempotency marker before task completion. A restart
            # between these writes can safely rerun reconciliation without
            # incrementing batch counters twice.
            atomic_json(STATE, state)
        update_task(task_obj, tid, status='COMPLETE', last_error=None,
                    evidence=[str(CERT_STATE), str(CERT_CSV), str(AUDIT / 'FULL_GAME_CERTIFICATION_SUMMARY.md')])
        state['last_completed_task'] = tid
        state['current_task'] = None
        state['next_action'] = 'Publicar reportes/checkpoints y recalcular la siguiente tarea.'
        save_tasks(task_obj)
        append_event('BATCH_COMPLETE', task_id=tid, metrics=evidence)
        append_event('TASK_COMPLETE', task_id=tid)
        publish_id = 'GITHUB-PUBLISH-' + tid
        if not any(x['id'] == publish_id for x in task_obj['tasks']):
            task_obj['tasks'].append(task(publish_id, 'GITHUB_PUBLISH', 'Publicar ' + tid + ' y verificar remoto',
                'READY', 5, automatic=True, source=tid,
                reason='Publicación posterior a reconciliación y rebuild del batch.',
                next_action='SECRET_SCAN, PAYLOAD_SCAN, publisher REST y verificación del HEAD remoto.',
                evidence=[str(CERT_STATE), str(AUDIT / 'github_publish_state.json')],
                do_not_change=['No incluir tokens ni datos runtime privados'],
                success='El SHA remoto coincide con el commit publicado.'))
        add_next_batch_task(task_obj, read_json(CERT_STATE, {}) or {})
        save_tasks(task_obj)
        write_cycle_summary(task_obj, state)
        return True
    except Exception as exc:
        update_task(task_obj, tid, status='FAILED', last_error=type(exc).__name__ + ':' + str(exc)[:200])
        save_tasks(task_obj)
        state.update({'status': 'ERROR', 'pause_reason': 'REPORT_REBUILD_FAIL', 'current_task': tid})
        atomic_json(STATE, state)
        append_event('TASK_FAILED', task_id=tid, error=state['pause_reason'])
        return False


def execute_publish(item):
    is_batch59 = item.get('id') == 'GITHUB-PUBLISH-CERT-BATCH-0059'
    message = ('arcade: reconcile resumed batch accounting and controller diagnostics'
               if is_batch59 else 'arcade: publish autopilot status and tasks')
    args = [str(PUBLISHER)]
    if is_batch59:
        args.extend(['--scope', 'incident-batch'])
    args.append(message)
    p = subprocess.run(args, capture_output=True, text=True, timeout=180)
    if p.returncode:
        return False, (p.stdout + p.stderr)[-500:]
    match = re.search(r'^COMMIT SHA: ([a-f0-9]{40})$', p.stdout, re.M)
    observed_head = re.search(r'^REMOTE HEAD: ([a-f0-9]{40})$', p.stdout, re.M)
    state_file = read_json(AUDIT / 'github_publish_state.json', {}) or {}
    remote_sha = state_file.get('last_known_remote_sha')
    committed = ('PUBLISH_PASS' in p.stdout and match and match.group(1) == remote_sha)
    already_published = ('NO_CHANGES' in p.stdout and observed_head and
                         observed_head.group(1) == remote_sha)
    if (not (committed or already_published) or
            state_file.get('last_successful_publish_sha') != remote_sha):
        return False, 'PUBLISH_RESULT_NOT_VERIFIED'
    match = re.fullmatch(r'GITHUB-PUBLISH-CERT-BATCH-(\d{4})', item.get('id', ''))
    if match:
        batch_name = f'priority_batch_{int(match.group(1))}'
        if not write_publication_receipt(batch_name, remote_sha,
                                         state_file.get('last_publish_at')):
            return False, 'PUBLICATION_RECEIPT_CREATE_FAILED'
    return True, {'remote_sha': remote_sha, 'output': p.stdout[-800:]}


def consume_reconciled_postprocess_job(publish_task_id, remote_sha, task_obj, state):
    """Archive a report-only failed job after Batch 59 artifacts are published."""
    if publish_task_id != 'GITHUB-PUBLISH-CERT-BATCH-0059':
        return True
    cp = read_json(CERT_STATE, {}) or {}
    latest = cp.get('latest_batch') or {}
    meta_path = AUDIT / 'jobs' / 'certifier_job.json'
    meta = read_json(meta_path, {}) or {}
    publish_task = next((item for item in task_obj['tasks']
                         if item.get('id') == publish_task_id), None)
    if (not publish_task or publish_task.get('status') != 'COMPLETE' or
            cp.get('status') != 'COMPLETE' or cp.get('blocked_reason') or
            cp.get('batch_in_progress') or latest.get('name') != 'priority_batch_59' or
            latest.get('launched') != 100 or latest.get('auto_pass') != 100 or
            latest.get('restore_verified') != '100/100' or
            meta.get('status') != 'FAILED' or meta.get('exit_code') != 5 or
            meta.get('checkpoint_status') != 'PAUSED_REPORT_RECONCILIATION'):
        raise RuntimeError('FAILED_POSTPROCESS_JOB_RECOVERY_STATE_MISMATCH')
    reconciled, _ = report_reconciled()
    if not reconciled or not summary_matches_checkpoint(cp):
        raise RuntimeError('FAILED_POSTPROCESS_JOB_REPORTS_NOT_RECONCILED')
    publisher = read_json(AUDIT / 'github_publish_state.json', {}) or {}
    receipt_path = AUDIT / 'jobs' / 'publications' / 'priority_batch_59.json'
    receipt = read_json(receipt_path, {}) or {}
    if (remote_sha != publisher.get('last_known_remote_sha') or
            remote_sha != publisher.get('last_successful_publish_sha') or
            receipt.get('remote_sha') != remote_sha or receipt.get('verified') is not True):
        raise RuntimeError('FAILED_POSTPROCESS_JOB_PUBLISH_NOT_VERIFIED')
    log_path = Path(meta.get('log_path') or '')
    log_text = log_path.read_text(encoding='utf-8', errors='replace')
    if ('REPORT_RECONCILIATION_PASS' not in log_text or
            'CURRENT_STATE_RECONCILIATION_FAIL' not in log_text):
        raise RuntimeError('FAILED_POSTPROCESS_JOB_CAUSE_NOT_VERIFIED')
    reconciliation = {
        'verified': True,
        'classification': 'POSTPROCESS_ONLY_CURRENT_STATE_RECONCILIATION',
        'batch_name': 'priority_batch_59',
        'launches': 100,
        'auto_pass': 100,
        'restore_verified': '100/100',
        'report_reconciled': True,
        'summary_reconciled': True,
        'current_state_reconciled': True,
        'remote_sha': remote_sha,
        'verified_at': now(),
    }
    history = AUDIT / 'jobs' / 'history'
    history.mkdir(parents=True, exist_ok=True, mode=0o700)
    archive = history / f"{meta['job_id']}.json"
    if archive.exists():
        raise RuntimeError('FAILED_POSTPROCESS_JOB_ARCHIVE_ALREADY_EXISTS')
    archived = dict(meta)
    archived['postprocess_reconciliation'] = reconciliation
    archived['archived_at'] = now()
    archived['archived_as'] = 'FAILED_POSTPROCESS_RECOVERED_AFTER_BATCH_RECONCILIATION'
    atomic_json(archive, archived)
    meta.update({
        'original_status': 'FAILED', 'status': 'CONSUMED',
        'checkpoint_status': 'COMPLETE', 'consumed_at': now(),
        'consumed_by_task': publish_task_id, 'archive_path': str(archive),
        'postprocess_reconciliation': reconciliation,
    })
    atomic_json(meta_path, meta)
    state_job = dict(state.get('certifier_job') or {})
    state_job.update({'status': 'CONSUMED', 'checkpoint_status': 'COMPLETE',
                      'consumed_at': meta['consumed_at'],
                      'consumed_by_task': publish_task_id,
                      'archive_path': str(archive),
                      'postprocess_reconciliation': reconciliation})
    state['certifier_job'] = state_job
    atomic_json(STATE, state)
    append_event('CERTIFIER_JOB_CONSUMED_POSTPROCESS_RECOVERED',
                 task_id=publish_task_id, job_id=meta['job_id'],
                 archive_path=str(archive), remote_sha=remote_sha)
    return True


def execute_one(item, task_obj, state):
    tid, kind = item['id'], item['type']
    update_task(task_obj, tid, status='RUNNING', attempts=int(item.get('attempts', 0)) + 1,
                last_error=None)
    save_tasks(task_obj)
    state.update({'current_task': tid, 'updated_at': now()})
    atomic_json(STATE, state)
    append_event('TASK_STARTED', task_id=tid, task_type=kind)
    log('TASK_STARTED', task_id=tid, task_type=kind)
    if kind == 'CERTIFICATION_BATCH':
        existing_job = get_cert_job_status()
        if existing_job.get('status') == 'RUNNING':
            cp = read_json(CERT_STATE, {}) or {}
            meta = read_json(AUDIT / 'jobs' / 'certifier_job.json', {}) or {}
            pid = existing_job.get('pid')
            proc = proc_record(pid) if isinstance(pid, int) else None
            if (not proc or str(CERTIFIER) not in proc['cmdline'] or
                    meta.get('job_id') != existing_job.get('job_id') or
                    cp.get('status') != 'RUNNING' or not cp.get('batch_in_progress')):
                update_task(task_obj, tid, status='PAUSED_SAFETY', last_error='RUNNING_CERTIFIER_NOT_ADOPTABLE')
                save_tasks(task_obj)
                state.update({'status': 'PAUSED_SAFETY', 'pause_reason': 'RUNNING_CERTIFIER_NOT_ADOPTABLE'})
                atomic_json(STATE, state)
                append_event('SAFETY_PAUSE', task_id=tid, reason='RUNNING_CERTIFIER_NOT_ADOPTABLE')
                return False
            state['certifier_job'] = existing_job
            append_event('CERTIFIER_ADOPTED', task_id=tid, job_id=existing_job.get('job_id'))
        elif existing_job.get('status') in ('COMPLETE', 'CONSUMED'):
            cp = read_json(CERT_STATE, {}) or {}
            latest = cp.get('latest_batch') or {}
            expected = re.search(r'(\d+)$', latest.get('name', ''))
            complete_id = f'CERT-BATCH-{int(expected.group(1)):04d}' if expected else None
            if (existing_job.get('status') == 'COMPLETE' and complete_id == tid and cp.get('status') == 'COMPLETE' and
                    not cp.get('batch_in_progress') and not cp.get('blocked_reason') and
                    not int(cp.get('engine_fail_active', 0))):
                append_event('CERTIFIER_COMPLETE_RECOVERED', task_id=tid,
                             job_id=existing_job.get('job_id'))
                return finish_batch(task_obj, tid, state)
            valid, consumption_reason = previous_job_consumption_check(tid, existing_job, cp,
                                                                        task_obj, state)
            if not valid:
                update_task(task_obj, tid, status='PAUSED_SAFETY',
                            last_error='COMPLETE_JOB_CHECKPOINT_MISMATCH:' + consumption_reason,
                            next_action='COMPLETE_JOB_CHECKPOINT_MISMATCH:' + consumption_reason +
                                        '; no launch until evidence is reconciled.')
                save_tasks(task_obj)
                failure = 'COMPLETE_JOB_CHECKPOINT_MISMATCH:' + consumption_reason
                state.update({'status': 'PAUSED_SAFETY', 'pause_reason': failure,
                              'next_action': 'Job COMPLETE inesperado o sin reconciliación; no se lanzó ningún juego.'})
                atomic_json(STATE, state)
                append_event('SAFETY_PAUSE', task_id=tid, reason=failure,
                             detail={'subreason': consumption_reason,
                                     'expected': 'snes:/userdata/roms/<valid path; spaces allowed>',
                                     'actual': cp.get('next_untested'),
                                     'sources': [str(CERT_STATE), str(AUDIT / 'jobs' / 'certifier_job.json'),
                                                 str(AUDIT / 'github_publish_state.json')]})
                log('SAFETY_PAUSE', task_id=tid, reason=failure,
                    expected='valid ROM path (spaces allowed)', actual=cp.get('next_untested'))
                return False
            if existing_job.get('status') == 'COMPLETE':
                consumed, consumption_reason = consume_previous_job(tid, existing_job, cp, task_obj, state)
                if not consumed:
                    update_task(task_obj, tid, status='PAUSED_SAFETY',
                                last_error='COMPLETE_JOB_CHECKPOINT_MISMATCH:' + consumption_reason)
                    save_tasks(task_obj)
                    failure = 'COMPLETE_JOB_CHECKPOINT_MISMATCH:' + consumption_reason
                    state.update({'status': 'PAUSED_SAFETY',
                                  'pause_reason': failure,
                                  'next_action': 'No se pudo archivar el job anterior; no se lanzó ningún juego.'})
                    atomic_json(STATE, state)
                    append_event('SAFETY_PAUSE', task_id=tid,
                                 reason=failure, detail={'subreason': consumption_reason,
                                                         'sources': [str(AUDIT / 'jobs' / 'certifier_job.json'),
                                                                     str(AUDIT / 'jobs' / 'history'),
                                                                     str(AUDIT / 'jobs' / 'publications')]})
                    log('SAFETY_PAUSE', task_id=tid, reason=failure)
                    return False
            append_event('PREVIOUS_JOB_COMPLETE_AND_CONSUMED', task_id=tid,
                         job_id=existing_job.get('job_id'))
            existing_job = {'status': 'NOT_RUNNING'}
        if existing_job.get('status') not in ('RUNNING', 'COMPLETE', 'CONSUMED'):
            ok, reason, checks = health_check(include_checkpoint=True, allow_self=True)
            state['last_safety_check'] = checks
            if not ok:
                update_task(task_obj, tid, status='PAUSED_SAFETY', last_error=reason,
                            next_action='Resolver el safety blocker; nunca forzar --resume ni repetir identidades.')
                save_tasks(task_obj)
                state.update({'status': 'PAUSED_SAFETY', 'pause_reason': reason,
                              'next_action': 'Esperar diagnóstico CODEX_REQUIRED.'})
                atomic_json(STATE, state)
                append_event('SAFETY_PAUSE', task_id=tid, reason=reason)
                return False
            batch_size = int(state.get('batch_size', DEFAULT_BATCH_SIZE))
            runner_env = os.environ.copy()
            runner_env['ARCADE_AUTOPILOT_RUN_ID'] = str(state.get('run_id') or '')
            p = subprocess.run([str(CERT_JOB), 'start', str(batch_size)], capture_output=True,
                               text=True, timeout=20, env=runner_env)
            if p.returncode or 'STARTED' not in p.stdout:
                why = (p.stdout + p.stderr)[-250:]
                update_task(task_obj, tid, status='PAUSED_SAFETY', last_error=why)
                save_tasks(task_obj)
                state.update({'status': 'PAUSED_SAFETY', 'pause_reason': 'CERTIFIER_START_REFUSED',
                              'next_action': 'Inspeccionar job runner/checkpoint.'})
                atomic_json(STATE, state)
                append_event('SAFETY_PAUSE', task_id=tid, reason='CERTIFIER_START_REFUSED')
                return False
            state['certifier_job'] = get_cert_job_status()
            append_event('CERTIFIER_STARTED', task_id=tid, job_id=state['certifier_job'].get('job_id'))
        while True:
            time.sleep(POLL_SECONDS)
            st = get_cert_job_status()
            state['certifier_job'] = st
            state['updated_at'] = now()
            atomic_json(STATE, state)
            if state.get('pause_requested') or state.get('stop_requested'):
                subprocess.run([str(CERT_JOB), 'stop-safe'], capture_output=True, text=True, timeout=10)
            if st.get('status') == 'RUNNING':
                continue
            if st.get('status') == 'COMPLETE':
                cp = read_json(CERT_STATE, {}) or {}
                if cp.get('status') == 'STOPPED_SAFE':
                    update_task(task_obj, tid, status='READY', last_error=None,
                                next_action='Retomar el lote parcial desde el siguiente cursor, conservando su límite original.')
                    save_tasks(task_obj)
                    state.update({'current_task': None, 'certifier_job': st, 'updated_at': now()})
                    if state.get('stop_requested'):
                        state.update({'status': 'STOPPED', 'pid': None, 'process_start_ticks': None,
                                      'next_action': 'Reanudar explícitamente con arcade_autopilot resume.'})
                        atomic_json(STATE, state)
                        append_event('AUTOPILOT_STOPPED_SAFE')
                        return True
                    if state.get('single_transaction_retry'):
                        state.update({'stop_requested': True,
                                      'next_action': 'Único retry autorizado terminado en un límite seguro.'})
                        atomic_json(STATE, state)
                        append_event('AUTHORIZED_SINGLE_TRANSACTION_RETRY_COMPLETE', task_id=tid)
                        return True
                    if state.get('pause_requested'):
                        state.update({'status': 'PAUSED', 'pid': None, 'process_start_ticks': None})
                        atomic_json(STATE, state)
                        append_event('AUTOPILOT_PAUSED')
                        return True
                    atomic_json(STATE, state)
                    return True
                if not finish_batch(task_obj, tid, state):
                    return False
                return True
            reason = 'CERTIFIER_FAILED:' + str(st.get('status'))
            update_task(task_obj, tid, status='PAUSED_SAFETY', last_error=reason)
            save_tasks(task_obj)
            state.update({'status': 'PAUSED_SAFETY', 'pause_reason': reason,
                          'next_action': 'Diagnosticar transacción/restore/checkpoint antes de reanudar.'})
            atomic_json(STATE, state)
            append_event('SAFETY_PAUSE', task_id=tid, reason=reason)
            return False
    if kind == 'REPORT_REBUILD':
        ok, reason = report_reconciled()
        if not ok:
            update_task(task_obj, tid, status='PAUSED_SAFETY', last_error=str(reason))
            save_tasks(task_obj)
            state.update({'status': 'PAUSED_SAFETY', 'pause_reason': 'CHECKPOINT_RECONCILIATION_FAIL'})
            atomic_json(STATE, state)
            return False
        for script in (SUMMARY_BUILDER, STATE_BUILDER):
            p = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=180)
            if p.returncode:
                raise RuntimeError(script.name + ':REBUILD_FAILED')
        update_task(task_obj, tid, status='COMPLETE')
        save_tasks(task_obj)
        state['last_completed_task'] = tid
        state['current_task'] = None
        atomic_json(STATE, state)
        append_event('TASK_COMPLETE', task_id=tid)
        return True
    if kind == 'GITHUB_PUBLISH':
        ok, result = execute_publish(item)
        if ok:
            state['last_github_sha'] = result.get('remote_sha')
            update_task(task_obj, tid, status='COMPLETE', evidence=[str(AUDIT / 'github_publish_state.json')])
            append_event('GITHUB_PUBLISHED', task_id=tid, sha=state['last_github_sha'])
            append_event('TASK_COMPLETE', task_id=tid)
            state['last_completed_task'] = tid
            state['current_task'] = None
            atomic_json(STATE, state)
            save_tasks(task_obj)
            if item.get('id') == 'GITHUB-PUBLISH-CERT-BATCH-0059':
                try:
                    consume_reconciled_postprocess_job(item['id'], state['last_github_sha'],
                                                       task_obj, state)
                except Exception as exc:
                    state.update({'status': 'PAUSED_SAFETY',
                                  'pause_reason': 'POSTPROCESS_JOB_CONSUME_FAIL:' + str(exc)[:160],
                                  'current_task': None})
                    atomic_json(STATE, state)
                    append_event('SAFETY_PAUSE', task_id=item['id'],
                                 reason=state['pause_reason'])
                    return False
            return True
        attempts = int(item.get('attempts', 0))
        terminal = attempts >= int(item.get('max_attempts', 3))
        delay = min(3600, 300 * (2 ** max(0, attempts - 1)))
        retry_at = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=delay)).isoformat(timespec='seconds')
        update_task(task_obj, tid, status='FAILED' if terminal else 'READY', last_error=str(result),
                    retry_after=None if terminal else retry_at,
                    next_action='Reintentar tras backoff; certificación local no se revierte.')
        save_tasks(task_obj)
        state['current_task'] = None
        atomic_json(STATE, state)
        append_event('TASK_FAILED', task_id=tid, error='GITHUB_PUBLISH_FAILED', retryable=not terminal)
        return True  # GitHub failure must not stop safe local certification work.
    if kind in ('REPAIR_AUTOMATIC', 'REGRESSION_CHECK'):
        ok, reason, checks = health_check(include_checkpoint=True, allow_self=True)
        state['last_safety_check'] = checks
        if not ok:
            update_task(task_obj, tid, status='PAUSED_SAFETY', last_error=reason)
            save_tasks(task_obj)
            state.update({'status': 'PAUSED_SAFETY', 'pause_reason': reason})
            atomic_json(STATE, state)
            append_event('SAFETY_PAUSE', task_id=tid, reason=reason)
            return False
        if kind == 'REGRESSION_CHECK':
            update_task(task_obj, tid, status='COMPLETE', last_error=None,
                        evidence=[json.dumps(checks, sort_keys=True)])
            state['last_completed_task'] = tid
            state['current_task'] = None
            state['next_action'] = 'Safety review PASS; continuar scheduler.'
            append_event('TASK_COMPLETE', task_id=tid)
        else:
            # No automatic repair is executed without an explicit, reviewed repair recipe.
            update_task(task_obj, tid, status='BLOCKED', last_error='NO_APPROVED_REPAIR_RECIPE')
            state['current_task'] = None
            append_event('TASK_BLOCKED', task_id=tid)
        save_tasks(task_obj)
        atomic_json(STATE, state)
        return True
    raise RuntimeError('AUTOMATION_NOT_IMPLEMENTED:' + kind)


def initial_state():
    return {'schema_version': 1, 'status': 'STOPPED', 'started_at': None, 'updated_at': now(),
            'pid': None, 'process_start_ticks': None, 'run_id': None, 'current_task': None,
            'last_completed_task': None, 'safe_mode': True, 'pause_reason': None,
            'pause_requested': False, 'stop_requested': False, 'batches_completed': 0,
            'games_processed_this_run': 0, 'last_github_sha': None,
            'next_action': 'arcade_autopilot start --dry-run'}


def initialize_state(status='STOPPED', reason=None):
    old = read_json(STATE, {}) or initial_state()
    old.update({'schema_version': 1, 'status': status, 'updated_at': now(),
                'pid': None, 'process_start_ticks': None, 'run_id': None,
                'pause_reason': reason, 'safe_mode': True})
    atomic_json(STATE, old)
    return old


def run_loop(run_id):
    state = read_json(STATE, {}) or initial_state()
    state.update({'status': 'RUNNING', 'run_id': run_id, 'pid': os.getpid(),
                  'started_at': now(), 'updated_at': now(), 'safe_mode': True,
                  'pause_reason': None})
    rec = proc_record(os.getpid())
    state['process_start_ticks'] = rec['start_ticks'] if rec else None
    atomic_json(STATE, state)
    append_event('AUTOPILOT_STARTED', run_id=run_id)
    log('AUTOPILOT_STARTED', run_id=run_id)
    while True:
        state = read_json(STATE, {}) or state
        if state.get('stop_requested'):
            state.update({'status': 'STOPPED', 'pid': None, 'process_start_ticks': None,
                          'updated_at': now(), 'current_task': None,
                          'next_action': 'Reanudar explícitamente con arcade_autopilot resume.'})
            atomic_json(STATE, state)
            append_event('AUTOPILOT_STOPPED_SAFE')
            log('AUTOPILOT_STOPPED_SAFE')
            return 0
        if state.get('pause_requested'):
            state.update({'status': 'PAUSED', 'pid': None, 'process_start_ticks': None,
                          'updated_at': now(), 'next_action': 'arcade_autopilot resume'})
            atomic_json(STATE, state)
            append_event('AUTOPILOT_PAUSED')
            return 0
        job = get_cert_job_status()
        ok, reason, checks = health_check(include_checkpoint=False, allow_self=True,
                                          allow_certifier_pid=job.get('pid') if job.get('status') == 'RUNNING' else None)
        state['last_safety_check'] = checks
        if not ok:
            state.update({'status': 'PAUSED_SAFETY', 'pause_reason': reason,
                          'pid': None, 'process_start_ticks': None, 'updated_at': now(),
                          'next_action': 'Resolver safety blocker; no task launched.'})
            atomic_json(STATE, state)
            append_event('SAFETY_PAUSE', reason=reason)
            log('SAFETY_PAUSE', reason=reason)
            return 3
        obj = load_tasks(create=True)
        write_handoffs(obj['tasks'])
        item = select_task(obj['tasks'])
        if item is None:
            retry_times = []
            for queued in obj['tasks']:
                if queued.get('automatic') and queued.get('status') in ('PENDING', 'READY') and queued.get('retry_after'):
                    try:
                        retry_times.append(dt.datetime.fromisoformat(queued['retry_after']).timestamp())
                    except ValueError:
                        pass
            future = [x for x in retry_times if x > time.time()]
            if future:
                state.update({'status': 'RUNNING', 'updated_at': now(), 'current_task': None,
                              'next_action': 'Esperar backoff para retry seguro.'})
                atomic_json(STATE, state)
                time.sleep(max(1, min(POLL_SECONDS, int(min(future) - time.time()))))
                continue
            codex, manual = pending_handoffs(obj['tasks'])
            status = 'WAITING_CODEX' if codex else ('WAITING_MANUAL' if manual else 'COMPLETE')
            state.update({'status': status, 'pid': None, 'process_start_ticks': None,
                          'updated_at': now(), 'current_task': None,
                          'next_action': str(CODEX_HANDOFF if codex else MANUAL_HANDOFF if manual else 'No tasks pending')})
            atomic_json(STATE, state)
            append_event('CODEX_REQUIRED' if codex else 'MANUAL_REQUIRED' if manual else 'AUTOPILOT_COMPLETE')
            return 0
        if state.get('batches_completed', 0) >= int(state.get('max_batches', DEFAULT_MAX_BATCHES)):
            if state.get('single_transaction_retry'):
                if not single_transaction_retry_publish_boundary(state, item):
                    state.update({'status': 'STOPPED', 'pid': None, 'process_start_ticks': None,
                                  'current_task': None, 'stop_requested': True,
                                  'single_transaction_retry_completed': True,
                                  'next_action': 'Límite del retry único alcanzado; no ejecutar otra tarea/game.'})
                    atomic_json(STATE, state)
                    append_event('AUTHORIZED_SINGLE_TRANSACTION_RETRY_STOPPED_BEFORE_NEXT_TASK',
                                 task_id=item.get('id'), batches_completed=state.get('batches_completed'))
                    return 0
            else:
                ok, reason, checks = health_check(include_checkpoint=True, allow_self=True)
                state['last_safety_check'] = checks
                if not ok:
                    state.update({'status': 'PAUSED_SAFETY', 'pause_reason': 'DEEP_HEALTH_REVIEW:' + str(reason),
                                  'pid': None, 'process_start_ticks': None, 'updated_at': now()})
                    atomic_json(STATE, state)
                    append_event('SAFETY_PAUSE', reason=state['pause_reason'])
                    return 3
                state['batches_completed'] = 0
        try:
            if not execute_one(item, obj, state):
                return 3
            if single_transaction_retry_publish_boundary(state, item):
                state.update({'status': 'STOPPED', 'pid': None, 'process_start_ticks': None,
                              'current_task': None, 'stop_requested': True,
                              'single_transaction_retry_completed': True,
                              'next_action': 'Retry de una transacción completado y publicado; revisión explícita requerida antes de otro batch.'})
                atomic_json(STATE, state)
                append_event('AUTHORIZED_SINGLE_TRANSACTION_RETRY_STOPPED', task_id='CERT-BATCH-0068',
                             published_task=item.get('id'),
                             publish_status=next((x.get('status') for x in obj.get('tasks', [])
                                                  if x.get('id') == item.get('id')), None))
                return 0
        except Exception as exc:
            update_task(obj, item['id'], status='FAILED', last_error=type(exc).__name__ + ':' + str(exc)[:200])
            save_tasks(obj)
            state.update({'status': 'ERROR', 'pause_reason': type(exc).__name__, 'current_task': item['id'],
                          'updated_at': now(), 'pid': None, 'process_start_ticks': None})
            atomic_json(STATE, state)
            append_event('TASK_FAILED', task_id=item['id'], error=type(exc).__name__)
            log('TASK_FAILED', task_id=item['id'], error=type(exc).__name__)
            return 1
        # Avoid a tight loop on retryable GitHub failures or blocked tasks.
        time.sleep(2)


def acquire_lock(nonblocking=True):
    AUDIT.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(str(LOCK), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | (fcntl.LOCK_NB if nonblocking else 0))
    except BlockingIOError:
        os.close(fd)
        raise RuntimeError('AUTOPILOT_ALREADY_RUNNING')
    return fd


def start(batch_size=DEFAULT_BATCH_SIZE, max_batches=DEFAULT_MAX_BATCHES, dry_run=False):
    if not 1 <= batch_size <= MAX_BATCH_SIZE:
        raise RuntimeError('BATCH_SIZE_MUST_BE_1_TO_100')
    if not 1 <= max_batches <= 100:
        raise RuntimeError('MAX_BATCHES_MUST_BE_1_TO_100')
    state = read_json(STATE, {}) or initial_state()
    if single_transaction_retry_completion_lock(state):
        print('SINGLE_TRANSACTION_RETRY_COMPLETE_OPERATOR_REVIEW_REQUIRED')
        return 3
    active_pid, active = find_autopilot_process()
    if active_pid:
        print('AUTOPILOT_ALREADY_RUNNING')
        return 2
    cert_pid, cert_proc = certifier_active()
    job_status = get_cert_job_status()
    obj = load_tasks(create=not dry_run)
    cp = read_json(CERT_STATE, {}) or {}
    one_game_retry = batch68_single_transaction_retry_authorized(obj, cp)
    if one_game_retry:
        batch_size = 1
        max_batches = 1
    recover_unfinished_tasks(obj, job_status, cp, state)
    adopt_task_id = None
    if job_status.get('status') == 'RUNNING':
        meta = read_json(AUDIT / 'jobs' / 'certifier_job.json', {}) or {}
        adoptable = (cert_pid == job_status.get('pid') and cert_proc and
                     str(CERTIFIER) in cert_proc.get('cmdline', '') and
                     cp.get('status') == 'RUNNING' and bool(cp.get('batch_in_progress')) and
                     meta.get('job_id') == job_status.get('job_id'))
        if not adoptable:
            print('CERTIFIER_ALREADY_RUNNING')
            return 2
        current = cp.get('batch_in_progress', {}).get('name', 'priority_batch_unknown')
        match = re.search(r'(\d+)$', current)
        adopt_task_id = f'CERT-BATCH-{int(match.group(1)):04d}' if match else 'CERT-BATCH-UNKNOWN'
        found = next((x for x in obj['tasks'] if x['id'] == adopt_task_id), None)
        if found:
            found.update({'status': 'READY', 'automatic': True, 'priority': 0, 'last_error': None,
                          'next_action': 'Adoptar y monitorizar el job certifier existente; no lanzar otro.'})
        else:
            obj['tasks'].append(task(adopt_task_id, 'CERTIFICATION_BATCH', 'Adoptar batch en curso', 'READY', 0,
                automatic=True, source='detached job recovery', reason='Certifier existente y checkpoint RUNNING; se adopta sin duplicarlo.',
                next_action='Monitorizar el job persistente.', evidence=[str(CERT_STATE)]))
    elif cert_pid:
        print('CERTIFIER_ALREADY_RUNNING')
        return 2
    if not dry_run:
        save_tasks(obj)
    next_game = cp.get('next_untested')
    ok, reason, checks = health_check(include_checkpoint=not bool(adopt_task_id),
                                      allow_certifier_pid=job_status.get('pid') if adopt_task_id else None)
    safe_resume = (cp.get('status') == 'STOPPED_SAFE' and not cp.get('blocked_reason') and
                   isinstance(cp.get('batch_in_progress'), dict) and not int(cp.get('engine_fail_active', 0)))
    cp_ok = ((cp.get('status') == 'RUNNING' and bool(cp.get('batch_in_progress'))) if adopt_task_id else
             ((cp.get('status') == 'COMPLETE' and not cp.get('blocked_reason') and not cp.get('batch_in_progress')
               and not int(cp.get('engine_fail_active', 0))) or safe_resume))
    if ok and cp_ok and not adopt_task_id:
        refresh_batch_task(obj, cp)
        if not dry_run:
            save_tasks(obj)
    next_item = select_task(obj['tasks'])
    previous_job_reason = None
    if (job_status.get('status') in ('COMPLETE', 'CONSUMED') and next_item and
            next_item.get('type') == 'CERTIFICATION_BATCH'):
        previous_job_ok, previous_job_reason = previous_job_consumption_check(
            next_item['id'], job_status, cp, obj, state)
        if not previous_job_ok:
            ok, reason, cp_ok = False, 'COMPLETE_JOB_CHECKPOINT_MISMATCH:' + previous_job_reason, False
    if dry_run:
        print('ARCADE AUTOPILOT DRY RUN')
        print('STATUS: WOULD_ADOPT' if adopt_task_id and ok and cp_ok else 'STATUS: WOULD_START' if ok and cp_ok else 'STATUS: PAUSED_SAFETY')
        next_label = 'NEXT SAFE TASK' if ok and cp_ok else 'NEXT TASK CANDIDATE (SAFETY BLOCKED)'
        print(next_label + ': ' + (next_item['id'] if next_item else 'NONE'))
        print('WOULD START: ' + str(batch_size) + ' games' if next_item and next_item['type'] == 'CERTIFICATION_BATCH' else 'WOULD START: no game batch')
        print('STARTING_GAME: ' + str(next_game or 'BLOCKED/UNKNOWN'))
        print('HEALTH: ' + ('PASS' if ok else 'FAIL:' + str(reason)))
        print('CHECKPOINT: ' + ('PASS' if cp_ok else 'FAIL:' + str(cp.get('status')) + ':' + str(cp.get('blocked_reason'))))
        print('ARCADE_SAFETY: ' + ('PASS' if ok and cp_ok else 'FAIL'))
        if previous_job_reason:
            print('PREVIOUS_JOB: ' + previous_job_reason)
        return 0 if ok and cp_ok else 3
    if not ok or not cp_ok:
        reason = reason if not ok else 'CHECKPOINT_SAFETY_BLOCK:' + str(cp.get('status')) + ':' + str(cp.get('blocked_reason'))
        initialize_state('PAUSED_SAFETY', reason)
        state = read_json(STATE, initial_state())
        state['last_safety_check'] = checks
        state['next_action'] = 'Resolver safety blocker antes de iniciar Autopilot.'
        atomic_json(STATE, state)
        append_event('SAFETY_PAUSE', reason=reason)
        print('PAUSED_SAFETY: ' + reason)
        return 3
    if next_item is None:
        state.update({'status': 'COMPLETE', 'updated_at': now(), 'next_action': 'No hay tarea automática READY.'})
        atomic_json(STATE, state)
        print('NO_AUTOMATABLE_TASK_READY')
        return 0
    try:
        fd = acquire_lock()
    except RuntimeError as exc:
        if str(exc) == 'AUTOPILOT_ALREADY_RUNNING':
            print('AUTOPILOT_ALREADY_RUNNING')
            return 2
        raise
    run_id = dt.datetime.now().strftime('%Y%m%dT%H%M%S') + '_' + uuid.uuid4().hex[:8]
    state = state or initial_state()
    state.update({'schema_version': 1, 'status': 'STARTING', 'started_at': now(), 'updated_at': now(),
                  'safe_mode': True, 'pause_reason': None, 'pause_requested': False,
                  'stop_requested': False, 'current_task': None, 'batch_size': batch_size,
                  'max_batches': max_batches, 'single_transaction_retry': one_game_retry,
                  'run_id': run_id, 'pid': None,
                  'current_task': adopt_task_id})
    atomic_json(STATE, state)
    try:
        proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--worker', run_id],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            close_fds=True, pass_fds=(fd,), start_new_session=True)
        state.update({'status': 'RUNNING', 'pid': proc.pid})
        rec = proc_record(proc.pid)
        state['process_start_ticks'] = rec['start_ticks'] if rec else None
        atomic_json(STATE, state)
        atomic_text(PIDFILE, f'{proc.pid}\n')
    finally:
        os.close(fd)
    print('AUTOPILOT_STARTED')
    print(json.dumps({'pid': state['pid'], 'run_id': run_id, 'status': state['status'],
                      'session_id': proc_record(state['pid']).get('sid') if proc_record(state['pid']) else None,
                      'process_group': proc_record(state['pid']).get('pgid') if proc_record(state['pid']) else None}, indent=2))
    return 0


def command_pause(stop=False):
    state = read_json(STATE, {}) or initial_state()
    active_pid, _ = find_autopilot_process()
    if not active_pid:
        state.update({'status': 'STOPPED', 'updated_at': now(), 'pid': None,
                      'next_action': 'Use resume para iniciar un nuevo proceso.'})
        atomic_json(STATE, state)
        print('NOT_RUNNING')
        return 0
    state['pause_requested'] = not stop
    state['stop_requested'] = bool(stop)
    state['updated_at'] = now()
    if stop:
        # Ask the existing certifier to complete the current transaction/restore first.
        subprocess.run([str(CERT_JOB), 'stop-safe'], capture_output=True, text=True, timeout=10)
        state['next_action'] = 'Stopping safely at the next verified game boundary.'
    else:
        state['next_action'] = 'Pause after current safe boundary; do not start another task.'
    atomic_json(STATE, state)
    print('STOP_SAFE_REQUESTED' if stop else 'PAUSE_REQUESTED')
    return 0


def resume(batch_size=DEFAULT_BATCH_SIZE, max_batches=DEFAULT_MAX_BATCHES):
    state = read_json(STATE, {}) or initial_state()
    pid, _ = find_autopilot_process()
    if pid:
        state.update({'pause_requested': False, 'stop_requested': False, 'status': 'RUNNING',
                      'updated_at': now(), 'pause_reason': None})
        atomic_json(STATE, state)
        print('RESUMED_EXISTING_AUTOPILOT')
        return 0
    return start(batch_size, max_batches, dry_run=False)


def status():
    state = read_json(STATE, {}) or initial_state()
    pid, rec = find_autopilot_process()
    if pid:
        current_status = 'RUNNING'
    else:
        current_status = state.get('status', 'STOPPED')
        if current_status == 'RUNNING':
            current_status = 'ERROR'  # dead PID with a previously running state
    cp = read_json(CERT_STATE, {}) or {}
    batch = cp.get('batch_in_progress') or cp.get('latest_batch') or {}
    tasks_obj = load_tasks(create=False)
    tasks = tasks_obj['tasks']
    codex, manual = pending_handoffs(tasks)
    job = get_cert_job_status()
    gh = read_json(AUDIT / 'github_publish_state.json', {}) or {}
    latest = cp.get('latest_batch', {})
    next_safe = select_task(tasks)
    autopilot_elapsed = None
    if pid and state.get('started_at'):
        try:
            started = dt.datetime.fromisoformat(str(state['started_at']).replace('Z', '+00:00'))
            autopilot_elapsed = max(0, int((dt.datetime.now(dt.timezone.utc) - started).total_seconds()))
        except (TypeError, ValueError):
            pass
    safety_ok = ((cp.get('status') == 'COMPLETE' and not cp.get('blocked_reason') and
                  not cp.get('batch_in_progress')) or
                 (cp.get('status') == 'STOPPED_SAFE' and not cp.get('blocked_reason') and
                  isinstance(cp.get('batch_in_progress'), dict)) or
                 (cp.get('status') == 'RUNNING' and not cp.get('blocked_reason') and
                  isinstance(cp.get('batch_in_progress'), dict) and job.get('status') == 'RUNNING')) and \
                not int(cp.get('engine_fail_active', 0))
    task_label = 'next_safe_task' if safety_ok else 'next_task_candidate'
    result = {
        'status': current_status, 'pid': pid, 'session_id': rec.get('sid') if rec else None,
        'process_group': rec.get('pgid') if rec else None,
        'current_task': state.get('current_task'), 'last_completed_task': state.get('last_completed_task'),
        task_label: next_safe.get('id') if next_safe else None,
        'batch_name': batch.get('name'), 'batch': f"{batch.get('launched',0)}/{batch.get('considered',0)}",
        'current_game': job.get('current_game') or cp.get('current_test'),
        'last_game': batch.get('last_game'), 'certifier_pid': job.get('pid'),
        'certifier_pid_state': job.get('pid_state', 'UNKNOWN'),
        'certifier_elapsed_seconds': job.get('elapsed_seconds'), 'autopilot_elapsed_seconds': autopilot_elapsed,
        'AUTO_PASS': batch.get('auto_pass', 0), 'GAME_FAIL': batch.get('game_fail', 0),
        'RESTORES': batch.get('restore_verified', 0), 'AUTO_CERTIFIED': cp.get('auto_certified'),
        'CODEX_TASKS': len(codex), 'MANUAL_TASKS': len(manual),
        'certifier_status': job.get('status'), 'next_game': cp.get('next_untested'),
        'github_sha': gh.get('last_known_remote_sha'), 'pause_reason': state.get('pause_reason'),
        'next_action': ('Certifier activo; continuar monitorizando el checkpoint y RESTORE_VERIFIED.'
                        if current_status == 'RUNNING' and job.get('status') == 'RUNNING' and safety_ok else
                        state.get('next_action') or ('Sin acción pendiente.' if safety_ok else 'Resolver safety blocker.')),
        'last_batch': latest.get('name'),
        'arcade_safety': 'PASS' if safety_ok else 'FAIL:' + str(cp.get('status')) + ':' + str(cp.get('blocked_reason')),
    }
    print('ARCADE AUTOPILOT\n================')
    for key, value in result.items():
        print(f'{key.upper()}: {value}')
    return 0


def tasks_summary():
    tasks = load_tasks(create=True)['tasks']
    counts = {s: sum(1 for x in tasks if x['status'] == s) for s in
              ('READY', 'RUNNING', 'CODEX_REQUIRED', 'MANUAL_REQUIRED', 'FAILED', 'BLOCKED', 'PAUSED_SAFETY', 'COMPLETE')}
    print('ARCADE AUTOPILOT TASKS')
    for name, count in counts.items():
        print(f'{name}: {count}')
    for item in sorted(tasks, key=lambda x: (x['priority'], x['id'])):
        if item['status'] in ('READY', 'RUNNING', 'CODEX_REQUIRED', 'MANUAL_REQUIRED', 'FAILED', 'PAUSED_SAFETY'):
            print(f"- {item['id']} [{item['status']}] {item['title']}")
    return 0


def next_task():
    tasks = load_tasks(create=True)['tasks']
    active_pid, _ = find_autopilot_process()
    if active_pid:
        state = read_json(STATE, {}) or initial_state()
        print(f"AUTOPILOT RUNNING PID={active_pid}; CURRENT_TASK={state.get('current_task') or 'NONE'}")
        print('Use arcade_autopilot status for live progress; no second task will start.')
        return 0
    item = select_task(tasks)
    ok, reason, _ = health_check(include_checkpoint=True)
    if not ok:
        print('AUTOPILOT PAUSED_SAFETY: ' + str(reason))
        if item:
            print(f"NEXT TASK CANDIDATE (NOT SAFE TO START): {item['id']} — {item['title']}")
        codex, manual = pending_handoffs(tasks)
        if codex:
            print(f"CODEX_REQUIRED: {codex[0]['id']} — {codex[0]['title']}")
            print('HANDOFF: ' + str(CODEX_HANDOFF))
        elif manual:
            print(f"MANUAL_REQUIRED: {manual[0]['id']} — {manual[0]['title']}")
            print('HANDOFF: ' + str(MANUAL_HANDOFF))
        return 3
    if item:
        print(f"NEXT SAFE TASK: {item['id']} [{item['status']}] — {item['title']}")
        print('ACTION: ' + str(item.get('next_action')))
        return 0
    codex, manual = pending_handoffs(tasks)
    if codex:
        print(f"CODEX_REQUIRED: {codex[0]['id']} — {codex[0]['title']}")
        print('HANDOFF: ' + str(CODEX_HANDOFF))
    elif manual:
        print(f"MANUAL_REQUIRED: {manual[0]['id']} — {manual[0]['title']}")
        print('HANDOFF: ' + str(MANUAL_HANDOFF))
    else:
        print('NO_TASK_READY')
    return 0


def publish_reconciled_batch59():
    """Run only the ready Batch 59 publication task; never starts certification."""
    if find_autopilot_process()[0]:
        print('AUTOPILOT_ALREADY_ACTIVE')
        return 3
    task_obj = load_tasks(create=False)
    if not task_obj:
        print('TASKS_UNAVAILABLE')
        return 3
    item = next((x for x in task_obj.get('tasks', [])
                 if x.get('id') == 'GITHUB-PUBLISH-CERT-BATCH-0059'), None)
    if not item or item.get('status') not in ('READY', 'PENDING'):
        print('BATCH59_PUBLISH_TASK_NOT_READY')
        return 3
    selected = select_task(task_obj['tasks'])
    if not selected or selected.get('id') != item.get('id'):
        print('BATCH59_PUBLISH_TASK_NOT_NEXT')
        return 3
    ok, reason, checks = health_check(include_checkpoint=True)
    if not ok:
        print('ARCADE_SAFETY: FAIL ' + str(reason))
        return 3
    state = read_json(STATE, {}) or initial_state()
    state['last_safety_check'] = checks
    if not execute_one(item, task_obj, state):
        print('BATCH59_PUBLISH_LIFECYCLE_FAIL')
        return 3
    print('BATCH59_PUBLISH_LIFECYCLE_PASS')
    print('GITHUB_SHA: ' + str(state.get('last_github_sha')))
    print('JOB: ' + str((read_json(AUDIT / 'jobs' / 'certifier_job.json', {}) or {}).get('status')))
    next_item = select_task(task_obj['tasks'])
    print('NEXT_TASK: ' + (next_item.get('id') if next_item else 'NONE'))
    return 0


def show_log(lines=100):
    if not 1 <= lines <= 1000:
        raise RuntimeError('LOG_LINES_MUST_BE_1_TO_1000')
    try:
        from collections import deque
        with LOG.open(encoding='utf-8', errors='replace') as stream:
            for line in deque(stream, maxlen=lines):
                print(line, end='')
    except FileNotFoundError:
        print('NO_LOG')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog='arcade_autopilot')
    subs = parser.add_subparsers(dest='action', required=True)
    s = subs.add_parser('start'); s.add_argument('--dry-run', action='store_true')
    s.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE); s.add_argument('--max-batches', type=int, default=DEFAULT_MAX_BATCHES)
    subs.add_parser('status'); l = subs.add_parser('log'); l.add_argument('lines', nargs='?', type=int, default=100)
    recovery = subs.add_parser('reconcile-recovered-safety', help='Reconciliar blockers ES recuperables tras verificar runtime y restore')
    recovery.add_argument('--normal-selector-cancel-confirmed', action='store_true',
                          help='Confirmar que el selector de Batch 68 se canceló normalmente en la interfaz local')
    subs.add_parser('reconcile-report-recovery', help='Cerrar Batch 59 tras validar sólo su post-procesamiento')
    subs.add_parser('publish-reconciled-batch59', help='Completar el publish task ya publicado y consumir su job reconciliado')
    subs.add_parser('pause'); subs.add_parser('resume')
    st = subs.add_parser('stop-safe'); st.add_argument('--unused', action='store_true', help=argparse.SUPPRESS)
    subs.add_parser('tasks'); subs.add_parser('next')
    args = parser.parse_args(argv)
    if args.action == 'start': return start(args.batch_size, args.max_batches, args.dry_run)
    if args.action == 'status': return status()
    if args.action == 'reconcile-recovered-safety':
        return reconcile_recovered_safety_block(
            operator_confirmed_normal_selector_cancel=args.normal_selector_cancel_confirmed)
    if args.action == 'reconcile-report-recovery': return reconcile_report_recovery()
    if args.action == 'publish-reconciled-batch59': return publish_reconciled_batch59()
    if args.action == 'log': return show_log(args.lines)
    if args.action == 'pause': return command_pause(False)
    if args.action == 'resume': return resume()
    if args.action == 'stop-safe': return command_pause(True)
    if args.action == 'tasks': return tasks_summary()
    if args.action == 'next': return next_task()
    return 2


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == '--worker':
        try:
            sys.exit(run_loop(sys.argv[2]))
        except Exception as exc:
            state = read_json(STATE, {}) or initial_state()
            state.update({'status': 'ERROR', 'pause_reason': type(exc).__name__,
                          'updated_at': now(), 'pid': None, 'process_start_ticks': None})
            atomic_json(STATE, state)
            append_event('AUTOPILOT_ERROR', error=type(exc).__name__)
            log('AUTOPILOT_ERROR', error=type(exc).__name__)
            sys.exit(1)
    try:
        sys.exit(main())
    except Exception as exc:
        print(type(exc).__name__ + ': ' + str(exc)[:250], file=sys.stderr)
        sys.exit(1)
