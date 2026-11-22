"""Synthetic-only Ball child dispatch alias versus 94 Tree firstword tests."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/"scripts"
TESTS=ROOT/"tests"
sys.path.insert(0,str(SCRIPTS))


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


m=load("tree_ball_alias",SCRIPTS/"p0_tree_ball_runtime_table_alias_private.py")
indirect=load("indirect_fixture",
              TESTS/"test_p0_tree_ball_indirect_dispatch_private.py")


class RD:
    def __init__(self,mem):
        self.mem=mem
    def u32(self,addr):
        return self.mem.get(addr,0)


def dform(opcode,rt,ra,disp):
    return (opcode<<26)|(rt<<21)|(ra<<16)|(disp&65535)


def source_fixture():
    words,read,ram,u32,bank=indirect.fixture()
    base=m.native.UNITS["Ball"][0]
    for off,op,rt,ra,disp in m.EXPECTED_SOURCE:
        words[base+off]=dform(op,rt,ra,disp)
    for off in m.SOURCE_BCTRL:
        words[base+off]=0x4E800421
    for off in m.SOURCE_MTCTR:
        words[base+off]=0x7D8903A6
    return words,read,ram,bank


def memory_fixture():
    words,read,ram,bank=source_fixture()
    pm=0x90009000
    ram[m.roster.PLAYER_MANAGER_STATIC_CANDIDATE]=pm
    for i in range(4):
        obj=0x9000B000+i*0x200
        ram[pm+m.roster.BALL_CANDIDATE_MEMBER+i*m.roster.ROSTER_STRIDE]=obj
        ram[obj]=m.roster.BALL_DATA[0]
        for name,field,sub in m.CHILDREN:
            child=0x90010000+i*0x800+field*2
            ram[obj+field]=child
            ram[child+sub]=indirect.TABLE if i==0 and field==0x13C else 0x80000800
    return words,read,RD(ram),bank


class TreeBallRuntimeAliasTests(unittest.TestCase):
    def test_source_exact_member_and_ctr_chain(self):
        words,read,rd,bank=memory_fixture()
        self.assertTrue(m.validate_source(read))

    def test_mutated_ball_child_offset_fails(self):
        words,read,rd,bank=memory_fixture()
        pc=m.native.UNITS["Ball"][0]+0x03BC
        words[pc]=dform(32,3,31,0x13C)
        with self.assertRaises(ValueError):
            m.validate_source(read)

    def test_missing_ctr_call_abstains(self):
        words,read,rd,bank=memory_fixture()
        words[m.native.UNITS["Ball"][0]+0x0498]=0
        with self.assertRaises(ValueError):
            m.validate_source(read)

    def test_tree_alias_only_in_specific_child(self):
        words,read,rd,bank=memory_fixture()
        r=m.compare_receivers(rd,indirect.TABLE,bank)
        self.assertEqual(r["ball_candidate_firstword_in_public_Ball_data_count"],4)
        self.assertEqual(
            r["candidate_alias_to_tree_table_count_by_child"][
                "child_plus_0x13C_firstword"],1)
        self.assertEqual(
            r["candidate_alias_to_tree_table_count_by_child"][
                "child_plus_0x140_firstword"],0)
        self.assertEqual(
            r["candidate_alias_to_tree_table_count_by_child"][
                "child_plus_0x144_plus_0x78"],0)
        self.assertFalse(r["tree_contact_event_proven"])
        self.assertFalse(r["shared_firstword_is_actual_cpp_vtable_proven"])
        self.assertFalse(r["training_approved"])

    def test_fully_distinct_tables_do_not_claim_collision(self):
        words,read,rd,bank=memory_fixture()
        first=0x9000B000
        child=rd.u32(first+0x13C)
        rd.mem[child]=0x80000800
        r=m.compare_receivers(rd,indirect.TABLE,bank)
        self.assertEqual(sum(r["candidate_alias_to_tree_table_count_by_child"].values()),0)
        self.assertFalse(r["native_tree_hitbox_proven"])

    def test_missing_child_remains_unknown_not_negative(self):
        words,read,rd,bank=memory_fixture()
        rd.mem[0x9000B000+0x13C]=0
        r=m.compare_receivers(rd,indirect.TABLE,bank)
        first=r["candidate_ball_child_receivers"][0]
        self.assertFalse(first["child_plus_0x13C_firstword_table_bounded"])
        self.assertIsNone(first["child_plus_0x13C_firstword_table_equals_94_tree_firstword"])

    def test_no_candidate_balls_abstains(self):
        words,read,rd,bank=memory_fixture()
        for i in range(4):
            rd.mem[0x9000B000+i*0x200]=0
        with self.assertRaises(ValueError):
            m.compare_receivers(rd,indirect.TABLE,bank)

    def test_qualifies_actual_tree_source_table_and_dispatch_syntax(self):
        words,read,rd,bank=memory_fixture()
        r=m.indirect.inspect_tree_firstword(
            rd.u32,indirect.TREE_OBJECT,94,bank)
        self.assertTrue(r["all_94_tree_firstwords_identical"])
        self.assertEqual(r["table_slots_inspected"],64)
        self.assertTrue(m.validate_source(read))


if __name__=="__main__":
    unittest.main()
