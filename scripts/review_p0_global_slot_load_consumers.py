"""Pure PPC straight-line *first-use* hints for the source-global r13 ball slot.

Consumes ONLY the 15 prior #240 authenticated direct lwz sites, not new
heuristic memory scans. The exact 6 Golf code units, source r13 slot, and
original seven-bank Rev1 SHA gates belong to the parent reader.
No native I/O, raw instructions, heap addresses, floats, upload, or live game.
A syntactic first use is never proof of runtime execution or visible ball.
"""
from __future__ import annotations
import re

UNIT_BASE = 0x80296FD8
UNIT_END = 0x8029B240
MAX_FORWARD_WORDS = 6

def _signed16(u: int) -> int:
    u &= 65535
    return u - 65536 if u & 32768 else u

def _word(read, pc):
    w = read(pc)
    if type(w) is not int or not 0 <= w <= 0xffffffff:
        raise ValueError("unqualified PPC source instruction")
    return w

def _fields(w):
    return (w >> 26, (w >> 21) & 31, (w >> 16) & 31, _signed16(w))

def _mr(w):
    if (w >> 26) != 31 or ((w >> 1) & 1023) != 444:
        return None
    rs, ra, rb = (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31
    return (ra, rs) if rs == rb else None

def _potential_write(w, reg):
    """Conservative register-effect gate, not comprehensive PPC semantics."""
    op, rt, ra, _ = _fields(w)
    mr = _mr(w)
    if mr is not None:
        return mr[0] == reg
    if op in (12, 13, 14, 15, 32, 33, 34, 35, 40, 41, 42, 43):
        return rt == reg or (op in (33, 35, 41, 43) and ra == reg)
    if op == 46:
        return rt <= reg
    if op in (20, 21, 23, 24, 25, 26, 27, 28, 29):
        return ra == reg
    if op in (37, 39, 45, 49, 51, 53, 55):
        return ra == reg
    if op in (36, 38, 44, 47, 48, 50, 52, 54, 10, 11, 59, 63):
        return False
    # Unknown X-form and paired-single writes MAY affect tracked GPR.
    if op in (4, 30, 31):
        return True
    # All other unrecognized opcode classes stop rather than claiming use.
    return True

def _loc(pc):
    return "+0x%04X" % (pc - UNIT_BASE)

def first_consumer(read, pc: int, disp: int) -> dict:
    if type(pc) is not int or pc % 4 or not UNIT_BASE <= pc < UNIT_END:
        raise ValueError("source site outside exact published MapObjBall")
    if type(disp) is not int or not -32768 <= disp < 32768:
        raise ValueError("source r13 displacement unqualified")
    op, reg, ra, imm = _fields(_word(read, pc))
    if (op, ra, imm) != (32, 13, disp):
        raise ValueError("not the expected source-global direct lwz")
    # The object-pointer load is a static PPC use, not a live data point.
    event = "no_certified_consumer_in_six_words"
    off = None
    rel_field = None
    forwarded_r3 = (reg == 3)
    for step in range(1, MAX_FORWARD_WORDS + 1):
        here = pc + step * 4
        if here >= UNIT_END:
            event = "source_unit_boundary"
            break
        w = _word(read, here)
        typ, rs, base, immediate = _fields(w)
        mr = _mr(w)
        if typ in (16, 17, 18, 19):
            if typ == 18 and w & 1 and forwarded_r3:
                event = "direct_bl_after_r3_pointer_candidate"
            else:
                event = "branch_or_call_before_proven_consumer"
            off = _loc(here)
            break
        if mr is not None and mr[0] == 3 and mr[1] == reg:
            forwarded_r3 = True
            # Do not claim BL yet: the next word could clobber r3.
            continue
        if typ in (10, 11) and base == reg and immediate == 0:
            event = "immediate_zero_compare_on_loaded_pointer"
            off = _loc(here)
            break
        if typ in (32, 34, 40, 42, 48, 50) and base == reg:
            event = "field_load_from_source_global_pointer"
            off = _loc(here)
            rel_field = immediate if -512 <= immediate <= 512 else None
            break
        if typ in (36, 38, 44, 52, 54) and base == reg:
            event = "field_store_through_source_global_pointer"
            off = _loc(here)
            rel_field = immediate if -512 <= immediate <= 512 else None
            break
        if typ in (36, 38, 44) and rs == reg:
            event = "source_global_pointer_value_stored"
            off = _loc(here)
            break
        if _potential_write(w, reg) or (forwarded_r3 and _potential_write(w, 3)):
            event = "possible_register_clobber_before_proven_consumer"
            off = _loc(here)
            break
    return {
        "source_unit": "RPGolMapObjBall",
        "global_load_unit_relative_pc": _loc(pc),
        "destination_GPR": "r%d" % reg,
        "first_bounded_consumer_class": event,
        "first_bounded_consumer_unit_relative_pc": off,
        "source_syntactic_field_displacement": rel_field,
        "all_path_pointer_dataflow_verified": False,
        "call_target_or_receiver_type_verified": False,
        "rendered_active_ball_verified": False,
    }

def analyze(read, sites, disp: int) -> dict:
    if type(sites) is not list or len(sites) != 15:
        raise ValueError("expected exact 15 source-direct read references")
    out = []
    seen = set()
    for s in sites:
        if type(s) is not dict or s.get("source_unit") != "RPGolMapObjBall" or s.get("source_access_type") != "direct_lwz_read":
            raise ValueError("unverified published source read")
        name = s.get("unit_relative_pc")
        if type(name) is not str or not re.fullmatch(r"\+0x[0-9A-F]{4}", name):
            raise ValueError("invalid public code relative offset")
        pc = UNIT_BASE + int(name[3:], 16)
        if pc in seen:
            raise ValueError("duplicate source read site")
        seen.add(pc)
        out.append(first_consumer(read, pc, disp))
    out.sort(key=lambda x: x["global_load_unit_relative_pc"])
    return {
        "kind": "S002-GLOBAL-SLOT-DIRECT-READ-FIRST-USE-HINTS",
        "exact_known_direct_loads_checked": len(out),
        "bounded_forward_instruction_count": MAX_FORWARD_WORDS,
        "source_only_first_use_hints": out,
        "no_cross_branch_or_indirect_dataflow_claim": True,
        "all_path_source_consumer_identity_verified": False,
        "dynamic_rendered_object_role_verified": False,
        "ball_world_xyz_velocity_power_impact_score_verified": False,
        "approved_for_model_training": False,
        "allowed_to_publish": False,
    }
