#!/usr/bin/env python3
"""Regenerate the universal certification summary from canonical audit state."""
import csv
import json
import os
import re
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

AUDIT = Path('/userdata/system/state/arcade_audit')
TABLE = AUDIT / 'full_game_certification.csv'
CHECKPOINT = AUDIT / 'full_game_certification_checkpoint.json'
MASTER = AUDIT / 'arcade_master_checkpoint.json'
SYSTEMS = AUDIT / 'data/detected_systems.csv'
OUTPUTS = [AUDIT / 'FULL_GAME_CERTIFICATION_SUMMARY.md', AUDIT / 'reports/FULL_GAME_CERTIFICATION_SUMMARY.md']


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, 0o644)
        os.replace(temp, path)
        dfd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def count(rows, field, value):
    return sum(1 for row in rows if row.get(field) == value)


def main():
    rows = read_csv(TABLE)
    cp = json.loads(CHECKPOINT.read_text(encoding='utf-8'))
    master = json.loads(MASTER.read_text(encoding='utf-8'))
    systems = read_csv(SYSTEMS) if SYSTEMS.exists() else []

    auto = count(rows, 'auto_certification', 'AUTO_CERTIFIED')
    controls = sum(row.get('control_certification') == 'CONTROL_CERTIFIED' for row in rows)
    guest = sum(row.get('guest_ready') == 'YES' for row in rows)
    static_fail = count(rows, 'auto_certification', 'STATIC_FAIL')
    game_fail = count(rows, 'auto_certification', 'GAME_FAIL')
    flaky = count(rows, 'auto_certification', 'FLAKY')
    needs_repair = count(rows, 'lifecycle_state', 'NEEDS_REPAIR')
    attempted = cp.get('attempted_new')
    tx_results = cp.get('results', [])
    result_records = len(tx_results)
    result_keys = {(x.get('system'), x.get('rom')) for x in tx_results}
    unique_games = len(result_keys)
    launch_transactions = sum(bool(x.get('transaction_id')) for x in tx_results)
    retry_transactions = max(0, launch_transactions - len({(x.get('system'), x.get('rom')) for x in tx_results if x.get('transaction_id')}))
    static_preflight_results = sum(x.get('result') == 'STATIC_FAIL' for x in tx_results)
    engine_fail_total = sum(x.get('result') == 'ENGINE_FAIL' for x in tx_results)
    # A prior engine-class result is historical if the same identity later has
    # a successful terminal result. Keep the total separately from active cases.
    latest_by_key = {}
    for item in tx_results:
        latest_by_key[(item.get('system'), item.get('rom'))] = item
    engine_states = {'ENGINE_FAIL','WRONG_GAME_DISPATCH','AUDIO_ROUTE_CHANGED','RESTORE_FAILURE'}
    engine_fail_active = sum(item.get('result') in engine_states for item in latest_by_key.values())
    next_game = cp.get('next_untested') or 'NONE'
    total_restores = sum(1 for item in tx_results if item.get('transaction_id') and item.get('restore', {}).get('status') == 'RESTORE_VERIFIED')
    restore_failures = sum(1 for item in tx_results if item.get('restore', {}).get('status') == 'RESTORE_FAILURE')
    adapter_ready = sum(row.get('adapter_status') == 'READY' for row in systems)
    adapter_pending = sum(row.get('adapter_status') != 'READY' for row in systems)
    historical = sum(bool(row.get('boot_core')) for row in rows)
    installed = count(rows, 'installed', 'YES')

    mismatches = []
    for label, actual, expected in (
        ('auto_certified', auto, cp.get('auto_certified')),
        ('attempted_new_transactions', attempted, launch_transactions),
        ('unique_games_processed', unique_games, cp.get('unique_games_processed')),
        ('result_records', result_records, cp.get('result_records')),
        ('retry_transactions', retry_transactions, cp.get('retry_transactions')),
        ('control_certified', controls, cp.get('manual_control_certified')),
        ('guest_ready', guest, cp.get('guest_ready')),
    ):
        if actual != expected:
            mismatches.append(f'{label}:table={actual},checkpoint={expected}')
    if cp.get('counts', {}).get('AUTO_PASS') != auto:
        mismatches.append(f"counts.AUTO_PASS={cp.get('counts', {}).get('AUTO_PASS')},table.AUTO_CERTIFIED={auto}")
    master_phase = master.get('phases', {}).get('PHASE_14_FULL_GAME_CERTIFICATION', {})
    if master_phase.get('status') not in ('RUNNING', 'COMPLETE', 'COMPLETE_WITH_ISSUES', 'MANUAL_REQUIRED'):
        mismatches.append('master certification phase has unknown status')

    per_system = defaultdict(lambda: defaultdict(int))
    for row in rows:
        stat = per_system[row.get('system') or 'unknown']
        stat['TOTAL'] += 1
        stat['INSTALLED'] += row.get('installed') == 'YES'
        stat['HISTORICAL_BOOT_OK'] += bool(row.get('boot_core'))
        stat['AUTO_CERTIFIED'] += row.get('auto_certification') == 'AUTO_CERTIFIED'
        stat['STATIC_FAIL'] += row.get('auto_certification') == 'STATIC_FAIL'
        stat['GAME_FAIL'] += row.get('auto_certification') == 'GAME_FAIL'
        stat['FLAKY'] += row.get('auto_certification') == 'FLAKY'
        stat['CONTROL_CERTIFIED'] += row.get('control_certification') == 'CONTROL_CERTIFIED'
        stat['GUEST_READY'] += row.get('guest_ready') == 'YES'
        stat['NOT_TESTED'] += row.get('auto_certification') in ('NOT_TESTED', '')

    lines = [
        '# Certificación completa de juegos — estado actual', '',
        f"- UPDATED_AT: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- TOTAL_INVENTORY: {len(rows)}",
        f"- INSTALLED: {installed}",
        f"- HISTORICAL_BOOT_OK: {historical}",
        f"- ATTEMPTED_NEW: {attempted}",
        f"- UNIQUE_GAMES_PROCESSED: {unique_games}",
        f"- RESULT_RECORDS: {result_records}",
        f"- LAUNCH_TRANSACTIONS: {launch_transactions}",
        f"- RETRY_TRANSACTIONS: {retry_transactions}",
        f"- STATIC_PREFLIGHT_RESULTS: {static_preflight_results}",
        f"- AUTO_CERTIFIED: {auto}",
        f"- STATIC_FAIL: {static_fail}",
        f"- GAME_FAIL: {game_fail}",
        f"- FLAKY: {flaky}",
        f"- NEEDS_REPAIR: {needs_repair}",
        f"- CONTROL_CERTIFIED: {controls}",
        f"- GUEST_READY: {guest}",
        f"- ADAPTERS_READY: {adapter_ready}",
        f"- ADAPTERS_PENDING: {adapter_pending}",
        f"- NEXT_GAME: {next_game}",
        f"- TOTAL_RESTORES: {total_restores}",
        f"- RESTORE_FAILURES: {restore_failures}",
        f"- ENGINE_FAIL_TOTAL_HISTORICAL: {engine_fail_total}",
        f"- ENGINE_FAIL_ACTIVE: {engine_fail_active}",
        f"- CERTIFICATION_PHASE: {master_phase.get('status', 'UNKNOWN')}", '',
        'Los resultados históricos (`HISTORICAL_BOOT_OK`) se mantienen separados de la nueva auto-certificación. `AUTO_CERTIFIED` no certifica botones físicos. `GUEST_READY` permanece sujeto a certificación de controles y salida.', '',
        '## Conteos por sistema', '',
        '| Sistema | TOTAL | INSTALLED | HISTORICAL_BOOT_OK | AUTO_CERTIFIED | STATIC_FAIL | GAME_FAIL | FLAKY | CONTROL_CERTIFIED | GUEST_READY | NOT_TESTED |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    cols = ('TOTAL', 'INSTALLED', 'HISTORICAL_BOOT_OK', 'AUTO_CERTIFIED', 'STATIC_FAIL', 'GAME_FAIL', 'FLAKY', 'CONTROL_CERTIFIED', 'GUEST_READY', 'NOT_TESTED')
    for system in sorted(per_system):
        stat = per_system[system]
        lines.append('| ' + system + ' | ' + ' | '.join(str(stat[c]) for c in cols) + ' |')
    lines += ['', '## Último lote y reanudación', '']
    latest = cp.get('latest_batch') or {}
    lines.append(f"- Lote más reciente: {latest.get('name', 'sin lote registrado')}; considerados {latest.get('considered', 'N/D')}; lanzados {latest.get('launched', 'N/D')}; AUTO_PASS {latest.get('auto_pass', 'N/D')}; restore {latest.get('restore_verified', 'N/D')}.")
    lines.append(f"- Estado de runner: {cp.get('status', 'UNKNOWN')}.")
    lines.append(f"- NEXT_GAME: {next_game}.")
    lines.append('- No se promovieron juegos a `GUEST_READY` ni a `CONTROL_CERTIFIED` por un resultado automático.')
    lines += ['', '## HISTORY', '', 'Los totales anteriores se excluyeron de la cabecera. La columna histórica se deriva del campo `boot_core` conservado en el CSV canónico.', '']
    text = '\n'.join(lines)

    # Parse the rendered summary itself before replacing the current report.
    def parse_int(label):
        match = re.search(rf'^- {re.escape(label)}: (\d+)$', text, re.MULTILINE)
        return int(match.group(1)) if match else None
    parsed_auto = parse_int('AUTO_CERTIFIED')
    parsed_attempted = parse_int('ATTEMPTED_NEW')
    parsed_controls = parse_int('CONTROL_CERTIFIED')
    parsed_guest = parse_int('GUEST_READY')
    m = re.search(r'^- NEXT_GAME: (.*)$', text, re.MULTILINE)
    parsed_next = m.group(1) if m else None
    if (parsed_auto != cp.get('auto_certified') or parsed_attempted != cp.get('attempted_new')
            or parsed_next != next_game or parsed_controls != controls or parsed_guest != guest):
        mismatches.append('rendered markdown reconciliation failed')
    if mismatches:
        print('REPORT_RECONCILIATION_FAIL')
        for item in mismatches:
            print(item)
        return 2

    for path in OUTPUTS:
        atomic_write(path, text + '\n')
    print('REPORT_RECONCILIATION_PASS')
    print(json.dumps({'total_inventory': len(rows), 'installed': installed, 'historical_boot_ok': historical,
        'attempted_new': attempted, 'unique_games_processed': unique_games, 'result_records': result_records,
        'launch_transactions': launch_transactions, 'retry_transactions': retry_transactions,
        'static_preflight_results': static_preflight_results, 'engine_fail_total_historical': engine_fail_total,
        'engine_fail_active': engine_fail_active, 'auto_certified': auto, 'static_fail': static_fail, 'game_fail': game_fail,
        'flaky': flaky, 'needs_repair': needs_repair, 'control_certified': controls, 'guest_ready': guest,
        'adapters_ready': adapter_ready, 'adapters_pending': adapter_pending, 'next_game': next_game,
        'total_restores': total_restores, 'restore_failures': restore_failures}, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    sys.exit(main())
