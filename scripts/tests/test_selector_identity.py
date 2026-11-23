import importlib.util
import json
import sys
import unittest
from pathlib import Path

SCRIPT = Path('/userdata/system/el_gordo_tools/full_game_certifier.py')
SPEC = importlib.util.spec_from_file_location('full_game_certifier_selector_identity', SCRIPT)
CERT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CERT
SPEC.loader.exec_module(CERT)

SYSTEM = 'saturn'
ROM = '/userdata/roms/saturn/Chill (Jan 19, 1998 prototype).zip'
TX = '20261121T173203_686d870ebf'


def event(name, **kwargs):
    return {'event': name, 'system': SYSTEM, 'rom': ROM, **kwargs}


def line(value):
    return json.dumps(value)


def automatic(invocation='invocation-1', **kwargs):
    values = {'transaction_id': TX, 'selector_invocation_id': invocation,
              'automatic_context_match': True, 'choice': 'JOYSTICKS PRIMERO',
              'one_shot_consumed': True}
    values.update(kwargs)
    return event('automatic_selector_context_choice', **values)


class SelectorIdentityTests(unittest.TestCase):
    def identity(self, *events):
        return CERT.selector_identity('\n'.join(map(line, events)), SYSTEM, ROM, TX)

    def test_launch_before_valid_automatic_context_is_proven(self):
        result = self.identity(event('launch'), automatic())
        self.assertTrue(CERT.selector_identity_is_proven(result))
        self.assertEqual(result['event'], 'automatic_selector_context_choice')

    def test_foreign_transaction_plus_local_launch_fails(self):
        foreign = automatic(transaction_id='another-transaction')
        result = self.identity(foreign, event('launch'))
        self.assertFalse(CERT.selector_identity_is_proven(result))

    def test_two_valid_invocations_in_same_transaction_are_proven(self):
        result = self.identity(automatic('invocation-1'), automatic('invocation-2'))
        self.assertTrue(CERT.selector_identity_is_proven(result))
        self.assertEqual(result['selector_invocation_ids'], ['invocation-1', 'invocation-2'])

    def test_launch_only_is_not_proof(self):
        result = self.identity(event('launch'))
        self.assertEqual(result['event'], 'launch')
        self.assertFalse(CERT.selector_identity_is_proven(result))

    def test_valid_automatic_context_before_launch_is_proven(self):
        result = self.identity(automatic(), event('launch'))
        self.assertTrue(CERT.selector_identity_is_proven(result))

    def test_valid_automatic_context_after_launch_is_proven(self):
        result = self.identity(event('launch'), automatic())
        self.assertTrue(CERT.selector_identity_is_proven(result))

    def test_wrong_rom_system_match_flag_or_choice_fails_closed(self):
        wrong_rom = dict(automatic(), rom='/userdata/roms/saturn/Other.zip')
        wrong_system = dict(automatic(), system='dreamcast')
        no_match = automatic(automatic_context_match=False)
        wrong_choice = automatic(choice='BOTONERAS PRIMERO')
        for item in (wrong_rom, wrong_system, no_match, wrong_choice):
            with self.subTest(item=item):
                self.assertFalse(CERT.selector_identity_is_proven(self.identity(item)))


if __name__ == '__main__':
    unittest.main()
