"""Synthetic-only source census for global object +0x5C byte gate."""
from __future__ import annotations
import importlib.util
import json
import io
import tempfile
from unittest import mock
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
p=ROOT/"scripts"/"p0_ball_global_5c_source_census_private.py"
s=importlib.util.spec_from_file_location("p0_global_byte_census",p)
m=importlib.util.module_from_spec(s)
s.loader.exec_module(m)


def d(op,reg,base,disp):
    return (op<<26)|(reg<<21)|(base<<16)|(disp&0xffff)


def data():
    return {
        m.EXACT_PTR_LOAD:d(32,3,13,m.GLOBAL_SLOT),
        m.EXACT_FLAG_READ:d(34,0,3,m.BYTE_FIELD),
    }


def reader(c):
    return lambda pc:c.get(pc,0x60000000)


class GlobalByteWriterCensusTests(unittest.TestCase):
    def test_known_global_slot_load_plus_byte_gate_exact(self):
        q=m.exact_flag_gate(reader(data()))
        self.assertTrue(q["original_native_pointer_and_byte_loads_consecutive"])
        self.assertEqual(q["original_global_pointer_load_site"],"Ball+0x2FB8")
        self.assertEqual(q["original_flag_byte_read_site"],"Ball+0x2FBC")
        self.assertFalse(q["global_object_is_selected_Ball_proven"])

    def test_global_byte_offset_changed_abstains(self):
        p=data()
        p[m.EXACT_FLAG_READ]=d(34,0,3,0x60)
        with self.assertRaises(ValueError):
            m.exact_flag_gate(reader(p))

    def test_global_slot_changed_abstains(self):
        p=data()
        p[m.EXACT_PTR_LOAD]=d(32,3,13,-23300)
        with self.assertRaises(ValueError):
            m.exact_flag_gate(reader(p))

    def test_direct_global_plus_byte_read_has_bounded_source(self):
        q=m.bounded_global_producer(reader(data()),"Ball",m.EXACT_FLAG_READ,3)
        self.assertEqual(q["status"],"bounded_direct_global_slot_load")
        self.assertEqual(q["instructions_prior_to_byte_access"],1)
        self.assertFalse(q["same_global_object_proven"])

    def test_intervening_r3_redefinition_stops_producer(self):
        p=data()
        p[m.EXACT_FLAG_READ-4]=d(14,3,3,4)
        p[m.EXACT_FLAG_READ-8]=d(32,3,13,m.GLOBAL_SLOT)
        q=m.bounded_global_producer(reader(p),"Ball",m.EXACT_FLAG_READ,3)
        self.assertEqual(q["status"],"stop_other_GPR_base_definition")

    def test_control_transfer_abstains_before_looking_for_global_load(self):
        p=data()
        p[m.EXACT_FLAG_READ-4]=0x48000008
        q=m.bounded_global_producer(reader(p),"Ball",m.EXACT_FLAG_READ,3)
        self.assertEqual(q["status"],"stop_prior_control_transfer")

    def test_source_byte_stores_and_slot_writes_counted_without_object_promotion(self):
        p=data()
        a=m.BALL+0x0100
        p[a]=d(32,7,13,m.GLOBAL_SLOT)
        p[a+4]=d(38,9,7,0x5c)
        p[a+8]=d(36,8,13,m.GLOBAL_SLOT)
        out=m.census(reader(p))
        ball=out["per_source_unit"]["Ball"]
        self.assertEqual(ball["original_r13_slot_store_count"],1)
        self.assertEqual(ball["source_numeric_0x5C_D_form_access_counts"]["stb"],1)
        matches=[x for x in ball["bounded_access_sites"]
                 if x["source_site"]=="Ball+0x0104"]
        self.assertEqual(len(matches),1)
        self.assertEqual(matches[0]["possible_global_base_ancestry"]["status"],
                         "bounded_direct_global_slot_load")
        self.assertFalse(matches[0]["object_receiver_identity_verified"])
        self.assertFalse(out["byte_plus_0x5C_is_selected_Ball_or_tree_material_proven"])

    def test_numeric_offset_match_not_same_receiver(self):
        p=data()
        p[m.BALL+0x0200]=d(38,0,31,0x5c)
        out=m.census(reader(p))
        x=[q for q in out["per_source_unit"]["Ball"]["bounded_access_sites"]
           if q["source_site"]=="Ball+0x0200"][0]
        self.assertEqual(x["possible_global_base_ancestry"]["status"],
                         "no_bounded_global_source")
        self.assertFalse(x["object_receiver_identity_verified"])

    def test_nonbyte_store_to_member_not_misclassified_stb(self):
        p=data()
        p[m.BALL+0x0400]=d(52,0,3,0x5c)
        out=m.census(reader(p))
        self.assertIn("stfs",out["per_source_unit"]["Ball"][
            "source_numeric_0x5C_D_form_access_counts"])
        self.assertNotIn("stb",out["per_source_unit"]["Ball"][
            "source_numeric_0x5C_D_form_access_counts"])

    def test_original_byte_census_reports_last_synthetic_source_stage(self):
        progress={"stage":"initial"}
        r=m.inspect(reader(data()),progress)
        self.assertEqual(progress["stage"],"native_unit_GolfKCol")
        self.assertFalse(r["wood_vs_foliage_material_split_verified"])

    def test_abstention_reports_safe_stage_without_private_exception_text(self):
        captured=io.StringIO()
        secret="PRIVATE-SHA-AND-GAME-DATA-MUST-NOT-BE-OUTPUT"
        progress={}
        def fail(*args):
            progress["checked"]=True
            raise ValueError(secret)
        with mock.patch.object(m,"run",side_effect=fail):
            with mock.patch("sys.stdout",captured):
                result=m.main(["--archive","irrelevant-private-path","--capture","7"])
        self.assertTrue(progress["checked"])
        self.assertEqual(result,2)
        report=json.loads(captured.getvalue())
        self.assertEqual(report["status"],"ABSTAIN_ORIGINAL_SHA_SOURCE_OR_ARGUMENT_GATE")
        self.assertEqual(report["failure_exception_class"],"ValueError")
        self.assertEqual(report["failed_public_stage"],"initial")
        self.assertNotIn(secret,captured.getvalue())
        self.assertFalse(report["training_approved"])

    def test_native_archive_mmap_uses_open_file_handle_not_path(self):
        # Synthetic-only bank fixture: no original source archive/ROM.
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"synthetic.mem1"
            path.write_bytes(bytes.fromhex("60000000")*4)
            def fake_inspect(read,progress=None):
                if progress is not None:
                    progress["stage"]="synthetic_native_bank_check"
                if read(m.MEM1)!=0x60000000:
                    raise ValueError("Synthetic MEM1 mapping mismatch")
                return {"status":"SYNTHETIC_SOURCE_BANK_OPENED"}
            fake_sha_gate={
                "original_seven_pair_SHA_and_source_verified":True,
                "original_source_capture":7,
                "original_entry_r4_to_r28_straightline_source_verified":True,
            }
            with mock.patch.object(m.before,"run",return_value=fake_sha_gate):
                with mock.patch.object(m.seven,"_check_archive",
                                       return_value={7:Path(folder)}) as verifier:
                    with mock.patch.object(m.seven,"SIZE",(16,)):
                        with mock.patch.object(m.seven.src,"_file",
                                               return_value=path):
                            with mock.patch.object(m,"inspect",side_effect=fake_inspect):
                                result=m.run(Path(folder),7)
            self.assertEqual(result["status"],"SYNTHETIC_SOURCE_BANK_OPENED")
            self.assertTrue(result["original_archive_and_native_scene_SHA_verified"])
            self.assertEqual(verifier.call_count,2)

    def test_output_remains_source_only_no_original_RAM_or_physics_promotion(self):
        r=m.inspect(reader(data()))
        text=json.dumps(r,sort_keys=True)
        self.assertNotIn("0x90008000",text)
        self.assertNotIn("private_archive",text)
        self.assertFalse(r["global_owner_selected_live_Ball_verified"])
        self.assertFalse(r["wood_vs_foliage_material_split_verified"])
        self.assertFalse(r["training_approved"])


if __name__=="__main__":
    unittest.main()
