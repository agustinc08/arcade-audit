import importlib.util
import json
import os
import tempfile
import unittest
import sys
import contextlib
import io
import ast
import importlib.util
from pathlib import Path
from unittest import mock

SCRIPT = Path('/userdata/system/el_gordo_tools/arcade_autopilot.py')
SPEC = importlib.util.spec_from_file_location('arcade_autopilot_tested', SCRIPT)
AP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AP)
RUNNER_PATH = Path('/userdata/system/el_gordo_tools/arcade_certifier_job.py')
RUNNER_SPEC = importlib.util.spec_from_file_location('arcade_certifier_job_tested', RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(RUNNER)
sys.path.insert(0, '/userdata/system/el_gordo_tools')
import full_game_certifier as CERT


class AutopilotTests(unittest.TestCase):
    def recovered_checkpoint_fixture(self):
        return {
            'status': 'PAUSED_SYSTEM_SAFETY_FAILURE',
            'blocked_reason': 'RuntimeError: ES_NOT_IDLE',
            'engine_fail_active': 0,
            'next_untested': AP.POST_REBOOT_GAME,
            'batch_in_progress': {'name': 'priority_batch_59', 'considered': 100,
                'launched': 1, 'auto_pass': 1, 'game_fail': 0, 'static_fail': 0,
                'flaky': 0, 'restore_verified': 1, 'restore_failures': 0,
                'adapter_pending': 13, 'unprocessed': 86},
        }

    def recovered_evidence_fixture(self):
        checks = {key: True for key in (
            'no_engine_fail', 'marker_absent', 'launch_processes_absent',
            'no_active_certifier', 'historical_failed_job_preserved',
            'es_idle', 'running_game_none', 'last_result_restore_verified',
            'manifest_restore_verified', 'protected_config_matches',
            'protected_semantic_config_matches', 'logical_p1_p4_stable_identity',
            'mame_overrides_expected', 'queue_checkpoint_reconciled')}
        return {'passed': True, 'current_boot_id': 'boot-new', 'previous_boot_id': 'boot-old',
                'checks': checks, 'last_restored_transaction': AP.POST_REBOOT_TX}

    def controller_identity_fixture(self):
        ports = {'P1': '5', 'P2': '6', 'P3': '8', 'P4': '7'}
        return {player: {'expected_usb_port': port, 'usb_port': port,
                         'physical_path': f'pci-0000:00:14.0-usb-0:{port}:1.0',
                         'by_path': f'/dev/input/by-path/pci-0000:00:14.0-usb-0:{port}:1.0-event-joystick',
                         'device_identity': {'vendor_id': '0079', 'product_id': '0006',
                                             'name': 'DragonRise Inc. Generic USB Joystick'},
                         'event': f'/dev/input/event{17 + i}', 'js': f'/dev/input/js{i}'}
                for i, (player, port) in enumerate(ports.items())}

    def test_stable_controller_identity_ignores_event_renumber(self):
        state = self.controller_identity_fixture()
        state['P1']['event'] = '/dev/input/event18'
        state['P2']['event'] = '/dev/input/event19'
        state['P3']['event'] = '/dev/input/event21'
        state['P4']['event'] = '/dev/input/event20'
        self.assertTrue(CERT.stable_profile_matches(state))

    def test_stable_controller_identity_rejects_physical_swap(self):
        state = self.controller_identity_fixture()
        state['P1']['physical_path'], state['P2']['physical_path'] = (
            state['P2']['physical_path'], state['P1']['physical_path'])
        state['P1']['by_path'], state['P2']['by_path'] = (
            state['P2']['by_path'], state['P1']['by_path'])
        state['P1']['usb_port'], state['P2']['usb_port'] = '6', '5'
        self.assertFalse(CERT.stable_profile_matches(state))

    def test_stable_controller_identity_rejects_missing_duplicate_and_wrong_device(self):
        state = self.controller_identity_fixture()
        del state['P3']
        self.assertFalse(CERT.stable_profile_matches(state))
        state = self.controller_identity_fixture()
        state['P2']['physical_path'] = state['P1']['physical_path']
        self.assertFalse(CERT.stable_profile_matches(state))
        state = self.controller_identity_fixture()
        state['P4']['device_identity']['product_id'] = '0001'
        self.assertFalse(CERT.stable_profile_matches(state))

    def test_semantic_config_allows_benign_volume_change(self):
        with tempfile.TemporaryDirectory() as td:
            old = Path(td) / 'old.conf'; new = Path(td) / 'new.conf'
            old.write_text('global.videooutput=HDMI-0\nglobal.videomode=max-1920x1080\n'
                           'audio.device=hdmi-surround\naudio.volume=40\nmame.core=mame078plus\n')
            new.write_text('global.videooutput=HDMI-0\nglobal.videomode=max-1920x1080\n'
                           'audio.device=hdmi-surround\naudio.volume=45\nmame.core=mame078plus\n')
            result = AP.compare_protected_config(old, new)
            self.assertTrue(result['matches'])
            self.assertTrue(result['whole_file_sha_changed'])
            evidence = self.recovered_evidence_fixture()
            self.assertTrue(AP.recovered_safety_plan(
                self.recovered_checkpoint_fixture(), evidence)[0])

    def test_semantic_config_pauses_on_protected_or_unknown_critical_change(self):
        with tempfile.TemporaryDirectory() as td:
            old = Path(td) / 'old.conf'; new = Path(td) / 'new.conf'
            old.write_text('global.videooutput=HDMI-0\naudio.device=hdmi-surround\n')
            new.write_text('global.videooutput=DP-0\naudio.device=hdmi-surround\n')
            self.assertFalse(AP.compare_protected_config(old, new)['matches'])
            new.write_text('global.videooutput=HDMI-0\naudio.device=hdmi-surround\n'
                           'global.video.custom_mode=unsafe\n')
            result = AP.compare_protected_config(old, new)
            self.assertFalse(result['matches'])
            self.assertIn('global.video.custom_mode', result['unknown_critical_keys'])
            evidence = self.recovered_evidence_fixture()
            evidence['checks']['protected_semantic_config_matches'] = False
            evidence['passed'] = False
            self.assertFalse(AP.recovered_safety_plan(
                self.recovered_checkpoint_fixture(), evidence)[0])

    def test_recovered_es_not_idle_allows_clean_post_reboot_reconciliation(self):
        allowed, blocker, recovery = AP.recovered_safety_plan(
            self.recovered_checkpoint_fixture(), self.recovered_evidence_fixture())
        self.assertTrue(allowed)
        self.assertEqual(blocker, 'ES_NOT_IDLE')
        self.assertEqual(recovery['recovery_reason'], 'POST_REBOOT_RUNTIME_CLEAN')

    def test_recovery_rejects_active_selector_process(self):
        evidence = self.recovered_evidence_fixture()
        evidence['checks']['launch_processes_absent'] = False
        evidence.update({'passed': False, 'failure': 'LAUNCH_PROCESS_ACTIVE'})
        self.assertFalse(AP.recovered_safety_plan(self.recovered_checkpoint_fixture(), evidence)[0])

    def test_recovery_rejects_active_running_game(self):
        evidence = self.recovered_evidence_fixture()
        evidence['checks']['running_game_none'] = False
        evidence.update({'passed': False, 'failure': 'RUNNING_GAME_ACTIVE'})
        self.assertFalse(AP.recovered_safety_plan(self.recovered_checkpoint_fixture(), evidence)[0])

    def test_recovery_never_clears_restore_failure(self):
        evidence = self.recovered_evidence_fixture()
        evidence['checks']['manifest_restore_verified'] = False
        evidence.update({'passed': False, 'failure': 'LAST_TRANSACTION_NOT_RESTORE_VERIFIED'})
        cp = self.recovered_checkpoint_fixture()
        cp['blocked_reason'] = 'RuntimeError: RESTORE_FAILURE'
        self.assertFalse(AP.recovered_safety_plan(cp, evidence)[0])

    def test_recovery_never_clears_foreign_marker(self):
        evidence = self.recovered_evidence_fixture()
        evidence['checks']['marker_absent'] = False
        evidence.update({'passed': False, 'failure': 'MARKER_FOREIGN_UNKNOWN'})
        self.assertFalse(AP.recovered_safety_plan(self.recovered_checkpoint_fixture(), evidence)[0])

    def test_pre_reboot_pid_is_not_live_when_boot_id_changed(self):
        with mock.patch.object(AP, 'current_boot_id', return_value='boot-new'), \
             mock.patch.object(AP, 'proc_record', return_value={'cmdline': str(AP.CERTIFIER)}):
            self.assertFalse(AP.pid_matches_boot(21930, 'boot-old'))

    def test_recovery_keeps_partial_batch_progress_and_exact_cursor(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            checkpoint = self.recovered_checkpoint_fixture()
            checkpoint.update({'results': [{'transaction_id': AP.POST_REBOOT_TX}],
                               'latest_batch': {'name': 'priority_batch_58'},
                               'launch_transactions': 5199, 'unique_games_processed': 5724,
                               'result_records': 5726, 'auto_certified': 5026,
                               'game_fail': 171, 'restore_failures': 0,
                               'engine_fail_active': 0})
            before_batch = json.loads(json.dumps(checkpoint['batch_in_progress']))
            before_cursor = checkpoint['next_untested']
            state_file = root / 'checkpoint.json'
            state_file.write_text(json.dumps(checkpoint))
            with mock.patch.object(AP, 'CERT_STATE', state_file), \
                 mock.patch.object(AP, 'AUDIT', root), \
                 mock.patch.object(AP, 'EVENTS', root / 'events.jsonl'), \
                 mock.patch.object(AP, 'recovered_runtime_evidence',
                                   return_value=self.recovered_evidence_fixture()), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(AP.reconcile_recovered_safety_block(), 0)
            updated = json.loads(state_file.read_text())
            self.assertEqual(updated['status'], 'STOPPED_SAFE')
            self.assertIsNone(updated['blocked_reason'])
            self.assertEqual(updated['batch_in_progress'], before_batch)
            self.assertEqual(updated['next_untested'], before_cursor)
            self.assertEqual(updated['batch_in_progress']['auto_pass'], 1)
            self.assertEqual(updated['batch_in_progress']['adapter_pending'], 13)
            self.assertEqual(updated['batch_in_progress']['unprocessed'], 86)

    def previous_batch_fixture(self, td):
        root = Path(td)
        job_id = '20261117T085034_f43abe4f'
        meta = {'job_id': job_id, 'pid': 2096, 'worker_pid': 2094,
                'started_at': '2026-11-17T11:50:34+00:00',
                'finished_at': '2026-11-17T12:33:22+00:00', 'status': 'COMPLETE',
                'exit_code': 0, 'checkpoint_status': 'COMPLETE', 'batch_name': 'priority_batch_11',
                'next_game': 'mame:/userdata/roms/mame/starcas.zip',
                'autopilot_owner': {'run_id': '20261117T085032_4f18d1ce', 'pid': 2061,
                                    'process_start_ticks': 38846002}}
        job_status = {'status': 'COMPLETE', 'job_id': job_id, 'pid': 2096, 'worker_pid': 2094,
                      'NEXT_GAME': "snes:/userdata/roms/snes/Magical Pop'n.zip"}
        cp = {'status': 'COMPLETE', 'latest_batch': {'name': 'priority_batch_11',
              'started_at': '2026-11-16T23:22:54-03:00',
              'finished_at': '2026-11-17T09:33:21-03:00', 'considered': 100,
              'launched': 7, 'auto_pass': 7, 'static_fail': 93,
              'restore_verified': '7/7', 'restore_failures': 0},
              'batch_in_progress': None, 'blocked_reason': None, 'engine_fail_active': 0,
              'next_untested': "snes:/userdata/roms/snes/Magical Pop'n.zip"}
        tasks = {'tasks': [{'id': 'CERT-BATCH-0011', 'status': 'COMPLETE'},
                           {'id': 'GITHUB-PUBLISH-CERT-BATCH-0011', 'status': 'COMPLETE'},
                           {'id': 'CERT-BATCH-0012', 'status': 'PAUSED_SAFETY'}]}
        state = {'last_github_sha': 'f4e77ef44791e0be5b8c8c0d92ec6df3fff2b6a9',
                 'certifier_job': {'job_id': job_id, 'pid': 2096, 'worker_pid': 2094}}
        paths = {'AUDIT': root, 'meta': root / 'jobs' / 'certifier_job.json',
                 'archive': root / 'jobs' / 'history' / f'{job_id}.json'}
        paths['meta'].parent.mkdir(parents=True)
        paths['meta'].write_text(json.dumps(meta))
        (root / 'full_game_certification_checkpoint.json').write_text('{"status":"COMPLETE"}')
        (root / 'FULL_GAME_CERTIFICATION_SUMMARY.md').write_text('AUTO_CERTIFIED: fixture\n')
        report = root / 'reports' / 'PRIORITY_CERTIFICATION_BATCH_11.md'
        report.parent.mkdir(parents=True)
        report.write_text('fixture static-heavy batch report\n')
        publish = {'last_known_remote_sha': '156721dad12ac1bcbfc18877d57458c7b6d576b1',
                   'last_successful_publish_sha': '156721dad12ac1bcbfc18877d57458c7b6d576b1'}
        with mock.patch.object(AP, 'AUDIT', root):
            self.assertTrue(AP.write_publication_receipt(
                'priority_batch_11', publish['last_known_remote_sha'], '2026-11-17T12:35:00+00:00'))
        return job_status, cp, tasks, state, publish, paths

    def test_atomic_json_replace_and_mode(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / 'state.json'
            AP.atomic_json(target, {'schema_version': 1, 'status': 'PAUSED'})
            self.assertEqual(json.loads(target.read_text()), {'schema_version': 1, 'status': 'PAUSED'})
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertFalse(target.with_name('state.json.tmp').exists())

    def test_selector_requires_complete_dependencies(self):
        blocked = AP.task('BLOCKED', 'CERTIFICATION_BATCH', 'blocked', 'READY', 1,
                          automatic=True, depends=['GATE'])
        gate = AP.task('GATE', 'REGRESSION_CHECK', 'gate', 'RUNNING', 0, automatic=True)
        ready = AP.task('READY', 'REPORT_REBUILD', 'ready', 'READY', 2, automatic=True)
        self.assertEqual(AP.select_task([blocked, gate, ready])['id'], 'READY')
        gate['status'] = 'COMPLETE'
        self.assertEqual(AP.select_task([blocked, gate, ready])['id'], 'BLOCKED')

    def test_adopted_certifier_is_scheduled_before_other_ready_work(self):
        cert = AP.task('CERT-BATCH-0011', 'CERTIFICATION_BATCH', 'adopt', 'READY', 0,
                       automatic=True)
        health = AP.task('REGRESSION-HEALTH-001', 'REGRESSION_CHECK', 'health', 'READY', 8,
                         automatic=True)
        self.assertEqual(AP.select_task([health, cert])['id'], 'CERT-BATCH-0011')

    def test_pid_start_ticks_detect_stale_process_identity(self):
        rec = {'cmdline': str(SCRIPT) + ' --worker test', 'start_ticks': 123}
        with mock.patch.object(AP, 'proc_record', return_value=rec):
            self.assertTrue(AP.is_autopilot_process(10, 123))
            self.assertFalse(AP.is_autopilot_process(10, 122))

    def test_flock_prevents_second_autopilot_instance(self):
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(AP, 'AUDIT', Path(td)), mock.patch.object(AP, 'LOCK', Path(td) / 'lock'):
                fd = AP.acquire_lock()
                try:
                    with self.assertRaisesRegex(RuntimeError, 'AUTOPILOT_ALREADY_RUNNING'):
                        AP.acquire_lock()
                finally:
                    os.close(fd)

    def test_checkpoint_mismatch_fail_closes_health_check(self):
        with mock.patch.object(AP, 'certifier_active', return_value=(None, None)), \
             mock.patch.object(AP, 'find_autopilot_process', return_value=(None, None)), \
             mock.patch.object(AP, 'disk_health', return_value=(True, None, [])), \
             mock.patch.object(AP, 'read_json', return_value={
                 'status': 'PAUSED_ENGINE_FAILURE', 'blocked_reason': 'marker collision',
                 'engine_fail_active': 1, 'next_untested': 'mame:/rom.zip'}):
            ok, reason, _ = AP.health_check(include_checkpoint=True)
        self.assertFalse(ok)
        self.assertIn('CHECKPOINT_SAFETY_BLOCK', reason)

    def test_foreign_marker_fails_closed_as_safety_pause(self):
        with tempfile.TemporaryDirectory() as td:
            marker = Path(td) / 'boot_audit_once.json'
            marker.write_text('{"system":"mame","rom":"/tmp/foreign.zip"}\n')
            with mock.patch.object(AP, 'MARKER', marker), \
                 mock.patch.object(AP, 'certifier_active', return_value=(None, None)), \
                 mock.patch.object(AP, 'find_autopilot_process', return_value=(None, None)), \
                 mock.patch.object(AP, 'disk_health', return_value=(True, None, [])):
                ok, reason, checks = AP.health_check(include_checkpoint=True)
            self.assertFalse(ok)
            self.assertEqual(reason, 'MARKER_FOREIGN_UNKNOWN')
            self.assertEqual(checks['marker']['ownership'], 'FOREIGN_UNKNOWN')

    def test_publish_failure_is_bounded_retry_and_keeps_local_progress(self):
        item = AP.task('PUB', 'GITHUB_PUBLISH', 'publish', 'READY', 1,
                       automatic=True, max_attempts=3)
        queue = {'schema_version': 1, 'tasks': [item]}
        state = {}
        with mock.patch.object(AP, 'execute_publish', return_value=(False, 'network unavailable')), \
             mock.patch.object(AP, 'save_tasks'), mock.patch.object(AP, 'append_event'), \
             mock.patch.object(AP, 'atomic_json'), mock.patch.object(AP, 'log'):
            result = AP.execute_one(item, queue, state)
        self.assertTrue(result)
        self.assertEqual(item['status'], 'READY')
        self.assertEqual(item['attempts'], 1)
        self.assertIsNotNone(item['retry_after'])
        self.assertEqual(item['last_error'], 'network unavailable')

    def test_stop_safe_requests_runner_boundary_without_signal_kill(self):
        state = AP.initial_state()
        with mock.patch.object(AP, 'read_json', return_value=state), \
             mock.patch.object(AP, 'find_autopilot_process', return_value=(777, {})), \
             mock.patch.object(AP, 'atomic_json'), \
             mock.patch.object(AP.subprocess, 'run') as runner, \
             mock.patch('builtins.print'):
            self.assertEqual(AP.command_pause(stop=True), 0)
        runner.assert_called_once_with([str(AP.CERT_JOB), 'stop-safe'],
                                       capture_output=True, text=True, timeout=10)
        self.assertTrue(state['stop_requested'])

    def test_pause_and_resume_without_running_process_do_not_launch_a_game(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / 'autopilot_state.json'
            with mock.patch.object(AP, 'STATE', state_path), \
                 mock.patch.object(AP, 'find_autopilot_process', return_value=(None, None)), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(AP.command_pause(False), 0)
                paused = json.loads(state_path.read_text())
                self.assertEqual(paused['status'], 'STOPPED')
                with mock.patch.object(AP, 'start', return_value=3) as start:
                    self.assertEqual(AP.resume(), 3)
            start.assert_called_once_with(AP.DEFAULT_BATCH_SIZE, AP.DEFAULT_MAX_BATCHES, dry_run=False)

    def test_resume_rechecks_gates_when_pid_is_stale(self):
        with mock.patch.object(AP, 'read_json', return_value=AP.initial_state()), \
             mock.patch.object(AP, 'find_autopilot_process', return_value=(None, None)), \
             mock.patch.object(AP, 'start', return_value=3) as start:
            self.assertEqual(AP.resume(), 3)
        start.assert_called_once_with(AP.DEFAULT_BATCH_SIZE, AP.DEFAULT_MAX_BATCHES, dry_run=False)

    def test_next_does_not_label_candidate_safe_when_checkpoint_is_blocked(self):
        task = AP.task('CERT', 'CERTIFICATION_BATCH', 'batch', 'READY', 1, automatic=True)
        with mock.patch.object(AP, 'load_tasks', return_value={'tasks': [task]}), \
             mock.patch.object(AP, 'find_autopilot_process', return_value=(None, None)), \
             mock.patch.object(AP, 'health_check', return_value=(False, 'CHECKPOINT_BLOCKED', {})), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(AP.next_task(), 3)
        self.assertIn('NOT SAFE TO START', output.getvalue())

    def test_reconciled_checkpoint_releases_only_safety_paused_batch(self):
        item = AP.task('CERT-BATCH-0012', 'CERTIFICATION_BATCH', 'next', 'PAUSED_SAFETY', 10,
                       automatic=True)
        obj = {'tasks': [item]}
        AP.refresh_batch_task(obj, {'status': 'COMPLETE', 'latest_batch': {'name': 'priority_batch_11'},
                                    'engine_fail_active': 0, 'blocked_reason': None})
        self.assertEqual(item['status'], 'READY')
        item['status'] = 'CODEX_REQUIRED'
        AP.refresh_batch_task(obj, {'status': 'COMPLETE', 'latest_batch': {'name': 'priority_batch_11'}})
        self.assertEqual(item['status'], 'CODEX_REQUIRED')

    def test_completed_job_recovery_marks_batch_for_finalize_not_relaunch(self):
        item = AP.task('CERT-BATCH-0011', 'CERTIFICATION_BATCH', 'batch', 'RUNNING', 10,
                       automatic=True)
        obj = {'tasks': [item]}
        cp = {'status': 'COMPLETE', 'latest_batch': {'name': 'priority_batch_11'},
              'batch_in_progress': None}
        AP.recover_unfinished_tasks(obj, {'status': 'COMPLETE'}, cp, {})
        self.assertEqual(item['status'], 'READY')
        self.assertIn('no relanzar', item['next_action'])

    def test_finish_batch_recovery_is_idempotent_after_checkpoint_reconcile(self):
        item = AP.task('CERT-BATCH-0015', 'CERTIFICATION_BATCH', 'batch 15', 'RUNNING', 10,
                       automatic=True)
        publish = AP.task('GITHUB-PUBLISH-CERT-BATCH-0015', 'GITHUB_PUBLISH', 'publish',
                          'READY', 5, automatic=True)
        next_batch = AP.task('CERT-BATCH-0016', 'CERTIFICATION_BATCH', 'batch 16',
                             'READY', 10, automatic=True)
        obj = {'schema_version': 1, 'tasks': [item, publish, next_batch]}
        state = {'batches_completed': 0, 'games_processed_this_run': 0}
        cp = {'latest_batch': {'launched': 7, 'considered': 100, 'static_fail': 93}}
        with mock.patch.object(AP, 'report_reconciled', return_value=(True, {'ok': True})), \
             mock.patch.object(AP, 'SUMMARY_BUILDER', Path('/tmp/summary_builder_fixture.py')), \
             mock.patch.object(AP, 'STATE_BUILDER', Path('/tmp/state_builder_fixture.py')), \
             mock.patch.object(AP.subprocess, 'run', return_value=mock.Mock(returncode=0, stdout='', stderr='')), \
             mock.patch.object(AP, 'read_json', side_effect=lambda path, fallback=None:
                               cp if Path(path) == AP.CERT_STATE else (fallback or {})), \
             mock.patch.object(AP, 'save_tasks'), mock.patch.object(AP, 'append_event'), \
             mock.patch.object(AP, 'atomic_json'), mock.patch.object(AP, 'write_cycle_summary'):
            self.assertTrue(AP.finish_batch(obj, 'CERT-BATCH-0015', state))
            self.assertTrue(AP.finish_batch(obj, 'CERT-BATCH-0015', state))
        self.assertEqual(state['batches_completed'], 1)
        self.assertEqual(state['games_processed_this_run'], 7)
        self.assertEqual(state['completed_batch_ids'], ['CERT-BATCH-0015'])

    def test_consumed_previous_job_recovers_interrupted_next_batch_task(self):
        item = AP.task('CERT-BATCH-0012', 'CERTIFICATION_BATCH', 'next batch', 'RUNNING', 10,
                       automatic=True)
        obj = {'tasks': [item]}
        cp = {'status': 'COMPLETE', 'latest_batch': {'name': 'priority_batch_11'},
              'batch_in_progress': None}
        AP.recover_unfinished_tasks(obj, {'status': 'CONSUMED'}, cp, {})
        self.assertEqual(item['status'], 'READY')
        self.assertIn('runner del batch siguiente', item['next_action'])

    def test_publish_running_at_crash_recovers_as_retryable_ready(self):
        item = AP.task('GITHUB-PUBLISH-CERT-BATCH-0015', 'GITHUB_PUBLISH', 'publish',
                       'RUNNING', 5, automatic=True)
        obj = {'tasks': [item]}
        AP.recover_unfinished_tasks(obj, {'status': 'COMPLETE'},
                                    {'status': 'COMPLETE', 'latest_batch': {'name': 'priority_batch_15'}}, {})
        self.assertEqual(item['status'], 'READY')
        self.assertIn('Reintentar tarea idempotente', item['next_action'])

    def test_complete_batch_job_is_reconciled_without_second_runner_start(self):
        item = AP.task('CERT-BATCH-0011', 'CERTIFICATION_BATCH', 'batch', 'READY', 10,
                       automatic=True)
        obj = {'schema_version': 1, 'tasks': [item]}
        cp = {'status': 'COMPLETE', 'latest_batch': {'name': 'priority_batch_11'},
              'batch_in_progress': None, 'blocked_reason': None, 'engine_fail_active': 0}
        with mock.patch.object(AP, 'get_cert_job_status', return_value={'status': 'COMPLETE'}), \
             mock.patch.object(AP, 'read_json', side_effect=lambda path, fallback=None:
                               cp if Path(path) == AP.CERT_STATE else (fallback or {})), \
             mock.patch.object(AP, 'save_tasks'), mock.patch.object(AP, 'append_event'), \
             mock.patch.object(AP, 'atomic_json'), mock.patch.object(AP, 'log'), \
             mock.patch.object(AP, 'finish_batch', return_value=True) as finalize, \
             mock.patch.object(AP.subprocess, 'run') as runner:
            self.assertTrue(AP.execute_one(item, obj, {}))
        finalize.assert_called_once()
        runner.assert_not_called()

    def test_previous_complete_batch_is_archived_consumed_and_next_batch_eligible(self):
        with tempfile.TemporaryDirectory() as td:
            job, cp, tasks, state, publish, paths = self.previous_batch_fixture(td)
            with mock.patch.object(AP, 'AUDIT', paths['AUDIT']), \
                 mock.patch.object(AP, 'report_reconciled', return_value=(True, {})), \
                 mock.patch.object(AP, 'summary_matches_checkpoint', return_value=True), \
                 mock.patch.object(AP, 'read_json', side_effect=lambda path, fallback=None:
                                   publish if Path(path) == paths['AUDIT'] / 'github_publish_state.json'
                                   else json.loads(Path(path).read_text()) if Path(path).is_file() else fallback), \
                 mock.patch.object(AP, 'append_event'):
                consumed, reason = AP.consume_previous_job('CERT-BATCH-0012', job, cp, tasks, state)
                self.assertTrue(consumed, reason)
                refreshed = tasks['tasks'][2]
                AP.refresh_batch_task(tasks, cp)
                with mock.patch.object(AP, 'health_check', return_value=(True, None, {})) as health:
                    self.assertTrue(AP.health_check(include_checkpoint=True)[0])
                    health.assert_called_once_with(include_checkpoint=True)
            self.assertEqual(reason, 'PREVIOUS_JOB_COMPLETE_AND_CONSUMED')
            self.assertEqual(refreshed['status'], 'READY')
            archived = json.loads(paths['archive'].read_text())
            current = json.loads(paths['meta'].read_text())
            self.assertEqual(archived['status'], 'COMPLETE')
            self.assertEqual(current['status'], 'CONSUMED')
            self.assertEqual(current['consumed_by_task'], 'CERT-BATCH-0012')

    def test_static_heavy_batch_with_spaced_cursor_has_valid_handoff(self):
        with tempfile.TemporaryDirectory() as td:
            job, cp, tasks, state, publish, paths = self.previous_batch_fixture(td)
            with mock.patch.object(AP, 'AUDIT', paths['AUDIT']), \
                 mock.patch.object(AP, 'report_reconciled', return_value=(True, {})), \
                 mock.patch.object(AP, 'summary_matches_checkpoint', return_value=True), \
                 mock.patch.object(AP, 'read_json', side_effect=lambda path, fallback=None:
                                   publish if Path(path) == paths['AUDIT'] / 'github_publish_state.json'
                                   else json.loads(Path(path).read_text()) if Path(path).is_file() else fallback):
                allowed, reason = AP.previous_job_consumption_check(
                    'CERT-BATCH-0012', job, cp, tasks, state)
            self.assertTrue(allowed, reason)
            batch = cp['latest_batch']
            self.assertEqual(batch['considered'], batch['launched'] + batch['static_fail'])
            self.assertEqual((batch['launched'], batch['auto_pass'], batch['restore_verified']),
                             (7, 7, '7/7'))

    def test_batch15_fixture_ignores_stale_remote_publish_task_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            job, cp, tasks, state, publish, paths = self.previous_batch_fixture(td)
            cp['latest_batch']['name'] = 'priority_batch_15'
            cp['latest_batch']['next_game'] = cp['next_untested']
            tasks['tasks'][0]['id'] = 'CERT-BATCH-0015'
            tasks['tasks'][1]['id'] = 'GITHUB-PUBLISH-CERT-BATCH-0015'
            tasks['tasks'][2]['id'] = 'CERT-BATCH-0016'
            meta_path = paths['meta']
            meta = json.loads(meta_path.read_text())
            meta['batch_name'] = 'priority_batch_15'
            meta_path.write_text(json.dumps(meta))
            report = paths['AUDIT'] / 'reports' / 'PRIORITY_CERTIFICATION_BATCH_15.md'
            report.write_text('considered=100 launched=7 auto_pass=7 static_fail=93 restore=7/7\n')
            with mock.patch.object(AP, 'AUDIT', paths['AUDIT']):
                self.assertTrue(AP.write_publication_receipt(
                    'priority_batch_15', publish['last_successful_publish_sha']))
            # The publisher commit can contain its own task as RUNNING because
            # that snapshot predates the local COMPLETE write. Consumption uses
            # the reconciled local task object plus the verified receipt.
            remote_snapshot = {'GITHUB-PUBLISH-CERT-BATCH-0015': {'status': 'RUNNING'}}
            self.assertEqual(remote_snapshot['GITHUB-PUBLISH-CERT-BATCH-0015']['status'], 'RUNNING')
            with mock.patch.object(AP, 'AUDIT', paths['AUDIT']), \
                 mock.patch.object(AP, 'report_reconciled', return_value=(True, {})), \
                 mock.patch.object(AP, 'summary_matches_checkpoint', return_value=True), \
                 mock.patch.object(AP, 'read_json', side_effect=lambda path, fallback=None:
                                   publish if Path(path) == paths['AUDIT'] / 'github_publish_state.json'
                                   else json.loads(Path(path).read_text()) if Path(path).is_file() else fallback):
                allowed, reason = AP.previous_job_consumption_check(
                    'CERT-BATCH-0016', job, cp, tasks, state)
            self.assertTrue(allowed, reason)

    def test_publication_receipt_detects_changed_batch_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            job, cp, tasks, state, publish, paths = self.previous_batch_fixture(td)
            report = paths['AUDIT'] / 'reports' / 'PRIORITY_CERTIFICATION_BATCH_11.md'
            report.write_text('changed after publish\n')
            with mock.patch.object(AP, 'AUDIT', paths['AUDIT']), \
                 mock.patch.object(AP, 'report_reconciled', return_value=(True, {})), \
                 mock.patch.object(AP, 'summary_matches_checkpoint', return_value=True), \
                 mock.patch.object(AP, 'read_json', side_effect=lambda path, fallback=None:
                                   publish if Path(path) == paths['AUDIT'] / 'github_publish_state.json'
                                   else json.loads(Path(path).read_text()) if Path(path).is_file() else fallback):
                allowed, reason = AP.previous_job_consumption_check(
                    'CERT-BATCH-0012', job, cp, tasks, state)
            self.assertFalse(allowed)
            self.assertEqual(reason, 'PUBLICATION_RECEIPT_INVALID')

    def test_consuming_previous_job_starts_exactly_one_next_runner(self):
        with tempfile.TemporaryDirectory() as td:
            job, cp, tasks, state, publish, paths = self.previous_batch_fixture(td)
            item = AP.task('CERT-BATCH-0012', 'CERTIFICATION_BATCH', 'next batch', 'READY', 10,
                           automatic=True)
            tasks['tasks'][2] = item
            state.update({'status': 'RUNNING', 'batch_size': 100,
                          'run_id': 'new-autopilot-run'})
            running = {'status': 'RUNNING', 'job_id': '20261117T130700_abcdef12',
                       'pid': 4001, 'worker_pid': 4002}
            started = AP.subprocess.CompletedProcess(args=[], returncode=0, stdout='STARTED', stderr='')
            atomic_json = AP.atomic_json
            with mock.patch.object(AP, 'AUDIT', paths['AUDIT']), \
                 mock.patch.object(AP, 'get_cert_job_status', side_effect=[job, running]), \
                 mock.patch.object(AP, 'read_json', side_effect=lambda path, fallback=None:
                                   cp if Path(path) == AP.CERT_STATE else
                                   publish if Path(path) == paths['AUDIT'] / 'github_publish_state.json' else
                                   json.loads(Path(path).read_text()) if Path(path).is_file() else fallback), \
                 mock.patch.object(AP, 'report_reconciled', return_value=(True, {})), \
                 mock.patch.object(AP, 'summary_matches_checkpoint', return_value=True), \
                 mock.patch.object(AP, 'health_check', return_value=(True, None, {})), \
                 mock.patch.object(AP, 'save_tasks'), mock.patch.object(AP, 'append_event'), \
                 mock.patch.object(AP, 'atomic_json', side_effect=lambda path, value:
                                   atomic_json(path, value) if Path(path).is_relative_to(paths['AUDIT']) else None), \
                 mock.patch.object(AP, 'log'), \
                 mock.patch.object(AP.subprocess, 'run', return_value=started) as runner, \
                 mock.patch.object(AP.time, 'sleep', side_effect=RuntimeError('STOP_TEST_LOOP')):
                with self.assertRaisesRegex(RuntimeError, 'STOP_TEST_LOOP'):
                    AP.execute_one(item, tasks, state)
            runner.assert_called_once()
            self.assertEqual(runner.call_args.args[0][:2], [str(AP.CERT_JOB), 'start'])
            self.assertEqual(json.loads(paths['meta'].read_text())['status'], 'CONSUMED')

    def test_complete_unpublished_or_mismatched_job_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            job, cp, tasks, state, publish, paths = self.previous_batch_fixture(td)
            tasks['tasks'][1]['status'] = 'READY'
            with mock.patch.object(AP, 'AUDIT', paths['AUDIT']), \
                 mock.patch.object(AP, 'report_reconciled', return_value=(True, {})), \
                 mock.patch.object(AP, 'summary_matches_checkpoint', return_value=True), \
                 mock.patch.object(AP, 'read_json', side_effect=lambda path, fallback=None:
                                   publish if Path(path) == paths['AUDIT'] / 'github_publish_state.json'
                                   else json.loads(Path(path).read_text()) if Path(path).is_file() else fallback):
                allowed, reason = AP.previous_job_consumption_check(
                    'CERT-BATCH-0012', job, cp, tasks, state)
            self.assertFalse(allowed)
            self.assertEqual(reason, 'PUBLISH_TASK_NOT_COMPLETE')
            item = AP.task('CERT-BATCH-0012', 'CERTIFICATION_BATCH', 'next batch', 'READY', 10,
                           automatic=True)
            tasks['tasks'][2] = item
            state['status'] = 'RUNNING'
            with mock.patch.object(AP, 'AUDIT', paths['AUDIT']), \
                 mock.patch.object(AP, 'get_cert_job_status', return_value=job), \
                 mock.patch.object(AP, 'read_json', side_effect=lambda path, fallback=None:
                                   cp if Path(path) == AP.CERT_STATE else
                                   publish if Path(path) == paths['AUDIT'] / 'github_publish_state.json' else
                                   json.loads(Path(path).read_text()) if Path(path).is_file() else fallback), \
                 mock.patch.object(AP, 'report_reconciled', return_value=(True, {})), \
                 mock.patch.object(AP, 'summary_matches_checkpoint', return_value=True), \
                 mock.patch.object(AP, 'save_tasks'), mock.patch.object(AP, 'append_event'), \
                 mock.patch.object(AP, 'atomic_json'), mock.patch.object(AP, 'log'), \
                 mock.patch.object(AP.subprocess, 'run') as runner:
                self.assertFalse(AP.execute_one(item, tasks, state))
            self.assertEqual(state['pause_reason'],
                             'COMPLETE_JOB_CHECKPOINT_MISMATCH:PUBLISH_TASK_NOT_COMPLETE')
            runner.assert_not_called()

    def test_consumed_metadata_requires_archive_proof_and_does_not_bypass_duplicate_guard(self):
        with tempfile.TemporaryDirectory() as td:
            job, cp, tasks, state, publish, paths = self.previous_batch_fixture(td)
            original = json.loads(paths['meta'].read_text())
            archived = dict(original, archived_at='2026-11-17T12:40:00+00:00',
                            archived_as='PREVIOUS_JOB_COMPLETE_AND_CONSUMED')
            paths['archive'].parent.mkdir(parents=True)
            paths['archive'].write_text(json.dumps(archived))
            original.update({'status': 'CONSUMED', 'consumed_by_task': 'CERT-BATCH-0012',
                             'archive_path': str(paths['archive'])})
            paths['meta'].write_text(json.dumps(original))
            job['status'] = 'CONSUMED'
            with mock.patch.object(AP, 'AUDIT', paths['AUDIT']), \
                 mock.patch.object(AP, 'report_reconciled', return_value=(True, {})), \
                 mock.patch.object(AP, 'summary_matches_checkpoint', return_value=True), \
                 mock.patch.object(AP, 'read_json', side_effect=lambda path, fallback=None:
                                   publish if Path(path) == paths['AUDIT'] / 'github_publish_state.json'
                                   else json.loads(Path(path).read_text()) if Path(path).is_file() else fallback):
                allowed, reason = AP.previous_job_consumption_check(
                    'CERT-BATCH-0012', job, cp, tasks, state)
            self.assertTrue(allowed, reason)
            # The runner's existing active-job check remains authoritative even after consume.
            with mock.patch.object(AP, 'certifier_active', return_value=(555, {})), \
                 mock.patch.object(AP, 'get_cert_job_status', return_value={'status': 'RUNNING'}), \
                 mock.patch.object(AP, 'find_autopilot_process', return_value=(None, None)), \
                 mock.patch.object(AP, 'load_tasks', return_value=tasks), \
                 mock.patch.object(AP.subprocess, 'run') as runner, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(AP.start(dry_run=False), 2)
            runner.assert_not_called()

    def test_idempotent_consume_keeps_existing_archive_and_consumed_timestamp(self):
        with tempfile.TemporaryDirectory() as td:
            job, cp, tasks, state, publish, paths = self.previous_batch_fixture(td)
            archived = json.loads(paths['meta'].read_text())
            archived.update({'archived_at': '2026-11-17T12:40:00+00:00',
                             'archived_as': 'PREVIOUS_JOB_COMPLETE_AND_CONSUMED'})
            paths['archive'].parent.mkdir(parents=True)
            paths['archive'].write_text(json.dumps(archived))
            consumed_at = '2026-11-17T12:41:00+00:00'
            current = dict(archived, status='CONSUMED', consumed_at=consumed_at,
                           consumed_by_task='CERT-BATCH-0012', archive_path=str(paths['archive']))
            paths['meta'].write_text(json.dumps(current))
            job['status'] = 'CONSUMED'
            original_archive = paths['archive'].read_bytes()
            with mock.patch.object(AP, 'AUDIT', paths['AUDIT']), \
                 mock.patch.object(AP, 'report_reconciled', return_value=(True, {})), \
                 mock.patch.object(AP, 'summary_matches_checkpoint', return_value=True), \
                 mock.patch.object(AP, 'read_json', side_effect=lambda path, fallback=None:
                                   publish if Path(path) == paths['AUDIT'] / 'github_publish_state.json'
                                   else json.loads(Path(path).read_text()) if Path(path).is_file() else fallback), \
                 mock.patch.object(AP, 'append_event') as event:
                self.assertEqual(AP.consume_previous_job('CERT-BATCH-0012', job, cp, tasks, state),
                                 (True, 'PREVIOUS_JOB_COMPLETE_AND_CONSUMED'))
            self.assertEqual(paths['archive'].read_bytes(), original_archive)
            self.assertEqual(json.loads(paths['meta'].read_text())['consumed_at'], consumed_at)
            event.assert_not_called()

    def test_running_checkpoint_is_not_rendered_as_arcade_safety_failure(self):
        state = {'status': 'RUNNING', 'pid': 99, 'started_at': None, 'current_task': 'CERT-BATCH-0012',
                 'last_github_sha': None, 'pause_reason': None}
        cp = {'status': 'RUNNING', 'batch_in_progress': {'name': 'priority_batch_12',
              'launched': 1, 'considered': 100}, 'engine_fail_active': 0}
        job = {'status': 'RUNNING', 'pid': 100}
        with mock.patch.object(AP, 'read_json', side_effect=lambda path, fallback=None:
                               state if Path(path) == AP.STATE else cp if Path(path) == AP.CERT_STATE
                               else (fallback or {})), \
             mock.patch.object(AP, 'find_autopilot_process', return_value=(99, {'sid': 99, 'pgid': 99})), \
             mock.patch.object(AP, 'load_tasks', return_value={'tasks': []}), \
             mock.patch.object(AP, 'pending_handoffs', return_value=([], [])), \
             mock.patch.object(AP, 'get_cert_job_status', return_value=job), \
             mock.patch.object(AP, 'select_task', return_value=None), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            AP.status()
        self.assertIn('STATUS: RUNNING', output.getvalue())
        self.assertIn('ARCADE_SAFETY: PASS', output.getvalue())
        self.assertIn('NEXT_ACTION: Certifier activo;', output.getvalue())

    def test_detached_session_is_independent_of_calling_shell(self):
        proc = AP.subprocess.Popen([AP.sys.executable, '-c', 'import time; time.sleep(1.5)'],
                                   stdin=AP.subprocess.DEVNULL, stdout=AP.subprocess.DEVNULL,
                                   stderr=AP.subprocess.DEVNULL, start_new_session=True,
                                   close_fds=True)
        try:
            rec = AP.proc_record(proc.pid)
            self.assertIsNotNone(rec)
            self.assertEqual(rec['sid'], proc.pid)
            self.assertEqual(rec['pgid'], proc.pid)
            self.assertIsNone(proc.poll())
        finally:
            proc.wait(timeout=4)

    def test_certifier_job_runner_uses_new_session(self):
        tree = ast.parse(RUNNER_PATH.read_text())
        detached = [node for node in ast.walk(tree)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'Popen'
                    and any(keyword.arg == 'start_new_session' and isinstance(keyword.value, ast.Constant)
                            and keyword.value.value is True for keyword in node.keywords)]
        self.assertTrue(detached, 'certifier job must detach its supervisor from SSH/TUI')

    def test_manual_certifier_start_is_refused_while_autopilot_owns_run(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / 'autopilot_state.json'
            state_path.write_text(json.dumps({'status': 'RUNNING', 'run_id': 'run-1', 'pid': 123,
                                              'process_start_ticks': 456}))
            with mock.patch.object(CERT, 'AUTOPILOT_STATE', state_path), \
                 mock.patch.dict(CERT.os.environ, {}, clear=False):
                CERT.os.environ.pop('ARCADE_AUTOPILOT_RUN_ID', None)
                self.assertFalse(CERT.autopilot_process_owned_by_current_run())

    def test_job_runner_rejects_manual_start_during_autopilot(self):
        with mock.patch.object(RUNNER, 'read_json', return_value={
                'status': 'RUNNING', 'run_id': 'run-1', 'pid': 123, 'process_start_ticks': 456}), \
             mock.patch.dict(RUNNER.os.environ, {}, clear=False):
            RUNNER.os.environ.pop('ARCADE_AUTOPILOT_RUN_ID', None)
            self.assertFalse(RUNNER.autopilot_owns_start())

    def test_detached_certifier_accepts_only_runner_delegated_autopilot_owner(self):
        state = {'status': 'RUNNING', 'run_id': 'run-1', 'pid': 123,
                 'process_start_ticks': 456}
        owner = {'run_id': 'run-1', 'pid': 123, 'process_start_ticks': 456}
        job = {'status': 'RUNNING', 'pid': 789, 'worker_pid': 654,
               'autopilot_owner': owner}
        owner_proc = {'cmdline': '/usr/bin/python3 /userdata/system/el_gordo_tools/arcade_autopilot.py '
                                '--worker run-1', 'start_ticks': 456}
        cert_cmd = '/usr/bin/python3 /userdata/system/el_gordo_tools/full_game_certifier.py --batch 90'
        self.assertTrue(CERT.delegated_autopilot_owner_matches(
            state, 'run-1', owner, job, 789, 654, cert_cmd, owner_proc))
        self.assertFalse(CERT.delegated_autopilot_owner_matches(
            state, 'run-1', owner, job, 789, 999, cert_cmd, owner_proc))
        foreign_job = dict(job, autopilot_owner={'run_id': 'other-run', 'pid': 123,
                                                 'process_start_ticks': 456})
        self.assertFalse(CERT.delegated_autopilot_owner_matches(
            state, 'run-1', owner, foreign_job, 789, 654, cert_cmd, owner_proc))

    def test_certifier_lock_refuses_a_second_certifier(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(CERT, 'CERTIFIER_LOCK', Path(td) / 'certifier.lock'):
            fd = CERT.acquire_certifier_lock()
            try:
                with self.assertRaisesRegex(RuntimeError, 'CERTIFIER_ALREADY_RUNNING'):
                    CERT.acquire_certifier_lock()
            finally:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
                CERT.CERTIFIER_LOCK_FD = None

    def test_cycle_summary_reports_batch_and_handoffs(self):
        with tempfile.TemporaryDirectory() as td:
            audit = Path(td)
            task_queue = {'tasks': [
                AP.task('C', 'REPAIR_CODEX', 'codex', 'CODEX_REQUIRED', 1, codex=True),
                AP.task('M', 'CONTROL_PHYSICAL', 'manual', 'MANUAL_REQUIRED', 2, manual=True),
            ]}
            def fake_read(path, fallback=None):
                return {'latest_batch': {'name': 'priority_batch_11', 'launched': 1,
                        'considered': 1, 'auto_pass': 1, 'game_fail': 0,
                        'restore_verified': '1/1'}, 'next_untested': 'mame:/next.zip',
                        'auto_certified': 898, 'status': 'COMPLETE'} if Path(path) == AP.CERT_STATE else fallback
            with mock.patch.object(AP, 'AUDIT', audit), mock.patch.object(AP, 'CERT_STATE', audit / 'cp.json'), \
                 mock.patch.object(AP, 'read_json', side_effect=fake_read):
                AP.write_cycle_summary(task_queue, {'next_action': 'continue'})
            report = (audit / 'reports/AUTOPILOT_STATUS.md').read_text()
            self.assertIn('priority_batch_11', report)
            self.assertIn('CODEX_REQUIRED pendientes: 1', report)
            self.assertIn('MANUAL_REQUIRED pendientes: 1', report)


class Batch68SafetyRecoveryTests(unittest.TestCase):
    def checkpoint(self):
        results = []
        for index in range(20):
            results.append({'system': 'demo', 'rom': f'/userdata/roms/demo/{index}.rom',
                            'result': 'AUTO_PASS', 'transaction_id': f'b68-{index}',
                            'restore': {'status': 'RESTORE_VERIFIED'}})
        results.append({'system': 'prboom', 'rom': '/userdata/roms/prboom/doom1_shareware.wad',
                        'result': 'SYSTEM_SAFETY_FAILURE', 'failure_class': 'ES_LAUNCH_PROCESS_ACTIVE',
                        'transaction_id': AP.BATCH68_TX,
                        'restore': {'status': 'RESTORE_VERIFIED', 'transaction_id': AP.BATCH68_TX}})
        return {'status': 'PAUSED_SYSTEM_SAFETY_FAILURE',
                'blocked_reason': 'ES_LAUNCH_PROCESS_ACTIVE', 'engine_fail_active': 1,
                'next_untested': AP.BATCH68_GAME, 'current_test': None,
                'auto_certified': 20, 'game_fail': 0, 'restore_failures': 0,
                'launch_transactions': 21, 'result_records': 21,
                'batch_in_progress': {'name': 'priority_batch_68', 'considered': 41,
                    'launched': 21, 'auto_pass': 20, 'game_fail': 0,
                    'restore_verified': 21, 'restore_failures': 0},
                'results': results}

    def evidence(self, cp):
        import hashlib
        import json
        checks = {key: True for key in (
            'operator_confirmed_normal_selector_cancel', 'two_consecutive_clean_runtime_observations',
            'es_idle', 'running_game_none', 'marker_absent', 'all_launch_and_emulator_processes_absent',
            'selector_absent', 'launcher_absent', 'emulator_absent',
            'no_active_certifier', 'no_active_autopilot', 'no_partial_transaction',
            'last_result_restore_verified', 'transaction_record_consistent',
            'manifest_restore_verified', 'restored_paths_match_pre_state',
            'batch68_transactions_consistent', 'previous_terminal_result_preserved',
            'doom_csv_still_not_tested', 'cursor_matches_canonical_queue', 'hdmi_pass',
            'logical_p1_p4_stable_identity', 'protected_config_pass',
            'only_active_stop_is_reconciled_safety_incident', 'no_other_active_engine_failure',
            'result_evidence_unchanged', 'batch_progress_unchanged', 'no_game_terminal_result_for_doom')}
        return {'passed': True, 'current_boot_id': 'test-boot', 'checks': checks,
                'transaction_id': AP.BATCH68_TX, 'next_game': AP.BATCH68_GAME,
                'active_stop_result_count': 1,
                'result_records_sha256': hashlib.sha256(json.dumps(
                    cp['results'], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                'batch_progress_sha256': hashlib.sha256(json.dumps(
                    cp['batch_in_progress'], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                'csv_sha256': 'fixture-csv-sha'}

    def test_es_launch_active_historical_blocker_recovers_clean_consistent_batch68(self):
        cp = self.checkpoint()
        ok, reason, recovery = AP.recovered_safety_plan(cp, self.evidence(cp))
        self.assertTrue(ok, reason)
        self.assertEqual(recovery['reconciled_engine_fail_active'], 0)

    def test_es_launch_blocker_fails_if_selector_is_active(self):
        cp = self.checkpoint(); evidence = self.evidence(cp)
        evidence['checks']['selector_absent'] = False
        self.assertFalse(AP.recovered_safety_plan(cp, evidence)[0])

    def test_es_launch_blocker_fails_if_launcher_is_active(self):
        cp = self.checkpoint(); evidence = self.evidence(cp)
        evidence['checks']['launcher_absent'] = False
        self.assertFalse(AP.recovered_safety_plan(cp, evidence)[0])

    def test_es_launch_blocker_fails_if_emulator_is_active(self):
        cp = self.checkpoint(); evidence = self.evidence(cp)
        evidence['checks']['emulator_absent'] = False
        self.assertFalse(AP.recovered_safety_plan(cp, evidence)[0])

    def test_es_launch_blocker_fails_for_restore_or_result_mismatch(self):
        cp = self.checkpoint(); evidence = self.evidence(cp)
        cp['results'][-1]['restore']['status'] = 'RESTORE_FAILURE'
        self.assertFalse(AP.recovered_safety_plan(cp, evidence)[0])
        cp = self.checkpoint(); evidence = self.evidence(cp)
        evidence['checks']['manifest_restore_verified'] = False
        self.assertFalse(AP.recovered_safety_plan(cp, evidence)[0])

    def test_es_launch_blocker_fails_for_cursor_batch_or_result_mutation(self):
        cp = self.checkpoint(); evidence = self.evidence(cp)
        cp['next_untested'] = 'prboom:/userdata/roms/prboom/other.wad'
        self.assertFalse(AP.recovered_safety_plan(cp, evidence)[0])
        cp = self.checkpoint(); evidence = self.evidence(cp)
        cp['batch_in_progress']['launched'] = 20
        self.assertFalse(AP.recovered_safety_plan(cp, evidence)[0])
        cp = self.checkpoint(); evidence = self.evidence(cp)
        cp['results'][0]['rom'] = '/userdata/roms/demo/changed.rom'
        self.assertFalse(AP.recovered_safety_plan(cp, evidence)[0])

    def test_recovery_preserves_batch68_and_keeps_doom_nonterminal(self):
        cp = self.checkpoint()
        results_before = json.loads(json.dumps(cp['results']))
        batch_before = json.loads(json.dumps(cp['batch_in_progress']))
        _, _, recovery = AP.recovered_safety_plan(cp, self.evidence(cp))
        recovered = AP.apply_recovered_checkpoint_metadata(cp, recovery)
        self.assertEqual(recovered['results'], results_before)
        self.assertEqual(recovered['batch_in_progress'], batch_before)
        self.assertEqual(recovered['next_untested'], AP.BATCH68_GAME)
        self.assertEqual(recovered['engine_fail_active'], 0)
        self.assertEqual(recovered['results'][-1]['result'], 'SYSTEM_SAFETY_FAILURE')
        self.assertEqual(recovered['results'][-1]['restore']['status'], 'RESTORE_VERIFIED')
        self.assertEqual(recovered['batch_in_progress']['considered'], 41)
        self.assertEqual(recovered['batch_in_progress']['launched'], 21)
        self.assertEqual(recovered['batch_in_progress']['auto_pass'], 20)
        self.assertEqual(recovered['batch_in_progress']['game_fail'], 0)
        self.assertEqual(recovered['batch_in_progress']['restore_verified'], 21)

    def test_recovery_fails_if_doom_was_already_marked_terminal(self):
        cp = self.checkpoint(); evidence = self.evidence(cp)
        cp['results'][-1]['result'] = 'AUTO_PASS'
        self.assertFalse(AP.recovered_safety_plan(cp, evidence)[0])


class Batch68RunnerRecoveryGateTests(unittest.TestCase):
    def checkpoint(self):
        return {'status': 'STOPPED_SAFE', 'blocked_reason': None, 'engine_fail_active': 0,
                'next_untested': AP.BATCH68_GAME,
                'safety_recovery': {
                    'previous_blocked_reason': 'ES_LAUNCH_PROCESS_ACTIVE',
                    'recovery_reason': 'NORMAL_SELECTOR_CANCELLATION_AND_RUNTIME_CLEAN',
                    'operator_confirmed_normal_selector_cancel': True,
                    'reconciled_engine_fail_active': 0,
                    'transaction_id': AP.BATCH68_TX, 'next_game': AP.BATCH68_GAME},
                'results': [{'system': 'prboom',
                    'rom': '/userdata/roms/prboom/doom1_shareware.wad',
                    'result': 'SYSTEM_SAFETY_FAILURE', 'failure_class': 'ES_LAUNCH_PROCESS_ACTIVE',
                    'transaction_id': AP.BATCH68_TX,
                    'restore': {'status': 'RESTORE_VERIFIED', 'transaction_id': AP.BATCH68_TX}}]}

    def test_runner_ignores_only_the_exact_reconciled_safety_incident(self):
        cp = self.checkpoint()
        self.assertEqual(RUNNER.active_engine_failure_count(cp, CERT.STOP_ENGINE), 0)

    def test_runner_still_blocks_another_active_failure(self):
        cp = self.checkpoint()
        cp['results'].append({'system': 'mame', 'rom': '/userdata/roms/mame/other.zip',
                              'result': 'ENGINE_FAIL', 'transaction_id': 'foreign-engine-failure'})
        self.assertEqual(RUNNER.active_engine_failure_count(cp, CERT.STOP_ENGINE), 1)

    def test_runner_does_not_exempt_without_recovery_metadata(self):
        cp = self.checkpoint(); cp['safety_recovery'] = None
        self.assertEqual(RUNNER.active_engine_failure_count(cp, CERT.STOP_ENGINE), 1)

    def test_runner_does_not_exempt_mismatched_transaction_or_restore(self):
        cp = self.checkpoint(); cp['results'][0]['transaction_id'] = 'different-tx'
        self.assertEqual(RUNNER.active_engine_failure_count(cp, CERT.STOP_ENGINE), 1)
        cp = self.checkpoint(); cp['results'][0]['restore']['status'] = 'RESTORE_FAILURE'
        self.assertEqual(RUNNER.active_engine_failure_count(cp, CERT.STOP_ENGINE), 1)

    def test_runtime_gate_accepts_only_hash_bound_reconciled_incident(self):
        import hashlib
        import json
        cp = self.checkpoint()
        cp['status'] = 'STOPPED_SAFE'
        cp['blocked_reason'] = None
        cp['engine_fail_active'] = 0
        cp['batch_in_progress'] = {'name': 'priority_batch_68', 'considered': 41,
                                   'launched': 21, 'auto_pass': 20, 'game_fail': 0,
                                   'restore_verified': 21, 'restore_failures': 0}
        runtime_keys = (
            'operator_confirmed_normal_selector_cancel', 'two_consecutive_clean_runtime_observations',
            'es_idle', 'running_game_none', 'marker_absent', 'all_launch_and_emulator_processes_absent',
            'no_active_certifier', 'no_active_autopilot', 'no_partial_transaction',
            'last_result_restore_verified', 'manifest_restore_verified', 'restored_paths_match_pre_state',
            'batch68_transactions_consistent', 'previous_terminal_result_preserved',
            'doom_csv_still_not_tested', 'cursor_matches_canonical_queue', 'hdmi_pass',
            'logical_p1_p4_stable_identity', 'protected_config_pass', 'result_evidence_unchanged',
            'batch_progress_unchanged', 'no_game_terminal_result_for_doom')
        cp['safety_recovery'] = {
            'previous_blocked_reason': 'ES_LAUNCH_PROCESS_ACTIVE',
            'recovery_reason': 'NORMAL_SELECTOR_CANCELLATION_AND_RUNTIME_CLEAN',
            'operator_confirmed_normal_selector_cancel': True,
            'previous_active_engine_fail_count': 1, 'reconciled_engine_fail_active': 0,
            'transaction_id': AP.BATCH68_TX, 'next_game': AP.BATCH68_GAME,
            'runtime_checks': {key: True for key in runtime_keys}, 'csv_sha256': 'fixture-csv',
            'result_records_sha256': hashlib.sha256(json.dumps(
                cp['results'], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            'batch_progress_sha256': hashlib.sha256(json.dumps(
                cp['batch_in_progress'], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}
        self.assertTrue(AP.batch68_reconciled_incident_matches(
            cp, cp['results'], 'fixture-csv'))

    def test_runtime_gate_rejects_other_stop_or_changed_evidence(self):
        cp = self.checkpoint()
        self.assertFalse(AP.batch68_reconciled_incident_matches(
            cp, cp['results'], 'fixture-csv'))
        extra = cp['results'] + [{'result': 'ENGINE_FAIL'}]
        self.assertFalse(AP.batch68_reconciled_incident_matches(
            cp, extra, 'fixture-csv'))

    def test_queue_allows_only_hash_bound_reconciled_doom_retry(self):
        import hashlib
        import json
        cp = self.checkpoint()
        cp['status'] = 'STOPPED_SAFE'; cp['blocked_reason'] = None; cp['engine_fail_active'] = 0
        cp['batch_in_progress'] = {'name': 'priority_batch_68', 'considered': 41,
                                   'launched': 21, 'auto_pass': 20, 'game_fail': 0,
                                   'restore_verified': 21, 'restore_failures': 0}
        runtime_keys = (
            'operator_confirmed_normal_selector_cancel', 'two_consecutive_clean_runtime_observations',
            'es_idle', 'running_game_none', 'marker_absent', 'all_launch_and_emulator_processes_absent',
            'no_active_certifier', 'no_active_autopilot', 'no_partial_transaction',
            'last_result_restore_verified', 'manifest_restore_verified', 'restored_paths_match_pre_state',
            'batch68_transactions_consistent', 'previous_terminal_result_preserved',
            'doom_csv_still_not_tested', 'cursor_matches_canonical_queue', 'hdmi_pass',
            'logical_p1_p4_stable_identity', 'protected_config_pass', 'result_evidence_unchanged',
            'batch_progress_unchanged', 'no_game_terminal_result_for_doom')
        cp['safety_recovery'] = {
            'previous_blocked_reason': 'ES_LAUNCH_PROCESS_ACTIVE',
            'recovery_reason': 'NORMAL_SELECTOR_CANCELLATION_AND_RUNTIME_CLEAN',
            'operator_confirmed_normal_selector_cancel': True,
            'previous_active_engine_fail_count': 1, 'reconciled_engine_fail_active': 0,
            'transaction_id': AP.BATCH68_TX, 'next_game': AP.BATCH68_GAME,
            'runtime_checks': {key: True for key in runtime_keys}, 'csv_sha256': 'fixture-csv',
            'result_records_sha256': hashlib.sha256(json.dumps(
                cp['results'], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            'batch_progress_sha256': hashlib.sha256(json.dumps(
                cp['batch_in_progress'], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}
        game = {'system': 'prboom', 'rom': '/userdata/roms/prboom/doom1_shareware.wad'}
        self.assertTrue(CERT.reconciled_batch68_retry_matches(game, cp, 'fixture-csv'))
        cp['safety_recovery']['csv_sha256'] = 'different-csv'
        self.assertFalse(CERT.reconciled_batch68_retry_matches(game, cp, 'fixture-csv'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
