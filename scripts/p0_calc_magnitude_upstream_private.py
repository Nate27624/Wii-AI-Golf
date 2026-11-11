"""Read-only source-bound RSPE01 Rev1 swing-magnitude WRITER micro-audit.

Requires the EXISTING exact-SHA seven numbered MEM1/MEM2 archive. Inspects ONLY
original PPC code, does not launch Dolphin or require ROM/game-file arguments.
Outputs only sanitized SOURCE PC / register / field / branch classifications.
No raw native words, original memory dumps, private hashes, heap pointers,
physical power claims, or native-value vectors are printed.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_p0_seven_numbered_source_pairs_private as private
import audit_golf_two_bank_roster_private as roster
import audit_p0_inflight_vs_b0_private as source

DATA = HERE.parents[1] / "Wii-AI-Golf-Data"
PUBLIC_OWNER = "Pack/RPSports/RPGolScene/RPGolScene_unsplit.o"
OWNER_START, OWNER_END = 0x802A79F8, 0x802C7924
CONTROLLER_OWNER_START, CONTROLLER_OWNER_END = 0x8019B214, 0x8019C74C
CONTROLLER_ACCESSOR_WINDOW = (0x8019BAE8, 0x8019BB38)
MEM1_BASE = roster.MEM1_BASE

# The original operator's exact PPC proof on the preserved Rev1 cohort.
# These are two distinct stages: current/peak writer and later state-3 latch.
STFS_GATES = {
    0x802B4914: (30, 24, 0x08),
    0x802B4924: (1, 24, 0x0C),
    0x802B31C4: (0, 27, 0x10),
}
LFS_GATES = {
    0x802B31B0: (0, 27, 0x0C),
}
STW_GATES = {
    0x802B31C0: (0, 27, 0x1A4),
}
CALL_GATES = {
    0x802B4938: 0x802B3BA0,
    0x802B3D04: 0x802B2F90,
}
# Source-window instructions copied from the operator's actual original
# SHA-qualified disassembly (not reconstructed from public C++):
CONTROLLER_ACCESS_CALLS = {
    0x802B47E0: 0x8019BAE8,
    0x802B47F4: 0x8019BAE8,
    0x802B4808: 0x8019BAE8,
    0x802B4818: 0x802B4474,
}
CONTROLLER_ACCESS_SELECTORS = {
    0x802B47DC: 1, 0x802B47F0: 2, 0x802B4804: 3,
}
CONTROLLER_RESULT_COPIES = {
    0x802B47E4: (28,3), 0x802B47F8: (31,3),
    0x802B480C: (27,3),
}
CONTROLLER_ENTRY_GATES = {
    0x802B47B8: (30,4,0x854),
}
CONTROLLER_FP_CONSTANT_LOAD = 0x802B47C0
CONTROLLER_RETURN_FP_LOAD = 0x802B481C

# PPC "mr" is OR rA,rS,rS (primary31, XO444). Earlier original
# operator source trace showed a calc receiver preserved through two calls.
# This proves register copies only; branches/guest invocation still matter.
MR_GATES = {
    0x802B4928: (3, 24),
    0x802B3BD0: (29, 3),
    0x802B3CFC: (3, 29),
    0x802B2FB8: (27, 3),
}

# Exact source-derived floating-point dataflow recovered from operator's
# original 14-bank SHA-validated 2026-11-11 native audit:
# two individually weighted indirect-call results, strict-greater maxima.
MAG_LFS_GATES = {
    0x802B48C0: (0, 24, 0x18),
    0x802B48CC: (0, 24, 0x28),
    0x802B48F0: (0, 24, 0x1C),
    0x802B48F4: (2, 24, 0x08),
    0x802B48FC: (1, 24, 0x2C),
    0x802B4918: (0, 24, 0x0C),
}
MAG_STFS_GATES = {0x802B490C: (0, 24, 0x98)}
# (opcode, FD, FA, FB, FC, 5-bit XO) for single precision:
# fmuls 59/25; fsubs 59/20. For fmuls, FB is unused/encoded as zero.
MAG_ARITH_GATES = {
    0x802B48C8: (59, 1, 0, 0, 1, 25),
    0x802B48DC: (59, 30, 0, 0, 1, 25),
    0x802B48F8: (59, 3, 0, 0, 1, 25),
    0x802B4900: (59, 0, 30, 2, 0, 20),
    0x802B4908: (59, 1, 1, 0, 3, 25),
}
MAG_FCMP_GATES = {
    0x802B4904: (0, 30, 2),  # CR0, f30 > old calc[+0x08]
    0x802B491C: (0, 1, 0),   # CR0, f1 > old calc[+0x0C]
}
# BO=4: branch when CR[BI] is FALSE; BI=1: CR0 greater-than.
MAG_SKIP_BRANCHES = {
    0x802B4910: 0x802B4918,
    0x802B4920: 0x802B4928,
}
# TWO indirect virtual dispatches through +0x38 (= decimal 56).
MAG_VTABLE_LOADS = {
    0x802B48B0: (12, 12, 56),
    0x802B48E4: (12, 12, 56),
}
MAG_BCCTRL_SITES = (0x802B48B8, 0x802B48EC)

HISTORY_LOADS = {
    0x802B4820:(0,24,0x18),0x802B4830:(1,31,0x18),
    0x802B4834:(0,24,0x1C),0x802B4844:(0,24,0x20),
    0x802B4848:(1,24,0x24),0x802B4850:(0,24,0x28),
    0x802B4860:(1,31,0x1C),0x802B4870:(0,31,0x1C),
    0x802B4884:(1,24,0x24),0x802B4888:(0,24,0x2C),
}
HISTORY_STORES = {
    0x802B482C:(1,24,0x18),0x802B4840:(1,24,0x1C),
    0x802B4858:(3,24,0x20),0x802B485C:(2,24,0x24),
    0x802B4868:(1,24,0x20),0x802B4878:(0,24,0x24),
    0x802B4880:(1,24,0x28),0x802B4894:(1,24,0x2C),
}
HISTORY_FP_GATES = {
    0x802B484C:(59,3,0,0,31,25), 0x802B4854:(59,2,1,0,31,25),
    0x802B4864:(59,1,3,1,0,21), 0x802B4874:(59,0,2,0,0,21),
}
HISTORY_COMPARE_GATES = {
    0x802B4824:(0,1,0),0x802B4838:(0,1,0),
    0x802B486C:(0,1,0),0x802B488C:(0,1,0),
}
HISTORY_SKIP_BRANCHES = {
    0x802B4828:0x802B4830,0x802B483C:0x802B4844,
    0x802B487C:0x802B4884,0x802B4890:0x802B4898,
}
SELECTOR_GLOBAL_LOADS={0x802B4898:(3,13,-23168),0x802B48BC:(3,13,-23168)}
SELECTOR_INDEX_LOADS={0x802B489C:(0,3,0x1C),0x802B48C4:(0,3,0x1C)}
SELECTOR_ELEMENT_LOADS={0x802B48A8:(3,3,0x0C),0x802B48D8:(3,3,0x0C)}
SELECTOR_VPTR_LOADS={0x802B48AC:(12,3,0),0x802B48E0:(12,3,0)}
SELECTOR_RLWINM=(0x802B48A0,0x802B48D0)
SELECTOR_ADDS=(0x802B48A4,0x802B48D4)
SELECTOR_MTCTR=(0x802B48B4,0x802B48E8)
# EXACT bounded source ranges within the compiled GolfScene_unsplit.o;
# the broad target names are annotations, not evidence of execution.
PEAK_WINDOW = (0x802B4794, 0x802B493C)
STATED_LATCH_WINDOW = (0x802B31A8, 0x802B31C8)
SOURCE_CALL_WINDOWS = ((0x802B3BC0, 0x802B3D08),)
COHORT_PPC_WINDOWS = (PEAK_WINDOW, STATED_LATCH_WINDOW,
                      CONTROLLER_ACCESSOR_WINDOW, *SOURCE_CALL_WINDOWS)
EXCERPT = (0x802B4820, 0x802B4938)
PREPROCESSOR_WINDOW = (0x802B4474, 0x802B4504)
DIRECT_CALL_TARGETS = {
    0x802B4794: "calc_history_update",
    0x802B4474: "calc_preprocessor",
    0x802B3BA0: "calc_state_next_step",
    0x802B2F90: "calc_latch_step",
}

class Abstain(ValueError):
    """Sanitized failure. Never embed private file path or native values."""


def _pc_check(pc: int) -> None:
    if (type(pc) is not int or pc % 4 or not (
            OWNER_START <= pc < OWNER_END or
            CONTROLLER_ACCESSOR_WINDOW[0] <= pc < CONTROLLER_ACCESSOR_WINDOW[1])):
        raise Abstain("source_window_outside_verified_golf_unit_or_controller_accessor")


def _word(mm, pc: int) -> int:
    _pc_check(pc)
    off = pc - MEM1_BASE
    if not 0 <= off <= len(mm) - 4:
        raise Abstain("source_word_unmapped")
    return int.from_bytes(mm[off:off + 4], "big")


def _dform(word: int):
    return ((word >> 26), (word >> 21) & 31,
            (word >> 16) & 31, (word & 0xFFFF))


def _signed(x: int, bits: int) -> int:
    return x - (1 << bits) if x & (1 << (bits - 1)) else x


def _branch(pc: int, word: int):
    op = word >> 26
    if op == 18:
        li = word & 0x03FFFFFC
        val = _signed(li, 26)
    elif op == 16:
        li = word & 0xFFFC
        val = _signed(li, 16)
    else:
        return None
    addr = val if word & 2 else (pc + val)
    return {"dest": addr & 0xFFFFFFFF,
            "link": bool(word & 1), "absolute": bool(word & 2)}


def _dform_match(read, pc: int, op: int, fr: int,
                 base: int, offset: int) -> bool:
    return _dform(read(pc)) == (op, fr, base, offset & 0xFFFF)


def _mr_matches(word: int, target: int, source_reg: int) -> bool:
    return bool((word >> 26) == 31
                and (word >> 1) & 1023 == 444
                and (word >> 16) & 31 == target
                and (word >> 21) & 31 == source_reg
                and (word >> 11) & 31 == source_reg)


def _arith_matches(word: int, spec: tuple[int, int, int, int, int, int]) -> bool:
    op, fd, fa, fb, fc, xo5 = spec
    return (word >> 26 == op and (word >> 21) & 31 == fd
            and (word >> 16) & 31 == fa and (word >> 11) & 31 == fb
            and (word >> 6) & 31 == fc and (word >> 1) & 31 == xo5
            and not word & 1)


def _cmp_matches(word: int, spec: tuple[int, int, int]) -> bool:
    crfd, fa, fb = spec
    return ((word >> 26) == 63 and (word >> 1) & 1023 == 32
            and (word >> 23) & 7 == crfd and (word >> 21) & 3 == 0
            and (word >> 16) & 31 == fa
            and (word >> 11) & 31 == fb and not word & 1)


def verify_magnitude_arithmetic(read) -> dict:
    """Exact PowerPC f32 multiply, greater-than and virtual return lineage.

    This is source-code arithmetic and NOT proof of a live controller
    sample, real accepted shot power, or identical virtual receiver.
    """
    for pc, spec in MAG_LFS_GATES.items():
        if not _dform_match(read, pc, 48, *spec):
            raise Abstain("magnitude_factor_reader_gate_failed")
    for pc, spec in MAG_STFS_GATES.items():
        if not _dform_match(read, pc, 52, *spec):
            raise Abstain("magnitude_delta_writer_gate_failed")
    for pc, spec in MAG_ARITH_GATES.items():
        if not _arith_matches(read(pc), spec):
            raise Abstain("magnitude_fp_arithmetic_gate_failed")
    for pc, spec in MAG_FCMP_GATES.items():
        if not _cmp_matches(read(pc), spec):
            raise Abstain("magnitude_strict_peak_compare_gate_failed")
    for pc, target in MAG_SKIP_BRANCHES.items():
        word = read(pc)
        b = _branch(pc, word)
        if ((word >> 26) != 16 or (word >> 21) & 31 != 4
                or (word >> 16) & 31 != 1
                or b is None or b["absolute"] or b["link"]
                or b["dest"] != target):
            raise Abstain("magnitude_strict_peak_branch_gate_failed")
    for pc, spec in MAG_VTABLE_LOADS.items():
        if not _dform_match(read, pc, 32, *spec):
            raise Abstain("magnitude_virtual_getter_slot_gate_failed")
    for pc in MAG_BCCTRL_SITES:
        word = read(pc)
        if (word >> 26 != 19 or (word >> 1) & 1023 != 528
                or not word & 1):
            raise Abstain("magnitude_virtual_getter_call_gate_failed")

    return {
        "status":"REV1_TWO_PRODUCT_MAX_UPDATE_SOURCE_PASS",
        "pc_1st_callback":"0x802B48B8",
        "pc_2nd_callback":"0x802B48EC",
        "both_virtual_load_offset_decimal":56,
        "actual_virtual_callee_address_verified":False,
        "two_callbacks_same_object_verified":False,
        "candidate_A_pseudocode":"(calc[+0x18] * virtual_return_f1_at_48B8) * calc[+0x28]",
        "candidate_B_pseudocode":"(calc[+0x1C] * virtual_return_f1_at_48EC) * calc[+0x2C]",
        "delta_0x98_pseudocode":"candidate_A - old_calc[+0x08]",
        "calc_0x08_rule":"if candidate_A > old_calc[+0x08]: store candidate_A",
        "calc_0x0C_rule":"if candidate_B > old_calc[+0x0C]: store candidate_B",
        "single_precision_rounding_and_nan_behavior_not_modeled":True,
        "controller_input_semantics_verified":False,
        "native_accepted_shot_power_verified":False,
    }


def _guard_strict_peak(read, sites, reason: str):
    for pc,target in sites.items():
        word=read(pc)
        b=_branch(pc,word)
        if ((word>>26)!=16 or (word>>21)&31!=4
                or (word>>16)&31!=1 or b is None
                or b["absolute"] or b["link"] or b["dest"]!=target):
            raise Abstain(reason)


def verify_history_pipeline(read) -> dict:
    for pc,spec in HISTORY_LOADS.items():
        if not _dform_match(read,pc,48,*spec):
            raise Abstain("history_float_load_gate_failed")
    for pc,spec in HISTORY_STORES.items():
        if not _dform_match(read,pc,52,*spec):
            raise Abstain("history_float_store_gate_failed")
    for pc,spec in HISTORY_FP_GATES.items():
        if not _arith_matches(read(pc),spec):
            raise Abstain("history_float_operation_gate_failed")
    for pc,spec in HISTORY_COMPARE_GATES.items():
        if not _cmp_matches(read(pc),spec):
            raise Abstain("history_greater_compare_gate_failed")
    _guard_strict_peak(read,HISTORY_SKIP_BRANCHES,
                       "history_greater_branch_gate_failed")
    return {
        "status":"REV1_TWO_ACCUMULATORS_FOUR_RUNNING_MAX_SITES_SOURCE_PASS",
        "calc_0x18_rule":"if incoming_f1 > old_calc[+0x18]: calc[+0x18] = incoming_f1",
        "calc_0x1C_rule":"if source_r31[+0x18] > old_calc[+0x1C]: calc[+0x1C] = source_r31[+0x18]",
        "calc_0x20_rule":"calc[+0x20] = (old_calc[+0x20] * f31) + source_r31[+0x1C]",
        "calc_0x24_rule":"calc[+0x24] = (old_calc[+0x24] * f31) + source_r31[+0x1C]",
        "calc_0x28_rule":"if calc[+0x20] > old_calc[+0x28]: calc[+0x28] = calc[+0x20]",
        "calc_0x2C_rule":"if calc[+0x24] > old_calc[+0x2C]: calc[+0x2C] = calc[+0x24]",
        "f31_source_and_meaning_verified":False,
        "source_r31_struct_identity_verified":False,
        "floating_point_nan_and_rounding_not_modeled":True,
        "guest_control_value_verified":False,
    }


def verify_virtual_selector_reuse(read) -> dict:
    for pc,spec in SELECTOR_GLOBAL_LOADS.items():
        if not _dform_match(read,pc,32,*spec):
            raise Abstain("selector_global_gate_failed")
    for pc,spec in SELECTOR_INDEX_LOADS.items():
        if not _dform_match(read,pc,32,*spec):
            raise Abstain("selector_index_gate_failed")
    for pc,spec in SELECTOR_ELEMENT_LOADS.items():
        if not _dform_match(read,pc,32,*spec):
            raise Abstain("selector_element_gate_failed")
    for pc,spec in SELECTOR_VPTR_LOADS.items():
        if not _dform_match(read,pc,32,*spec):
            raise Abstain("selector_vptr_gate_failed")
    for pc in SELECTOR_RLWINM:
        word=read(pc)
        if ((word>>26)!=21 or (word>>21)&31!=0
                or (word>>16)&31!=0 or (word>>11)&31!=2
                or (word>>6)&31!=0 or (word>>1)&31!=29 or word&1):
            raise Abstain("selector_times_four_index_gate_failed")
    for pc in SELECTOR_ADDS:
        word=read(pc)
        if ((word>>26)!=31 or (word>>1)&1023!=266
                or (word>>21)&31!=3 or (word>>16)&31!=3
                or (word>>11)&31!=0):
            raise Abstain("selector_pointer_add_gate_failed")
    for pc in SELECTOR_MTCTR:
        word=read(pc)
        if ((word>>26)!=31 or (word>>1)&1023!=467
                or (word>>21)&31!=12 or (word>>16)&31!=9
                or (word>>11)&31!=0):
            raise Abstain("selector_mtctr_gate_failed")
    return {
        "status":"REV1_TWIN_GLOBAL_INDEXED_VTABLE_SLOT56_SOURCE_PASS",
        "same_source_global_r13_offset":-23168,
        "both_index_field_offset":0x1C,
        "index_scale_bytes":4,
        "both_element_pointer_offsets":0x0C,
        "both_vtable_slot_offsets":0x38,
        "same_static_selection_expression":True,
        "actual_selected_receiver_identity_verified":False,
        "actual_runtime_getter_return_equality_verified":False,
        "actual_virtual_callee_address_verified":False,
        "same_r31_input_object_as_selector_verified":False,
    }


def verify_controller_selector_call_chain(read) -> dict:
    """Verify the caller ABI and sample-record consumers, not callee identity."""
    for pc,target in CONTROLLER_ACCESS_CALLS.items():
        w=read(pc)
        b=_branch(pc,w)
        if (w>>26!=18 or b is None or not b["link"] or b["absolute"]
                or b["dest"]!=target):
            raise Abstain("controller_accessor_caller_call_gate_failed")
    for pc,index in CONTROLLER_ACCESS_SELECTORS.items():
        if not _dform_match(read,pc,14,4,0,index):
            raise Abstain("controller_accessor_selector_gate_failed")
    for pc,(dest,source) in CONTROLLER_RESULT_COPIES.items():
        if not _mr_matches(read(pc),dest,source):
            raise Abstain("controller_accessor_record_copy_gate_failed")
    for pc,(reg,base,disp) in CONTROLLER_ENTRY_GATES.items():
        if not _dform_match(read,pc,32,reg,base,disp):
            raise Abstain("controller_accessor_sample_count_gate_failed")
    if not _dform_match(read,CONTROLLER_FP_CONSTANT_LOAD,48,31,2,-12892):
        raise Abstain("controller_accessor_decay_constant_gate_failed")
    if not _dform_match(read,CONTROLLER_RETURN_FP_LOAD,48,1,31,0x18):
        raise Abstain("controller_accessor_return_field_gate_failed")
    return {
      "status":"REV1_CONTROLLER_THREE_EXTENDED_STATUS_CALLERS_SOURCE_PASS",
      "selector_codes":[1,2,3],
      "record_1_register":"r28",
      "record_2_register":"r31",
      "record_3_register":"r27",
      "second_record_0x18_consumed_in_f1":True,
      "second_record_0x1C_consumed_in_accumulators":True,
      "read_length_source_field_offset":0x854,
      "f31_constant_source":"SDA2 r2-12892",
      "compiled_accessor_address":"0x8019BAE8",
      "compiled_accessor_unit":"Pack/RPKernel/RPSysController.cpp",
      "source_controller_access_method_candidate":"RPSysCoreController::getExCoreStatus",
      "native_accessor_body_exactly_matched_to_public_method":False,
      "sample_record_KPAD_acc_value_and_acc_speed_link_verified":False,
      "public_KPADStatus_fields":{"record+0x18":"acc_value",
                                  "record+0x1C":"acc_speed"},
      "source_controller_filter_config":{"1":[0.1,0.015],
                                          "2":[0.1,0.05],
                                          "3":[0.1,0.02]},
      "source_reference":"doldecomp/ogws src/Pack/RPKernel/RPSysController.cpp; include/revolution/KPAD/KPAD.h",
      "guest_runtime_controller_consumption_verified":False,
    }


def verify_static_gates(read) -> dict:
    for pc in (*STFS_GATES, *LFS_GATES, *STW_GATES, *CALL_GATES, *MR_GATES):
        _pc_check(pc)
    for pc, (fr, base, disp) in STFS_GATES.items():
        if not _dform_match(read, pc, 52, fr, base, disp):
            raise Abstain("calc_writer_instruction_gate_failed")
    for pc, (fr, base, disp) in LFS_GATES.items():
        if not _dform_match(read, pc, 48, fr, base, disp):
            raise Abstain("calc_latch_reader_instruction_gate_failed")
    for pc, (reg, base, disp) in STW_GATES.items():
        if not _dform_match(read, pc, 36, reg, base, disp):
            raise Abstain("calc_state_gate_failed")
    for pc, target in CALL_GATES.items():
        b = _branch(pc, read(pc))
        if (read(pc) >> 26 != 18 or b is None or not b["link"]
                or b["absolute"] or b["dest"] != target):
            raise Abstain("calc_call_chain_gate_failed")
    for pc, (dest, src) in MR_GATES.items():
        if not _mr_matches(read(pc), dest, src):
            raise Abstain("calc_receiver_identity_chain_gate_failed")
    # Source owner: both writer and latch lie in same unsplit Golf text unit.
    if any(not OWNER_START <= pc < OWNER_END for pc in (*STFS_GATES, *CALL_GATES)):
        raise Abstain("source_owner_invalid")
    return {
        "calc_current_writer_at": "0x802B4914",
        "calc_peak_writer_at": "0x802B4924",
        "calc_peak_reader_at": "0x802B31B0",
        "calc_state3_latch_writer_at": "0x802B31C4",
        "calc_state3_writer_at": "0x802B31C0",
        "two_direct_bl_edges_exact": True,
        "four_explicit_mr_receiver_copies_exact": True,
        "writer_instruction_gates_exact": True,
    }


def symbolize(pc: int, word: int) -> dict:
    """No 4-byte private source word in output; public PC and operands only."""
    _pc_check(pc)
    op = word >> 26
    line = {"pc": f"0x{pc:08X}", "opcode": op}
    if op in (14, 15, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 57, 60, 61):
        o, rt, ra, u = _dform(word)
        names = {
            14:"addi", 15:"addis", 32:"lwz", 34:"lbz", 36:"stw", 38:"stb",
            40:"lhz", 42:"lha", 44:"sth", 46:"lmw", 48:"lfs", 50:"lfd",
            52:"stfs", 54:"stfd", 56:"psq_l", 57:"psq_lu",
            60:"psq_st", 61:"psq_stu",
        }
        line.update({"class": names.get(op, "dform"), "reg": rt,
                     "base": ra, "disp": _signed(u, 16)})
    elif op in (16, 18):
        b = _branch(pc, word)
        line.update({"class": "bc" if op == 16 else ("bl" if b["link"] else "b"),
                     "target": f"0x{b['dest']:08X}",
                     "link": b["link"], "absolute": b["absolute"]})
        if op == 16:
            line.update({"bo":(word >> 21) & 31,
                         "bi":(word >> 16) & 31})
    elif op in (59, 63):
        line.update({
            "class": "fp_opcode59" if op == 59 else "fp_opcode63",
            "fd": (word >> 21) & 31, "fa":(word >> 16) & 31,
            "fb":(word >> 11) & 31, "fc":(word >> 6) & 31,
            "xo5":(word >> 1) & 31, "xo10":(word >> 1) & 1023})
    elif op == 21:
        # PowerPC rlwinm RS,RA,SH,MB,ME[,Rc]: index scaling/masking.
        # In original audit this was "unclassified" before each virtual
        # dispatch; revealing the fields does NOT verify runtime object ID.
        line.update({"class":"rlwinm",
                     "rs":(word >> 21) & 31,"ra":(word >> 16) & 31,
                     "sh":(word >> 11) & 31,"mb":(word >> 6) & 31,
                     "me":(word >> 1) & 31,"record":bool(word & 1)})
    elif op == 31:
        line.update({"class":"int_xform", "rd":(word >> 21) & 31,
                     "ra":(word >> 16) & 31,"rb":(word >> 11) & 31,
                     "xo10":(word >> 1) & 1023})
    elif op == 19:
        xo = (word >> 1) & 1023
        line.update({"class": ("bclr" if xo==16 else
                               "bcctr" if xo==528 else "op19"),
                     "xo10":xo, "link":bool(word & 1)})
    else:
        line.update({"class":"unclassified"})
    return line


def scan_direct_golf_call_sites(read, *, start=OWNER_START, end=OWNER_END) -> dict:
    """Direct BL coverage of this ONE source-owned text unit only.

    Never infer that absent BL means no dynamic function-pointer/virtual call.
    Operates on decoded relative instructions, prints only public source PCs.
    """
    if (type(start) is not int or type(end) is not int
            or start % 4 or end % 4
            or start < OWNER_START or end > OWNER_END or start >= end):
        raise Abstain("direct_call_scan_window_outside_source_text")
    hits={name: [] for name in DIRECT_CALL_TARGETS.values()}
    totals={name: 0 for name in DIRECT_CALL_TARGETS.values()}
    for pc in range(start,end,4):
        word=read(pc)
        if (word>>26) != 18 or (word&3)!=1:
            continue
        target=_branch(pc,word)["dest"]
        name=DIRECT_CALL_TARGETS.get(target)
        if name is None:
            continue
        totals[name] += 1
        if len(hits[name]) < 40:
            hits[name].append(f"0x{pc:08X}")
    return {
        "status":"REV1_BOUNDED_GOLF_DIRECT_BL_INVENTORY",
        "text_unit":PUBLIC_OWNER,
        "scan_start":f"0x{start:08X}",
        "scan_end_exclusive":f"0x{end:08X}",
        "direct_call_sites":hits,
        "direct_call_totals":totals,
        "call_site_list_capped_at":40,
        "indirect_or_external_callers_exhaustive":False,
        "absence_of_direct_call_proves_not_invoked":False,
        "guest_invocation_verified":False,
    }


def source_slice(read) -> dict:
    gates = verify_static_gates(read)
    math_report = verify_magnitude_arithmetic(read)
    history_report = verify_history_pipeline(read)
    selector_report = verify_virtual_selector_reuse(read)
    controller_call_report = verify_controller_selector_call_chain(read)
    accessor_excerpt=[symbolize(pc,read(pc))
                      for pc in range(*CONTROLLER_ACCESSOR_WINDOW,4)]
    entry = [symbolize(pc, read(pc)) for pc in range(0x802B4794, 0x802B4820,4)]
    words = [symbolize(pc, read(pc)) for pc in range(*EXCERPT, 4)]
    # Candidate upstream scratch fields on the same r24 CALC base.
    store_sites = [
        {"pc":line["pc"], "field":f"+0x{line['disp']:X}",
         "source_freg":line["reg"]}
        for line in words if line.get("class") == "stfs"
        and line.get("base") == 24 and 0 <= line.get("disp", -1) <= 0x40
    ]
    producer_window = [line for line in words if
                       0x802B4860 <= int(line["pc"], 16) <= 0x802B4924]
    # Three return/callback-candidate sites are NOT automatically game inputs.
    bl_sites = [line for line in words if line["class"] == "bl"]
    virtual_selection = [line for line in words if
                         int(line["pc"], 16) in
                         (0x802B4898, 0x802B489C, 0x802B48A0,
                          0x802B48A4, 0x802B48A8, 0x802B48AC,
                          0x802B48B0, 0x802B48B8,
                          0x802B48BC, 0x802B48C4, 0x802B48D0,
                          0x802B48D4, 0x802B48D8,
                          0x802B48E0, 0x802B48E4, 0x802B48EC)]
    return {
        "status":"REV1_CALC_UPSTREAM_STATIC_SOURCE_PASS",
        "public_unit": PUBLIC_OWNER,
        "source_callee":"fn_802B4794",
        "source_code_only":True,
        "game_input_consumption_verified":False,
        "calc_0x0C_accepted_power_verified":False,
        "native_club_angular_velocity_verified":False,
        "guest_execution_verified":False,
        "training_approved":False,
        "latch":gates,
        "native_magnitude_arithmetic":math_report,
        "upstream_two_accumulators_and_four_peak_sites":history_report,
        "repeated_global_virtual_getter_selector":selector_report,
        "input_function_entry_source_excerpt":entry,
        "controller_extended_status_call_chain":controller_call_report,
        "candidate_getExCoreStatus_binary_excerpt":accessor_excerpt,
        "current_and_peak_register_writer_annotations":{
            "+0x08":"f30 through calc r24",
            "+0x0C":"f1 through calc r24 (comparison-before-store to be proved by control flow)",
        },
        "r24_candidate_calculation_stores":store_sites,
        "potential_upstream_direct_calls":bl_sites,
        "virtual_return_selector_source_instructions":virtual_selection,
        "fp_reaching_definitions_source_excerpt":producer_window,
        "full_bounded_excerpt": words,
        "next_step":"Manually verify registers feeding f30/f1, candidate callback recipients, and exact branches before assigning acceleration/peak/accepted-power semantics.",
    }


def _default_archive(data_root: Path) -> Path:
    if data_root.name != "Wii-AI-Golf-Data" or data_root.is_symlink():
        raise Abstain("private_data_root_unqualified")
    captures = data_root / "captures"
    if not captures.is_dir() or captures.is_symlink():
        raise Abstain("private_capture_root_missing")
    candidates = []
    for path in captures.iterdir():
        if not path.is_dir() or path.is_symlink():
            continue
        manifest = path / "manifest-PRIVATE.json"
        if not manifest.is_file() or manifest.is_symlink():
            continue
        if manifest.stat().st_size > 65536:
            continue
        try:
            header = json.loads(manifest.read_text(encoding="utf-8-sig"))
        except (ValueError, OSError, UnicodeError):
            continue
        if (type(header) is dict
                and header.get("kind") == "p0-private-numbered-capture-inventory"
                and header.get("capture_count") == 7):
            candidates.append(path)
    if len(candidates) != 1:
        raise Abstain("expected_one_existing_qualified_original_archive")
    return candidates[0]


def run(archive: Path, *, detailed: bool = False) -> dict:
    # _check_archive cryptographically validates all original 14 banks,
    # and confirms the private archived inventory manifest's provenance.
    try:
        folders = private._check_archive(archive)
    except (ValueError, OSError, KeyError, TypeError):
        raise Abstain("original_archive_sha_or_manifest_gate_failed") from None

    with ExitStack() as stack:
        phase_windows = []
        readers = []
        for n in (1, 5, 7):
            path = source._file(folders[n], f"{n}.1.raw", roster.MEM1_SIZE)
            fh = stack.enter_context(path.open("rb"))
            mm = stack.enter_context(mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ))
            readers.append(mm)
        # This entire decomp-qualified Golf text unit is immutable native
        # CODE across the original source phases before scanning BL sites.
        for lo,hi in (*COHORT_PPC_WINDOWS,
                      (OWNER_START,OWNER_END),PREPROCESSOR_WINDOW):
            phase_windows.append([
                bytes(mm[lo-MEM1_BASE:hi-MEM1_BASE])
                for mm in readers
            ])
        if any(windows[0] != windows[1] or windows[0] != windows[2]
               for windows in phase_windows):
            raise Abstain("native_code_differs_between_original_1_5_7")
        read=lambda pc:_word(readers[0],pc)
        result = source_slice(read)
        result["golf_text_direct_call_inventory"]=scan_direct_golf_call_sites(read)
        result["calc_preprocessor_source_excerpt"]=[
            symbolize(pc,read(pc)) for pc in range(*PREPROCESSOR_WINDOW,4)]
        result["complete_golf_text_phases_1_5_7_identical"]=True
    # Verify originals again after reading, fail closed on races/altered hashes.
    try:
        private._check_archive(archive)
    except (ValueError, OSError, KeyError, TypeError):
        raise Abstain("original_archive_post_sha_gate_failed") from None
    result.update({
        "original_14_bank_sha_pre_and_post_verified":True,
        "native_mem1_code_phases_1_5_7_identical":True,
        "disassembly_excerpt_includes_private_raw_bytes":False,
    })
    if not detailed:
        # Keep small default result; detailed output consists only of public
        # source PCs, register indices, and instruction class/operands.
        result.pop("full_bounded_excerpt")
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path,
                        help="existing private archive; default auto-discovers unique cohort")
    parser.add_argument("--detailed", action="store_true",
                        help="include bounded PC/operator instruction table (never raw bytes)")
    args = parser.parse_args(argv)
    try:
        archive = args.archive if args.archive else _default_archive(DATA)
        report = run(archive, detailed=args.detailed)
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (Abstain, ValueError, OSError, TypeError, KeyError, OverflowError):
        # Never expose native paths, original-bank byte content or private
        # addresses in an exception string.
        print(json.dumps({"status":"ABSTAIN",
                          "reason":"source_or_original_archive_qualification_failed",
                          "training_approved":False}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
