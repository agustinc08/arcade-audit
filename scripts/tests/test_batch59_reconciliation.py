import importlib.util
import sys
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

TOOLS = Path('/userdata/system/el_gordo_tools')
sys.path.insert(0, str(TOOLS))

import certification_batch_accounting as accounting
import full_game_certifier as cert
import rebuild_priority_batch_report as batch_report


def controller_fixture():
    identity = {}
    for player, port, event, js in (
            ('P1', '5', 'event18', 'js1'), ('P2', '6', 'event19', 'js2'),
            ('P3', '8', 'event21', 'js4'), ('P4', '7', 'event20', 'js3')):
        identity[player] = {
            'expected_usb_port': port,
            'usb_port': port,
            'physical_path': cert.expected_controller_id_path(port),
            'by_path': cert.expected_controller_by_path(port),
            'device_identity': {'vendor_id': '0079', 'product_id': '0006',
                                'name': 'DragonRise Inc. Generic USB Joystick'},
            'event': '/dev/input/' + event,
            'js': '/dev/input/' + js,
        }
    return identity


def batch_fixture(processed_before_resume):
    start = '2026-11-18T16:19:02.644-03:00'
    finish = '2026-11-19T00:13:48.261-03:00'
    results, rows = [], []
    for index in range(100):
        base = (datetime.fromisoformat('2026-11-18T16:20:00-03:00') + timedelta(seconds=index)
                if index < processed_before_resume else
                datetime.fromisoformat('2026-11-18T23:30:00-03:00') +
                timedelta(seconds=index - processed_before_resume))
        stamp = base.isoformat(timespec='milliseconds')
        txid = f'tx-{index:03d}'
        system = 'demo'
        rom = f'/userdata/roms/demo/game-{index:03d}.rom'
        results.append({'system': system, 'rom': rom, 'result': 'AUTO_PASS',
                        'transaction_id': txid, 'finished_at': stamp,
                        'restore': {'status': 'RESTORE_VERIFIED', 'transaction_id': txid}})
        rows.append({'system': system, 'rom': rom, 'test_id': txid,
                     'auto_certification': 'AUTO_CERTIFIED', 'test_result': 'AUTO_PASS',
                     'restore_status': 'RESTORE_VERIFIED'})
    batch = {'name': 'priority_batch_59', 'considered': 100, 'launched': 100,
             'auto_pass': 100, 'game_fail': 0, 'static_fail': 0,
             'restore_verified': '100/100', 'restore_failures': 0,
             'started_at': start, 'finished_at': finish,
             'first_game': '/userdata/roms/demo/first-candidate.rom',
             'last_game': results[-1]['rom'], 'next_game': 'demo:/userdata/roms/demo/next.rom'}
    return {'latest_batch': batch, 'results': results,
            'next_untested': batch['next_game'], 'auto_certified': 5125}, rows


class StableControllerIdentityTests(unittest.TestCase):
    def test_runtime_event_and_js_renumbering_is_informational(self):
        identity = controller_fixture()
        self.assertTrue(cert.stable_profile_matches(identity))
        identity['P1']['event'] = '/dev/input/event88'
        identity['P1']['js'] = '/dev/input/js77'
        self.assertTrue(cert.stable_profile_matches(identity))

    def test_wrong_physical_usb_port_fails(self):
        identity = controller_fixture()
        identity['P1'].update(usb_port='6', physical_path=cert.expected_controller_id_path('6'),
                              by_path=cert.expected_controller_by_path('6'))
        self.assertFalse(cert.stable_profile_matches(identity))

    def test_missing_duplicate_and_unexpected_logical_mapping_fail(self):
        identity = controller_fixture()
        del identity['P3']
        self.assertFalse(cert.stable_profile_matches(identity))
        identity = controller_fixture()
        identity['P4']['physical_path'] = identity['P3']['physical_path']
        self.assertFalse(cert.stable_profile_matches(identity))
        identity = controller_fixture()
        identity['P2']['expected_usb_port'] = '8'
        self.assertFalse(cert.stable_profile_matches(identity))

    def test_current_state_uses_stable_helper_and_does_not_call_dispatcher(self):
        spec = importlib.util.spec_from_file_location(
            'rebuild_current_state_test', TOOLS / 'rebuild_arcade_current_state.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        identity = controller_fixture()
        fake_cert = type('CertModule', (), {
            'profile_state': staticmethod(lambda: identity),
            'stable_profile_matches': staticmethod(cert.stable_profile_matches),
        })
        with patch.dict(sys.modules, {'full_game_certifier': fake_cert}), \
                patch.object(module.subprocess, 'run') as run:
            _, lines, _ = module.controller_state()
        run.assert_not_called()
        self.assertIn('USB5 / /dev/input/event18 / /dev/input/js1', lines[0])
        self.assertIn('ID_PATH', lines[0])
        self.assertIn('runtime actuales', lines[0])


class ResumeAccountingTests(unittest.TestCase):
    def _exercise_resume(self, before, resumed):
        progress = accounting.new_batch_progress('priority_batch_59', 100, 'first', 'start')
        for index in range(before + resumed):
            accounting.record_batch_result(progress, {
                'rom': f'game-{index}', 'transaction_id': f'tx-{index}',
                'result': 'AUTO_PASS', 'restore': {'status': 'RESTORE_VERIFIED'}})
        checkpoint = {}
        accounting.set_invocation_selection(checkpoint, resumed)
        self.assertEqual(progress['considered'], 100)
        self.assertEqual(progress['launched'], 100)
        self.assertEqual(progress['auto_pass'], 100)
        self.assertEqual(progress['restore_verified'], 100)
        self.assertEqual(checkpoint['invocation_selected_count'], resumed)
        self.assertEqual(checkpoint['selected_count'], resumed)
        summary = accounting.phase_summary({**progress, 'restore_verified': '100/100'}, 5125, 'next')
        self.assertIn('100 considerados, 100 lanzados, 100 AUTO_PASS', summary)

    def test_one_before_restart_and_99_on_resume(self):
        self._exercise_resume(1, 99)

    def test_37_before_restart_and_63_on_resume(self):
        self._exercise_resume(37, 63)


class BatchReportTests(unittest.TestCase):
    def test_report_reconciles_100_results_and_csv_transactions(self):
        checkpoint, rows = batch_fixture(1)
        report = batch_report.render_report(checkpoint, rows)
        self.assertIn('- Considerados: 100', report)
        self.assertIn('- AUTO_PASS: 100', report)
        self.assertIn('- Restores: 100/100', report)
        self.assertIn('- AUTO_CERTIFIED: 5125', report)

    def test_report_fails_for_missing_or_wrong_restore(self):
        checkpoint, rows = batch_fixture(37)
        checkpoint['results'].pop()
        with self.assertRaisesRegex(RuntimeError, 'TRANSACTION_SET'):
            batch_report.render_report(checkpoint, rows)
        checkpoint, rows = batch_fixture(37)
        checkpoint['results'][0]['restore']['status'] = 'RESTORE_FAILURE'
        with self.assertRaisesRegex(RuntimeError, 'RESTORE_SET'):
            batch_report.render_report(checkpoint, rows)

    def test_phase_summary_uses_cumulative_latest_batch_fields(self):
        checkpoint, _ = batch_fixture(1)
        batch = checkpoint['latest_batch']
        summary = accounting.phase_summary(batch, 5125, checkpoint['next_untested'])
        self.assertIn('100 considerados, 100 lanzados, 100 AUTO_PASS', summary)
        self.assertIn('restores 100/100', summary)

    def test_summary_labels_selected_count_as_invocation_only(self):
        line = accounting.invocation_selection_line({'selected_count': 99})
        self.assertIn('CURRENT_INVOCATION_SELECTED_COUNT: 99', line)
        self.assertIn('no es el total acumulado del batch', line)


if __name__ == '__main__':
    unittest.main()
