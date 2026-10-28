"""P0 offline bounded PowerPC control-flow probe from a candidate r3->r31 copy.

This is not a full function CFG or proof of dynamic instance ownership. No
native instruction words, private offsets, addresses, values or hashes printed.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import sys
import audit_ball_xyz_source_callers_private as upstream

UNIT = "RPGolPlayer"
UNIT_START = 0x8029E62C
COPY_REL = 0x1BE8
STORE_REL = 0x1C18
COPY = UNIT_START + COPY_REL
STORE = UNIT_START + STORE_REL
MAX_INSNS = 16


def _branch(pc: int, word: int):
    """Only true unconditional/conditional branch forms, not generic opcode19."""
    op = word >> 26
    aa = bool(word & 2)
    lk = bool(word & 1)
    if op == 18:
        disp = word & 0x03FFFFFC
        if disp & 0x02000000:
            disp -= 0x04000000
        return ("linked_call" if lk else "unconditional_branch",
                (disp if aa else pc + disp) & 0xFFFFFFFF)
    if op == 16:
        disp = word & 0xFFFC
        if disp & 0x8000:
            disp -= 0x10000
        bo = (word >> 21) & 31
        branch_always = (bo & 0x14) == 0x14
        return (("linked_call" if lk else "unconditional_branch") if branch_always
                else ("linked_conditional_call" if lk else "conditional_branch"),
                (disp if aa else pc + disp) & 0xFFFFFFFF)
    if op == 19 and ((word >> 1) & 0x3FF) in (16, 528, 50):
        return ("indirect_or_return", None)
    if op == 17:
        return ("system_call", None)
    return None


def _r31_effect(word: int) -> str:
    """Conservative possible GPR modification; branch handling is separate."""
    op = word >> 26
    rt = (word >> 21) & 31
    ra = (word >> 16) & 31
    rb = (word >> 11) & 31
    if op == 31:
        xo = (word >> 1) & 0x3FF
        if xo == 444 and ra == 31:
            if rt == rb == 3:
                return "r3_copy"
            return "other_register_copy_or_or"
        return "possible_gpr_writer" if rt == 31 or ra == 31 else "none"
    if op in (32, 34, 40, 42, 14, 15, 7, 8, 12, 13):
        return "possible_gpr_writer" if rt == 31 else "none"
    if op in (33, 35, 41, 43):
        return "possible_gpr_writer" if rt == 31 or ra == 31 else "none"
    if op in (24, 25, 26, 27, 28, 29, 20, 21, 22, 23, 30):
        return "possible_gpr_writer" if ra == 31 else "none"
    if op in (37, 39, 45, 49, 51, 53, 55):
        return "possible_gpr_writer" if ra == 31 else "none"
    if op in (36, 38, 44, 48, 50, 52, 54, 59, 63):
        return "none"
    if op == 19:
        return "none"
    if op in (16, 17, 18):
        return "none"
    return "unknown_possible_gpr_effect"


def analyze_window(data: bytes, start: int = COPY):
    """Bounded source-local possible paths; not dominance of a whole function.

    Calls are modeled as tainted returns. Targets outside this tiny slice are
    untracked and could re-enter the selected instruction.
    """
    if (type(data) is not bytes or type(start) is not int or
            start != COPY or len(data) != STORE - COPY + 4 or
            len(data) % 4 or len(data)//4 > MAX_INSNS):
        raise ValueError("Unexpected source window")
    words = {start + off: struct.unpack_from(">I", data, off)[0]
             for off in range(0, len(data), 4)}
    mr = words[COPY]
    if not ((mr >> 26) == 31 and ((mr >> 1) & 1023) == 444 and
            (mr >> 21) & 31 == 3 and (mr >> 16) & 31 == 31 and
            (mr >> 11) & 31 == 3 and (mr & 1) == 0):
        raise ValueError("Expected r3-to-r31 register copy absent")
    st = words[STORE]
    if not ((st >> 26) == 52 and ((st >> 21) & 31) == 0 and
            ((st >> 16) & 31) == 31 and (st & 0xFFFF) == 0x90):
        raise ValueError("Expected f0 to +0x90(r31) store absent")
    todo = [(COPY + 4, True, False)]
    visited = set()
    reached = set()
    reasons = set()
    edges = set()
    per_pc = {}
    while todo:
        pc, preserved, unknown = todo.pop()
        state = (pc, preserved, unknown)
        if state in visited:
            continue
        visited.add(state)
        if len(visited) > 256:
            raise ValueError("Exceeded bounded CFG states")
        if pc == STORE:
            reached.add((preserved, unknown))
            continue
        if pc not in words or pc < COPY or pc > STORE:
            reasons.add("path_leaves_bounded_slice")
            continue
        word = words[pc]
        event = _branch(pc, word)
        if event:
            kind, dest = event
            target_label = None
            if dest is not None and COPY <= dest <= STORE:
                target_label = f"+0x{dest-UNIT_START:04X}"
            edges.add((f"+0x{pc-UNIT_START:04X}", kind, target_label))
            if kind in ("system_call", "indirect_or_return"):
                reasons.add("unresolved_indirect_or_system_flow")
                continue
            if kind == "unconditional_branch":
                todo.append((dest, preserved, unknown))
            elif kind == "conditional_branch":
                todo.append((dest, preserved, unknown))
                todo.append((pc + 4, preserved, unknown))
            else:
                reasons.add("linked_call_return_unverified")
                todo.append((pc + 4, False, True))
            continue
        effect = _r31_effect(word)
        if effect == "r3_copy":
            preserved = True
        elif effect != "none":
            preserved = False
            unknown = True
            reasons.add("unresolved_r31_write_or_opcode")
            per_pc[pc] = effect
        todo.append((pc + 4, preserved, unknown))
    return {
        "kind": "S002-P0-R31-LOCAL-CFG-CANDIDATES",
        "source_game": "RSPE01", "disc_revision": 1,
        "source_unit": UNIT,
        "copy_site_source_offset": "+0x1BE8",
        "store_site_source_offset": "+0x1C18",
        "copy_is_r3_to_r31_source_confirmed": True,
        "store_is_stfs_f0_to_r31_plus_90_source_confirmed": True,
        "window_instructions": len(words),
        "local_path_reaches_store": bool(reached),
        "local_path_reaches_store_with_unmodified_r31": (True, False) in reached,
        "local_path_reaches_store_with_unknown_r31": any(not p or u for p,u in reached),
        "control_flow_edges": [{"site":pc, "kind":k, "target_if_within_slice":t}
                               for pc,k,t in sorted(edges)],
        "unresolved_r31_site_offsets": [f"+0x{x-UNIT_START:04X}"
                                        for x in sorted(per_pc)],
        "incomplete_path_reasons": sorted(reasons),
        "full_function_cfg_dominance_proven": False,
        "runtime_receiver_is_selected_player_record_verified": False,
        "dynamic_store_execution_verified": False,
        "physical_world_xyz_verified": False,
        "velocity_power_impact_score_verified": False,
        "approved_for_training": False,
        "allowed_to_publish": False,
    }


def audit(session: Path, data_root: Path):
    try:
        file = upstream.checked_private_b0(session, data_root)
    except upstream.UntrustedInput:
        raise ValueError("Original B0 verification failed") from None
    if not any(name == UNIT and lo == UNIT_START and lo <= COPY < STORE < hi
               for name, lo, hi in upstream.UNITS):
        raise ValueError("Published Rev1 unit mismatch")
    with file.open("rb") as fp:
        header = fp.read(8)
        if len(header) != 8 or header[:6] != upstream.GAME_ID or header[7] != 1:
            raise ValueError("Original B0 header mismatch")
        fp.seek(COPY - upstream.MEM1_START)
        data = fp.read(STORE - COPY + 4)
    if len(data) != STORE - COPY + 4:
        raise ValueError("Source window short")
    try:
        upstream.checked_private_b0(session, data_root)
    except upstream.UntrustedInput:
        raise ValueError("Original B0 changed") from None
    report = analyze_window(data)
    report["original_private_B0_SHA_verified_before_and_after"] = True
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    default=Path(__file__).resolve().parents[2]/"Wii-AI-Golf-Data"
    p.add_argument("--data-root",type=Path,default=default)
    p.add_argument("--private-session",type=Path)
    args=p.parse_args(argv)
    session=args.private_session or args.data_root/"ball-study-20261027-212633"
    try:
        report=audit(session,args.data_root)
    except (OSError,ValueError,TypeError,KeyError,OverflowError,ImportError,AttributeError):
        print("P0 local r31 CFG ABSTAINED: original private source or code predicates failed; no native values or paths emitted.",file=sys.stderr)
        return 2
    print(json.dumps(report,sort_keys=True,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
