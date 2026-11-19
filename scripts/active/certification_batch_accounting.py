"""Pure helpers for separating invocation counts from cumulative batch counts."""


def new_batch_progress(name, considered, first_game, started_at):
    return {
        'name': name,
        'considered': considered,
        'launched': 0,
        'auto_pass': 0,
        'game_fail': 0,
        'static_fail': 0,
        'flaky': 0,
        'adapter_pending': 0,
        'skipped': 0,
        'deferred': 0,
        'other_unlaunched': 0,
        'processed': 0,
        'restore_verified': 0,
        'restore_failures': 0,
        'started_at': started_at,
        'first_game': first_game,
        'last_game': None,
    }


def record_batch_result(progress, result):
    """Add one result to cumulative progress; never infer counts from selection."""
    progress['launched'] = progress.get('launched', 0) + bool(result.get('transaction_id'))
    restore = (result.get('restore') or {}).get('status')
    progress['restore_verified'] = progress.get('restore_verified', 0) + (restore == 'RESTORE_VERIFIED')
    progress['restore_failures'] = progress.get('restore_failures', 0) + (restore == 'RESTORE_FAILURE')
    result_type = result.get('result')
    for field, expected in (('auto_pass', 'AUTO_PASS'), ('game_fail', 'GAME_FAIL'),
                            ('static_fail', 'STATIC_FAIL'), ('flaky', 'FLAKY')):
        progress[field] = progress.get(field, 0) + (result_type == expected)
    progress['last_game'] = result.get('rom')
    progress['processed'] = progress.get('processed', 0) + 1
    if not result.get('transaction_id'):
        if result_type == 'ADAPTER_NOT_READY':
            progress['adapter_pending'] = progress.get('adapter_pending', 0) + 1
        elif result_type in ('SKIPPED', 'NOT_ELIGIBLE', 'PRECHECK_SKIPPED',
                             'ALREADY_TERMINAL', 'CONTENT_MISSING', 'UNSUPPORTED'):
            progress['skipped'] = progress.get('skipped', 0) + 1
        elif result_type == 'DEFERRED':
            progress['deferred'] = progress.get('deferred', 0) + 1
        elif result_type != 'STATIC_FAIL':
            progress['other_unlaunched'] = progress.get('other_unlaunched', 0) + 1


def set_invocation_selection(checkpoint, selected):
    """Record current invocation selection; selected_count is a legacy alias."""
    checkpoint['invocation_selected_count'] = selected
    checkpoint['selected_count'] = selected


def phase_summary(batch, auto_certified, next_game):
    name = batch.get('name', 'priority_batch_unknown')
    return (f"{name}: {batch.get('considered', 0)} considerados, "
            f"{batch.get('launched', 0)} lanzados, {batch.get('auto_pass', 0)} AUTO_PASS, "
            f"{batch.get('game_fail', 0)} GAME_FAIL, {batch.get('static_fail', 0)} STATIC_FAIL; "
            f"restores {batch.get('restore_verified', '0/0')}; "
            f"AUTO_CERTIFIED={auto_certified}; NEXT_GAME={next_game}")


def invocation_selection_line(checkpoint):
    selected = checkpoint.get('invocation_selected_count', checkpoint.get('selected_count'))
    if selected is None:
        return '- CURRENT_INVOCATION_SELECTED_COUNT: no registrado.'
    return (f'- CURRENT_INVOCATION_SELECTED_COUNT: {selected} '
            '(selección de la invocación más reciente; no es el total acumulado del batch).')
