#!/usr/bin/env python3
"""Read-only, source-qualified Wii Golf lift/side normalization guard study.

Study the original RSPE01 Rev1 PPC compare/branch callsite geometry around
source-proposed normalized lift/side helpers, without guessing native epsilon.
Static bytes, branch syntax and original SHA may be verified; actual Ball
receiver, runtime path, zero-vector threshold and per-shot parity remain
UNVERIFIED. Uses the reviewed same-checkout preflight module from draft #454.
"""
from __future__ import annotations

import json
from pathlib import Path
import struct

import audit_p0_localops_rev1_study as source

# Bounded source-WINDOWS, NOT asserted entire function boundaries. Public
# helper entry addresses are source-reported, but interval endings and any
# instruction outside these windows need independent symbol/CFG validation.
GUARD_WINDOWS = {
    "lift_candidate": (0x80295F3C, 0x80295FE0),
    "scale_candidate": (0x80295FE0, 0x8029605C),
    "lateral_candidate": (0x8029605C, 0x80296120),
}
TARGETS = (0x800E8558, 0x80295FE0)
MAX_GUARD_RECORDS = 22
MAX_OUTPUT = 1900


def decode_compare(pc: int, word: int) -> dict | None:
    """PowerPC FP compare fcmpu/fcmpo (opcode 63, XO 0/32)."""
    if (word >> 26) != 63:
        return None
    xo = (word >> 1) & 1023
    if xo not in (0, 32):
        return None
    return {
        "pc": f"0x{pc:08X}",
        "op": "fcmpu" if xo == 0 else "fcmpo",
        "crf": (word >> 23) & 7,
        "fra": (word >> 16) & 31,
        "frb": (word >> 11) & 31,
    }


def decode_bc(pc: int, word: int) -> dict | None:
    """Direct conditional PPC bc; preserve AA and LK, not assume branch taken."""
    if word >> 26 != 16:
        return None
    displacement = word & 0xfffc
    if displacement & 0x8000:
        displacement -= 0x10000
    absolute = bool(word & 2)
    target = (displacement if absolute else pc + displacement) & 0xffffffff
    return {
        "pc": f"0x{pc:08X}",
        "bo": (word >> 21) & 31,
        "bi": (word >> 16) & 31,
        "target": f"0x{target:08X}",
        "aa": absolute,
        "lk": bool(word & 1),
    }


def lexical_guard_report(windows: dict[tuple[int, int], bytes]) -> dict:
    """Return bounded compare/branch and norm-call candidate facts, no CFG."""
    observations = {}
    for name, (lo, hi) in GUARD_WINDOWS.items():
        data = windows[(lo, hi)]
        if len(data) != hi - lo or len(data) % 4:
            raise source.Abstain("GUARD_SOURCE_WINDOW_BOUNDS")
        comparisons, branches, calls = [], [], []
        for i in range(0, len(data), 4):
            pc = lo + i
            word = struct.unpack_from(">I", data, i)[0]
            compare = decode_compare(pc, word)
            branch = decode_bc(pc, word)
            if compare is not None:
                comparisons.append(compare)
            if branch is not None:
                branches.append(branch)
            target = source._branch(pc, word)
            if target in TARGETS:
                calls.append([f"0x{pc:08X}", f"0x{target:08X}"])
        if len(comparisons) + len(branches) + len(calls) > MAX_GUARD_RECORDS:
            raise source.Abstain("GUARD_REPORT_COUNT_CAP")
        observations[name] = {
            "fp_comparisons": comparisons[:6],
            "conditional_branches": branches[:7],
            "direct_helper_calls": calls[:5],
            "total_counts": [len(comparisons), len(branches), len(calls)],
        }
    result = {
        "status": "NATIVE_GUARD_OPCODE_CANDIDATES_ONLY",
        "stage": "lift_lateral_normalizer_guards",
        "windows": observations,
        "zero_branch_operand_proven": False,
        "native_epsilon_or_exact_zero_proven": False,
        "nondegenerate_normalized_force_eligible": "UNKNOWN",
        "lift_vs_side_update_order": "UNKNOWN",
        "same_selected_ball_receiver_verified": False,
        "guest_runtime_branch_observed": False,
        "native_game_parity_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }
    if len(json.dumps(result, separators=(",", ":"))) > MAX_OUTPUT:
        raise source.Abstain("GUARD_RECEIPT_BUDGET")
    return result


def audit(checkout: Path) -> dict:
    """Full original 14-bank source provenance before and after PPC reads."""
    if not source._source_owners():
        raise source.Abstain("PUBLIC_REV1_UNIT_MAP")
    ((archive, topology),) = source._find_candidates(checkout)
    before = source._validate_banks(archive)
    if len(before) != 14:
        raise source.Abstain("ORIGINAL_14_BANKS_REQUIRED")
    mem1_by_phase = {
        phase: path for phase, size, path, _ in before
        if size == source.MEM1_SIZE
    }
    read_windows = source.SOURCE_WINDOWS + tuple(GUARD_WINDOWS.values())
    phase_sources = [source._read_windows(mem1_by_phase[p], read_windows)
                     for p in (1, 5, 7)]
    if not (phase_sources[0] == phase_sources[1] == phase_sources[2]):
        raise source.Abstain("ORIGINAL_PHASE_SOURCE_MISMATCH")
    source._source_gates(lambda pc: source._word(phase_sources[0], pc))
    result = lexical_guard_report(phase_sources[0])
    after = source._validate_banks(archive)
    if len(after) != 14 or tuple(x[3] for x in before) != tuple(x[3] for x in after):
        raise source.Abstain("ORIGINAL_SHA_POST_MISMATCH")
    result["original_14_bank_sha_pre_post_verified"] = True
    result["phase_1_5_7_source_equal"] = True
    result["native_nonlinear_source_gates_pass"] = True
    result["archive_topology"] = topology
    if len(json.dumps(result, separators=(",", ":"))) > MAX_OUTPUT:
        raise source.Abstain("GUARD_RECEIPT_BUDGET")
    return result


def main() -> int:
    try:
        result = audit(Path(__file__).resolve().parents[1])
    except (source.Abstain, ValueError, OSError, KeyError, TypeError,
            UnicodeError, struct.error) as exc:
        result = {
            "status": "DIAGNOSTIC_ABSTAIN",
            "reason": exc.code if type(exc) is source.Abstain else "SOURCE_PRECONDITION",
            "stage": "lift_lateral_normalizer_guards",
            "native_game_parity_verified": False,
            "training_approved": False,
            "allowed_to_publish": False,
        }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 2 if result["status"] == "DIAGNOSTIC_ABSTAIN" else 0


if __name__ == "__main__":
    raise SystemExit(main())
