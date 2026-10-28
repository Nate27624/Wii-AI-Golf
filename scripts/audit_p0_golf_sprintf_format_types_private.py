#!/usr/bin/env python3
"""P0 source-only conservative sprintf format type probe.

A strict same-linear-segment lis/addi/r4 chain can justify *attempting* a
local read of a bounded private B0 NUL-terminated ASCII format buffer.
Only conversion categories leave the machine. No source literal text,
dynamic pointer, guest memory value, game action or training promotion.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_golf_sprintf_r31_variadics_private as upstream

base = upstream.base
ui = upstream.ui
prior = upstream.prior
MAX_BACK = upstream.LOOKBACK
MEM1_END = base.MEM1_START + base.MEM1_LEN
MAX_TEXT = 96
TARGETS = (4, 6, 31)

# PPC opcode 18/16 etc are control-transfer barriers (including non-link b).
# Treat calls as barriers; no cross-function/branch reaching-definition proof.
def signed16(word: int) -> int:
    v = word & 0xFFFF
    return v - 65536 if v & 0x8000 else v


def _potential_write(word: int, reg: int) -> bool:
    op = word >> 26
    rt = (word >> 21) & 31
    ra = (word >> 16) & 31
    # Simple D-form destination and update-form RA aliases.
    if op in (14, 15, 32, 33, 34, 35, 40, 41, 42, 43, 46) and (
            rt == reg or (op in (33, 35, 41, 43) and ra == reg)):
        return True
    if op == 46 and reg >= rt:  # lmw loads all registers from rT through r31
        return True
    if op in (20, 21, 23, 24, 25, 26, 27, 28, 29) and ra == reg:
        return True
    if op in (37, 39, 45, 49, 51, 53, 55) and ra == reg:
        return True
    # X-form destinations differ by opcode; treat rT/rA occurrences as
    # ambiguous unless the complete word is a provably benign mr source.
    if op == 31 and (rt == reg or ra == reg):
        xo = (word >> 1) & 1023
        rs = rt
        rb = (word >> 11) & 31
        if xo == 444 and rs == rb and ra != reg:
            return False
        return True
    return False


def _decode_d(word: int):
    return word >> 26, (word >> 21) & 31, (word >> 16) & 31, signed16(word)


def _linear_format_address(code: bytes, start: int, call_pc: int):
    """Return (candidate_address_or_none, reason_enum, suffix_start).

    At most 0xC00 preceding bytes. This is deliberately stricter than the
    previous heuristic; an unknown CFG path leaves the result unverified.
    """
    off = call_pc - start
    low = max(0, off - MAX_BACK)
    words = [(x, struct.unpack_from(">I", code, x)[0])
             for x in range(low, off, 4)]
    barriers = [x for x, w in words if prior._control_barrier(w)]
    begin = barriers[-1] + 4 if barriers else low
    suffix = [(x, w) for x, w in words if x >= begin]
    # Identify the exact *last* r4 definition in this control-transfer-free
    # suffix. Ignore X-form lookalikes only when they provably don't write r4.
    defs4 = [(i, w) for i, (x, w) in enumerate(suffix)
             if _potential_write(w, 4)]
    if not defs4:
        return None, "r4_origin_not_recognized", begin
    idx4, word4 = defs4[-1]
    op4, rd4, ra4, lo4 = _decode_d(word4)
    if (op4, rd4, ra4) != (14, 4, 31):
        return None, "r4_last_def_not_addi_r31", begin

    # The final def of r31 *before* r4 must be addi from r31 or r6.
    before4 = suffix[:idx4]
    defs31 = [(i, w) for i, (_, w) in enumerate(before4)
              if _potential_write(w, 31)]
    if not defs31:
        return None, "r31_definition_outside_safe_segment", begin
    idx31, word31 = defs31[-1]
    op31, rd31, ra31, lo31 = _decode_d(word31)
    if op31 != 14 or rd31 != 31 or ra31 not in (6, 31):
        return None, "r31_not_safe_addi_const_chain", begin

    # Source register of that addi must have a bounded 'lis' / addis rX,r0
    # assignment, with no *subsequent* write to that register before addi.
    src = ra31
    prior_defs = [(i, w) for i, (_, w) in enumerate(suffix[:idx31])
                  if _potential_write(w, src)]
    if not prior_defs:
        return None, "high_half_outside_safe_segment", begin
    idx_hi, word_hi = prior_defs[-1]
    op_hi, rd_hi, ra_hi, hi = _decode_d(word_hi)
    if (op_hi, rd_hi, ra_hi) != (15, src, 0):
        return None, "high_half_not_source_lis", begin

    # The use of r31 after its def and r4 after its def must not be
    # overwritten by an instruction with a recognized or ambiguous write.
    for _, word in suffix[idx31 + 1:idx4]:
        if _potential_write(word, 31):
            return None, "r31_clobber_after_const_chain", begin
    for _, word in suffix[idx4 + 1:]:
        if _potential_write(word, 4):
            return None, "r4_clobber_after_const_chain", begin

    # No claim that this format address was *executed* at runtime.
    candidate = ((hi << 16) + lo31 + lo4) & 0xFFFFFFFF
    if not (base.MEM1_START <= candidate < MEM1_END):
        return None, "candidate_pointer_outside_original_mem1", begin
    return candidate, "bounded_linear_constant_candidate", begin


def _classify_buffer(read_at, guest_addr: int) -> dict:
    """Return only NUL/ASCII/printf conversion categories, never text."""
    try:
        raw = read_at(guest_addr, MAX_TEXT)
    except (ValueError, OSError):
        return {"status": "unreadable_bounded_candidate"}
    if type(raw) is not bytes or len(raw) == 0:
        return {"status": "unreadable_bounded_candidate"}
    end = raw.find(b"\x00")
    if end < 0:
        return {"status": "no_nul_within_96_bytes"}
    data = raw[:end]
    if not data or any(byte not in (9, 10, 13) and
                       not 0x20 <= byte < 0x7F for byte in data):
        return {"status": "not_printable_ascii_cstring"}
    literal = data.decode("ascii")
    # Do not print raw literal. This rejects unknown extension formats.
    tokens = re.findall(
        r'%(?:[-+ #0]*)(?:\d+|\*)?(?:\.(?:\d+|\*))?'
        r'(?:hh|h|ll|l|L|j|z|t)?([diuoxXfFeEgGaAcspn%])', literal
    )
    conversions = [token for token in tokens if token != "%"]
    return {
        "status": "bounded_printable_ascii_cstring_candidate",
        "has_integer_conversion": any(ch in "diuoxXc" for ch in conversions),
        "has_float_conversion": any(ch in "fFeEgGaA" for ch in conversions),
        "has_string_conversion": "s" in conversions,
        "has_pointer_conversion": "p" in conversions,
        "has_unsafe_n_conversion": "n" in conversions,
        "conversion_count": len(conversions),
        "literal_content_exposed": False,
    }


def examine(code: bytes, unit_start: int, source_file: str,
            call_pc: int, read_at) -> dict:
    base.ensure(source_file.startswith(ui.GOLF_PREFIX)
                and type(code) is bytes and len(code) % 4 == 0
                and type(unit_start) is int and type(call_pc) is int
                and call_pc % 4 == 0
                and unit_start <= call_pc < unit_start + len(code)
                and base.decode_ppc_branch(
                    call_pc,
                    struct.unpack_from(">I", code, call_pc - unit_start)[0]
                ) == (prior.SPRINTF, True))
    candidate, reason, _ = _linear_format_address(
        code, unit_start, call_pc)
    result = {
        "source_file": source_file,
        "sprintf_site_file_relative": f"+0x{call_pc - unit_start:05X}",
        "static_format_candidate_status": reason,
        "format_buffer_class": {"status": "not_qualified"},
        "format_source_or_cfg_proven": False,
        "visible_result_or_backing_state_verified": False,
    }
    if candidate is not None:
        result["format_buffer_class"] = _classify_buffer(read_at, candidate)
    return result


def summarize(rows: list[dict]) -> dict:
    base.ensure(type(rows) is list
                and len(rows) == prior.EXPECTED_ORIGINAL_B0_SPRINTF_SITES)
    return {
        "kind": "P0-SPRINTF-BOUNDED-FORMAT-TYPES-V1",
        "game_id": "RSPE01",
        "disc_revision": 1,
        "source_14_exact_bl_and_original_b0_sha_verified": True,
        "sites": rows,
        "bounded_linear_constant_candidates": sum(
            r["static_format_candidate_status"]
            == "bounded_linear_constant_candidate" for r in rows),
        "candidate_printf_numeric_type_count": sum(
            bool(r["format_buffer_class"].get("has_integer_conversion") or
                 r["format_buffer_class"].get("has_float_conversion"))
            for r in rows),
        "format_literal_address_or_cfg_proven": False,
        "hitting_green_result_display_or_backing_state_verified": False,
        "guest_frame_or_visual_event_verified": False,
        "ball_xyz_velocity_power_impact_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }


def audit(baseline: Path, data_root: Path):
    bank = base.checked_private_b0(baseline, data_root)
    units = ui.golf_units(base.load_public_text_units())
    rows = []
    with bank.open("rb") as stream:
        base.ensure(stream.read(6) == base.GAME_ID)
        stream.seek(7)
        base.ensure(stream.read(1) == b"\x01")

        def read_at(addr, length):
            if not (base.MEM1_START <= addr
                    and addr + length <= MEM1_END):
                raise ValueError("bounded read outside original B0 bank")
            stream.seek(addr - base.MEM1_START)
            data = stream.read(length)
            if len(data) != length:
                raise ValueError("short bounded string read")
            return data

        for start, end, name in units:
            stream.seek(start - base.MEM1_START)
            code = stream.read(end - start)
            base.ensure(len(code) == end - start and any(code))
            for unit, offset, callee, _, linked, _ in ui.classify_calls(
                    [(name, start, code)]):
                if callee == "c_sprintf" and linked:
                    rows.append(examine(code, start, unit, start + offset,
                                        read_at))
    base.ensure(len(rows) == prior.EXPECTED_ORIGINAL_B0_SPRINTF_SITES)
    base.ensure(base.checked_private_b0(baseline, data_root) == bank)
    return summarize(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        root = Path(__file__).resolve().parents[2] / "Wii-AI-Golf-Data"
        report = audit(args.baseline, root)
    except (base.UntrustedInput, OSError, ValueError, TypeError,
            IndexError, KeyError, AttributeError, OverflowError):
        print("P0_SPRINTF_FORMAT_ABSTAIN: original B0 or strict source "
              "classification not qualified", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
