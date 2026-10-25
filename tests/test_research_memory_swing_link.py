"""All synthetic; no Dolphin, network, raw RAM or game outcomes."""
import json
import unittest
from wii_ai_golf.research_memory_swing_link import assess_memory_swing_link

A = 'a' * 64
B = 'b' * 64


def fixture():
    memory = {
        'kind':'golf-memory-phase-differential','schema_version':1,
        'id':'mem-A','game_id':'RSPE01','disc_revision':1,'game_mode_raw':4,
        'scope':'focused','max_non_atomic_frame_span':2,
        'top_changed_relative_words':[
            {'region':'golf_config','relative_offset':'+0x9C','documented_role':'unknown',
             'phase_change_counts':{'idle':0,'aim_only':0,'a_hold':0,'club_motion':2,'shot_attempt':3}},
            {'region':'golf_field','relative_offset':'+0x94','documented_role':'minimap_player_effect_pointer',
             'phase_change_counts':{'idle':0,'aim_only':1,'club_motion':2}},
        ],
        'phase_frame_brackets':[{'phase':'idle','frame_start':90,'frame_end':91},
                                {'phase':'club_motion','frame_start':110,'frame_end':112},
                                {'phase':'shot_attempt','frame_start':120,'frame_end':121}],
        'linkage':{'swing_id':'shot-A','session_id':'boot-A','scene_fingerprint':'tee-A',
                   'bridge_sha256':A,'trace_sha256':B,'shot_start_frame':100},
    }
    swing = {'kind':'v1','schema':1,'id':'shot-A','process_exit_code':0,
             'bridge_sha256':A,'controller':{'trace_sha256':B,'generated_trace_frames':89},
             'human':{'contact_human':'yes','initial_club_pose_human':'back',
                       'shot_start_frame_before_controller_trace':100,
                       'displayed_distance_human':100,'displayed_unit_human':'ft',
                       'displayed_power_percent_human':75,'finished_on_green_human':'no'},
             'linkage':{'memory_id':'mem-A','session_id':'boot-A','scene_fingerprint':'tee-A',
                        'bridge_sha256':A,'trace_sha256':B,'shot_start_frame':100}}
    return memory,swing

class LinkGates(unittest.TestCase):
    def test_valid_future_synthetic_link_ranks_control(self):
        m,s=fixture(); result=assess_memory_swing_link(m,s)
        self.assertTrue(result['mutually_linked_trial']); self.assertFalse(result['blockers'])
        self.assertEqual(result['phase_specific_candidate_count'],2)
        self.assertEqual(result['candidate_priorities'][0]['priority'],'test_with_repeated_controls')
        self.assertEqual(result['candidate_priorities'][1]['priority'],'visual_or_structural_control')
        self.assertFalse(result['game_power_calibrated'])

    def test_current_real_report_without_linkage_is_not_joined(self):
        m,s=fixture(); m.pop('linkage'); s.pop('linkage')
        v=assess_memory_swing_link(m,s)
        self.assertFalse(v['mutually_linked_trial']); self.assertEqual(v['candidate_priorities'],[])
        self.assertIn('no_mutual_same_shot_linkage',v['blockers'])

    def test_same_bridge_different_boot_never_assumed_paired(self):
        m,s=fixture();s['linkage']['session_id']='boot-B'
        self.assertIn('missing_or_mismatched_session_id',assess_memory_swing_link(m,s)['blockers'])

    def test_scene_isolation(self):
        m,s=fixture();s['linkage']['scene_fingerprint']='tee-B'
        self.assertIn('missing_or_mismatched_scene_fingerprint',assess_memory_swing_link(m,s)['blockers'])

    def test_reciprocal_shot_ids(self):
        m,s=fixture();s['linkage']['memory_id']='mem-other'
        self.assertIn('nonreciprocal_same_shot_ids',assess_memory_swing_link(m,s)['blockers'])

    def test_swing_start_frame_conflict(self):
        m,s=fixture();s['human']['shot_start_frame_before_controller_trace']=999
        self.assertIn('missing_original_swing_frame_anchor',assess_memory_swing_link(m,s)['blockers'])

    def test_absent_frame_brackets(self):
        m,s=fixture(); m.pop('phase_frame_brackets')
        self.assertIn('no_phase_specific_frame_brackets',assess_memory_swing_link(m,s)['blockers'])

    def test_samples_outside_swing_window(self):
        m,s=fixture();m['phase_frame_brackets']=[{'phase':'club_motion','frame_start':600,'frame_end':601}]
        self.assertIn('no_memory_samples_overlap_swing_window',assess_memory_swing_link(m,s)['blockers'])

    def test_high_nonatomic_sample_span_rejected(self):
        m,s=fixture();m['max_non_atomic_frame_span']=12
        self.assertIn('slow_or_unknown_non_atomic_ram_read',assess_memory_swing_link(m,s)['blockers'])

    def test_existing_global_only_offset_counts_do_not_pretend_phase_specific(self):
        m,s=fixture();m['top_changed_relative_words'][0].pop('phase_change_counts');m['top_changed_relative_words'][1].pop('phase_change_counts')
        v=assess_memory_swing_link(m,s)
        self.assertTrue(v['mutually_linked_trial'])
        self.assertIn('no_per_offset_phase_change_counts',v['blockers'])
        self.assertEqual(v['candidate_priorities'],[])

    def test_negative_control_sensitivity_downgraded(self):
        m,s=fixture(); m['top_changed_relative_words'][0]['phase_change_counts']['idle']=2
        v=assess_memory_swing_link(m,s)
        self.assertEqual(v['candidate_priorities'][0]['priority'],'negative_control_sensitive')

    def test_nonfinite_unsanitized_strings_do_not_leak(self):
        m,s=fixture();m['raw_memory']='private-secret';s['file_path']='private-local'
        t=json.dumps(assess_memory_swing_link(m,s))
        self.assertNotIn('private-secret',t);self.assertNotIn('private-local',t)
        self.assertNotIn('bytes_hex',t)

    def test_human_100ft_penalty_not_physical_measurement(self):
        m,s=fixture();v=assess_memory_swing_link(m,s)
        self.assertFalse(v['physical_ball_carry_verified'])
        self.assertFalse(v['game_power_calibrated'])
        self.assertNotIn('displayed_distance_human',json.dumps(v))

    def test_bad_revision_refused(self):
        m,s=fixture();m['disc_revision']=0
        self.assertIn('memory_game_revision_not_explicitly_validated',assess_memory_swing_link(m,s)['blockers'])

    def test_corrupt_waveform_rejected(self):
        m,s=fixture();s['controller']['trace_sha256']='0' * 64
        self.assertIn('swing_waveform_linkage_conflict',assess_memory_swing_link(m,s)['blockers'])

    def test_fail_run_unknowns_preserved(self):
        m,s=fixture();s['process_exit_code']=1;s['human']['contact_human']='unknown'
        v=assess_memory_swing_link(m,s)
        self.assertFalse(v['mutually_linked_trial']);self.assertIn('incomplete_swing_run',v['blockers'])

    def test_reject_invalid_stage_counts(self):
        m,s=fixture();m['top_changed_relative_words'][0]['phase_change_counts']['shot_attempt']=-1
        v=assess_memory_swing_link(m,s)
        self.assertEqual(v['phase_specific_candidate_count'],1)

    def test_safe_bounded_return(self):
        m,s=fixture();m['top_changed_relative_words']*=200
        v=assess_memory_swing_link(m,s)
        self.assertIn('missing_or_oversized_sanitized_offset_list',v['blockers'])
        self.assertEqual(v['phase_specific_candidate_count'],0)

if __name__=='__main__': unittest.main()
