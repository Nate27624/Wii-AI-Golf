#!/usr/bin/env python3
"""P0 Golf: two exact integer printf literals, coarse semantic categories only.

Read-only, US RSPE01 Rev1 original B0 source-gated by #219, reusing
#256's exact branch-free constant-chain test. No output of format
strings, instruction words, native pointers, SHA values or RAM bytes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_golf_sprintf_format_types_private as fmt

base = fmt.base
ui = fmt.ui
prior = fmt.prior
EXPECTED = frozenset((0x18EC0, 0x19B50))
GOLF_UNSPLIT = "Pack/RPSports/RPGolScene/RPGolScene_unsplit.o"

# Standalone tokens only. These are category flags, not a verified UI message.
# Only exact positive categories are exposed, never the original text.
UNIT_PATTERN = re.compile(
    r"(?<![a-z])(?:ft|feet|foot|yd|yards|yard|meters?|metres?|"
    r"centimeters?|centimetres?|cm|inches|inch)(?![a-z])",
    re.IGNORECASE,
)
DISTANCE_PATTERN = re.compile(
    r"(?<![a-z])(?:distance|dist|near|nearest|pin|cup|green|"
    r"target|landing|landed)(?![a-z])",
    re.IGNORECASE,
)
RESULT_PATTERN = re.compile(
    r"(?<![a-z])(?:result|nice|on|best|new record|success|"
    r"hit|miss)(?![a-z])", re.IGNORECASE,
)
SCORE_PATTERN = re.compile(
    r"(?<![a-z])(?:score|par|bogey|birdie|eagle|stroke|"
    r"strokes|hole)(?![a-z])", re.IGNORECASE,
)
TIMER_PATTERN = re.compile(
    r"(?<![a-z])(?:time|timer|seconds?|secs?|minutes?|"
    r"millis|milliseconds?|ms)(?![a-z])", re.IGNORECASE,
)
DEBUG_PATTERN = re.compile(
    r"(?<![a-z])(?:debug|dbg|assert|error|log|trace|"
    r"fps|frame|counter|index)(?![a-z])", re.IGNORECASE,
)

def classify_literal_bytes(raw: bytes) -> dict:
    """Zero raw text leaves this process; recognized tokens only."""
    if type(raw) is not bytes or len(raw) != fmt.MAX_TEXT:
        raise base.UntrustedInput
    nul = raw.find(b"\x00")
    if nul <= 0:
        return {"status": "unqualified_not_nul_terminated"}
    segment = raw[:nul]
    if any(c not in (9, 10, 13) and not 0x20 <= c < 0x7F for c in segment):
        return {"status": "unqualified_non_ascii"}
    literal = segment.decode("ascii")
    parent = fmt._classify_buffer(lambda _addr, _n: raw, base.MEM1_START)
    if (parent["status"] != "bounded_printable_ascii_cstring_candidate"
            or parent.get("conversion_count") != 1
            or parent.get("has_integer_conversion") is not True
            or parent.get("has_unsafe_n_conversion") is True):
        return {"status": "unqualified_non_single_int_format"}
    # Exclude conversion tokens to avoid interpreting "%d" as the English
    # word "distance"; retain only static surrounding context.
    context = re.sub(
        r"%(?:[-+ #0]*)(?:\d+|\*)?(?:\.(?:\d+|\*))?"
        r"(?:hh|h|ll|l|L|j|z|t)?[diuoxXfFeEgGaAcspn%]", " ",
        literal,
    )
    return {
        "status": "one_integer_printf_conversion_context_classified",
        "explicit_distance_unit_token": bool(UNIT_PATTERN.search(context)),
        "distance_or_target_token": bool(DISTANCE_PATTERN.search(context)),
        "result_screen_word_token": bool(RESULT_PATTERN.search(context)),
        "score_or_stroke_token": bool(SCORE_PATTERN.search(context)),
        "timer_token": bool(TIMER_PATTERN.search(context)),
        "debug_or_counter_token": bool(DEBUG_PATTERN.search(context)),
        "no_recognized_role_tokens": not any((
            UNIT_PATTERN.search(context),
            DISTANCE_PATTERN.search(context),
            RESULT_PATTERN.search(context),
            SCORE_PATTERN.search(context),
            TIMER_PATTERN.search(context),
            DEBUG_PATTERN.search(context),
        )),
        "literal_content_exposed": False,
        "source_message_semantics_verified": False,
    }

def audit(baseline: Path, data_root: Path) -> dict:
    bank = base.checked_private_b0(baseline, data_root)
    units = ui.golf_units(base.load_public_text_units())
    seen_sprintf = 0
    qualified = {}
    with bank.open("rb") as stream:
        base.ensure(stream.read(6) == base.GAME_ID)
        stream.seek(7)
        base.ensure(stream.read(1) == b"\x01")

        def read_at(addr: int, size: int) -> bytes:
            if (size != fmt.MAX_TEXT or not base.MEM1_START <= addr
                    or addr + size > fmt.MEM1_END):
                raise base.UntrustedInput
            stream.seek(addr - base.MEM1_START)
            data = stream.read(size)
            base.ensure(len(data) == size)
            return data

        for start, end, name in units:
            stream.seek(start - base.MEM1_START)
            code = stream.read(end - start)
            base.ensure(len(code) == end - start and any(code))
            for _unit, offset, callee, _, linked, _ in ui.classify_calls(
                    [(name, start, code)]):
                if callee != "c_sprintf" or not linked:
                    continue
                seen_sprintf += 1
                address, reason, _ = fmt._linear_format_address(
                    code, start, start + offset)
                if address is None:
                    continue
                base.ensure(reason == "bounded_linear_constant_candidate"
                            and name == GOLF_UNSPLIT
                            and offset in EXPECTED
                            and offset not in qualified)
                try:
                    raw = read_at(address, fmt.MAX_TEXT)
                    classified = classify_literal_bytes(raw)
                except (OSError, ValueError):
                    classified = {"status": "unreadable_candidate"}
                qualified[offset] = {
                    "source_file": name,
                    "source_relative_site": f"+0x{offset:05X}",
                    "literal_context": classified,
                    "original_b0_code_and_bank_sha_verified": True,
                    "actual_ui_render_or_runtime_execution_verified": False,
                }

    # Fail closed if earlier synthetic/source-gated B0 classification drifted.
    base.ensure(seen_sprintf == prior.EXPECTED_ORIGINAL_B0_SPRINTF_SITES)
    base.ensure(set(qualified) == EXPECTED)
    base.checked_private_b0(baseline, data_root)
    return {
        "kind": "P0-GOLF-TWO-QUALIFIED-SPRINTF-LITERAL-ROLE-TRIAGE-V1",
        "source_only_golf_rev1": True,
        "original_b0_manifest_sha_verified": True,
        "direct_sprintf_source_sites_checked": seen_sprintf,
        "strict_constant_candidates": len(qualified),
        "sites": [qualified[key] for key in sorted(qualified)],
        "static_literal_role_is_only_heuristic": True,
        "result_ui_and_backing_memory_proven": False,
        "same_guest_frame_visual_link_proven": False,
        "ball_world_xyz_velocity_power_contact_proven": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        data_root = Path(__file__).resolve().parents[2] / "Wii-AI-Golf-Data"
        report = audit(args.baseline, data_root)
    except (base.UntrustedInput, OSError, ValueError, TypeError,
            OverflowError, IndexError, KeyError, AttributeError):
        print("P0_GOLF_LITERAL_ROLE_ABSTAIN: source or original B0 not qualified",
              file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
