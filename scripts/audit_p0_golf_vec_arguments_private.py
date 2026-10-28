#!/usr/bin/env python3
"""P0: local r3/r4 vector ARG source syntax at 18 source-qualified PSVEC BLs.

Same exact original private B0 SHA+Rev1 source and public Golf unit mapping as
companion FPR-return script. Nearest syntactic register source only; not CFG,
dynamic vectors, pin/ball pointers, distance units or real shot execution.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_golf_vec_f1_return_private as f1

base = f1.base
BACKWARD = 0x80
UNKNOWN = "NOT_RECOGNIZED_IN_BOUNDED_SUFFIX"


def _gpr_write(word: int, reg: int) -> str | None:
    """Conservative relevant PowerPC write categories, not complete decoding."""
    if type(word) is not int or type(reg) is not int or reg not in (3, 4):
        raise ValueError("untrusted instruction or register")
    op, rt, ra = (word >> 26), ((word >> 21) & 31), ((word >> 16) & 31)
    if op in (14, 15) and rt == reg:
        if ra == 0:
            return "ADD_IMMEDIATE_LITERAL_ZERO_BASE"
        return "ADDI_FROM_r%d" % ra if op == 14 else "ADDIS_FROM_r%d" % ra
    if op in (32, 33, 34, 35, 40, 41, 42, 43):
        if rt == reg:
            return "LOAD_GPR_FROM_BASE_r%d" % ra
        if op in (33, 35, 41, 43) and ra == reg:
            return "INTEGER_LOAD_UPDATE_BASE_WRITE"
    if op in (20, 21, 23, 24, 25, 26, 27, 28, 29) and ra == reg:
        return "ROTATE_LOGICAL_rA_DEST_UNRESOLVED"
    if op == 46 and rt <= reg:
        return "LMW_RANGE_OVERWRITES_GPR"
    if op in (37, 39, 45, 49, 51, 53, 55) and ra == reg:
        return "MEMORY_UPDATE_BASE_WRITE"
    if op == 31:
        xo = (word >> 1) & 1023
        rs = (word >> 21) & 31
        rb = (word >> 11) & 31
        if xo == 444 and ra == reg and rs == rb:
            return "MR_FROM_r%d" % rs
        if rt == reg or ra == reg:
            return "OTHER_X_FORM_POSSIBLE_GPR_WRITE"
    # Unmodelled instructions remain a scientific limitation: never claim
    # all-path source identity or that no writes occur, even if UNKNOWN.
    return None


def inspect_args(code: bytes, start: int, owner: str, call_pc: int):
    if (not owner.startswith(f1.ui.GOLF_PREFIX) or type(code) is not bytes
            or type(start) is not int or type(call_pc) is not int
            or start % 4 or call_pc % 4 or not start <= call_pc < start + len(code)
            or len(code) % 4):
        raise ValueError("malformed source code/owner")
    at = call_pc - start
    if base.decode_ppc_branch(call_pc, f1._word(code, at)) != (f1.DISTANCE, True):
        raise ValueError("not exact vector square-distance BL")
    lo = max(0, at - BACKWARD)
    prior = [(off, f1._word(code, off)) for off in range(lo, at, 4)]
    barriers = [i for i, (_, w) in enumerate(prior) if f1._control(w)]
    suffix = prior[barriers[-1] + 1:] if barriers else prior
    classes = {}
    for reg in (3, 4):
        candidates = [(off, kind) for off, word in suffix
                      if (kind := _gpr_write(word, reg)) is not None]
        classes[f"r{reg}_nearest_local_source"] = (
            candidates[-1][1] if candidates else UNKNOWN)
    return {
        "source_file": owner,
        "source_unit_relative_site": f"+0x{at:05X}",
        "source_backward_window_bytes": BACKWARD,
        "control_barrier_in_backward_window": bool(barriers),
        "post_barrier_instruction_count": len(suffix),
        **classes,
        "vector_pointer_provenance_or_runtime_identity_verified": False,
        "source_branch_dominance_or_fully_known_GPR_writes": False,
        "ball_pin_argument_or_distance_role_verified": False,
    }


def summarize(rows):
    if type(rows) is not list or len(rows) != f1.EXACT_CALLS:
        raise ValueError("not exact source 18 BL corpus")
    return {
        "kind": "P0-GOLF-REV1-PUBLIC-PSVEC-R3-R4-INPUT-SYNTAX",
        "game_id": "RSPE01",
        "disc_revision": 1,
        "original_private_B0_sha_checked_before_after": True,
        "public_source_index_832_units_checked": True,
        "exact_source_direct_distance_BL_count": len(rows),
        "both_local_GPR_args_syntactically_defined_count": sum(
            row["r3_nearest_local_source"] != UNKNOWN
            and row["r4_nearest_local_source"] != UNKNOWN for row in rows),
        "source_sites": rows,
        "vector_arguments_are_source_ball_and_pin_verified": False,
        "source_register_reaching_definitions_verified": False,
        "UI_result_producer_or_backing_memory_verified": False,
        "same_guest_frame_or_live_motion_verified": False,
        "physical_ball_XYZ_velocity_impact_power_score_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }


def audit(baseline: Path, root: Path):
    bank, sites = f1._source_sites(baseline, root)
    report = summarize([
        inspect_args(code, start, owner, pc)
        for code, start, owner, pc in sites])
    if base.checked_private_b0(baseline, root) != bank:
        raise ValueError("original B0 source SHA drift after read")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        root = Path(__file__).resolve().parents[2] / "Wii-AI-Golf-Data"
        report = audit(args.baseline, root)
    except (base.UntrustedInput, OSError, ValueError, TypeError,
            KeyError, AttributeError, IndexError, OverflowError):
        print("P0_VECTOR_ARGS_ABSTAIN: original B0 SHA/Rev1 or exact "
              "18 source-call geometry gate failed", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
