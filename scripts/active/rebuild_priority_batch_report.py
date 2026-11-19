#!/usr/bin/env python3
"""Regenerate the latest priority batch report from canonical results."""
import csv
import datetime as dt
import json
import os
import tempfile
from collections import Counter
from pathlib import Path

AUDIT = Path('/userdata/system/state/arcade_audit')
CHECKPOINT = AUDIT / 'full_game_certification_checkpoint.json'
TABLE = AUDIT / 'full_game_certification.csv'


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, 0o644)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def batch_records(checkpoint, rows, expected_name='priority_batch_59'):
    batch = checkpoint.get('latest_batch') or {}
    if batch.get('name') != expected_name:
        raise RuntimeError('LATEST_BATCH_NAME_MISMATCH')
    start = dt.datetime.fromisoformat(batch['started_at'])
    finish = dt.datetime.fromisoformat(batch['finished_at'])
    selected = []
    for result in checkpoint.get('results', []):
        txid = result.get('transaction_id')
        stamped = result.get('finished_at')
        if not txid or not stamped:
            continue
        at = dt.datetime.fromisoformat(stamped)
        if start <= at <= finish:
            selected.append(result)
    selected.sort(key=lambda item: item['finished_at'])
    unique = {(item.get('system'), item.get('rom')) for item in selected}
    txids = [item.get('transaction_id') for item in selected]
    if len(selected) != 100 or len(unique) != 100 or len(set(txids)) != 100:
        raise RuntimeError('BATCH_59_TRANSACTION_SET_NOT_100_UNIQUE')
    counts = Counter(item.get('result') for item in selected)
    restores = Counter((item.get('restore') or {}).get('status') for item in selected)
    if counts != Counter({'AUTO_PASS': 100}):
        raise RuntimeError('BATCH_59_RESULT_SET_MISMATCH')
    if restores != Counter({'RESTORE_VERIFIED': 100}):
        raise RuntimeError('BATCH_59_RESTORE_SET_MISMATCH')
    csv_by_tx = {row.get('test_id'): row for row in rows if row.get('test_id')}
    for item in selected:
        row = csv_by_tx.get(item['transaction_id'])
        if (not row or row.get('system') != item.get('system') or row.get('rom') != item.get('rom') or
                row.get('auto_certification') != 'AUTO_CERTIFIED' or
                row.get('test_result') != 'AUTO_PASS' or row.get('restore_status') != 'RESTORE_VERIFIED'):
            raise RuntimeError('BATCH_59_CSV_TRANSACTION_MISMATCH')
    first_launch = selected[0]
    last_launch = selected[-1]
    if (last_launch.get('rom') != batch.get('last_game') or
            batch.get('next_game') != checkpoint.get('next_untested')):
        raise RuntimeError('BATCH_59_CURSOR_OR_LAST_GAME_MISMATCH')
    expected = {
        'considered': 100, 'launched': 100, 'auto_pass': 100, 'game_fail': 0,
        'static_fail': 0, 'restore_verified': '100/100', 'restore_failures': 0,
    }
    if any(batch.get(key) != value for key, value in expected.items()):
        raise RuntimeError('BATCH_59_CUMULATIVE_SUMMARY_MISMATCH')
    return batch, selected, first_launch, last_launch


def render_report(checkpoint, rows):
    batch, selected, first_launch, last_launch = batch_records(checkpoint, rows)
    candidate = batch.get('first_game') or 'UNKNOWN'
    next_game = checkpoint.get('next_untested')
    lines = [
        f"# Certificación prioritaria — {batch['name']}", '',
        f"- Considerados: {batch['considered']}",
        f"- Lanzados: {batch['launched']}",
        f"- AUTO_PASS: {batch['auto_pass']}",
        f"- GAME_FAIL: {batch['game_fail']}",
        f"- STATIC_FAIL: {batch['static_fail']}",
        f"- Restores: {batch['restore_verified']}",
        f"- Restore failures: {batch['restore_failures']}",
        f"- AUTO_CERTIFIED: {checkpoint.get('auto_certified')}",
        f"- Primer candidato seleccionado: `{candidate}`",
        f"- Primera transacción lanzada: `{first_launch['system']}:{first_launch['rom']}`",
        f"- Última transacción lanzada: `{last_launch['system']}:{last_launch['rom']}`",
        f"- Transacciones únicas verificadas desde checkpoint y CSV: {len(selected)}",
        f"- NEXT_GAME: `{next_game}`", '',
    ]
    return '\n'.join(lines)


def main():
    checkpoint = json.loads(CHECKPOINT.read_text(encoding='utf-8'))
    rows = read_csv(TABLE)
    text = render_report(checkpoint, rows)
    output = AUDIT / 'reports/PRIORITY_CERTIFICATION_BATCH_59.md'
    atomic_write(output, text)
    print('BATCH_REPORT_RECONCILIATION_PASS')
    print(output)


if __name__ == '__main__':
    main()
