"""Conservative PPC intra-function control-flow must-definition proof for P0.

SOURCE-ONLY: the owner must provide an already verified Rev1 read_u32 callback
for the ORIGINAL source code. No files, emulator, bridge, runtime RAM or
private values are opened/exported. This proves at most a *static* alias of
entry-r3 through r31 back into r3 at a known bl callsite. It never proves
runtime invocation, the class of entry-r3, or the rendered moving ball.

Unknown instruction, dynamic branch, out-of-window edge, or other callee:
ABSTAIN rather than extrapolate a straight-line r31 hypothesis.
"""
from __future__ import annotations

from collections import deque
import json
from typing import Callable

CACHE_TARGET = 0x80299C70
# Public Rev1 function entries, bounded callsites from #219/#240.
CALLERS = (
    ("fn_80299ACC", 0x80299ACC, 0x80299B64),
    ("fn_80299C20", 0x80299C20, 0x80299C58),
)
MAX_WORDS = 128
MAX_STATES = MAX_WORDS * 4


class Unresolved(Exception):
    pass


def _signed16(value: int) -> int:
    return value - 0x10000 if value & 0x8000 else value


def _branch(pc: int, word: int, bits: int) -> int:
    mask = (1 << bits) - 4
    offset = word & mask
    if offset & (1 << (bits - 1)):
        offset -= 1 << bits
    return (offset if word & 2 else pc + offset) & 0xFFFFFFFF


def _mr(word: int) -> tuple[int, int] | None:
    # PPC or rA,rS,rB with rS==rB is the canonical mr form.
    if word >> 26 != 31 or (word >> 1) & 1023 != 444:
        return None
    rs = (word >> 21) & 31
    ra = (word >> 16) & 31
    rb = (word >> 11) & 31
    if rs != rb:
        return None
    return ra, rs


def _effect(word: int, entry_r3: bool, entry_r31: bool) -> tuple[bool, bool]:
    """Symbolically track exactly 2 GPRs; fail on unsupported opcode classes."""
    op = word >> 26
    mr = _mr(word)
    if mr is not None:
        dst, src = mr
        val = {3:entry_r3, 31:entry_r31}.get(src, False)
        if dst == 3:
            entry_r3 = val
        if dst == 31:
            entry_r31 = val
        return entry_r3, entry_r31
    if op == 31:
        xo = (word >> 1) & 1023
        # mfspr (including mflr) and mfcr; GPR destination is RT.
        if xo in (339, 19):
            dst = (word >> 21) & 31
            return (False if dst == 3 else entry_r3,
                    False if dst == 31 else entry_r31)
        # cmp/cmpl only change CR, not GPR.
        if xo in (0, 32):
            return entry_r3, entry_r31
        raise Unresolved("other X-form instruction could clobber tracked GPR")
    # Comparison, floating arithmetic, 'nop' ori, and ordinary rlwimi etc
    # must not be allowed to smuggle writes to tracked r3/r31.
    if op in (10, 11, 4, 59, 63):
        return entry_r3, entry_r31
    # D-format integer immediate and load GPR (rt is destination).
    if op in (12, 13, 14, 15, 32, 33, 34, 35, 40, 41, 42, 43):
        rt, ra = (word >> 21) & 31, (word >> 16) & 31
        if rt == 3:
            entry_r3 = False
        if rt == 31:
            entry_r31 = False
        if op in (33, 35, 41, 43):  # indexed base register write-back
            if ra == 3:
                entry_r3 = False
            if ra == 31:
                entry_r31 = False
        return entry_r3, entry_r31
    # D-format stores and float loads/stores, with update variants.
    if op in (36,37,38,39,44,45,46,47,48,49,50,51,52,53,54,55):
        ra = (word >> 16) & 31
        if op == 46:  # lmw loads rT through r31
            rt = (word >> 21) & 31
            if rt <= 3:
                entry_r3 = False
            entry_r31 = False
        if op in (37,39,45,49,51,53,55):
            if ra == 3:
                entry_r3 = False
            if ra == 31:
                entry_r31 = False
        return entry_r3, entry_r31
    # rA destinations for rotate/mask and integer OR immediate.
    if op in (20, 21, 23, 24, 25, 26, 27, 28, 29):
        ra = (word >> 16) & 31
        if ra == 3:
            entry_r3 = False
        if ra == 31:
            entry_r31 = False
        return entry_r3, entry_r31
    raise Unresolved("unsupported PPC opcode may affect source alias")


def _next(pc: int, word: int, callsite: int) -> tuple[int, ...]:
    op = word >> 26
    lk = word & 1
    if op == 18:
        if lk:
            # Non-target BL returns with volatile r3 clobber. Conservatively
            # abstain even when r31 appears preserved under ABI convention.
            raise Unresolved("subcall or conditional call before target")
        return (_branch(pc, word, 26),)
    if op == 16:
        if lk:
            raise Unresolved("conditional call")
        # Conservative overapprox: both possible outcomes for ANY BO field.
        # No speculative "always taken" shortcut can cause false proof.
        return (pc+4, _branch(pc, word, 16))
    if op == 19:
        # Exact unconditional blr = terminal return with no reaching call.
        if word == 0x4E800020:
            return ()
        raise Unresolved("indirect branch, bclr/bcctr or CR opcode unsupported")
    if op == 17:
        raise Unresolved("system call")
    if pc == callsite:
        raise Unresolved("target must be exact linked call")
    return (pc+4,)


def prove_caller(read_u32: Callable[[int], int], *, entry: int,
                 callsite: int, target: int = CACHE_TARGET) -> dict:
    """Must-definition over all reachable, conservatively decoded paths.

    The callable must be backed by independently hash/Rev1-gated ORIGINAL PPC.
    No code words or PC addresses in returned report. Unknown -> abstain.
    """
    status = "ABSTAIN_SOURCE_UNRESOLVED"
    reached = False
    seen = set()
    try:
        if (type(entry) is not int or type(callsite) is not int
            or type(target) is not int or entry % 4 or callsite % 4
            or not 0x80000000 <= entry < callsite < 0x81000000
            or (callsite-entry)//4 > MAX_WORDS):
            raise Unresolved("invalid published function boundary")
        code = {}
        for pc in range(entry, callsite+4, 4):
            word = read_u32(pc)
            if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
                raise Unresolved("unqualified source code")
            code[pc] = word
        tail = code[callsite]
        if tail >> 26 != 18 or not tail & 1 or _branch(callsite, tail, 26) != target:
            raise Unresolved("not exact bl to cache writer")
        q = deque([(entry, True, False)])
        status = "STATIC_ENTRY_R3_MUST_FLOW"
        while q:
            pc, r3, r31 = q.popleft()
            k = (pc, r3, r31)
            if k in seen:
                continue
            seen.add(k)
            if len(seen) > MAX_STATES:
                raise Unresolved("bounded CFG state budget exceeded")
            if pc < entry or pc > callsite or pc not in code:
                raise Unresolved("branch leaves certified function window")
            word = code[pc]
            if pc == callsite:
                reached = True
                if not (r3 and r31):
                    status = "NOT_PROVEN_FOR_ALL_REACHING_PATHS"
                continue
            if word == 0:  # invalid / missing executable body
                raise Unresolved("zero instruction word")
            next_r3, next_r31 = _effect(word, r3, r31)
            for dest in _next(pc, word, callsite):
                if dest < entry or dest > callsite or dest % 4:
                    raise Unresolved("uncertified direct branch destination")
                q.append((dest, next_r3, next_r31))
        if not reached:
            status = "ABSTAIN_TARGET_UNREACHABLE"
    except (Unresolved, KeyError, TypeError, IndexError):
        status = "ABSTAIN_SOURCE_UNRESOLVED"
    return {
        "kind": "P0-STATIC-PPC-R31-CALLSITE-MUSTDEF",
        "status": status,
        "known_exact_cache_writer_callsite_reached": reached,
        "all_reaching_paths_pass_entry_r3_through_r31_to_call_r3":
            status == "STATIC_ENTRY_R3_MUST_FLOW",
        "source_code_rev1_and_sha_verified_by_this_pure_function": False,
        "incoming_entry_r3_object_class_verified": False,
        "runtime_receiver_object_verified": False,
        "executed_cache_write_verified": False,
        "guest_frame_and_rendered_ball_verified": False,
        "physical_xyz_velocity_power_contact_score_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }


def inspect_known_callers(read_u32: Callable[[int], int]) -> dict:
    """Use only after the source-owner authenticates read_u32 over Rev1 code."""
    results = []
    for name, entry, call in CALLERS:
        row = prove_caller(read_u32, entry=entry, callsite=call)
        # The name is public ogws source symbol, not private heap address.
        results.append({"published_source_function": name, **row})
    return {
        "kind": "P0-STATIC-TWO-CALLER-R31-MUSTDEF-REVIEW",
        "sources": results,
        "both_static_proofs_succeeded": all(
            x["all_reaching_paths_pass_entry_r3_through_r31_to_call_r3"]
            for x in results
        ),
        "real_native_source_was_inspected_by_this_module": False,
        "runtime_receiver_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }


if __name__ == "__main__":
    # Intentionally NO --native/--archive/--live option: owner integration only.
    print(json.dumps({
        "kind":"P0-CFG-MUSTDEF-OFFLINE-LIBRARY-ONLY",
        "private_banks_read":False, "dolphin_contacted":False,
        "dynamic_receiver_claim":False, "training_approved":False
    }, sort_keys=True))
