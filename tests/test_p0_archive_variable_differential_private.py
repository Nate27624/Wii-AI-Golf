"""Synthetic-only private archive differential regression; no emulator or captures."""
import copy
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'p0_archive_variable_differential_private.py'
spec = importlib.util.spec_from_file_location('p0_archive_variable_differential_private', SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def registry():
    return {'schema_version': 1, 'status_vocabulary': ['unresolved', 'source_candidate',
            'snapshot_correlated', 'runtime_verified', 'rejected'],
            'variables': [{'id': key, 'priority': 'P0', 'status': 'source_candidate',
                           'memory_locator': {'kind': 'pointer_chain_hypothesis',
                                              'expression': 'BE_f32x3(registered_source_object+0x30)'},
                           'evidence': {'source_confidence': 'rev1_source_candidate_only'},
                           'required_controls': ['independent same-shot source witness']}
                          for key in audit.P0_IDS]}


def samples():
    values = {}
    for i in range(1, 8):
        cur = (100, 200, 300) if i not in (5, 6, 7) else (100+i, 200+i, 300+i)
        rec = (1,2,3)
        a = {'source_gate': True, 'scene_gate': True,
             'selected_index': 0, 'hole': 1, 'selected_ball_obj': 0x90010000,
             'pin_obj': 0x90020000, 'start_obj': 0x90030000,
             'field': 0x90040000, 'cfg_bc': 7, 'cfg_c0': 0, 'cfg_c4': 1,
             'mode_word': (4,), 'hole_word': (0,),
             'source_current_start': (100,200,300), 'pin': (1,2,3),
             'record_0x054': rec, 'record_0x060': rec,
             'ball_object_0x030': cur, 'ball_cache_0x0cc': (107,207,307),
             'ball_cache_0x0f0': (107,207,307),
             'ball_cache_0x0fc': (107,207,307),
             'global_current': (107,207,307),
             'aim_word': (0x3f800000,), 'tag_118': (0,), 'tag_11c': (0,),
             'standard_score_table': tuple(range(36)), 'scalar_030': (42,),
             'scalar_090': (43,), 'stroke_word': (1,),
             '_global_identity_private': 0x90080000}
        values[i] = a
    return values


class RegistryTest(unittest.TestCase):
    def test_p0_exact_25(self):
        self.assertEqual(len(audit.registry_entries(registry())), 25)

    def test_missing_and_duplicate_p0_refused(self):
        bad=registry()
        bad['variables'].pop()
        with self.assertRaises(ValueError): audit.registry_entries(bad)
        bad=registry()
        bad['variables'][-1]['id'] = bad['variables'][0]['id']
        with self.assertRaises(ValueError): audit.registry_entries(bad)

    def test_invalid_locator_and_registry_gate(self):
        bad=registry()
        bad['variables'][0]['memory_locator']={}
        with self.assertRaises(ValueError): audit.registry_entries(bad)
        bad=registry()
        bad['variables'][0]['status']='runtime_claimed_without_proof'
        with self.assertRaises(ValueError): audit.registry_entries(bad)


class NumericAndIdentityTest(unittest.TestCase):
    def test_big_endian_bitwords_not_decoded_as_little_endian_or_float(self):
        a=(0x3F800000, 0x40000000, 0x40400000)
        b=(0x3F800000, 0x40000001, 0x40400000)
        self.assertEqual(audit._bits_changed(a,b), 1)
        self.assertEqual(audit._bits_changed(a,a), 0)
        with self.assertRaises(ValueError): audit._bits_changed((1.0,), (2.0,))
        with self.assertRaises(ValueError): audit._bits_changed((1,), (1,2))

    def test_full_and_partial_span_alias_rejected(self):
        p = 0x90010000
        for shift in (0x94,0x98,0x9C,0xA0,0xA4):
            self.assertTrue(audit._overlap(p+0xCC,12,p+shift+0x30,12))
            self.assertTrue(audit._overlap(p,0x1AC,p+shift,0x50))
        self.assertFalse(audit._overlap(p,0x1AC,p+0x1AC,0x50))

    def test_wrong_selected_owner_hole_mode_or_scene_fails(self):
        for key,value in [('selected_ball_obj',0x90050000),('hole',2),
                          ('selected_index',1),('mode_word',(0,)),('pin_obj',0x90099900),
                          ('source_gate',False),('scene_gate',False)]:
            with self.subTest(key=key):
                data=samples()
                data[6][key]=value
                with self.assertRaises(ValueError): audit.matrix(registry(),data)

    def test_missing_phase_fails(self):
        data=samples(); data.pop(7)
        with self.assertRaises(ValueError): audit.matrix(registry(),data)


class EvidenceMatrixTest(unittest.TestCase):
    def test_d1_contradiction_wedge_differential_and_stable_controls(self):
        report=audit.matrix(registry(),samples())
        self.assertEqual(report['number_of_p0_rows'],25)
        self.assertEqual(report['control_summary']['wedge_pin_changed_counts'],[0,0,0])
        self.assertTrue(report['control_summary']['D1_selected_current_equals_start'])
        self.assertFalse(report['training_approved'])
        self.assertFalse(report['native_sha_pre_post_checked_by_existing_reader'])
        rows={v['id']:v for v in report['p0_rows']}
        self.assertEqual(rows['golf.ball_object.current_translation_candidate']
                         ['wedge_5_6_6_7_5_7_changed_word_counts'],[3,3,3])
        self.assertEqual(rows['golf.ball_object.initialized_cache_cc']
                         ['wedge_5_6_6_7_5_7_changed_word_counts'],[0,0,0])
        self.assertEqual(rows['golf.ball.world_xyz']['archive_observation'],
                         'unresolved_no_rendered_ball_locator')
        self.assertEqual(rows['golf.wind.hole_speed_table_source_candidate']['new_capture'],
                         'source_witness_first')
        self.assertIn('D1_human_airborne_selected_equals_START_unverified_mapping',
                      rows['golf.ball_object.current_translation_candidate']['contradictory_evidence'])
        self.assertEqual(report['absence_from_registry'],
                         ['verified_power','verified_impact_frame','verified_velocity',
                          'verified_result_distance'])

    def test_pin_changes_confounds_ball_discrimination(self):
        data=samples()
        data[6]['pin']=(1,8,3)
        report=audit.matrix(registry(),data)
        row=next(v for v in report['p0_rows'] if v['id']=='golf.ball_object.current_translation_candidate')
        self.assertFalse(row['supports_candidate_temporal_change_only'])
        self.assertIn('wedge_reference_geometry_changed_confounded',row['contradictory_evidence'])

    def test_pointer_values_and_private_paths_never_serialized(self):
        data=samples()
        data[5]['_sensitive_name']='C:/Users/private/archive/5.2.raw'
        report=audit.matrix(registry(),data)
        out=json.dumps(report)
        self.assertNotIn('0x90010000',out)
        self.assertNotIn('C:/Users/private',out)
        self.assertNotIn('90080000',out)
        self.assertIn('allowed_to_publish',out)

    def test_not_measured_wind_and_scores_do_not_become_verified(self):
        report=audit.matrix(registry(),samples())
        rows={v['id']:v for v in report['p0_rows']}
        for k in ('golf.wind.hole_direction_table_source_candidate',
                  'golf.wind.hole_speed_table_source_candidate',
                  'golf.sequence_mgr.golf_scores_hole_major_9x4'):
            self.assertEqual(rows[k]['archive_observation'],
                             'not_source_measured_in_this_reader')
            self.assertFalse(rows[k]['training_approved'])


class CliTest(unittest.TestCase):
    def test_unavailable_source_archive_refuses_without_path_leak(self):
        fake=types.ModuleType('audit_p0_seven_numbered_source_pairs_private')
        fake._check_archive=lambda _: (_ for _ in ()).throw(ValueError('C:/private/raw: hash invalid'))
        with patch.dict(sys.modules, {'audit_p0_seven_numbered_source_pairs_private':fake}):
            with tempfile.TemporaryDirectory() as tmp:
                archive=Path(tmp)/'secret-archive'
                out=io.StringIO()
                with redirect_stdout(out):
                    rc=audit.main(['--archive',str(archive)])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(out.getvalue())['status'],'ABSTAIN')
        self.assertNotIn('secret-archive',out.getvalue())
        self.assertNotIn('C:/private/raw',out.getvalue())

    def test_archive_manifest_pre_and_post_are_invoked(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            for n in range(1,8):
                (folder/f'{n}.1.raw').write_bytes(b'\x00'*24)
                (folder/f'{n}.2.raw').write_bytes(b'\x00'*64)
            called=[]
            fake=types.ModuleType('audit_p0_seven_numbered_source_pairs_private')
            fake.SIZE=(24,64)
            fake.roster=types.SimpleNamespace(TwoBankReader=lambda a,b: (a,b))
            fake.src=types.SimpleNamespace(_file=lambda root,name,size: root/name)
            def check(_):
                called.append(True)
                if len(called)>1:
                    raise ValueError('post hash failure')
                return {n: folder for n in range(1,8)}
            fake._check_archive=check
            values=samples()
            with patch.dict(sys.modules, {'audit_p0_seven_numbered_source_pairs_private':fake}),\
                 patch.object(audit,'_read_one',side_effect=[values[n] for n in range(1,8)]):
                reg=folder/'registry.json'
                reg.write_text(json.dumps(registry()))
                with self.assertRaisesRegex(ValueError,'post hash failure'):
                    audit.analyze(folder,reg)
            self.assertEqual(len(called),2)


if __name__=='__main__':
    unittest.main()
