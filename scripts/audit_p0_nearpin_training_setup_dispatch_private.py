#!/usr/bin/env python3
"""P0: source-bounded Golf training SetupGame/SetupTrainingGame dispatcher census.

EXPLICIT LIMIT: public Rev1 typed function ENTRY/SIZE only; no proof
of executed mode-4 path, training phase identity, result or memory field.
Never emits raw guest instructions, private addresses, vectors, paths or
hashes. Reads precisely 23+38 published code words from the seven
original SHA-pinned, source-selected RSPE01 Rev1 captures (NO new shots).
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as src
import audit_golf_two_bank_roster_private as roster

# Public Kokeshi annotations independently matched exact ogws symbols.txt
# function entries and sizes, pinned in the accompanying research note.
PUBLIC_CONFIG_UNIT = (0x8029CA4C, 0x8029E62C)
WINDOWS = (
    ("SetupTrainingGame", 0x8029D778, 0x98), # 38 instructions
    ("SetupGame", 0x8029D810, 0x5C),         # 23 instructions
)
MAX_WINDOWS = 2

def _signed(v: int, bits: int) -> int:
    return v - (1 << bits) if (v & (1 << (bits - 1))) else v

def _branch_target(word: int, pc: int, conditional: bool) -> int:
    # Strict PPC primary op 18 LI (26-bit including low zeros),
    # or primary op 16 BD (16-bit including low zeros). Direct only.
    field = (word & (0xFFFC if conditional else 0x03FFFFFC))
    off = _signed(field, 16 if conditional else 26)
    return off if (word & 2) else (pc + off) & 0xFFFFFFFF

def _site_class(target: int, start: int, length: int) -> str:
    if start <= target < start + length:
        return f"IN_THIS_FUNCTION+0x{target - start:03X}"
    lo, hi = PUBLIC_CONFIG_UNIT
    if lo <= target < hi:
        return f"IN_PUBLISHED_CONFIG_UNIT+0x{target-lo:04X}"
    return "OUTSIDE_PUBLISHED_CONFIG_UNIT_UNTYPED"

def classify_window(name: str, start: int, size: int, words: tuple[int,...]) -> dict:
    if type(start) is not int or type(size) is not int or start % 4 or size % 4:
        raise ValueError("unaligned source window")
    if type(words) is not tuple or len(words) != size // 4 or len(words) == 0:
        raise ValueError("bounded function source window length mismatch")
    allowed = {(n,pc,span) for n,pc,span in WINDOWS}
    if (name,start,size) not in allowed:
        raise ValueError("not a preapproved source function")
    calls, branches, literal_comps = [], [], []
    returns=indirect=unknown=0
    for idx, word in enumerate(words):
        if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
            raise ValueError("invalid source instruction word")
        pc = start + 4 * idx
        op = word >> 26
        at = f"+0x{4*idx:03X}"
        if op == 18:
            target = _branch_target(word,pc,False)
            row = {"site":at,"target_region":_site_class(target,start,size),
                   "link":bool(word & 1),"absolute":bool(word & 2)}
            (calls if word & 1 else branches).append(row)
        elif op == 16:
            target = _branch_target(word,pc,True)
            branches.append({"site":at,"target_region":_site_class(target,start,size),
                             "link":bool(word & 1),"absolute":bool(word & 2),
                             "conditional":True})
        elif op in (10,11):
            # These compare a register with an immediate; register's value
            # and controlling branch are NOT typed by this instruction.
            imm = (word & 0xFFFF)
            if op == 11:
                imm = _signed(imm,16)
            if imm in (3,4,5):
                literal_comps.append({"site":at,"compares_literal":imm,
                                      "unsigned":op == 10})
        elif word == 0x4E800020:
            returns += 1
        elif op == 19 and (word & 0x7FE) in (0x420, 0x020):
            # Branch-to-CTR/LR family (including condition variants).
            indirect += 1
        elif op == 17:
            unknown += 1  # system call, not a clean return
    # Any local literal compare is a *syntactic* candidate, never
    # proof of runtime mode==4 or training choice.
    return {
        "source_public_function_name_candidate":name,
        "source_window_word_count":size//4,
        "direct_linked_branch_site_count":len(calls),
        "direct_linked_branch_sites":calls,
        "direct_nonlinked_or_conditional_branches":branches,
        "mode_3_4_5_literal_compare_sites":literal_comps,
        "direct_literal_mode4_compare_syntax_seen":any(x["compares_literal"]==4
                                                    for x in literal_comps),
        "ordinary_blr_count":returns,
        "indirect_branch_family_count":indirect,
        "system_call_count":unknown,
        "mode4_branch_reachability_or_phase_receiver_proven":False,
        "training_phase_identity_proven":False,
    }

def inspect(read_u32, ctx: dict) -> tuple:
    if type(ctx) is not dict or type(ctx.get("selected_index")) is not int or \
       not 0 <= ctx["selected_index"] <= 3 or type(ctx.get("hole")) is not int or \
       not 0 <= ctx["hole"] <= 8:
        raise ValueError("source selection not qualified")
    return tuple(tuple(read_u32(addr+4*j) for j in range(span//4))
                 for _,addr,span in WINDOWS)

def summarize_observations(observations: dict) -> dict:
    if type(observations) is not dict or set(observations)!=set(range(1,8)):
        raise ValueError("exactly seven original numbered samples required")
    first = observations[1]
    if type(first) is not tuple or len(first) != MAX_WINDOWS:
        raise ValueError("bad source observations")
    if any(observations[n] != first for n in range(2,8)):
        raise ValueError("function source window drift across Rev1 captures")
    details=[classify_window(name,start,size,first[i])
             for i,(name,start,size) in enumerate(WINDOWS)]
    return {
        "kind":"P0-GOLF-TRAINING-SETUP-DISPATCH-SOURCE-V1",
        "game_id":"RSPE01","disc_revision":1,
        "source_selected_mode4_and_scene5_gated":True,
        "canonical_14_bank_archive_sha_before_and_after":True,
        "public_source_window_code_stable_seven_of_seven":True,
        "public_function_identity_independently_compiled_verified":False,
        "mode4_to_phase_source_dispatch_verified":False,
        "golf_sequence_manager_class_identity_verified":False,
        "commit_result_backing_state_verified":False,
        "individual_nearpin_result_or_landing_verified":False,
        "actual_guest_physics_step_or_rendered_ball_verified":False,
        "training_approved":False,"allowed_to_publish":False,
        "windows":details,
    }

def analyze(archive: Path) -> dict:
    original=src._check_archive(archive)
    with ExitStack() as stack:
        observations={}
        for n in range(1,8):
            mm=[]
            for i,size in enumerate(src.SIZE):
                p=src.src._file(original[n],f"{n}.{i+1}.raw",size)
                fp=stack.enter_context(p.open("rb"))
                mm.append(stack.enter_context(mmap.mmap(fp.fileno(),0,access=mmap.ACCESS_READ)))
            rd=roster.TwoBankReader(*mm)
            ctx=src._get(rd)  # original native B0 source/scene/mode/hole chain
            observations[n]=inspect(rd.u32,ctx)
        result=summarize_observations(observations)
    src._check_archive(archive)  # second full original 14-bank SHA gate
    return result

def main(argv=None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    args=p.parse_args(argv)
    try:
        report=analyze(args.archive)
    except (OSError, ValueError, TypeError, KeyError, OverflowError, AttributeError):
        print("P0_TRAINING_SETUP_SOURCE_ABSTAIN: source window, original capture SHA or game owner unqualified",file=sys.stderr)
        return 2
    print(json.dumps(report,sort_keys=True,indent=2,allow_nan=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
