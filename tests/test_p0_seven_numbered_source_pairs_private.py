"""Mock-only tests: never use or create native game memory."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import subprocess
import struct
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
        "pin":(10,20,30),"selected_ball_obj":4,
        "pin_obj":1,"start_obj":2,"field":3,
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
        self.assertFalse(r["comparisons"][2]["record_74_changed"])
        x=seven()
        x[6]["whole_record"]=list(x[6]["whole_record"])
        x[6]["whole_record"][0x74//4]=10
        self.assertTrue(mod.summarize(x)["comparisons"][2]["record_74_changed"])

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
        self.assertNotIn("'pin_obj':",output)
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

    def test_single_selected_middle_direction_against_stationary_controls(self):
        phases=seven()
        for i, val in ((5,6.0), (6,3.0), (7,1.0)):
            words=list(phases[i]["triplets"]["ball_object_0x030"])
            words[1]=struct.unpack(">I",struct.pack(">f",val))[0]
            phases[i]["triplets"]["ball_object_0x030"]=tuple(words)
        output=mod.summarize(phases)["ball_middle_component_hypothesis"]
        self.assertEqual(output["relative_ball_object_offset"],"+0x34")
        self.assertEqual([row["transition"] for row in output["wedge_edges"]],
                         ["5_to_6","6_to_7","5_to_7"])
        for row in output["wedge_edges"]:
            self.assertEqual(row["selected_ball_plus_0x34_direction"],"decreasing")
            self.assertEqual(row["selected_cache_plus_0xD0_direction"],"unchanged")
            self.assertEqual(row["start_middle_direction"],"unchanged")
            self.assertEqual(row["pin_middle_direction"],"unchanged")
        self.assertFalse(output["middle_axis_as_world_y_verified"])
        self.assertFalse(output["source_global_control_measured_in_this_reader"])
        self.assertFalse(output["allowed_to_publish"])
        self.assertNotIn("6.0",str(output))
        self.assertNotIn("3.0",str(output))

    def test_middle_direction_numeric_not_float32_bitwise_signed_zero(self):
        a=struct.unpack(">I",struct.pack(">f",-0.0))[0]
        b=struct.unpack(">I",struct.pack(">f",0.0))[0]
        self.assertEqual(mod._middle_direction(a,b),"unchanged")
        self.assertEqual(mod._middle_direction(b,a),"unchanged")
        self.assertEqual(mod._middle_direction(0x3f800000,0x40000000),"increasing")
        self.assertEqual(mod._middle_direction(0x40000000,0x3f800000),"decreasing")

    def test_nan_infinity_noninteger_and_bool_rejected_without_leakage(self):
        for invalid in (0x7fc00001,0x7f800000,0xff800000,-1,2**32,
                        True,False,"0x3f800000"):
            with self.subTest(invalid=type(invalid).__name__):
                with self.assertRaisesRegex(ValueError,"middle-component"):
                    mod._middle_direction(0x3f800000,invalid)

    def test_wedge_ball_identity_changed_abstains(self):
        phases=seven()
        phases[6]["selected_ball_obj"]=12
        with self.assertRaisesRegex(ValueError,"owner or object identity"):
            mod.middle_component_study(phases)

    def test_wedge_owner_hole_changed_abstains(self):
        phases=seven()
        phases[7]["hole"]=3
        with self.assertRaisesRegex(ValueError,"owner or object identity"):
            mod.middle_component_study(phases)

    def test_wedge_config_changed_abstains(self):
        phases=seven()
        phases[6]["cfg_c0"]=77
        with self.assertRaisesRegex(ValueError,"Config selector"):
            mod.middle_component_study(phases)

    def test_wedge_start_or_pin_changed_abstains(self):
        for key in ("source_current_start","pin"):
            phases=seven()
            if key=="pin":
                phases[7]["pin"]=(10,999,30)
            else:
                phases[7]["triplets"][key]=(1,999,4)
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError,"tee or pin changed"):
                    mod.middle_component_study(phases)

    def test_wedge_selected_middle_nonfinite_abstains(self):
        phases=seven()
        words=list(phases[6]["triplets"]["ball_object_0x030"])
        words[1]=0x7fc00000
        phases[6]["triplets"]["ball_object_0x030"]=tuple(words)
        with self.assertRaisesRegex(ValueError,"Nonfinite"):
            mod.middle_component_study(phases)

    def test_other_club_pair_not_used_as_middle_height_evidence(self):
        phases=seven()
        phases[3]["triplets"]["ball_object_0x030"]=(999,999,999)
        output=mod.middle_component_study(phases)
        self.assertEqual([x["transition"] for x in output["wedge_edges"]],
                         ["5_to_6","6_to_7","5_to_7"])

    def test_confounded_scalar_abstains_without_suppressing_original_audit(self):
        for key in ("cfg_c4", "pin"):
            phases=seven()
            if key == "pin":
                phases[6]["pin_obj"]=777
            else:
                phases[6]["cfg_c4"]=999
            with self.subTest(key=key):
                report=mod.summarize(phases)
                self.assertEqual(report["ball_middle_component_hypothesis"]["status"],
                                 "abstained")
                self.assertEqual(report["ball_middle_component_hypothesis"]["wedge_edges"],[])
                self.assertFalse(report["ball_middle_component_hypothesis"]["allowed_to_publish"])
                self.assertEqual(len(report["comparisons"]),5)

    def test_middle_only_cli_prints_categorical_report_without_raw_values(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch
        output=StringIO()
        with patch.object(mod,"analyze",return_value=mod.summarize(seven())):
            with redirect_stdout(output):
                code=mod.main(["--archive","fake-local-only","--middle-only"])
        self.assertEqual(code,0)
        payload=__import__("json").loads(output.getvalue())
        self.assertEqual(payload["status"],"source_numeric_direction_only")
        self.assertEqual(payload["relative_ball_object_offset"],"+0x34")
        self.assertNotIn("whole_record",output.getvalue())
        self.assertNotIn('"samples"',output.getvalue())
        self.assertNotIn('"comparisons"',output.getvalue())

    def test_middle_only_cli_abstention_is_nonzero(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch
        x=seven()
        x[6]["cfg_bc"]=9
        output=StringIO()
        with patch.object(mod,"analyze",return_value=mod.summarize(x)):
            with redirect_stdout(output):
                code=mod.main(["--archive","fake-local-only","--middle-only"])
        self.assertEqual(code,2)
        self.assertIn('"status": "abstained"',output.getvalue())
        self.assertNotIn("whole_record",output.getvalue())

    def test_scoped_abstentions_use_fixed_privacy_safe_reason_codes(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch
        import json
        cases=(
            ("Archived bank SHA mismatch","archive_bank_sha_mismatch"),
            ("Source-selected ball object/selfref invalid","selected_ball_source_selfref_invalid"),
            ("Source pin/start/config incomplete","pin_start_config_source_gate_failed"),
            ("C:\\\\PRIVATE\\\\USER\\\\MEM2.BIN is missing","archive_or_source_gate_unqualified"),
        )
        for message, expected in cases:
            with self.subTest(expected=expected):
                output=StringIO()
                with patch.object(mod,"analyze",side_effect=ValueError(message)):
                    with redirect_stdout(output):
                        code=mod.main(["--archive","fake-private-folder","--middle-only"])
                self.assertEqual(code,2)
                report=json.loads(output.getvalue())
                self.assertEqual(report["status"],"abstained")
                self.assertEqual(report["reason_code"],expected)
                self.assertEqual(report["stage"],"archive_or_source_validation")
                self.assertFalse(report["training_approved"])
                self.assertFalse(report["allowed_to_publish"])
                self.assertNotIn("PRIVATE",output.getvalue())
                self.assertNotIn("MEM2.BIN",output.getvalue())

    def test_scoped_confound_has_specific_whitelisted_abstain_reason(self):
        phases=seven()
        phases[6]["cfg_c4"]=999
        row=mod.summarize(phases)["ball_middle_component_hypothesis"]
        self.assertEqual(row["status"],"abstained")
        self.assertEqual(row["reason_code"],"scalar_wedge_config_changed")
        self.assertEqual(row["wedge_edges"],[])

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
