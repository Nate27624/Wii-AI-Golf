#!/usr/bin/env python3
"""Source-gated P0: classify FPR f1 suffix after 18 exact PSVEC square-dist BLs.

Local to original preserved B0 MEM1, exact US Rev1 + original B0 manifest SHA
before/after, published Golf object .text index from #219/#256. No new shots,
Dolphin/control, memory writes, native instruction/heap/vector values, raw
floats, original paths or private hashes printed. Static syntax != execution.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_golf_result_ui_xrefs_private as ui

base = ui.base
DISTANCE = 0x800E86D0  # PSVEC square distance, PUBLIC Rev1 symbol
EXACT_CALLS = 18        # real original B0 #256 direct BL call count
FORWARD = 0x80
PPC_CODE_ALIGNMENT = 4


def _word(code: bytes, offset: int) -> int:
    if type(code) is not bytes or type(offset) is not int or (
            offset < 0 or offset % PPC_CODE_ALIGNMENT or offset + 4 > len(code)):
        raise ValueError("untrusted code window")
    return struct.unpack_from(">I", code, offset)[0]


def _control(word: int) -> str | None:
    op = word >> 26
    if op in (16, 18, 17):
        return "conditional_or_direct_control_barrier"
    if op == 19:
        xo = (word >> 1) & 1023
        if xo in (16, 50, 528):
            return "indirect_or_return_barrier"
    return None


def inspect_f1(code: bytes, start: int, owner: str, call_pc: int) -> dict:
    """First relevant post-call f1 event inside 0x80 bytes, not a CFG path.

    PPC EABI typically returns a scalar f32 in f1; this source-only helper
    does not prove that a particular instruction executes or stores the
    return of this preceding call.
    """
    if (not owner.startswith(ui.GOLF_PREFIX) or type(start) is not int
            or type(call_pc) is not int or call_pc % 4 or start % 4
            or call_pc < start or call_pc + 4 > start + len(code)
            or len(code) % 4):
        raise ValueError("untrusted public source window")
    at = call_pc - start
    if base.decode_ppc_branch(call_pc, _word(code, at)) != (DISTANCE, True):
        raise ValueError("not exact source Rev1 PSVECSquareDistance BL")
    high = min(len(code), at + 4 + FORWARD)
    kind = "NO_RECOGNIZED_F1_CONSUMER_IN_BOUNDED_SUFFIX"
    steps = 0
    for off in range(at + 4, high, 4):
        word = _word(code, off)
        steps += 1
        barrier = _control(word)
        if barrier:
            kind = "ABSTAIN_CONTROL_FLOW_BEFORE_F1_STORE"
            break
        op = word >> 26
        frt_or_frs = (word >> 21) & 31
        if op in (52, 53, 54, 55) and frt_or_frs == 1:
            kind = ("F1_STFS_SOURCE_STORE_SYNTAX" if op in (52, 53)
                    else "F1_STFD_SOURCE_STORE_SYNTAX")
            break
        if op in (48, 49, 50, 51) and frt_or_frs == 1:
            kind = "F1_OVERWRITTEN_BY_FPR_LOAD_BEFORE_LOCAL_STORE"
            break
        if op in (59, 63):
            # PPC floating op encoding is rich: f1 may be source, destination,
            # or both. Refuse to call it an observed returned value consumer.
            kind = "FPR_ARITHMETIC_OR_MOVE_UNRESOLVED"
            break
        if op in (56, 57, 60, 61):
            kind = "PAIRED_SINGLE_FPR_EFFECT_UNRESOLVED"
            break
    return {
        "source_file": owner,
        "source_unit_relative_site": f"+0x{at:05X}",
        "source_forward_window_bytes": FORWARD,
        "instructions_before_first_event": steps,
        "first_post_BL_F1_relevant_event_class": kind,
        "first_event_is_direct_F1_store_syntax": kind.startswith("F1_ST"),
        "source_D_form_store_receiver_register_proven": False,
        "F1_matches_dynamic_PSVEC_return_verified": False,
        "F1_value_is_ball_to_pin_distance_verified": False,
        "executed_in_golf_shot_or_UI_verified": False,
    }


def _source_sites(baseline: Path, root: Path):
    """Owned original B0 source gate plus exact published 18 calls, before SHA."""
    bank = base.checked_private_b0(baseline, root)
    units = ui.golf_units(base.load_public_text_units())
    sites = []
    with bank.open("rb") as stream:
        if stream.read(6) != b"RSPE01":
            raise ValueError("game ID changed")
        stream.seek(7)
        if stream.read(1) != b"\x01":
            raise ValueError("disc revision changed")
        for start, end, owner in units:
            if not (base.MEM1_START <= start < end
                    <= base.MEM1_START + base.MEM1_LEN):
                raise ValueError("public source range outside native MEM1")
            stream.seek(start - base.MEM1_START)
            code = stream.read(end - start)
            if len(code) != end - start or not any(code):
                raise ValueError("unexpected source unit")
            for source, offset, callee, _, linked, _ in ui.classify_calls(
                    [(owner, start, code)]):
                if callee == "vec_square_distance" and linked:
                    pc = start + offset
                    if base.decode_ppc_branch(pc, _word(code, offset)) != (DISTANCE, True):
                        raise ValueError("distance source link drift")
                    sites.append((code, start, source, pc))
    if len(sites) != EXACT_CALLS:
        raise ValueError("the original 18 exact PSVECSquareDistance sites changed")
    return bank, sites


def summarize(rows):
    if (type(rows) is not list or len(rows) != EXACT_CALLS
            or any(type(x) is not dict or
                   x.get("F1_value_is_ball_to_pin_distance_verified") is not False
                   for x in rows)):
        raise ValueError("invalid source results")
    kinds = sorted(set(x["first_post_BL_F1_relevant_event_class"] for x in rows))
    return {
        "kind": "P0-GOLF-REV1-PUBLIC-PSVEC-F1-POSTCALL-SYNTAX",
        "game_id": "RSPE01",
        "disc_revision": 1,
        "original_private_B0_sha_checked_before_after": True,
        "public_source_index_832_units_checked": True,
        "exact_source_direct_distance_BL_count": len(rows),
        "source_f1_store_syntax_sites": sum(
            x["first_event_is_direct_F1_store_syntax"] for x in rows),
        "event_categories": [
            {"category": kind, "site_count": sum(
                x["first_post_BL_F1_relevant_event_class"] == kind
                for x in rows)}
            for kind in kinds],
        "source_sites": rows,
        "f1_return_reaching_definition_verified": False,
        "distance_vector_arguments_or_semantics_verified": False,
        "UI_result_producer_or_backing_memory_verified": False,
        "same_guest_frame_or_live_motion_verified": False,
        "physical_ball_XYZ_velocity_impact_power_score_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }


def audit(baseline: Path, root: Path):
    bank, sites = _source_sites(baseline, root)
    report = summarize([
        inspect_f1(code, start, owner, pc)
        for code, start, owner, pc in sites])
    if base.checked_private_b0(baseline, root) != bank:
        raise ValueError("native B0 changed after read")
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
        print("P0_VECTOR_F1_ABSTAIN: original B0 / Rev1 / 18 BL source "
              "or FPR syntax gate failed", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
