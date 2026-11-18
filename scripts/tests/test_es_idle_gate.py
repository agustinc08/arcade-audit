import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, '/userdata/system/el_gordo_tools')
import full_game_certifier as CERT


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def monotonic(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class EsIdleGateTests(unittest.TestCase):
    def run_gate(self, observations, *, timeout=4, active=None, marker=None, evidence=None):
        clock = FakeClock()
        samples = iter(observations)
        with mock.patch.object(CERT, 'api_state', side_effect=lambda: next(samples)), \
             mock.patch.object(CERT, 'pids', return_value=active or []), \
             mock.patch.object(CERT.sr, 'MARKER', marker or Path('/tmp/es-idle-gate-marker-missing')):
            return CERT.wait_for_es_idle(timeout=timeout, interval=1,
                                         sleep=clock.sleep, clock=clock.monotonic,
                                         evidence_path=evidence), clock

    def test_game_pass_restore_verified_waits_for_temporary_es_transition(self):
        result = {'result': 'AUTO_PASS', 'restore': {'status': 'RESTORE_VERIFIED'}}
        with tempfile.TemporaryDirectory() as td:
            observations = [(False, {'path': '/game/previous'}), (True, None), (True, None)]
            gate, clock = self.run_gate(observations, evidence=Path(td) / 'evidence.json')
        self.assertEqual(result['result'], 'AUTO_PASS')
        self.assertEqual(result['restore']['status'], 'RESTORE_VERIFIED')
        self.assertTrue(gate['isIdle'])
        self.assertIsNone(gate['runningGame'])
        self.assertEqual(clock.value, 2)

    def test_es_never_idle_times_out_and_saves_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            evidence = Path(td) / 'evidence.json'
            with self.assertRaisesRegex(RuntimeError, '^ES_IDLE_TIMEOUT$'):
                self.run_gate([(False, {'path': '/game/previous'})] * 4,
                              timeout=2, evidence=evidence)
            saved = json.loads(evidence.read_text())
        self.assertEqual(saved['reason'], 'ES_IDLE_TIMEOUT')
        self.assertFalse(saved['last_observation']['isIdle'])

    def test_running_game_never_clears_does_not_continue(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(RuntimeError, '^ES_IDLE_TIMEOUT$'):
                self.run_gate([(True, {'path': '/game/still-running'})] * 3,
                              timeout=1, evidence=Path(td) / 'evidence.json')

    def test_orphan_emulator_blocks_immediately(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(RuntimeError, '^ES_LAUNCH_PROCESS_ACTIVE$'):
                self.run_gate([(True, None)], active=[{'pid': 42, 'comm': 'retroarch'}],
                              evidence=Path(td) / 'evidence.json')

    def test_active_selector_blocks_immediately(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(RuntimeError, '^ES_LAUNCH_PROCESS_ACTIVE$'):
                self.run_gate([(True, None)], active=[{'pid': 43, 'comm': 'selector_controles'}],
                              evidence=Path(td) / 'evidence.json')

    def test_foreign_marker_blocks_without_removal(self):
        with tempfile.TemporaryDirectory() as td:
            marker = Path(td) / 'foreign-marker.json'
            marker.write_text('{"owner":"unknown"}')
            evidence = Path(td) / 'evidence.json'
            with self.assertRaisesRegex(RuntimeError, '^MARKER_FOREIGN_UNKNOWN$'):
                self.run_gate([(True, None)], marker=marker, evidence=evidence)
            self.assertTrue(marker.exists())
            self.assertEqual(json.loads(evidence.read_text())['reason'], 'MARKER_FOREIGN_UNKNOWN')

    def test_clean_idle_allows_continuation_after_two_observations(self):
        gate, clock = self.run_gate([(True, None), (True, None)])
        self.assertTrue(gate['isIdle'])
        self.assertEqual(clock.value, 1)


if __name__ == '__main__':
    unittest.main()
