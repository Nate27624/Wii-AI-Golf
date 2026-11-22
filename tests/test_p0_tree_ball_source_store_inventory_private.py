"""Synthetic static PPC store syntax tests; no game RAM or emulator."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"scripts"/"p0_tree_ball_source_store_inventory_private.py"
spec=importlib.util.spec_from_file_location("tree_store_syntax",SRC)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def dform(op,rt,ra,disp):
    return (op<<26)|(rt<<21)|(ra<<16)|(disp&0xffff)


def read_source(changes):
    return lambda pc:changes.get(pc,0x60000000)


class SourceStoreSyntaxTests(unittest.TestCase):
    def test_ppc_store_and_load_dforms(self):
        self.assertEqual(m.form(dform(52,4,31,0xCC)),
                         {"op":52,"register":4,"base":31,"offset":0xCC})
        self.assertEqual(m.form(dform(32,5,6,-16))["offset"],-16)
        self.assertIsNone(m.form(0x60000000))

    def test_direct_native_offsets_bounded_by_published_units(self):
        lo,hi=m.SOURCE_UNITS["Ball"]
        program={
            lo+0x20:dform(52,2,31,0xCC),
            lo+0x24:dform(52,4,31,0xF0),
            lo+0x28:dform(52,3,31,0xFC),
            lo+0x2C:dform(52,5,31,0x30),
            lo+0x30:dform(36,8,31,0xAC),
            lo+0x34:dform(52,5,31,0xB0),
        }
        report=m.direct_store_inventory(read_source(program))["Ball"]
        self.assertEqual(report["candidate_displacement_store_instruction_count"],6)
        off={item["D_form_displacement"] for item in
             report["source_field_displacement_sites"]}
        self.assertTrue({"+0x0CC","+0x0F0","+0x0FC","+0x030","+0x0AC","+0x0B0"}<=off)
        src=json.dumps(report)
        self.assertIn("Ball+0x0020",src)
        self.assertNotIn(f"{lo:08X}",src)
        self.assertIn('"source_receiver_Ball_identity_proven": false',src)

    def test_bounded_lwz_member_pointer_then_component_float_stores(self):
        lo,_=m.SOURCE_UNITS["Ball"]
        program={
            lo+0x80:dform(32,6,31,0x4C),
            lo+0x84:dform(52,1,6,0),
            lo+0x88:dform(52,2,6,4),
            lo+0x8C:dform(52,3,6,8),
        }
        report=m.ptr_member_copies(read_source(program),"Ball")
        self.assertEqual(len(report["bounded_lwz_plus_0x4C_to_stfs_zero_four_eight_candidates"]),1)
        item=report["bounded_lwz_plus_0x4C_to_stfs_zero_four_eight_candidates"][0]
        self.assertEqual(len(item["possible_stfs_through_pointer"]),3)
        self.assertEqual(item["stop_reason"],"three_possible_components_seen")
        self.assertFalse(item["same_selected_Ball_receiver_verified"])

    def test_gpr_clobber_stops_false_pointer_alias(self):
        lo,_=m.SOURCE_UNITS["Ball"]
        program={
            lo+0x80:dform(32,6,31,0x4C),
            lo+0x84:dform(32,6,6,0x28),
            lo+0x88:dform(52,1,6,0),
        }
        x=m.ptr_member_copies(read_source(program),"Ball")
        self.assertEqual(x["bounded_lwz_plus_0x4C_to_stfs_zero_four_eight_candidates"],[])

    def test_unconditional_branch_stops_window(self):
        lo,_=m.SOURCE_UNITS["Ball"]
        program={
            lo+0x80:dform(32,6,31,0x4C),
            lo+0x84:0x48000000,
            lo+0x88:dform(52,1,6,0),
        }
        x=m.ptr_member_copies(read_source(program),"Ball")
        self.assertEqual(x["bounded_lwz_plus_0x4C_to_stfs_zero_four_eight_candidates"],[])

    def test_one_component_does_not_certify_complete_triplet(self):
        lo,_=m.SOURCE_UNITS["Ball"]
        program={
            lo+0x80:dform(32,6,31,0x4C),
            lo+0x84:dform(52,1,6,0),
            lo+0x88:0x48000000,
        }
        x=m.ptr_member_copies(read_source(program),"Ball")
        item=x["bounded_lwz_plus_0x4C_to_stfs_zero_four_eight_candidates"][0]
        self.assertEqual(len(item["possible_stfs_through_pointer"]),1)
        self.assertEqual(item["stop_reason"],"control_transfer_before_verified_copy")
        self.assertFalse(x["source_ptr_register_dataflow_complete"])

    def test_bounded_sites_never_invent_live_collision(self):
        lo,_=m.SOURCE_UNITS["Player"]
        result=m.source_audit(read_source({
            lo+0x10:dform(52,1,3,0x30),
        }))
        self.assertFalse(result["native_wood_vs_leaf_contact_branch_verified"])
        self.assertFalse(result["actual_collision_instruction_executed_proven"])
        self.assertFalse(result["training_approved"])
        self.assertIn("Player+0x0010",json.dumps(result))

    def test_no_arbitrary_byte_disassembly_or_source_data(self):
        result=m.source_audit(read_source({}))
        self.assertEqual(result["source_unit_displacement_stores"]["Ball"][
            "candidate_displacement_store_instruction_count"],0)
        self.assertEqual(result["source_unit_plus_0x4C_pointer_derived_float_triplets"]["Ball"][
            "bounded_lwz_plus_0x4C_to_stfs_zero_four_eight_candidates"],[])
        self.assertFalse(result["ball_plus_0x30_world_translation_semantics_proven"])

    def test_public_unit_labels_reject_out_of_unit_native_code(self):
        lo,hi=m.SOURCE_UNITS["Ball"]
        with self.assertRaises(ValueError):
            m.label(hi,"Ball")
        with self.assertRaises(ValueError):
            m.label(lo-4,"Ball")


if __name__=="__main__":
    unittest.main()
