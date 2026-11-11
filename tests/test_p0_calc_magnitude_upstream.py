"""Offline synthetic tests: do not open original game archives or Dolphin."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p0_calc_magnitude_upstream_private.py"
spec = importlib.util.spec_from_file_location("p0_calc_magnitude_upstream_private", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def dform(op, rt, ra, disp):
    return ((op << 26) | (rt << 21) | (ra << 16) | (disp & 0xFFFF))


def mr(dest, src):
    return (31 << 26 | src << 21 | dest << 16 |
            src << 11 | 444 << 1)


def bl(pc, target):
    diff = target - pc
    if diff % 4 or not -(1 << 25) <= diff < (1 << 25):
        raise ValueError("not representable")
    return 18 << 26 | (diff & 0x03FFFFFC) | 1


def ppc_fp(op, fd, fa, fb, fc, xo5):
    return ((op << 26) | (fd << 21) | (fa << 16) | (fb << 11) |
            (fc << 6) | (xo5 << 1))


def ppc_fcmpo(crfd, fa, fb):
    return ((63 << 26) | (crfd << 23) | (fa << 16) | (fb << 11) |
            (32 << 1))


def ppc_bc_le(pc, target):
    return ((16 << 26) | (4 << 21) | (1 << 16) |
            ((target - pc) & 0xFFFC))


def ppc_bcctrl():
    return ((19 << 26) | (20 << 21) | (528 << 1) | 1)


def ppc_rlwinm(rs, ra, sh, mb, me, rc=0):
    return ((21 << 26) | (rs << 21) | (ra << 16) | (sh << 11) |
            (mb << 6) | (me << 1) | rc)


def ppc_add(rd,ra,rb):
    return ((31 << 26) | (rd << 21) | (ra << 16) |
            (rb << 11) | (266 << 1))


def ppc_mtctr(rs):
    return ((31 << 26) | (rs << 21) | (9 << 16) | (467 << 1))


def fixture():
    words = {}
    for pc in (list(range(0x802B4794, 0x802B4820, 4))
               + list(range(*m.EXCERPT, 4))
               + list(range(*m.CONTROLLER_ACCESSOR_WINDOW, 4))):
        words[pc] = dform(14, 1, 1, 0)
    for pc, (freg, base, disp) in m.STFS_GATES.items():
        words[pc] = dform(52, freg, base, disp)
    for pc, (freg, base, disp) in m.LFS_GATES.items():
        words[pc] = dform(48, freg, base, disp)
    for pc, (reg, base, disp) in m.STW_GATES.items():
        words[pc] = dform(36, reg, base, disp)
    for pc, dest in m.CALL_GATES.items():
        words[pc] = bl(pc, dest)
    for pc, (dest, src) in m.MR_GATES.items():
        words[pc] = mr(dest, src)
    for pc, target in m.CONTROLLER_ACCESS_CALLS.items():
        words[pc] = bl(pc,target)
    for pc,idx in m.CONTROLLER_ACCESS_SELECTORS.items():
        words[pc] = dform(14,4,0,idx)
    for pc,(dest,src) in m.CONTROLLER_RESULT_COPIES.items():
        words[pc] = mr(dest,src)
    for pc,(reg,base,disp) in m.CONTROLLER_ENTRY_GATES.items():
        words[pc] = dform(32,reg,base,disp)
    words[m.CONTROLLER_FP_CONSTANT_LOAD] = dform(48,31,2,-12892)
    words[m.CONTROLLER_RETURN_FP_LOAD] = dform(48,1,31,0x18)
    # Known candidate intermediate r24-relative stores (synthetic payload).
    words[0x802B482C] = dform(52, 1, 24, 0x18)
    words[0x802B4840] = dform(52, 2, 24, 0x1C)
    words[0x802B4880] = dform(52, 3, 24, 0x28)
    words[0x802B4894] = dform(52, 4, 24, 0x2C)
    for pc, (reg, base, disp) in m.MAG_LFS_GATES.items():
        words[pc] = dform(48, reg, base, disp)
    for pc, (reg, base, disp) in m.MAG_STFS_GATES.items():
        words[pc] = dform(52, reg, base, disp)
    for pc, params in m.MAG_ARITH_GATES.items():
        words[pc] = ppc_fp(*params)
    for pc, params in m.MAG_FCMP_GATES.items():
        words[pc] = ppc_fcmpo(*params)
    for pc, target in m.MAG_SKIP_BRANCHES.items():
        words[pc] = ppc_bc_le(pc, target)
    for pc, (reg, base, disp) in m.MAG_VTABLE_LOADS.items():
        words[pc] = dform(32, reg, base, disp)
    for pc in m.MAG_BCCTRL_SITES:
        words[pc] = ppc_bcctrl()
    words[0x802B48A0] = ppc_rlwinm(0, 0, 2, 0, 29)
    words[0x802B48D0] = ppc_rlwinm(0, 0, 2, 0, 29)
    # Synthetic FP63 example at non-gated site for generic symbolizer test.
    words[0x802B47A8] = (
        (63 << 26) | (30 << 21) | (28 << 16) |
        (29 << 11) | (27 << 6) | (29 << 1)
    )
    for pc,spec in m.HISTORY_LOADS.items():
        words[pc]=dform(48,*spec)
    for pc,spec in m.HISTORY_STORES.items():
        words[pc]=dform(52,*spec)
    for pc,spec in m.HISTORY_FP_GATES.items():
        words[pc]=ppc_fp(*spec)
    for pc,spec in m.HISTORY_COMPARE_GATES.items():
        words[pc]=ppc_fcmpo(*spec)
    for pc,target in m.HISTORY_SKIP_BRANCHES.items():
        words[pc]=ppc_bc_le(pc,target)
    for table in (m.SELECTOR_GLOBAL_LOADS,m.SELECTOR_INDEX_LOADS,
                  m.SELECTOR_ELEMENT_LOADS,m.SELECTOR_VPTR_LOADS):
        for pc,spec in table.items():
            words[pc]=dform(32,*spec)
    for pc in m.SELECTOR_RLWINM:
        words[pc]=ppc_rlwinm(0,0,2,0,29)
    for pc in m.SELECTOR_ADDS:
        words[pc]=ppc_add(3,3,0)
    for pc in m.SELECTOR_MTCTR:
        words[pc]=ppc_mtctr(12)
    return words


class Tests(unittest.TestCase):
    def test_exact_peak_latch_and_static_call_gates(self):
        words = fixture()
        result = m.verify_static_gates(words.__getitem__)
        self.assertEqual(result["calc_peak_writer_at"], "0x802B4924")
        self.assertEqual(result["calc_state3_latch_writer_at"], "0x802B31C4")
        self.assertTrue(result["two_direct_bl_edges_exact"])
        self.assertTrue(result["four_explicit_mr_receiver_copies_exact"])
        self.assertEqual(m._branch(0x802B4938, words[0x802B4938])["dest"],
                         0x802B3BA0)

    def test_rejects_wrong_object_register_or_peak_source(self):
        for pc in m.STFS_GATES:
            words = fixture()
            words[pc] = dform(52, 31, 24, 0x0C)
            with self.assertRaisesRegex(m.Abstain, "gate_failed"):
                m.verify_static_gates(words.__getitem__)

    def test_rejects_changed_call_target_and_nonlink(self):
        for pc in m.CALL_GATES:
            words = fixture()
            words[pc] = bl(pc, m.CALL_GATES[pc] + 4)
            with self.assertRaisesRegex(m.Abstain, "calc_call_chain"):
                m.verify_static_gates(words.__getitem__)
            words[pc] = bl(pc, m.CALL_GATES[pc]) & ~1
            with self.assertRaisesRegex(m.Abstain, "calc_call_chain"):
                m.verify_static_gates(words.__getitem__)

    def test_calc_receiver_four_mr_hops_are_exact(self):
        for pc, (dest, source) in m.MR_GATES.items():
            words = fixture()
            self.assertTrue(m._mr_matches(words[pc], dest, source))
            words[pc] = mr(dest, (source + 1) % 32)
            with self.assertRaisesRegex(m.Abstain, "receiver_identity_chain"):
                m.verify_static_gates(words.__getitem__)

    def test_rejects_uncorroborated_latch_state(self):
        words = fixture()
        words[0x802B31C0] = dform(36, 0, 27, 0x18C)
        with self.assertRaisesRegex(m.Abstain, "calc_state_gate"):
            m.verify_static_gates(words.__getitem__)

    def test_symbolic_fp_producer_and_source_owner(self):
        words = fixture()
        line = m.symbolize(0x802B47A8, words[0x802B47A8])
        self.assertEqual(line["class"], "fp_opcode63")
        self.assertEqual((line["fd"], line["fa"], line["fb"], line["fc"]),
                         (30, 28, 29, 27))
        with self.assertRaisesRegex(m.Abstain, "source_window"):
            m.symbolize(0x80000100, 0)
        self.assertEqual(m.symbolize(0x802B4924, words[0x802B4924])["class"],
                         "stfs")

    def test_bounded_producer_excerpt_and_store_inventory(self):
        report = m.source_slice(fixture().__getitem__)
        self.assertEqual(report["status"], "REV1_CALC_UPSTREAM_STATIC_SOURCE_PASS")
        self.assertFalse(report["calc_0x0C_accepted_power_verified"])
        self.assertFalse(report["game_input_consumption_verified"])
        self.assertEqual(
            {row["field"] for row in report["r24_candidate_calculation_stores"]},
            {"+0x18", "+0x1C", "+0x20", "+0x24", "+0x28", "+0x2C", "+0x8", "+0xC"})
        self.assertEqual(report["public_unit"], m.PUBLIC_OWNER)
        self.assertGreater(len(report["fp_reaching_definitions_source_excerpt"]), 20)
        serialized = json.dumps(report)
        self.assertNotIn("0x91BF", serialized)
        self.assertNotIn("PRIVATE-SHA", serialized)
        self.assertNotIn("0xFC", serialized)
        self.assertNotIn('"word"', serialized)
        self.assertFalse(report["training_approved"])

    def test_real_source_pattern_two_products_and_max_updates(self):
        report = m.source_slice(fixture().__getitem__)
        arith = report["native_magnitude_arithmetic"]
        self.assertEqual(arith["status"], "REV1_TWO_PRODUCT_MAX_UPDATE_SOURCE_PASS")
        self.assertIn("calc[+0x18]", arith["candidate_A_pseudocode"])
        self.assertIn("calc[+0x1C]", arith["candidate_B_pseudocode"])
        self.assertEqual(arith["both_virtual_load_offset_decimal"], 56)
        self.assertFalse(arith["actual_virtual_callee_address_verified"])
        self.assertFalse(arith["native_accepted_shot_power_verified"])
        self.assertIn("candidate_A", arith["delta_0x98_pseudocode"])

    def test_magnitude_math_exact_gates_reject_mutations(self):
        for pc in m.MAG_LFS_GATES:
            words = fixture()
            words[pc] = words[pc] ^ (1 << 21)
            with self.assertRaisesRegex(m.Abstain, "factor_reader"):
                m.verify_magnitude_arithmetic(words.__getitem__)
        for pc in m.MAG_ARITH_GATES:
            words = fixture()
            words[pc] ^= 2
            with self.assertRaisesRegex(m.Abstain, "fp_arithmetic"):
                m.verify_magnitude_arithmetic(words.__getitem__)
        for pc in m.MAG_FCMP_GATES:
            words = fixture()
            words[pc] ^= (1 << 16)
            with self.assertRaisesRegex(m.Abstain, "strict_peak_compare"):
                m.verify_magnitude_arithmetic(words.__getitem__)
        for pc in m.MAG_SKIP_BRANCHES:
            words = fixture()
            words[pc] = ppc_bc_le(pc, m.MAG_SKIP_BRANCHES[pc]+4)
            with self.assertRaisesRegex(m.Abstain, "strict_peak_branch"):
                m.verify_magnitude_arithmetic(words.__getitem__)
        for pc in m.MAG_BCCTRL_SITES:
            words = fixture()
            words[pc] &= ~1
            with self.assertRaisesRegex(m.Abstain, "virtual_getter_call"):
                m.verify_magnitude_arithmetic(words.__getitem__)

    def test_original_virtual_selector_rotate_mask_operands_exposed(self):
        words = fixture()
        first = m.symbolize(0x802B48A0, words[0x802B48A0])
        second = m.symbolize(0x802B48D0, words[0x802B48D0])
        self.assertEqual(first["class"], "rlwinm")
        self.assertEqual(tuple(first[k] for k in
                               ("rs","ra","sh","mb","me","record")),
                         (0,0,2,0,29,False))
        self.assertEqual(first["sh"], second["sh"])
        report = m.source_slice(words.__getitem__)
        selections = report["virtual_return_selector_source_instructions"]
        self.assertEqual(len([x for x in selections if x["class"]=="rlwinm"]),2)
        self.assertFalse(
            report["native_magnitude_arithmetic"]["two_callbacks_same_object_verified"])

    def test_history_two_accumulators_and_maximum_sites(self):
        report=m.source_slice(fixture().__getitem__)
        h=report["upstream_two_accumulators_and_four_peak_sites"]
        self.assertEqual(h["status"],
            "REV1_TWO_ACCUMULATORS_FOUR_RUNNING_MAX_SITES_SOURCE_PASS")
        self.assertIn("f31",h["calc_0x20_rule"])
        self.assertIn("source_r31[+0x1C]",h["calc_0x24_rule"])
        self.assertFalse(h["source_r31_struct_identity_verified"])
        self.assertEqual(len(report["input_function_entry_source_excerpt"]),35)

    def test_repeated_virtual_getter_selection_is_structural_only(self):
        report=m.source_slice(fixture().__getitem__)
        sel=report["repeated_global_virtual_getter_selector"]
        self.assertEqual(sel["status"],
            "REV1_TWIN_GLOBAL_INDEXED_VTABLE_SLOT56_SOURCE_PASS")
        self.assertEqual(sel["same_source_global_r13_offset"],-23168)
        self.assertEqual(sel["both_index_field_offset"],28)
        self.assertEqual(sel["index_scale_bytes"],4)
        self.assertEqual(sel["both_element_pointer_offsets"],12)
        self.assertEqual(sel["both_vtable_slot_offsets"],56)
        self.assertTrue(sel["same_static_selection_expression"])
        self.assertFalse(sel["actual_runtime_getter_return_equality_verified"])

    def test_history_and_selector_mutations_fail_closed(self):
        for group,reason in [
            (m.HISTORY_LOADS,"history_float_load"),
            (m.HISTORY_STORES,"history_float_store"),
            (m.HISTORY_FP_GATES,"history_float_operation"),
            (m.HISTORY_COMPARE_GATES,"history_greater_compare"),
            (m.HISTORY_SKIP_BRANCHES,"history_greater_branch"),
            (m.SELECTOR_GLOBAL_LOADS,"selector_global"),
            (m.SELECTOR_INDEX_LOADS,"selector_index"),
            (m.SELECTOR_ELEMENT_LOADS,"selector_element"),
            (m.SELECTOR_VPTR_LOADS,"selector_vptr"),
            ({pc:None for pc in m.SELECTOR_RLWINM},
             "selector_times_four_index"),
            ({pc:None for pc in m.SELECTOR_ADDS},"selector_pointer_add"),
            ({pc:None for pc in m.SELECTOR_MTCTR},"selector_mtctr"),
        ]:
            for pc in group:
                words=fixture()
                words[pc] ^= (1 << 21)
                fn=(m.verify_history_pipeline if reason.startswith("history_")
                    else m.verify_virtual_selector_reuse)
                with self.assertRaisesRegex(m.Abstain,reason):
                    fn(words.__getitem__)

    def test_controller_extended_status_caller_and_public_field_annotation(self):
        report=m.source_slice(fixture().__getitem__)
        call=report["controller_extended_status_call_chain"]
        self.assertEqual(call["status"],
            "REV1_CONTROLLER_THREE_EXTENDED_STATUS_CALLERS_SOURCE_PASS")
        self.assertEqual(call["selector_codes"],[1,2,3])
        self.assertEqual(call["record_2_register"],"r31")
        self.assertEqual(call["public_KPADStatus_fields"]["record+0x18"],
                         "acc_value")
        self.assertEqual(call["public_KPADStatus_fields"]["record+0x1C"],
                         "acc_speed")
        self.assertFalse(call[
            "native_accessor_body_exactly_matched_to_public_method"])
        self.assertEqual(call["read_length_source_field_offset"],0x854)
        self.assertEqual(
            len(report["candidate_getExCoreStatus_binary_excerpt"]),
            (m.CONTROLLER_ACCESSOR_WINDOW[1]-m.CONTROLLER_ACCESSOR_WINDOW[0])//4)

    def test_controller_call_and_selector_gates_fail_closed(self):
        checks=[
            (m.CONTROLLER_ACCESS_CALLS,"controller_accessor_caller_call"),
            (m.CONTROLLER_ACCESS_SELECTORS,"controller_accessor_selector"),
            (m.CONTROLLER_RESULT_COPIES,"controller_accessor_record_copy"),
            (m.CONTROLLER_ENTRY_GATES,"controller_accessor_sample_count"),
            ({m.CONTROLLER_FP_CONSTANT_LOAD:None},
             "controller_accessor_decay_constant"),
            ({m.CONTROLLER_RETURN_FP_LOAD:None},
             "controller_accessor_return_field"),
        ]
        for group,reason in checks:
            for pc in group:
                words=fixture()
                words[pc] ^= (1 << 21)
                with self.assertRaisesRegex(m.Abstain,reason):
                    m.verify_controller_selector_call_chain(words.__getitem__)

    def test_bounded_golf_direct_bl_caller_inventory(self):
        start=0x802B4400
        stop=start+0x20
        words={pc:dform(14,1,1,0) for pc in range(start,stop,4)}
        words[start] = bl(start,0x802B4794)
        words[start+4] = bl(start+4,0x802B4474)
        words[start+8] = bl(start+8,0x802B4474) & ~1
        words[start+12] = bl(start+12,0x802B2F90)
        report=m.scan_direct_golf_call_sites(words.__getitem__,
                                             start=start,end=stop)
        self.assertEqual(report["status"],
                         "REV1_BOUNDED_GOLF_DIRECT_BL_INVENTORY")
        self.assertEqual(
            report["direct_call_sites"]["calc_history_update"],
            [f"0x{start:08X}"])
        self.assertEqual(
            report["direct_call_sites"]["calc_preprocessor"],
            [f"0x{start+4:08X}"])
        self.assertEqual(report["direct_call_totals"]["calc_preprocessor"],1)
        self.assertEqual(report["direct_call_totals"]["calc_latch_step"],1)
        self.assertFalse(report["indirect_or_external_callers_exhaustive"])
        self.assertNotIn('"word"',json.dumps(report))

    def test_bounded_direct_scan_abstains_on_outside_golf_text(self):
        for lo,hi in [(0x8019BAE8,0x8019BB00),
                      (m.OWNER_START,m.OWNER_END+4),
                      (m.OWNER_START+1,m.OWNER_START+0x20),
                      (m.OWNER_START,m.OWNER_START)]:
            with self.assertRaisesRegex(m.Abstain,"direct_call_scan_window"):
                m.scan_direct_golf_call_sites(lambda pc:0,start=lo,end=hi)

    def test_wrong_bank_or_unaligned_source_address_abstains(self):
        fake = bytes(64)
        with self.assertRaisesRegex(m.Abstain, "source_window"):
            m._word(fake, 0x802B4915)
        with self.assertRaisesRegex(m.Abstain, "source_word_unmapped"):
            m._word(fake, 0x802B4914)

    def test_archive_auto_discovery_requires_one_original(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "Wii-AI-Golf-Data"
            captures = root / "captures"
            captures.mkdir(parents=True)
            with self.assertRaisesRegex(m.Abstain, "expected_one"):
                m._default_archive(root)
            for name in ("a","b"):
                p = captures / name
                p.mkdir()
                (p / "manifest-PRIVATE.json").write_text(
                    json.dumps({"kind":"p0-private-numbered-capture-inventory",
                                "capture_count":7}), encoding="utf-8")
                if name == "a":
                    self.assertEqual(m._default_archive(root),p)
                else:
                    with self.assertRaisesRegex(m.Abstain, "expected_one"):
                        m._default_archive(root)

    def test_main_without_archive_fails_closed_and_never_calls_controller(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(m, "DATA", Path(d)), \
                 patch.object(m, "run", side_effect=AssertionError(
                     "must not open original archive on missing root")):
                self.assertEqual(m.main([]), 2)


if __name__ == "__main__":
    unittest.main()
