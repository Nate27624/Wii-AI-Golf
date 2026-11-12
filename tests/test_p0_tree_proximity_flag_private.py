"""Synthetic PPC tree proximity+0x48 and 94-record type profile tests."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import struct
import sys
import unittest
SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location("tree_prox",SCRIPTS/"p0_tree_proximity_flag_private.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fbits(value):
    return struct.unpack(">I",struct.pack(">f",value))[0]


def make_records(*,flags=None):
    base=0x90010000
    mem={}
    for i in range(94):
        at=base+84*i
        scale=1.0+(i%4)*0.1
        mem[at+4]=0x12345678 if i%2 else 0x87654321
        mem[at+8]=0x11223344 if i%2 else 0x44332211
        mem[at+0x30]=fbits(float(i*100))
        mem[at+0x34]=fbits(float(i))
        mem[at+0x38]=fbits(float(i*200))
        for j in range(3):
            mem[at+0x3C+j*4]=fbits(scale)
        mem[at+0x48]=(flags[i] if flags is not None else (i%2))<<24
        mem[at+0x4C]=fbits(3.+i*.1)
    def bank(p,n,kind):
        if kind=="MEM2":
            return 0x90000000<=p and p+n<=0x94000000
        if kind=="MEM1":
            return 0x80000000<=p and p+n<=0x81800000
        return False
    return lambda address:mem.get(address,0),base,bank


def branch(pc,target):
    delta=target-pc
    return (18<<26)|(delta&0x03FFFFFC)|1


def native_words():
    words={
        m.TREE+0x0020:0x38630030,
        m.TREE+0x0030:branch(m.TREE+0x0030,m.DISTANCE_FN),
        m.TREE+0x0034:0xC002C5C0,
        m.TREE+0x0038:0xFC010040,
        m.TREE+0x0044:0x981F0048,
        m.BALL+0x0750:branch(m.BALL+0x0750,m.DISTANCE_FN),
        m.BALL+0x0760:branch(m.BALL+0x0760,m.DISTANCE_FN),
    }
    return words,lambda p:words.get(p,0)


class TreeProximityTests(unittest.TestCase):
    def test_native_three_sqdistance_targets(self):
        words,read=native_words()
        self.assertTrue(m.fingerprint(read))
        self.assertEqual(m.DISTANCE_FN,0x800E86D0)

    def test_bad_flag_opcode_fails_closed(self):
        words,read=native_words()
        words[m.TREE+0x0044]=0
        self.assertFalse(m.fingerprint(read))

    def test_bad_distance_callee_fails_closed(self):
        words,read=native_words()
        words[m.BALL+0x0750]=branch(m.BALL+0x0750,m.DISTANCE_FN+4)
        self.assertFalse(m.fingerprint(read))

    def test_source_94_model_patterns_and_flags(self):
        rd,base,bank=make_records()
        r=m.inspect_records(rd,base,94,bank)
        self.assertEqual(r["byte_0x48_flag_counts"],{"0":47,"1":47})
        self.assertEqual(r["source_scale_equal_xyz_within_float_tolerance"],94)
        self.assertEqual(r["model_word_distinct_count"],2)
        self.assertEqual(r["mapobj_word_distinct_count"],2)
        self.assertEqual(r["model_mapobj_pair_distinct_count"],2)
        self.assertEqual(r["unknown_0x4c_distinct_raw_words"],94)
        self.assertFalse(r["native_tree_hitbox_verified"])
        self.assertFalse(r["flag_is_collision_or_visibility_proven"])

    def test_zero_flag_capture_acceptance(self):
        rd,base,bank=make_records(flags=[0]*94)
        r=m.inspect_records(rd,base,94,bank)
        self.assertEqual(r["byte_0x48_flag_counts"],{"0":94})

    def test_not_qualifying_invalid_source_count(self):
        rd,base,bank=make_records()
        for n in (0,93,95):
            with self.subTest(n=n),self.assertRaises(ValueError):
                m.inspect_records(rd,base,n,bank)

    def test_reject_array_outside_mem2(self):
        rd,base,bank=make_records()
        with self.assertRaises(ValueError):
            m.inspect_records(rd,0x94000000,94,bank)

    def test_byte_flags_not_words_or_pointer(self):
        rd,base,bank=make_records()
        self.assertEqual(rd(base+0x48),0)
        self.assertEqual(rd(base+84+0x48),0x01000000)

    def test_source_float_deconversion(self):
        self.assertEqual(m.u32_to_float(fbits(2.5)),2.5)

    def test_no_private_xyz_raw_pointer_in_report(self):
        rd,base,bank=make_records()
        import json
        report=json.dumps(m.inspect_records(rd,base,94,bank))
        self.assertNotIn("0x9001",report)
        self.assertNotIn("0x87654321",report)
        self.assertNotIn("tree_positions",report)

    def test_flag_consumer_queries_are_only_syntax(self):
        words,read=native_words()
        code=m.potential_flag_consumers(read)
        self.assertTrue(any(x["kind"]=="stb" and x["field"]=="+0x48"
                            for x in code["Tree"]))
        self.assertIsInstance(code["Ball"],list)


if __name__=="__main__":
    unittest.main()
