"""Mock-only tests: never use or create native game memory."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from copy import deepcopy

HERE=Path(__file__).resolve().parents[1]
FILE=HERE/"scripts"/"audit_p0_seven_numbered_source_pairs_private.py"
spec=importlib.util.spec_from_file_location("seven_p0",FILE)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def capture(n):
    ball=(n,3,4)
    a=[0]*51
    a[0x34//4]=n
    a[0x38//4]=1 if n in (3,4) else 2
    a[0x74//4]=9 if n>4 else 0
    return {
        "selected_index":0,"hole":2,"whole_record":tuple(a),
        "triplets":{
            "ball_object_0x030":ball,
            "source_current_start":(1,3,4),
            "ball_cache_0x0cc":(1,3,4),
            "ball_cache_0x0f0":(1,3,4),
            "ball_cache_0x0fc":(1,3,4)
        },
        "pin":(10,20,30),"pin_obj":1,"start_obj":2,"field":3,
        "cfg_bc":5,"cfg_c0":6,"cfg_c4":7
    }

def seven():
    return {i:capture(i) for i in range(1,8)}

class TestSeven(unittest.TestCase):
    def test_pair_names(self):
        r=mod.summarize(seven())
        self.assertEqual([x["transition"] for x in r["comparisons"]],
                         ["1_to_2","3_to_4","5_to_6","6_to_7","5_to_7"])

    def test_phase_hints_are_unverified(self):
        r=mod.summarize(seven())
        self.assertFalse(r["number_to_human_phase_mapping_independently_verified"])
        self.assertIn("UNVERIFIED_MAPPING",str(r["samples"]))

    def test_pair_ball_changes(self):
        r=mod.summarize(seven())
        self.assertEqual(r["comparisons"][0]["ball_changed_components"],1)

    def test_unchanged_pin_and_start(self):
        r=mod.summarize(seven())
        self.assertTrue(all(x["start_changed_components"]==0 for x in r["comparisons"]))
        self.assertTrue(all(x["pin_changed_components"]==0 for x in r["comparisons"]))

    def test_pin_confounds_exposed(self):
        x=seven();x[6]["pin"]=(11,21,31);x[6]["pin_obj"]=9
        r=mod.summarize(x)
        self.assertEqual(r["comparisons"][2]["pin_changed_components"],3)
        self.assertFalse(r["comparisons"][2]["pin_object_pointer_identical"])

    def test_config_discriminator(self):
        x=seven();x[7]["cfg_c4"]=999
        r=mod.summarize(x)
        self.assertFalse(r["comparisons"][3]["config_C4_identical"])

    def test_different_selected_owner_rejects_numeric_delta(self):
        x=seven();x[2]["selected_index"]=1
        r=mod.summarize(x)
        self.assertFalse(r["comparisons"][0]["same_source_selected_slot_and_hole"])
        self.assertIsNone(r["comparisons"][0]["ball_changed_components"])

    def test_different_hole_rejects_numeric_delta(self):
        x=seven();x[2]["hole"]=3
        r=mod.summarize(x)
        self.assertIsNone(r["comparisons"][0]["pin_changed_components"])

    def test_record_flags(self):
        r=mod.summarize(seven())
        self.assertTrue(r["comparisons"][0]["record_34_changed"])
        self.assertFalse(r["comparisons"][1]["record_38_changed"])
        self.assertTrue(r["comparisons"][2]["record_74_changed"])

    def test_own_cache_matches(self):
        r=mod.summarize(seven())
        self.assertEqual(r["samples"][0]["ball_equal_cache_CC_components"],3)

    def test_nonatomic_conservative(self):
        r=mod.summarize(seven())
        for flag in ("same_guest_frame_per_pair_machine_verified",
                     "same_boot_across_pairs_verified","actual_ball_world_xyz_verified",
                     "ball_velocity_verified","game_power_ram_verified",
                     "impact_frame_verified","training_approved","allowed_to_publish"):
            self.assertIs(r[flag],False)

    def test_raw_numbers_not_printed(self):
        output=str(mod.summarize(seven()))
        self.assertNotIn("whole_record",output)
        self.assertNotIn("pin_obj",output)
        self.assertNotIn("cfg_bc",output)
        self.assertNotIn("(10, 20, 30)",output)

    def test_missing_phase_rejected(self):
        x=seven();del x[7]
        with self.assertRaisesRegex(ValueError,"Exactly seven"):
            mod.summarize(x)

    def test_invalid_triplet_rejected(self):
        x=seven();x[2]["pin"]=(1,2)
        with self.assertRaisesRegex(ValueError,"Incompatible"):
            mod.summarize(x)

    def test_archive_wrong_kind_rejected_without_ram(self):
        from unittest.mock import patch
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as t:
            folder=Path(t)/"captures"/"cohort"
            folder.mkdir(parents=True)
            (folder/"manifest-PRIVATE.json").write_text('{"kind":"wrong"}')
            with patch.object(mod.src.selected,"DATA_ROOT",Path(t)):
                with self.assertRaisesRegex(ValueError,"Unexpected archived"):
                    mod._check_archive(folder)

    def test_aria_python_isolated_import_smoke(self):
        x=subprocess.run([sys.executable,"-I",str(FILE),"--help"],
                         cwd=str(HERE),capture_output=True,text=True,timeout=20)
        self.assertEqual(x.returncode,0,x.stderr)
        self.assertIn("--archive",x.stdout)

if __name__=="__main__":
    unittest.main()
