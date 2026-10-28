"""Only synthetic cache bit-equality tests; no Dolphin, RAM or external IO."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import audit_p0_inflight_cache_coherence_private as audit


def sample(*,current=(1,2,3),caches=None,index=0,hole=1,
           selfref=True):
    if caches is None:
        caches=(current,current,current)
    obj={
        "ball_nested_plus_0x4c":current,
        "ball_object_0x030":current,
        "ball_cache_0x0cc":caches[0],
        "ball_cache_0x0f0":caches[1],
        "ball_cache_0x0fc":caches[2],
        "record_0x054":(1,2,3),
        "record_0x060":(1,2,3),
        "source_current_start":(1,2,3),
    }
    return {
        "selected_index":index,"hole":hole,"triplets":obj,
        "ball_constructor_translation_selfref":selfref,
    }


class CacheCoherenceTests(unittest.TestCase):
    def test_source_ball_cache_aliased_same_in_both_phases(self):
        b0=sample()
        flight=sample(current=(4,5,6))
        output=audit.compare(b0,flight)
        self.assertEqual(
            output["phases"]["airborne_operator"]["unique_ball_related_three_word_bit_patterns"],1)
        self.assertTrue(output["all_three_caches_equal_current_ball_within_B0"])
        self.assertTrue(output["all_three_caches_equal_current_ball_within_airborne"])
        self.assertFalse(output["five_cross_phase_3_component_changes_independent_evidence"])
        self.assertFalse(output["actual_ball_world_xyz_verified"])
        self.assertFalse(output["approved_for_training"])
        self.assertNotIn('"4, 5, 6"',json.dumps(output))

    def test_three_caches_distinct_from_current(self):
        flight=sample(current=(4,5,6),caches=((4,5,6),(7,5,6),(8,5,6)))
        output=audit.compare(sample(),flight)
        p=output["phases"]["airborne_operator"]
        self.assertEqual(p["unique_ball_related_three_word_bit_patterns"],3)
        self.assertEqual(p["pairwise_equal_component_counts"][
            "ball_nested_plus_0x4c__vs__ball_cache_0x0f0"],2)
        self.assertFalse(output["all_three_caches_equal_current_ball_within_airborne"])

    def test_nested_plus_030_is_same_pointer_alias_not_distinct(self):
        a=sample()
        a["triplets"]["ball_object_0x030"]=(9,9,9)
        with self.assertRaisesRegex(ValueError,"alias disagree"):
            audit.compare(a,sample())
        with self.assertRaisesRegex(ValueError,"self-reference"):
            audit.compare(sample(selfref=False),sample())

    def test_different_selected_owner_rejected(self):
        for v in (sample(index=2),sample(hole=6)):
            with self.assertRaisesRegex(ValueError,"slot/hole"):
                audit.compare(sample(),v)

    def test_invalid_bitpatterns_are_not_finite_bounded(self):
        invalid=sample(current=(0x7FC00000,0,0))
        result=audit.compare(sample(),invalid)
        self.assertFalse(result["phases"]["airborne_operator"][
            "candidate_three_float_finite_bounded"]["ball_nested_plus_0x4c"])

    def test_python_I_help_from_unrelated_cwd_imports_source(self):
        with tempfile.TemporaryDirectory() as directory:
            proc=subprocess.run([sys.executable,"-I",
                    str(ROOT/"scripts"/"audit_p0_inflight_cache_coherence_private.py"),
                    "--help"],
                cwd=directory,capture_output=True,text=True,check=False,timeout=15)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertIn("--baseline",proc.stdout)
        self.assertNotIn("ModuleNotFoundError",proc.stderr)

    def test_bad_source_sample_shape_rejected(self):
        incomplete=sample()
        del incomplete["triplets"]["ball_cache_0x0cc"]
        with self.assertRaisesRegex(ValueError,"missing source-gated"):
            audit.compare(sample(),incomplete)


if __name__=="__main__":
    unittest.main()
