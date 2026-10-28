"""OFFLINE source-bounded PPC syntactic-chain triage for roster stride 0xCC.

Reads only an existing *private* Wii Sports Rev1 native MEM1 dump. Does not
launch Dolphin, follow RAM pointers, control the game, emit code/addresses,
or assert class type, base-register identity, ball position, club pose, power.

This is a narrow complement to S002 PR #160's two-bank candidate roster
inventory. A syntactic chain is NOT a verified PPC register-dataflow proof.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import struct
import sys

MEM1_BASE = 0x80000000
MEM1_SIZE = 24 * 1024 * 1024
PLAYER_MANAGER_CODE = (0x802A2210, 0x802A3560)  # Rev1 source compilation unit
STRIDE = 0xCC
CANDIDATE_MEMBER_OFFSETS = (0x8C, 0xC8)
MAX_LOOKAHEAD = 20


def _signed16(word: int) -> int:
    v = word & 0xFFFF
    return v - 0x10000 if v >= 0x8000 else v


def _op(word: int) -> int:
    return word >> 26


def _gpr_dest(word: int) -> int:
    return (word >> 21) & 31


def _ra(word: int) -> int:
    return (word >> 16) & 31


def _rb(word: int) -> int:
    return (word >> 11) & 31


def _is_add(word: int) -> bool:
    return _op(word) == 31 and ((word >> 1) & 0x1FF) == 266


# PPC opcode31 indexed memory X-form XO values; no receiver class inference.
# Only simple integer/FPR accesses are supported here, not string or
# multiple-register loads/stores.
INDEXED_MEM_XO = {
    23: "load",   # lwzx
    55: "load",   # lwzux
    87: "load",   # lbzx
    119: "load",  # lbzux
    279: "load",  # lhzx
    311: "load",  # lhzux
    151: "store", # stwx
    183: "store", # stwux
    215: "store", # stbx
    247: "store", # stbux
    407: "store", # sthx
    535: "load",  # lfsx
    567: "load",  # lfsux
    599: "load",  # lfdx
    631: "load",  # lfdux
    663: "store", # stfsx
    695: "store", # stfsux
    727: "store", # stfdx
    759: "store", # stfdux
}


def _is_mem(word: int) -> bool:
    return _op(word) in {32, 33, 34, 35, 36, 37, 38, 39,
                         40, 41, 42, 43, 44, 45, 46, 47,
                         48, 49, 50, 51, 52, 53, 54, 55}


def _kind(word: int) -> str:
    return "load" if _op(word) in {32, 33, 34, 35, 40, 41, 42, 43, 46, 48, 49, 50, 51} else "store"


def analyze_words(words: list[int], lookahead: int = MAX_LOOKAHEAD) -> dict:
    """Count syntactic index*0xCC + other-register + memory-member chains.

    Tracks ONLY exact recognized instruction forms. Unknown potentially
    register-writing instructions end the window instead of guessing aliases;
    every branch terminates the window, including calls and conditional jumps.
    A chain may still cross a non-executed instruction and does NOT establish
    that the other register is an RPGolPlayerManager instance or that fields
    +0x8C/+0xC8 are C++ members. No instruction words or PCs leave output.
    """
    if not 1 <= lookahead <= 32 or len(words) > 4096 or not words or any(
        type(w) is not int or not 0 <= w <= 0xFFFFFFFF for w in words
    ):
        raise ValueError("Invalid bounded PPC instruction stream/window")

    all_stride = Counter()
    all_member = Counter()
    chains = Counter()
    mul_with_join = mul_with_member = 0
    site_shape_counts = Counter()
    short_stop_counts = Counter()

    for i, w in enumerate(words):
        op = _op(w)
        if op in (7, 14) and _signed16(w) == STRIDE:
            all_stride["mulli" if op == 7 else "addi"] += 1
        if _is_mem(w) and _signed16(w) in CANDIDATE_MEMBER_OFFSETS:
            all_member[(f"+0x{_signed16(w):03X}", _kind(w))] += 1
        if op != 7 or _signed16(w) != STRIDE:
            continue

        # This mul destination carries the scaled slot index, not an
        # authenticated player-manager pointer.
        lineage = {_gpr_dest(w): "scaled"}
        found_join = False
        found_member = False
        site_shapes = set()
        stop_reason = "window_end"
        for nxt in words[i + 1: i + 1 + lookahead]:
            n_op = _op(nxt)
            if n_op in (16, 18, 19):
                stop_reason = "branch_before_complete_trace"
                break  # stop at control-flow boundary

            if n_op in (14, 15):  # addi, addis
                dst, src = _gpr_dest(nxt), _ra(nxt)
                prior = lineage.get(src) if src != 0 else None
                if dst in lineage:
                    lineage.pop(dst)
                if prior:
                    next_kind = prior
                    if prior == "joined" and n_op == 14:
                        if _signed16(nxt) in CANDIDATE_MEMBER_OFFSETS:
                            next_kind = "joined_offset_member"
                            site_shapes.add("joined_plus_candidate_member_addi")
                        elif _signed16(nxt) == 0:
                            site_shapes.add("joined_plus_zero_addi")
                        else:
                            site_shapes.add("joined_plus_other_addi")
                    lineage[dst] = next_kind
                continue

            if _is_add(nxt):  # add rD, rA, rB
                dst, ra, rb = _gpr_dest(nxt), _ra(nxt), _rb(nxt)
                left, right = lineage.get(ra), lineage.get(rb)
                # If one side is index-derived and other is an untraced
                # external base, this is only an address *shape* candidate.
                newkind = "joined" if (left or right) and not (left and right) else None
                if dst in lineage:
                    lineage.pop(dst)
                if newkind:
                    lineage[dst] = newkind
                    found_join = True
                continue

            if n_op == 46:  # lmw overwrites multiple registers; cannot track
                stop_reason = "multiple_register_load"
                break

            if n_op == 31 and ((nxt >> 1) & 0x3FF) in INDEXED_MEM_XO:
                xo = (nxt >> 1) & 0x3FF
                base = _ra(nxt)
                index = _rb(nxt)
                if lineage.get(base, "").startswith("joined") or lineage.get(index, "").startswith("joined"):
                    site_shapes.add("joined_indexed_memory_" + INDEXED_MEM_XO[xo])
                # X-form GPR loads clobber destination (float loads FPR).
                if xo in {23, 55, 87, 119, 279, 311}:
                    lineage.pop(_gpr_dest(nxt), None)
                # Indexed update-form loads/stores clobber base register.
                if xo in {55, 119, 311, 183, 247, 567, 631, 695, 759}:
                    lineage.pop(base, None)
                continue

            if _is_mem(nxt):
                base = _ra(nxt)
                disp = _signed16(nxt)
                base_kind = lineage.get(base)
                if base_kind == "joined":
                    if disp in CANDIDATE_MEMBER_OFFSETS:
                        chains[(f"+0x{disp:03X}", _kind(nxt))] += 1
                        found_member = True
                        site_shapes.add("joined_direct_candidate_member_" + _kind(nxt))
                    elif disp == 0:
                        site_shapes.add("joined_zero_offset_memory_" + _kind(nxt))
                    elif 0 < disp <= 0x100:
                        site_shapes.add("joined_other_small_offset_memory_" + _kind(nxt))
                    else:
                        site_shapes.add("joined_other_offset_memory_" + _kind(nxt))
                elif base_kind == "joined_offset_member" and disp == 0:
                    site_shapes.add("joined_addi_member_then_zero_memory_" + _kind(nxt))
                # Loads overwrite GPR dest, but float loads write FPR.
                if n_op in (32, 33, 34, 35, 40, 41, 42, 43, 46):
                    lineage.pop(_gpr_dest(nxt), None)
                if n_op in (33, 35, 37, 39, 41, 43, 45, 49, 51, 53, 55):
                    lineage.pop(base, None)  # update form overwrites base
                continue

            if n_op in (24, 25):  # ori / oris: dest in RA, source RS
                dst, src = _ra(nxt), _gpr_dest(nxt)
                prior = lineage.get(src)
                lineage.pop(dst, None)
                if prior:
                    lineage[dst] = prior
                continue

            # Unknown families may clobber tracked registers. Fail closed.
            stop_reason = "unsupported_ppc_opcode"
            break

        if found_join:
            short_stop_counts[stop_reason] += 1
            site_shape_counts.update(site_shapes)
        mul_with_join += int(found_join)
        mul_with_member += int(found_member)

    return {
        "kind": "offline_roster_ppc_bounded_syntactic_chain_study",
        "schema_version": 1,
        "source_unit": "RSPE01_01 RPGolPlayerManager.cpp .text",
        "code_unit_instructions_checked": len(words),
        "lookahead_instruction_limit": lookahead,
        "stride_immediate_0xcc": {"mulli": all_stride["mulli"],
                                   "addi": all_stride["addi"]},
        "direct_candidate_member_memory_opcode_counts": {
            f"{offset}_{kind}": all_member[(offset, kind)]
            for offset in ("+0x08C", "+0x0C8") for kind in ("load", "store")
        },
        "mulli_sites_with_bounded_index_plus_base_add": mul_with_join,
        "mulli_sites_with_bounded_index_add_then_member_access": mul_with_member,
        "post_join_site_shape_counts": {key: site_shape_counts[key] for key in (
            "joined_zero_offset_memory_load", "joined_zero_offset_memory_store",
            "joined_indexed_memory_load", "joined_indexed_memory_store",
            "joined_plus_candidate_member_addi",
            "joined_addi_member_then_zero_memory_load",
            "joined_addi_member_then_zero_memory_store",
            "joined_other_small_offset_memory_load",
            "joined_other_small_offset_memory_store",
            "joined_other_offset_memory_load",
            "joined_other_offset_memory_store",
            "joined_plus_other_addi",
            "joined_direct_candidate_member_load",
            "joined_direct_candidate_member_store",
        )},
        "joined_site_trace_stop_reason_counts": {
            key: short_stop_counts[key] for key in (
                "branch_before_complete_trace",
                "multiple_register_load",
                "unsupported_ppc_opcode",
                "window_end",
            )
        },
        "index_provenance_and_receiver_identity_verified": False,
        "syntactic_candidate_chains": {
            f"{offset}_{kind}": chains[(offset, kind)]
            for offset in ("+0x08C", "+0x0C8") for kind in ("load", "store")
        },
        "all_paths_exhaustively_traced": False,
        "control_flow_graph_verified": False,
        "other_base_register_is_player_manager_verified": False,
        "register_receiver_dataflow_proven": False,
        "roster_member_offsets_source_verified": False,
        "runtime_class_type_verified": False,
        "ball_xyz_verified": False,
        "club_pose_or_swing_power_verified": False,
        "allowed_to_publish": False,
        "interpretation": (
            "A bounded same-basic-block syntactic chain is a falsifiable code-side hint, "
            "not a verified C++ receiver or runtime ball/player member. Missing chains "
            "can reflect unsupported PPC instruction forms; never infer absent physics."
        ),
    }


def _private_mem1(path: Path, private_root: Path, stack: ExitStack):
    if path.is_symlink() or not path.is_file() or path.stat().st_size != MEM1_SIZE:
        raise ValueError("Invalid private native MEM1 image")
    if not path.resolve(strict=True).is_relative_to(private_root):
        raise ValueError("Private MEM1 must be inside sibling Data directory")
    fh = stack.enter_context(path.open("rb"))
    bank = stack.enter_context(mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ))
    if bytes(bank[:8]) != b"RSPE01\x00\x01":
        raise ValueError("Wrong native Wii Sports revision")
    return bank


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mem1", required=True, type=Path)
    parser.add_argument("--window", type=int, default=MAX_LOOKAHEAD)
    args = parser.parse_args(argv)
    try:
        private_root = (Path(__file__).resolve().parents[2] /
                        "Wii-AI-Golf-Data").resolve(strict=True)
        if not private_root.is_dir():
            raise ValueError("Missing private Data directory")
        with ExitStack() as stack:
            bank = _private_mem1(args.mem1, private_root, stack)
            start, end = PLAYER_MANAGER_CODE
            words = [struct.unpack_from(">I", bank, pos - MEM1_BASE)[0]
                     for pos in range(start, end, 4)]
            report = analyze_words(words, args.window)
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, struct.error):
        print("Roster PPC offline study stopped: invalid private image or bounded analysis", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
