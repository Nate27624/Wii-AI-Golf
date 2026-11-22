"""Synthetic-only active Wii Golf KCL dummy-prism layout tests."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import struct
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/"scripts"
TESTS=ROOT/"tests"
sys.path.insert(0,str(SCRIPTS))


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m=load("kcl_dummy_prism",SCRIPTS/"p0_ball_kcol_prism_dummy_layout_private.py")
source=load("active_kcl_source_fixture",
            TESTS/"test_p0_ball_kcol_active_resource_private.py")


class RD:
    def __init__(self,values):
        self.values=values
    def u32(self,addr):
        return self.values[addr]


def fixture(prism_offset=0x300,normal_ptr=None):
    # All bytes are synthetic; locator is injected, not an original KCL.
    bank1=bytearray(2048)
    bank2=bytearray((i*19+7)&0xFF for i in range(45000))
    po,no,pr=0x40,0x100,0x300
    octo=pr+16+m.broad.KCL_PRISMS*16
    struct.pack_into(">4I",bank2,0,po,no,pr,octo)
    obj=0x9000A500
    slot=0x80000100
    values={slot:obj,obj+4:0x90000040,
            obj+8:normal_ptr if normal_ptr is not None else 0x90000100,
            obj+12:0x90000000+prism_offset}
    return RD(values),(bank1,bank2),slot,lambda _: (1,0)


class KCLDummyPrismTests(unittest.TestCase):
    def test_original_source_gate(self):
        words,read=source.source_fixture()
        self.assertTrue(m.earlier.inspect_source(read))

    def test_native_dummy_base_matches_known_terrain(self):
        rd,banks,slot,locate=fixture()
        r=m.compare_prism_layout(rd,banks,slot,locate)
        self.assertTrue(r["active_prism_pointer_equals_terrain_dummy_base"])
        self.assertFalse(r["active_prism_pointer_equals_first_usable_prism"])
        self.assertTrue(r["active_prism_data_equal_after_dummy_16_byte_skip"])
        self.assertTrue(r["active_2498_prism_bytes_match_known_terrain"])
        self.assertEqual(r["active_2498_prism_class13_count_if_verified"],0)

    def test_first_usable_prism_pointer_direct_match(self):
        rd,banks,slot,locate=fixture(prism_offset=0x310)
        r=m.compare_prism_layout(rd,banks,slot,locate)
        self.assertFalse(r["active_prism_pointer_equals_terrain_dummy_base"])
        self.assertTrue(r["active_prism_pointer_equals_first_usable_prism"])
        self.assertTrue(r["active_prism_data_equal_at_direct_pointer"])
        self.assertTrue(r["active_2498_prism_bytes_match_known_terrain"])

    def test_wrong_prism_pointer_does_not_claim_other_mesh(self):
        rd,banks,slot,locate=fixture(prism_offset=0x500)
        r=m.compare_prism_layout(rd,banks,slot,locate)
        self.assertFalse(r["active_2498_prism_bytes_match_known_terrain"])
        self.assertIsNone(r["active_2498_prism_class13_count_if_verified"])
        self.assertFalse(r["other_collision_resource_proven"])
        self.assertFalse(r["tree_collision_proven"])

    def test_wrong_normals_pointer_fails_closed(self):
        rd,banks,slot,locate=fixture(normal_ptr=0x90000200)
        with self.assertRaises(ValueError):
            m.compare_prism_layout(rd,banks,slot,locate)

    def test_invalid_header_count_fails_closed(self):
        rd,banks,slot,locate=fixture()
        struct.pack_into(">I",banks[1],0x0C,0x1000)
        with self.assertRaises(ValueError):
            m.compare_prism_layout(rd,banks,slot,locate)

    def test_bad_global_slot_fails_closed(self):
        rd,banks,slot,locate=fixture()
        with self.assertRaises(ValueError):
            m.compare_prism_layout(rd,banks,0x90000100,locate)

    def test_no_training_promotion_even_with_complete_match(self):
        rd,banks,slot,locate=fixture()
        r=m.compare_prism_layout(rd,banks,slot,locate)
        self.assertFalse(r["training_approved"])
        self.assertFalse(r["ball_velocity_proven"])
        self.assertFalse(r["tree_collision_proven"])


if __name__=="__main__":
    unittest.main()
