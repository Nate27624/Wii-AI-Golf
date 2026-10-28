"""Fabricated PPC and native-object controls for source-global vs selected ball.

No RAM image is required, no network, no Dolphin and no private source bytes.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_p0_cache_global_receiver_private as target


def lwz(rt,ra,off):
    return (32<<26)|(rt<<21)|(ra<<16)|(off&65535)


def mr(ra,rs):
    return (31<<26)|(rs<<21)|(ra<<16)|(rs<<11)|(444<<1)


def bl(pc,dest):
    return (18<<26)|((dest-pc)&0x03fffffc)|1


def instruction_fixture():
    mem={
        target.R13_ANCHOR_PC: lwz(3,13,-23320),
        target.GLOBAL_LOAD_PC: lwz(3,13,-100),
        target.TRANSLATION_FOLLOW_PC: lwz(3,3,0x4c),
        target.RECEIVER_SAVE_PC: mr(27,3),
    }
    for _name,pc,start in target.CALLS:
        for addr in range(max(pc-0x40,start),pc,4):
            mem[addr]=0x60000000
        mem[pc-4]=mr(3,31)
        mem[pc]=bl(pc,target.CACHE_WRITER_ENTRY)
    return mem


def source_fixture():
    start=(1,2,3)
    end=(9,10,11)
    out={}
    for phase in range(1,8):
        cur=({5:(4,5,6),6:(7,8,9),7:end}).get(phase,start)
        out[phase]={
            "selected_index":0,"hole":1,
            "refs":{"ball":0x90002000,"start":0x90002100,
                    "pin":0x90002200,"scene_field":0x90002300},
            "triplets":{
                "ball_nested_plus_0x4c":cur,
                "ball_cache_0x0cc":end,
                "source_current_start":start,
            }
        }
    return out


class GlobalReceiverAuditTests(unittest.TestCase):
    def setUp(self):
        self.mem=instruction_fixture()

    def test_rev1_r13_anchor_and_direct_load(self):
        o=target.source_global_slot(self.mem.__getitem__)
        self.assertTrue(o["static_source_global_slot_supported"])
        self.assertEqual(o["slot"],target.SDA_BASE-100)
        self.assertIn("r13",o["global_load_type"])

    def test_wrong_anchor_abstains(self):
        self.mem[target.R13_ANCHOR_PC]=lwz(3,13,-23316)
        with self.assertRaises(ValueError):
            target.source_global_slot(self.mem.__getitem__)

    def test_wrong_nested_translation_follow_abstains(self):
        self.mem[target.TRANSLATION_FOLLOW_PC]=lwz(3,3,0x48)
        with self.assertRaises(ValueError):
            target.source_global_slot(self.mem.__getitem__)

    def test_receiver_r27_save_requires_real_or_register(self):
        self.mem[target.RECEIVER_SAVE_PC]=mr(26,3)
        with self.assertRaises(ValueError):
            target.source_global_slot(self.mem.__getitem__)

    def test_unknown_global_load_abstains_from_pointer_claim(self):
        self.mem[target.GLOBAL_LOAD_PC]=lwz(3,31,0x10)
        o=target.source_global_slot(self.mem.__getitem__)
        self.assertFalse(o["static_source_global_slot_supported"])
        self.assertIsNone(o["slot"])

    def test_two_exact_bl_and_nearby_r3_candidates(self):
        o=target.caller_input_probe(self.mem.__getitem__)
        self.assertEqual(len(o),2)
        self.assertEqual([x["nearest_bounded_r3_definition_class"] for x in o],
                         ["mr_from_r31","mr_from_r31"])
        self.assertTrue(all(x["exact_bl_to_cache_writer_entry"] for x in o))
        self.assertTrue(all(not x["runtime_r3_receiver_resolved"] for x in o))

    def test_wrong_static_call_destination_refused(self):
        _name,pc,_start=target.CALLS[0]
        self.mem[pc]=bl(pc,target.CACHE_WRITER_ENTRY+4)
        with self.assertRaises(ValueError):
            target.caller_input_probe(self.mem.__getitem__)

    def test_control_flow_hazard_marks_receiver_unknown(self):
        _name,pc,_start=target.CALLS[0]
        self.mem[pc-8]=(16<<26)  # unclassified conditional branch
        o=target.caller_input_probe(self.mem.__getitem__)
        self.assertTrue(o[0]["bounded_pre_call_control_transfer_present"])
        self.assertFalse(o[0]["runtime_r3_receiver_resolved"])

    def test_private_global_pointer_relation_does_not_export_pointer(self):
        code={"slot":0x804c5300,"static_source_global_slot_supported":True}
        val={
            code["slot"]:0x90002000,
            0x90002000+0x4c:0x90002030,
            0x90002030:9, 0x90002034:10, 0x90002038:11
        }
        source=source_fixture()[7]
        o=target.sample_runtime(val.__getitem__,source,code)
        self.assertTrue(o["source_global_is_source_selected_ball_object"])
        self.assertEqual(o["global_current_equals_selected_current_components"],3)
        self.assertEqual(o["global_current_equals_selected_cache_CC_components"],3)

    def test_nonselfref_object_abstains(self):
        code={"slot":0x804c5300,"static_source_global_slot_supported":True}
        val={code["slot"]:0x90002000,0x9000204c:0x90009000}
        with self.assertRaises(ValueError):
            target.sample_runtime(val.__getitem__,source_fixture()[7],code)

    def test_unexpected_global_load_no_runtime_dereference(self):
        o=target.sample_runtime(lambda a: (_ for _ in ()).throw(AssertionError("read")),source_fixture()[7],
                                {"slot":None,"static_source_global_slot_supported":False})
        self.assertFalse(o["supported"])

    def test_seven_phase_summary_excludes_private_pointer_and_bits(self):
        samples=source_fixture()
        codes={}
        for i in range(1,8):
            cur=samples[i]["triplets"]["ball_nested_plus_0x4c"]
            codes[i]={
                "global_load_type":"lwz_r3_disp_r13_then_lwz_r3_0x4c_r3",
                "static_source_global_slot_supported":True,
                "runtime":{
                    "supported":True,
                    "source_global_is_source_selected_ball_object":False,
                    "global_current_equals_selected_current_components":3 if i==7 else 0,
                    "global_current_equals_selected_cache_CC_components":3,
                    "global_current_equals_source_START_components":0,
                    "_private_runtime_source_global_pointer":0x90005000,
                    "_private_runtime_global_current_words":(9,10,11),
                }
            }
        report=target.summarize(samples,codes,[])
        self.assertTrue(report["source_global_ball_pointer_stable_W5_to_W7"])
        self.assertFalse(report["cache_writer_runtime_receiver_equals_selected_ball_verified"])
        self.assertFalse(report["allowed_to_publish"])
        txt=json.dumps(report)
        self.assertNotIn("0x90005000",txt)
        self.assertNotIn("_private",txt)
        self.assertNotIn("source_global_slot",txt.replace("source_global_pointer_resolution_supported",""))

    def test_same_shot_object_pointer_changed_abstains(self):
        samples=source_fixture()
        samples[6]["refs"]["ball"]+=4
        with self.assertRaises(ValueError):
            target.summarize(samples,{i:{"global_load_type":"x",
                                        "static_source_global_slot_supported":False,
                                        "runtime":{"supported":False}} for i in range(1,8)},[])

    def test_dform_signed_negative(self):
        self.assertEqual(target.dform(lwz(3,13,-100))["imm"],-100)
        self.assertEqual(target.dform(lwz(3,13,12))["imm"],12)

    def test_isolated_help_no_reader_leak(self):
        script=Path(target.__file__)
        p=subprocess.run([sys.executable,"-I",str(script),"--help"],
                         cwd=script.parents[2],capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("--dump-directory",p.stdout)


if __name__=="__main__":
    unittest.main()
