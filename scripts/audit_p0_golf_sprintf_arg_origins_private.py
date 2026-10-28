#!/usr/bin/env python3
"""P0: source-only syntactic argument origins near exact Golf sprintf BLs.

This does NOT identify the Hitting-the-Green UI distance producer.
Bounds all source reads to published Rev1 golf code units; fails closed on
original private B0 manifest and SHA before/after. Emits no PPC words,
addresses of dynamic objects, format-string contents, raw memory or game data.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_golf_result_ui_xrefs_private as ui

base = ui.base
SPRINTF = 0x800B75D8  # exact RSPE01 Rev1 public map entry; not an identified UI.
WINDOW = 0x80         # backward source syntax only; not a true function/CFG bound
MAX_SITES = 20
EXPECTED_ORIGINAL_B0_SPRINTF_SITES = 14


def _d_form(word):
    return ((word >> 26) & 63, (word >> 21) & 31,
            (word >> 16) & 31, word & 0xFFFF)


def _reg_def_class(word, reg):
    """Categorize only selected PPC syntax that MAY define GPR r3 or r4."""
    op, rt, ra, _ = _d_form(word)
    if op == 14 and rt == reg:
        return f"addi_from_r{ra}"
    if op == 15 and rt == reg:
        return f"addis_from_r{ra}"
    if op in (24, 25) and ra == reg:
        return f"ori_or_oris_from_r{rt}"
    if op in (32, 33) and rt == reg:
        return f"lwz_from_r{ra}"
    if op in (34, 35) and rt == reg:
        return f"lbz_from_r{ra}"
    if op in (40, 41, 42, 43) and rt == reg:
        return f"lhz_or_lha_from_r{ra}"
    if op == 31:
        xo = (word >> 1) & 1023
        rs = (word >> 21) & 31
        dest = (word >> 16) & 31
        rb = (word >> 11) & 31
        if xo == 444 and dest == reg and rb == rs:
            return f"mr_from_r{rs}"
        if dest == reg:
            return "other_X_form_possible_destination"
    return None


def _control_barrier(word):
    """Unknown control flow invalidates a linear reaching-definition claim."""
    op = (word >> 26) & 63
    if op in (16, 17, 18):
        return True
    if op == 19:
        xo = (word >> 1) & 1023
        if xo in (16, 50, 528):
            return True
    return False


def _fp_class(word):
    op = (word >> 26) & 63
    if op in (48, 49, 50, 51, 56, 57):
        return "fpr_memory_load_syntax"
    if op in (52, 53, 54, 55, 60, 61):
        return "fpr_memory_store_syntax"
    if op in (59, 63):
        return "fpr_op_syntax"
    return None


def local_sprintf_syntax(data: bytes, start: int, source_file: str,
                         call_pc: int):
    """Analyze <=0x80 bytes preceding a validated exact BL to sprintf.

    Earlier register writes separated by a branch/call are not credible
    straight-line sources. Even postbarrier nearest defs are SYNTAX ONLY.
    """
    base.ensure(source_file.startswith(ui.GOLF_PREFIX)
                and type(data) is bytes and len(data) % 4 == 0
                and type(start) is int and start % 4 == 0
                and type(call_pc) is int and call_pc % 4 == 0
                and start <= call_pc < start + len(data))
    offset = call_pc - start
    instruction = struct.unpack_from(">I", data, offset)[0]
    base.ensure(base.decode_ppc_branch(call_pc, instruction)
                == (SPRINTF, True))
    left = max(0, offset - WINDOW)
    prior = [(start + x, struct.unpack_from(">I", data, x)[0])
             for x in range(left, offset, 4)]
    # Break at the last branch/call/return in the local syntactic window.
    barriers = [i for i, (_, word) in enumerate(prior)
                if _control_barrier(word)]
    after = prior[barriers[-1] + 1:] if barriers else prior
    nearest = {}
    for _, word in after:
        for reg in (3, 4):
            kind = _reg_def_class(word, reg)
            if kind:
                nearest[reg] = kind
    fp = Counter(kind for _, word in after
                 if (kind := _fp_class(word)) is not None)
    direct = []
    for _, word in after:
        branch = base.decode_ppc_branch(0, word)
        if branch and branch[1]:
            direct.append("direct_link_barrier")  # defensive: should be none
    # A nearby FPR operation is NOT necessarily an argument to sprintf.
    has_float_syntax = (
        fp["fpr_memory_load_syntax"] > 0 or
        fp["fpr_op_syntax"] > 0
    )
    return {
        "source_file": source_file,
        "sprintf_site_file_relative": f"+0x{offset:05X}",
        "source_window_bytes_examined": offset - left,
        "control_barrier_seen_before_call": bool(barriers),
        "post_last_barrier_instructions": len(after),
        "output_buffer_r3_last_syntactic_definition": nearest.get(
            3, "not_recognized_in_bounded_straightline_suffix"),
        "format_pointer_r4_last_syntactic_definition": nearest.get(
            4, "not_recognized_in_bounded_straightline_suffix"),
        "fpr_load_class_count": fp["fpr_memory_load_syntax"],
        "fpr_store_class_count": fp["fpr_memory_store_syntax"],
        "fpr_op_class_count": fp["fpr_op_syntax"],
        "nearby_fpr_activity_possible_numeric_format_lead": has_float_syntax,
        "format_string_literal_or_specifiers_decoded": False,
        "register_reaching_definition_or_runtime_execution_proven": False,
        "output_text_is_hitting_the_green_distance_proven": False,
    }


def summarize(rows):
    base.ensure(type(rows) is list and 0 < len(rows) <= MAX_SITES)
    return {
        "kind": "P0-GOLF-SPRINTF-SOURCE-ARGUMENT-TRIAGE-V1",
        "game_id": "RSPE01",
        "disc_revision": 1,
        "original_b0_canonical_sha_verified": True,
        "exact_sprintf_direct_bl_sites": len(rows),
        "source_only_site_syntax": rows,
        "sites_with_nearby_fpr_activity": sum(
            x["nearby_fpr_activity_possible_numeric_format_lead"]
            for x in rows),
        "sites_with_postbarrier_format_r4_def": sum(
            x["format_pointer_r4_last_syntactic_definition"]
            != "not_recognized_in_bounded_straightline_suffix"
            for x in rows),
        "source_r4_is_verified_format_literal": False,
        "ui_render_call_link_verified": False,
        "displayed_result_producer_verified": False,
        "result_distance_memory_state_verified": False,
        "same_guest_frame_or_visual_label_verified": False,
        "ball_xyz_velocity_power_impact_units_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }


def audit(session: Path, data_root: Path):
    # Existing source/SHA gates from #219, not a new manifest parser.
    bank = base.checked_private_b0(session, data_root)
    units = ui.golf_units(base.load_public_text_units())
    sites = []
    with bank.open("rb") as fh:
        base.ensure(fh.read(6) == base.GAME_ID)
        fh.seek(7)
        base.ensure(fh.read(1) == b"\x01")
        for start, end, source_file in units:
            fh.seek(start - base.MEM1_START)
            code = fh.read(end - start)
            base.ensure(len(code) == end - start and any(code))
            for row in ui.classify_calls([(source_file, start, code)]):
                unit, offset, callee, _category, linked, _pc = row
                if callee == "c_sprintf" and linked:
                    sites.append(local_sprintf_syntax(
                        code, start, unit, start + offset))
    # Fail closed if source changed or the caller corpus differs from the
    # operator's original #256 14-direct-BL observation.
    base.ensure(len(sites) == EXPECTED_ORIGINAL_B0_SPRINTF_SITES)
    base.checked_private_b0(session, data_root)
    return summarize(sites)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        data_root = Path(__file__).resolve().parents[2] / "Wii-AI-Golf-Data"
        result = audit(args.baseline, data_root)
    except (base.UntrustedInput, OSError, ValueError, TypeError, IndexError,
            KeyError, AttributeError, OverflowError):
        print("P0_SPRINTF_ARG_ABSTAIN: original source, callsite set or "
              "canonical B0 integrity not verified", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
