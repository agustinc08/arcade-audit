import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, '/userdata/system/el_gordo_tools')
import automatic_selector_context as ASC


class AutomaticSelectorContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'context.json'
        self.rom = '/userdata/roms/prboom/doom1_shareware.wad'
        self.base = {
            101: {'pid': 101, 'ppid': 1, 'start_ticks': 11, 'comm': 'python3', 'exe': '/usr/bin/python3',
                  'cmdline': '/usr/bin/python3 /userdata/system/el_gordo_tools/full_game_certifier.py --batch 20'},
            202: {'pid': 202, 'ppid': 1, 'start_ticks': 22, 'comm': 'emulationstation', 'exe': '/usr/bin/emulationstation',
                  'cmdline': '/usr/bin/emulationstation'},
            303: {'pid': 303, 'ppid': 302, 'start_ticks': 33, 'comm': 'python3', 'exe': '/usr/bin/python3',
                  'cmdline': '/usr/bin/python3 /userdata/system/el_gordo_tools/controller_dispatcher -system prboom -rom ' + self.rom},
            304: {'pid': 304, 'ppid': 302, 'start_ticks': 34, 'comm': 'python3', 'exe': '/usr/bin/python3',
                  'cmdline': '/usr/bin/python3 /userdata/system/el_gordo_tools/controller_dispatcher -system prboom -rom ' + self.rom},
        }
        self.es = {'pid': 202, 'start_ticks': 22, 'comm': 'emulationstation'}
        with patch.object(ASC, 'current_boot_id', return_value='boot-A'):
            ASC.create_context(transaction_id='TX-A', system='prboom', rom=self.rom,
                certifier={'pid': 101, 'start_ticks': 11, 'cmdline': self.base[101]['cmdline']},
                es_identity=self.es, autopilot=None, path=self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def authorize(self, pid=303, system='prboom', rom=None, boot='boot-A', ancestry=True):
        values = dict(self.base)
        with patch.object(ASC, 'current_boot_id', return_value='boot-A'), \
             patch.object(ASC, 'process_identity', side_effect=lambda p: values.get(p)), \
             patch.object(ASC, '_ancestry_reaches_es', return_value=ancestry):
            return ASC.authorize_invocation(system=system, rom=rom or self.rom,
                dispatcher_pid=pid, ppid=302, path=self.path, boot_id=boot)

    def test_transaction_invocation_one_and_two_choose_joysticks(self):
        ok, reason, first = self.authorize()
        self.assertTrue(ok, reason)
        self.assertEqual(first['choice'], 'JOYSTICKS PRIMERO')
        self.assertTrue(ASC.set_phase('TX-A', 'POST_EMULATOR', path=self.path))
        ok, reason, second = self.authorize(pid=304)
        self.assertTrue(ok, reason)
        self.assertEqual(second['transaction_id'], 'TX-A')
        self.assertEqual(second['choice'], 'JOYSTICKS PRIMERO')
        self.assertEqual(len(json.loads(self.path.read_text())['invocations']), 2)

    def test_closed_same_rom_is_interactive(self):
        ASC.close_context('TX-A', path=self.path)
        self.assertFalse(self.authorize()[0])

    def test_new_transaction_requires_its_own_context(self):
        ASC.close_context('TX-A', path=self.path)
        self.assertFalse(self.authorize()[0])
        with patch.object(ASC, 'current_boot_id', return_value='boot-A'):
            ASC.create_context(transaction_id='TX-B', system='prboom', rom=self.rom,
                certifier={'pid': 101, 'start_ticks': 11, 'cmdline': self.base[101]['cmdline']},
                es_identity=self.es, autopilot=None, path=self.path)
        ok, reason, _ = self.authorize()
        self.assertTrue(ok, reason)

    def test_different_rom_does_not_inherit(self):
        self.assertFalse(self.authorize(rom='/userdata/roms/prboom/other.wad')[0])

    def test_different_es_identity_does_not_inherit(self):
        self.assertFalse(self.authorize(ancestry=False)[0])

    def test_reused_certifier_pid_with_different_start_ticks_fails_closed(self):
        values = dict(self.base)
        values[101] = dict(values[101], start_ticks=999)
        with patch.object(ASC, 'current_boot_id', return_value='boot-A'), \
             patch.object(ASC, 'process_identity', side_effect=lambda p: values.get(p)), \
             patch.object(ASC, '_ancestry_reaches_es', return_value=True):
            ok, reason, _ = ASC.authorize_invocation(system='prboom', rom=self.rom,
                dispatcher_pid=303, ppid=302, path=self.path, boot_id='boot-A')
        self.assertFalse(ok)
        self.assertEqual(reason, 'CERTIFIER_IDENTITY_NOT_LIVE')

    def test_different_boot_id_does_not_inherit(self):
        self.assertFalse(self.authorize(boot='boot-B')[0])

    def test_manual_launch_without_context_stays_interactive(self):
        self.path.unlink()
        self.assertFalse(self.authorize()[0])

    def test_corrupt_context_fails_closed(self):
        self.path.write_text('{broken')
        self.assertFalse(self.authorize()[0])

    def test_old_context_after_restart_is_invalid(self):
        self.assertFalse(self.authorize(boot='boot-B')[0])

    def test_unknown_invocation_cannot_consume_second_slot(self):
        ok, reason, _ = self.authorize()
        self.assertTrue(ok, reason)
        self.assertTrue(ASC.set_phase('TX-A', 'POST_EMULATOR', path=self.path))
        self.assertFalse(self.authorize(rom='/userdata/roms/prboom/other.wad')[0])
        ok, reason, _ = self.authorize(pid=304)
        self.assertTrue(ok, reason)

    def test_context_close_archives_invocations_and_removes_authority(self):
        self.authorize()
        archive = Path(self.tmp.name) / 'selector_context.json'
        closed = ASC.close_context('TX-A', archive_path=archive, path=self.path, reason='SAFETY_AFTER_PASS')
        self.assertEqual(closed['state'], 'CLOSED')
        self.assertEqual(closed['close_reason'], 'SAFETY_AFTER_PASS')
        self.assertEqual(len(json.loads(archive.read_text())['invocations']), 1)
        self.assertFalse(self.path.exists())


if __name__ == '__main__':
    unittest.main()
