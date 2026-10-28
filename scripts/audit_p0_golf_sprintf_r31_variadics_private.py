#!/usr/bin/env python3
"""Private/offline Rev1 Golf sprintf r31/r5-r7 *syntactic* source triage.

Requires exact 14 prior direct PPC BL sites, original B0 manifest/SHA pre/post.
No format string, raw native word, pointer, gameplay value or private path out.
This is not a backward CFG slice or identified on-screen result state.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_golf_sprintf_arg_origins_private as prior

ui = prior.ui
base = prior.base
LOOKBACK = 0xC00          # syntactic search only, may cross function boundaries
SUFFIX = prior.WINDOW    # 0x80 bytes, after last control flow barrier
SITE_LIMIT = prior.MAX_SITES
R31 = 31
GPRS = (5, 6, 7)
UNKNOWN = "no_recognized_source_in_bounded_window"


def reg_syntax(word: int, reg: int) -> str | None:
    """Decode only conservative GPR write syntax, no dataflow claim."""
    base.ensure(type(word) is int and 0 <= word <= 0xFFFFFFFF
                and type(reg) is int and 0 <= reg < 32)
    op, rt, ra, imm = prior._d_form(word)
    if op in (14, 15) and rt == reg:
        prefix = "addi" if op == 14 else "addis"
        return f"{prefix}_from_r{ra}"
    if op in (32, 33, 34, 35, 40, 41, 42, 43) and rt == reg:
        return "integer_load_from_r" + str(ra)
    if op in (24, 25) and ra == reg:
        return "integer_immediate_logic_from_r" + str(rt)
    if op == 31:
        src = (word >> 21) & 31
        dest = (word >> 16) & 31
        rb = (word >> 11) & 31
        xo = (word >> 1) & 1023
        if xo == 444 and dest == reg and src == rb:
            return "mr_from_r" + str(src)
        if dest == reg:
            return "other_x_form_possible_destination"
    # Some legitimate GPR writes use other PPC primary/X forms.
    return None


def bounded_site(code: bytes, unit_start: int, unit_name: str,
                 call_pc: int) -> dict:
    """All offsets are PUBLIC source-object-relative; unknown means unknown."""
    base.ensure(unit_name.startswith(ui.GOLF_PREFIX)
                and type(code) is bytes and len(code) % 4 == 0
                and type(unit_start) is int and unit_start % 4 == 0
                and type(call_pc) is int and call_pc % 4 == 0
                and unit_start <= call_pc < unit_start + len(code))
    off = call_pc - unit_start
    base.ensure(base.decode_ppc_branch(call_pc,
                struct.unpack_from(">I", code, off)[0])
                == (prior.SPRINTF, True))
    previous = []
    lower = max(0, off - LOOKBACK)
    for x in range(lower, off, 4):
        previous.append((x, struct.unpack_from(">I", code, x)[0]))
    barriers = [x for x, word in previous if prior._control_barrier(word)]
    # Previous definition at most 0xC00 back. Crossing function boundary
    # possible and explicitly NOT proof of r31 reaching the call.
    r31_writes = [(x, kind) for x, word in previous
                  if (kind := reg_syntax(word, R31)) is not None]
    closest_r31 = r31_writes[-1] if r31_writes else None
    const_pattern = (len(r31_writes) >= 2
                     and r31_writes[-2][1] == "addis_from_r0"
                     and r31_writes[-1][1] == "addi_from_r31")
    if closest_r31 is None:
        r31_result = UNKNOWN
        r31_distance = None
        barrier_after_r31 = None
    else:
        r31_result = closest_r31[1]
        r31_distance = off - closest_r31[0]
        barrier_after_r31 = any(x > closest_r31[0] for x in barriers)

    # The immediate prefix is a source syntax test, not format bytes.
    # Do not resolve r31 into a static address without a CFG/function proof.
    if const_pattern:
        const_kind = "addis_r31_r0_then_addi_r31_r31_candidate"
    elif r31_writes:
        const_kind = "r31_other_or_incomplete_construction"
    else:
        const_kind = "r31_origin_not_seen"
    suffix_start = max(0, off - SUFFIX)
    last_barrier = max((x for x in barriers if x >= suffix_start),
                       default=None)
    active_start = max(suffix_start, last_barrier + 4
                       if last_barrier is not None else suffix_start)
    active = [(x, word) for x, word in previous if x >= active_start]
    args = {}
    for reg in GPRS:
        defs = [(x, kind) for x, word in active
                if (kind := reg_syntax(word, reg)) is not None]
        args[f"r{reg}_last_syntactic_def"] = defs[-1][1] if defs else UNKNOWN
    return {
        "source_file": unit_name,
        "sprintf_file_relative_site": f"+0x{off:05X}",
        "r31_last_recognized_definition_syntax": r31_result,
        "r31_definition_distance_in_bytes": r31_distance,
        "r31_constant_pair_syntax_only": const_kind,
        "control_transfer_after_candidate_r31_definition":
            barrier_after_r31,
        "recognized_control_transfers_in_0xC00_window": len(barriers),
        "r5_r6_r7_post_last_barrier_syntax": args,
        "r4_from_r31_verified_reaching_definition": False,
        "format_string_bytes_or_types_read": False,
        "function_entry_or_cfg_reaching_def_verified": False,
        "visible_hitting_green_result_verified": False,
    }


def summarize(rows: list[dict]):
    base.ensure(type(rows) is list
                and len(rows) == prior.EXPECTED_ORIGINAL_B0_SPRINTF_SITES
                and all(type(x) is dict
                        and x.get("format_string_bytes_or_types_read") is False
                        for x in rows))
    return {
        "kind": "P0-SPRINTF-R31-AND-VARIADIC-GPR-SYNTAX-V1",
        "game_id": "RSPE01",
        "disc_revision": 1,
        "original_b0_manifest_sha_verified": True,
        "exact_direct_sprintf_call_count": len(rows),
        "r31_const_pair_syntactic_candidates": sum(
            row["r31_constant_pair_syntax_only"]
            == "addis_r31_r0_then_addi_r31_r31_candidate"
            for row in rows),
        "r31_definition_not_seen_count": sum(
            row["r31_last_recognized_definition_syntax"] == UNKNOWN
            for row in rows),
        "r31_candidate_with_control_transfer_after_count": sum(
            row["control_transfer_after_candidate_r31_definition"] is True
            for row in rows),
        "r5_syntactic_definition_in_suffix_count": sum(
            row["r5_r6_r7_post_last_barrier_syntax"]["r5_last_syntactic_def"]
            != UNKNOWN for row in rows),
        "sites": rows,
        "static_format_string_or_units_identified": False,
        "ui_result_dataflow_and_backing_memory_verified": False,
        "source_control_flow_and_function_bounds_verified": False,
        "actual_ui_result_screen_event_verified": False,
        "ball_physics_xyz_velocity_contact_power_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }


def audit(baseline: Path, data_root: Path):
    bank = base.checked_private_b0(baseline, data_root)
    units = ui.golf_units(base.load_public_text_units())
    sites = []
    with bank.open("rb") as stream:
        base.ensure(stream.read(6) == base.GAME_ID)
        stream.seek(7)
        base.ensure(stream.read(1) == b"\x01")
        for start, end, name in units:
            stream.seek(start - base.MEM1_START)
            code = stream.read(end - start)
            base.ensure(len(code) == end - start and any(code))
            for unit, offset, callee, _, linked, _ in ui.classify_calls(
                    [(name, start, code)]):
                if callee == "c_sprintf" and linked:
                    sites.append(bounded_site(code, start, unit,
                                              start + offset))
    base.ensure(len(sites) == prior.EXPECTED_ORIGINAL_B0_SPRINTF_SITES)
    base.ensure(base.checked_private_b0(baseline, data_root) == bank)
    return summarize(sites)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        root = Path(__file__).resolve().parents[2] / "Wii-AI-Golf-Data"
        report = audit(args.baseline, root)
    except (base.UntrustedInput, OSError, ValueError, TypeError,
            KeyError, IndexError, AttributeError, OverflowError):
        print("P0_SPRINTF_R31_ABSTAIN: original SHA-gated source or "
              "syntactic bounded site verification failed", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
