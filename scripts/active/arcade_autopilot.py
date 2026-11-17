#!/usr/bin/env python3
"""Deterministic, fail-closed coordinator for the Arcade Audit workflow."""
import argparse
import csv
import datetime as dt
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
        if rec and str(CERTIFIER) in rec['cmdline']:
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


def previous_job_consumption_check(task_id, job, cp, task_obj, state, *, reconciled=None,
                                   summary_ok=None, publish_state=None, archive_path=None):
    """Validate historical completion before allowing the next batch through the job guard."""
    latest = cp.get('latest_batch') or {}
    batch_name = latest.get('name')
    batch_n = _batch_index(batch_name)
    current_n = _batch_index(task_id)
    if not batch_n or current_n != batch_n + 1:
        return False, 'NOT_IMMEDIATELY_PREVIOUS_BATCH'
    if (job.get('status') not in ('COMPLETE', 'CONSUMED') or
            cp.get('status') != 'COMPLETE' or cp.get('blocked_reason') or
            cp.get('batch_in_progress') or int(cp.get('engine_fail_active', 0))):
        return False, 'CHECKPOINT_NOT_CLEAN_COMPLETE'
    if (cp.get('next_untested') not in (None, 'NONE') and
            not re.fullmatch(r'[a-z0-9_-]+:/userdata/roms/[^\s]+', str(cp.get('next_untested')))):
        return False, 'NEXT_GAME_INVALID'
    job_id = job.get('job_id')
    if not isinstance(job_id, str) or not re.fullmatch(r'\d{8}T\d{6}_[a-f0-9]{8}', job_id):
        return False, 'JOB_ID_INVALID'
    meta = read_json(AUDIT / 'jobs' / 'certifier_job.json', {}) or {}
    if (meta.get('job_id') != job_id or meta.get('status') not in ('COMPLETE', 'CONSUMED') or
            meta.get('exit_code') != 0 or meta.get('checkpoint_status') != 'COMPLETE' or
            not isinstance(meta.get('pid'), int) or meta.get('pid') <= 1 or
            not isinstance(meta.get('worker_pid'), int) or meta.get('worker_pid') <= 1):
        return False, 'JOB_METADATA_INCOMPATIBLE'
    owner = meta.get('autopilot_owner')
    if (not isinstance(owner, dict) or not owner.get('run_id') or
            not isinstance(owner.get('pid'), int) or owner.get('pid') <= 1 or
            not isinstance(owner.get('process_start_ticks'), int) or owner.get('process_start_ticks') <= 0):
        return False, 'JOB_OWNER_IDENTITY_INVALID'
    state_job = (state or {}).get('certifier_job') or {}
    for key in ('job_id', 'pid', 'worker_pid'):
        if state_job.get(key) != job.get(key):
            return False, 'JOB_STATE_IDENTITY_MISMATCH'
    if job.get('NEXT_GAME') not in (None, cp.get('next_untested')):
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
    if job.get('status') == 'CONSUMED':
        expected_archive = Path(archive_path or (AUDIT / 'jobs' / 'history' / f'{job_id}.json'))
        archived = read_json(expected_archive, {}) or {}
        if (meta.get('consumed_by_task') != task_id or meta.get('archive_path') != str(expected_archive) or
                archived.get('job_id') != job_id or archived.get('status') != 'COMPLETE'):
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
        update_task(task_obj, tid, status='COMPLETE', last_error=None,
                    evidence=[str(CERT_STATE), str(CERT_CSV), str(AUDIT / 'FULL_GAME_CERTIFICATION_SUMMARY.md')])
        state['batches_completed'] = int(state.get('batches_completed', 0)) + 1
        state['games_processed_this_run'] = int(state.get('games_processed_this_run', 0)) + int((read_json(CERT_STATE, {}) or {}).get('latest_batch', {}).get('launched', 0))
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
    message = 'arcade: publish autopilot status and tasks'
    p = subprocess.run([str(PUBLISHER), message], capture_output=True, text=True, timeout=180)
    if p.returncode:
        return False, (p.stdout + p.stderr)[-500:]
    state_file = read_json(AUDIT / 'github_publish_state.json', {}) or {}
    return True, {'remote_sha': state_file.get('last_known_remote_sha'), 'output': p.stdout[-800:]}


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
                            last_error='COMPLETE_JOB_CHECKPOINT_MISMATCH',
                            next_action='COMPLETE_JOB_CHECKPOINT_MISMATCH; no launch until evidence is reconciled.')
                save_tasks(task_obj)
                state.update({'status': 'PAUSED_SAFETY', 'pause_reason': 'COMPLETE_JOB_CHECKPOINT_MISMATCH',
                              'next_action': 'Job COMPLETE inesperado o sin reconciliación; no se lanzó ningún juego.'})
                atomic_json(STATE, state)
                append_event('SAFETY_PAUSE', task_id=tid, reason='COMPLETE_JOB_CHECKPOINT_MISMATCH',
                             detail=consumption_reason)
                return False
            if existing_job.get('status') == 'COMPLETE':
                consumed, consumption_reason = consume_previous_job(tid, existing_job, cp, task_obj, state)
                if not consumed:
                    update_task(task_obj, tid, status='PAUSED_SAFETY',
                                last_error='COMPLETE_JOB_CHECKPOINT_MISMATCH')
                    save_tasks(task_obj)
                    state.update({'status': 'PAUSED_SAFETY',
                                  'pause_reason': 'COMPLETE_JOB_CHECKPOINT_MISMATCH',
                                  'next_action': 'No se pudo archivar el job anterior; no se lanzó ningún juego.'})
                    atomic_json(STATE, state)
                    append_event('SAFETY_PAUSE', task_id=tid,
                                 reason='COMPLETE_JOB_CHECKPOINT_MISMATCH', detail=consumption_reason)
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
    active_pid, active = find_autopilot_process()
    if active_pid:
        print('AUTOPILOT_ALREADY_RUNNING')
        return 2
    cert_pid, cert_proc = certifier_active()
    job_status = get_cert_job_status()
    obj = load_tasks(create=not dry_run)
    cp = read_json(CERT_STATE, {}) or {}
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
                  'max_batches': max_batches, 'run_id': run_id, 'pid': None,
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
    subs.add_parser('pause'); subs.add_parser('resume')
    st = subs.add_parser('stop-safe'); st.add_argument('--unused', action='store_true', help=argparse.SUPPRESS)
    subs.add_parser('tasks'); subs.add_parser('next')
    args = parser.parse_args(argv)
    if args.action == 'start': return start(args.batch_size, args.max_batches, args.dry_run)
    if args.action == 'status': return status()
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
