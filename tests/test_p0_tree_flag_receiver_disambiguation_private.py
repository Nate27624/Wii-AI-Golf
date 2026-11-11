"""Synthetic-only falsification of +0x48 reader receiver identity."""
from __future__ import annotations

import importlib.util
import struct
from pathlib import Path
import sys
import unittest

DIR=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(DIR))
spec=importlib.util.spec_from_file_location("tree_receiver",DIR/"p0_tree_flag_receiver_disambiguation_private.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def direct_call(pc,dest):
    diff=dest-pc
    if diff%4 or not -(1<<25)<=diff<(1<<25):
        raise ValueError("PPC branch displacement out of range")
    return (18<<26)|(diff&0x03FFFFFC)|1


def d(op,rt,ra,off):
    return (op<<26)|(rt<<21)|(ra<<16)|(off&65535)


def floatword(f):
    return struct.unpack(">I",struct.pack(">f",f))[0]


def fixture():
    words=dict(m.ANCHORS)
    for _,(site,dest) in m.TARGETS.items():
        words[site]=direct_call(site,dest)
    # Native PSVECSquareDistance flag and exact native FieldManager loop.
    src=m.native.UNITS["FieldManager"][0]
    tree=m.TREE
    ball=m.native.UNITS["Ball"][0]
    words.update({
        src+0x06E8:d(32,0,28,0x20),
        src+0x06F0:direct_call(src+0x06F0,tree+0xC),
        src+0x06F4:d(14,31,31,84),
        src+0x06FC:d(32,0,28,0x1C),
        tree+0x0020:0x38630030,
        tree+0x0030:direct_call(tree+0x0030,m.proximity.DISTANCE_FN),
        tree+0x0034:0xC002C5C0,
        tree+0x0038:0xFC010040,
        tree+0x0044:0x981F0048,
        ball+0x0750:direct_call(ball+0x0750,m.proximity.DISTANCE_FN),
        ball+0x0760:direct_call(ball+0x0760,m.proximity.DISTANCE_FN),
    })
    source_code=dict(words)
    arrays={}
    base=0x90018000
    for i in range(94):
        obj=base+i*84
        for off in (0x1C,0x20,0x24,0x28):
            arrays[obj+off]=floatword((i%9)*0.1+1.0)
        # Most native tree +0x4c words are not finite candidate floats.
        arrays[obj+0x4C]=0xFFC01234
        arrays[obj+0x50]=floatword(2.0)
    def bank(ptr,size,kind):
        return (
            0x80000000<=ptr and ptr+size<=0x81800000
            if kind=="MEM1" else
            0x90000000<=ptr and ptr+size<=0x94000000
        )
    return source_code,lambda x:source_code.get(x,0),lambda x:arrays.get(x,0),bank,base


class TreeReceiverIdentityTests(unittest.TestCase):
    def test_native_reader_and_helper_target_fingerprints(self):
        _,read,_,_,_=fixture()
        self.assertTrue(m.validate_source(read))
        self.assertEqual(len(m.TARGETS),6)

    def test_actual_tree_field_structure_does_not_match_handle_object(self):
        _,read,mem,bank,base=fixture()
        r=m.classify_native_tree_fields(mem,bank,base,94)
        self.assertEqual(r["+0x1C"]["plausible_f32"],94)
        self.assertEqual(r["+0x1C"]["bounded_aligned_mem2_ptr"],0)
        self.assertEqual(r["+0x4C"]["plausible_f32"],0)
        self.assertEqual(r["+0x50"]["plausible_f32"],94)

    def test_source_receiver_context_still_unverified(self):
        _,read,mem,bank,base=fixture()
        r=m.classify(read,mem,bank,base,94)
        self.assertTrue(r["r30_offsets_0x4c_0x50_written_as_floats"])
        self.assertTrue(r["fieldmanager_byte_reader_after_camera_manager_call"])
        self.assertFalse(r["reader_has_proven_tree_record_receiver"])
        self.assertFalse(r["tree_0x48_flag_acts_as_hitbox_filter_proven"])
        self.assertFalse(r["tree_collision_geometry_proven"])
        self.assertFalse(r["training_approved"])

    def test_cross_source_camera_targets_are_explicit(self):
        _,read,mem,bank,base=fixture()
        r=m.classify(read,mem,bank,base,94)
        targets=r["specific_direct_call_targets"]
        self.assertEqual(
            targets["Tree+0x04CC -> Camera"]["source_target_relative"],
            "+0x028C"
        )
        self.assertEqual(
            targets["FieldManager+0x0784 -> CameraManager"]["source_target_relative"],
            "+0x02B0"
        )

    def test_single_native_reader_opcode_wrong_abstains(self):
        words,read,mem,bank,base=fixture()
        words[m.TREE+0x0504]=0
        # Reader-specific anchor is at +0x0504 and not in source
        # producer fingerprint. A changed opcode must fail.
        # Add explicit anchor; verified in native output.
        with self.assertRaises(ValueError):
            m.validate_source(read)

    def test_camera_callee_change_abstains(self):
        words,read,mem,bank,base=fixture()
        site=m.TREE+0x04CC
        words[site]=direct_call(site,0x8029BE44)
        with self.assertRaises(ValueError):
            m.validate_source(read)

    def test_fieldmanager_callee_change_abstains(self):
        words,read,mem,bank,base=fixture()
        site=m.FIELD+0x0784
        words[site]=direct_call(site,0x8028ED94)
        with self.assertRaises(ValueError):
            m.validate_source(read)

    def test_reject_wrong_tree_count(self):
        _,read,mem,bank,base=fixture()
        for count in (93,95,0):
            with self.subTest(count=count),self.assertRaises(ValueError):
                m.classify_native_tree_fields(mem,bank,base,count)

    def test_reject_array_outside_mem2(self):
        _,read,mem,bank,base=fixture()
        with self.assertRaises(ValueError):
            m.classify_native_tree_fields(mem,bank,0x94000000,94)

    def test_known_fieldmanager_tree_loop_direct_caller(self):
        _,read,mem,bank,base=fixture()
        r=m.find_callers(read)
        self.assertIn("FieldManager+0x06F0",
                      r["tree_distance_flag_writer"])

    def test_proven_source_module_is_not_hitbox(self):
        _,read,mem,bank,base=fixture()
        import json
        report=json.dumps(m.classify(read,mem,bank,base,94))
        self.assertNotIn("0x90018000",report)
        self.assertNotIn("0xFFC01234",report)
        self.assertNotIn("positions",report.lower())


if __name__=="__main__":
    unittest.main()
