"""Synthetic-only source-qualified Ball -> active KCL backing resource tests."""
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
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m=load("kcl_active_resource",SCRIPTS/"p0_ball_kcol_active_resource_private.py")
prior=load("prism_fixture",TESTS/"test_p0_ball_kcol_prism_type_origin_private.py")


def source_fixture():
    words,read=prior.fixture()
    words[m.native.UNITS["Ball"][0]+0x0A80]=0x836DA588
    return words,read


def insn(opcode,rt,ra,immediate):
    return (opcode<<26)|(rt<<21)|(ra<<16)|(immediate&0xFFFF)


class FakeReader:
    def __init__(self,values):
        self.values=values
    def u32(self,p):
        return self.values[p]


class ActiveKCLSourceTests(unittest.TestCase):
    def test_ball_r13_qualified_global_load(self):
        words,read=source_fixture()
        self.assertTrue(m.inspect_source(read))

    def test_wrong_global_register_abstains(self):
        words,read=source_fixture()
        words[m.native.UNITS["Ball"][0]+0x0A80]=insn(32,27,12,-23160)
        with self.assertRaises(ValueError):
            m.inspect_source(read)

    def test_previous_material_gate_cannot_be_bypassed(self):
        words,read=source_fixture()
        words[m.native.UNITS["Ball"][0]+0x0B84]=0
        with self.assertRaises(ValueError):
            m.inspect_source(read)

    def test_r13_recovered_from_native_lis_ori(self):
        words,read=source_fixture()
        base=0x804C52E0
        words[m.INIT_REGISTERS]=insn(15,13,0,base>>16)
        words[m.INIT_REGISTERS+4]=insn(24,13,13,base&65535)
        words[m.INIT_REGISTERS+8]=0x4E800020
        self.assertEqual(m.recover_r13_base(read),base)

    def test_r13_recovered_from_native_lis_addi_with_carry(self):
        words,read=source_fixture()
        base=0x804C52E0
        words[m.INIT_REGISTERS]=insn(15,13,0,0x804C)
        words[m.INIT_REGISTERS+4]=insn(14,13,13,0x52E0)
        words[m.INIT_REGISTERS+8]=0x4E800020
        self.assertEqual(m.recover_r13_base(read),base)

    def test_no_register_initializer_is_not_guessed(self):
        words,read=source_fixture()
        words[m.INIT_REGISTERS]=0x4E800020
        self.assertIsNone(m.recover_r13_base(read))

    def test_ambiguity_in_r13_initializer_abstains(self):
        words,read=source_fixture()
        words[m.INIT_REGISTERS]=insn(15,13,0,0x804C)
        words[m.INIT_REGISTERS+4]=insn(24,13,13,0x52E0)
        words[m.INIT_REGISTERS+8]=insn(15,13,0,0x804D)
        words[m.INIT_REGISTERS+12]=insn(24,13,13,0x52E0)
        words[m.INIT_REGISTERS+16]=0x4E800020
        self.assertIsNone(m.recover_r13_base(read))

    def test_array_bytes_can_be_verified_without_exporting_data(self):
        bank1=bytearray(512)
        bank2=bytearray(range(256))*4
        struct.pack_into(">4I",bank2,0,0x40,0x64,0x98,0xD8)
        obj=0x90000300
        slot=0x80000100
        source_pointers=(0x90000040,0x90000064,0x900000A8)
        rd=FakeReader({slot:obj,obj+4:source_pointers[0],
                       obj+8:source_pointers[1],obj+12:source_pointers[2]})
        original=m.locate_exact_terrain_kcl
        try:
            m.locate_exact_terrain_kcl=lambda _: (1,0)
            r=m.resource_comparison(rd,(bank1,bank2),slot)
            self.assertTrue(r["all_three_active_buffers_match_terrain_candidate"])
            self.assertEqual(r["active_buffers_exact_address_equal_to_terrain_candidate"],
                             [True,True,True])
            self.assertFalse(r["class13_from_other_active_kcl_proven"])
            self.assertFalse(r["tree_specific_collision_proven"])
        finally:
            m.locate_exact_terrain_kcl=original

    def test_wrong_buffer_does_not_promote_matching_resource(self):
        bank1=bytearray(512)
        bank2=bytearray(range(256))*4
        struct.pack_into(">4I",bank2,0,0x40,0x64,0x98,0xD8)
        obj=0x90000300
        slot=0x80000100
        pointers=(0x90000040,0x90000064,0x90000200)
        rd=FakeReader({slot:obj,obj+4:pointers[0],
                       obj+8:pointers[1],obj+12:pointers[2]})
        original=m.locate_exact_terrain_kcl
        try:
            m.locate_exact_terrain_kcl=lambda _: (1,0)
            r=m.resource_comparison(rd,(bank1,bank2),slot)
            self.assertFalse(r["all_three_active_buffers_match_terrain_candidate"])
            self.assertEqual(r["active_buffers_exact_address_equal_to_terrain_candidate"],
                             [True,True,False])
        finally:
            m.locate_exact_terrain_kcl=original


if __name__=="__main__":
    unittest.main()
