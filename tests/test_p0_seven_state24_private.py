"""Synthetic, native-free tests. Private user files are never loaded."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest

# The standalone study reuses #231 but synthetic tests stub upstream before load.
key = 'audit_p0_seven_numbered_source_pairs_private'
old_module = sys.modules.get(key)
sys.modules[key] = types.ModuleType(key)
spec = importlib.util.spec_from_file_location('state24_under_test',
    Path(__file__).resolve().parent.parent / 'scripts' / 'audit_p0_seven_state24_private.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
if old_module is None:
    sys.modules.pop(key, None)
else:
    sys.modules[key] = old_module


def sample(value, ball=(1,2,3), club=0):
    whole = [0] * 51
    whole[0x24 // 4] = value
    whole[0x88 // 4] = 0xA000
    return {
        'whole_record': tuple(whole), 'selected_index': 0, 'hole': 1,
        'field': 0x110, 'pin_obj': 0x220, 'start_obj': 0x330,
        'cfg_bc': 0x1, 'cfg_c0': 0x2, 'cfg_c4': 0x3,
        'pin': (1,2,3),
        'triplets': {
            'ball_object_0x030': ball,
            'source_current_start': (0,0,0),
        },
        'source_current_start': (0,0,0),
        'ball_object_0x030': ball,
    }


class State24Tests(unittest.TestCase):
    def cohort(self):
        return {i: sample(2) for i in range(1,8)}

    def test_stable(self):
        r = mod.summarize(self.cohort())
        self.assertEqual(r['distinct_private_state_values_count'], 1)
        self.assertTrue(all(not e['state24_changed'] for e in r['comparisons']))

    def test_transition_and_changed_ball_are_distinct(self):
        s = self.cohort()
        s[6] = sample(3, ball=(4,5,6))
        r = mod.summarize(s)
        self.assertTrue(next(e for e in r['comparisons'] if e['transition']=='5_to_6')['state24_changed'])
        self.assertEqual(next(e for e in r['comparisons'] if e['transition']=='5_to_6')['ball_candidate_changed_components'], 3)
        self.assertFalse(r['shot_state_verified'])

    def test_unexpected_value_is_not_named(self):
        s = self.cohort(); s[2] = sample(0xDEADBEEF)
        r = mod.summarize(s)
        self.assertTrue(r['snapshots'][1]['unexpected_nonzero_value'])
        self.assertNotIn('deadbeef', str(r).lower())
        self.assertNotIn('3735928559', str(r))

    def test_zero_unknown_is_not_enum(self):
        s = self.cohort(); s[1] = sample(0)
        r = mod.summarize(s)
        self.assertTrue(r['snapshots'][0]['is_zero'])
        self.assertFalse(r['snapshots'][0]['in_source_1_to_5_literal_set'])

    def test_confounded_transition_marked(self):
        r = mod.summarize(self.cohort())
        x = next(e for e in r['comparisons'] if e['transition']=='3_to_4')
        self.assertTrue(x['different_clubs_or_input_confound'])
        self.assertFalse(x['same_shot_human_note_only'])

    def test_reject_absent_phase(self):
        s=self.cohort();del s[4]
        with self.assertRaises(ValueError): mod.summarize(s)

    def test_reject_extra_phase(self):
        s=self.cohort();s[8]=sample(2)
        with self.assertRaises(ValueError): mod.summarize(s)

    def test_reject_wrong_word_length(self):
        s=self.cohort();s[5]['whole_record']=(2,3)
        with self.assertRaises(ValueError): mod.summarize(s)

    def test_reject_non_u32(self):
        s=self.cohort();w=list(s[5]['whole_record']);w[9]='bad';s[5]['whole_record']=tuple(w)
        with self.assertRaises(ValueError): mod.summarize(s)

    def test_reject_selected_pointer_change(self):
        s=self.cohort();w=list(s[7]['whole_record']);w[0x88//4]=0xA004;s[7]['whole_record']=tuple(w)
        with self.assertRaises(ValueError): mod.summarize(s)

    def test_reject_hole_change(self):
        s=self.cohort();s[5]['hole']=2
        with self.assertRaises(ValueError): mod.summarize(s)

    def test_reject_pin_changed(self):
        s=self.cohort();s[6]['pin']=(4,2,3)
        with self.assertRaises(ValueError): mod.summarize(s)

    def test_reject_config_change(self):
        s=self.cohort();s[7]['cfg_c4']=999
        with self.assertRaises(ValueError): mod.summarize(s)

    def test_reject_start_geometry_change(self):
        s=self.cohort();s[2]['triplets']['source_current_start']=(8,9,10)
        with self.assertRaises(ValueError): mod.summarize(s)

    def test_does_not_mark_training(self):
        r=mod.summarize(self.cohort())
        self.assertIs(r['training_approved'],False)
        self.assertIs(r['allowed_to_publish'],False)
        self.assertIs(r['same_boot_verified'],False)

    def test_snapshot_results_not_raw_words(self):
        s=self.cohort();s[7] = sample(0x12345678)
        r=mod.summarize(s)
        self.assertNotIn('305419896', str(r))
        self.assertNotIn('12345678', str(r))


if __name__=='__main__': unittest.main()
