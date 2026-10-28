"""Identify PUBLIC source-code targets of two authenticated CFG call blockers.

Strictly a source-only next-hop study stacked on #257. Reuses #257 original
private B0 SHA/Rev1/public source/immutable #254 diagnostic helper gates.
Never prints PPC words, original bank names/paths, private hashes or heap data.
It does NOT prove that a BL ran, preserves a receiver, or returned an object.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_cache_cfg_original_b0_adapter as adapter

source = adapter.source
KIND = "P0-SANITIZED-FIRST-CACHE-RECEIVER-INTERVENING-BL-TARGETS"


class SourceFailure(Exception):
    pass


def classify(report, read_u32, public_units):
    """Only classify exactly two separately SHA-authenticated code witnesses.

    Pure analysis for fabricated testing. The caller authenticates source
    before/after and passes the checked helper report.
    """
    if (type(report) is not dict
            or report.get("kind") != "P0-SOURCE-AUTHENTICATED-ORIGINAL-B0-CACHE-CFG-ADAPTER"
            or report.get("original_B0_SHA_and_manifest_verified_before_after") is not True
            or report.get("public_Golf_source_window_gated") is not True
            or report.get("reviewed_pure_CFG_helper_commit_verified") is not True
            or report.get("runtime_cache_receiver_or_executed_writer_verified") is not False
            or report.get("training_approved") is not False):
        raise SourceFailure
    rows = report.get("source_only_two_callers")
    if type(rows) is not list or len(rows) != len(adapter.EXPECTED_CALLERS):
        raise SourceFailure
    adapter._validate_source_ownership(public_units)
    output = []
    for row, (name, entry, target_site) in zip(rows, adapter.EXPECTED_CALLERS):
        if (type(row) is not dict or row.get("public_caller") != name
                or row.get("conservative_static_cfg_status") != "ABSTAIN_SOURCE_UNRESOLVED"
                or row.get("first_abstain_reason_class") != "INTERVENING_CALL"
                or row.get("all_reaching_paths_preserve_entry_receiver") is not False
                or row.get("exact_cache_writer_callsite_reached") is not False):
            raise SourceFailure
        rel = row.get("first_source_relative_unresolved_offset")
        if (type(rel) is not str or
                not rel.startswith("+0x") or
                len(rel) != 7 or
                not all(x in "0123456789ABCDEF" for x in rel[3:])):
            raise SourceFailure
        site = entry + int(rel[3:], 16)
        if site < entry or site >= target_site or site % 4:
            raise SourceFailure
        word = read_u32(site)
        if type(word) is not int or not 0 <= word <= 0xffffffff:
            raise SourceFailure
        if word >> 26 != 18 or not word & 1:
            # A conditional linked branch is also an 'INTERVENING_CALL'
            # category, but this limited study deliberately does not map it.
            if word >> 26 == 16 and word & 1:
                direct_kind = "CONDITIONAL_LINK_UNRESOLVED"
                matched = []
            else:
                raise SourceFailure
        else:
            branch = source.decode_ppc_branch(site, word)
            if branch is None or branch[1] is not True:
                raise SourceFailure
            dest = branch[0]
            matched = [(a, b, unit) for a, b, unit in public_units
                       if a <= dest < b]
            if len(matched) > 1:
                raise SourceFailure
            direct_kind = (
                "DIRECT_BL_TARGET_IN_PUBLIC_SOURCE_UNIT" if len(matched) == 1
                else "DIRECT_BL_TARGET_OUTSIDE_PUBLIC_SOURCE_INDEX"
            )
        code_owner = matched[0][2] if matched else None
        code_relative = (
            "+0x{:04X}".format(dest - matched[0][0]) if matched else None
        )
        output.append({
            "caller": name,
            "first_unresolved_call_source_relative_offset": rel,
            "source_opcode_class": direct_kind,
            "public_direct_callee_object_file": code_owner,
            "public_callee_object_file_relative_offset": code_relative,
            "callee_public_function_symbol_verified": False,
            "callee_register_effects_or_return_r3_verified": False,
            "receiver_identity_and_runtime_call_verified": False,
        })
    return {
        "kind": KIND,
        "original_B0_full_SHA_before_after": True,
        "RSPE01_Rev1_and_public_source_units_verified": True,
        "immutable_reviewed_CFG_helper_qualified": True,
        "static_intervening_caller_count": 2,
        "callsite_results": output,
        "intervening_call_must_clobber_entry_r3_verified": False,
        "possible_callee_side_effects_remain_unresolved": True,
        "cache_writer_reachability_or_runtime_receiver_verified": False,
        "ball_world_xyz_velocity_power_impact_score_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }


def audit(session: Path, data_root: Path, helper_root: Path):
    authenticated = adapter.audit(session, data_root, helper_root)
    bank = source.checked_private_b0(session, data_root)
    public = source.load_public_text_units()
    with bank.open("rb") as f:
        def read_u32(pc):
            if (type(pc) is not int or pc % 4 != 0 or
                    not any(start <= pc < call
                            for _, start, call in adapter.EXPECTED_CALLERS)):
                raise SourceFailure
            f.seek(pc - source.MEM1_START)
            raw = f.read(4)
            if len(raw) != 4:
                raise SourceFailure
            return struct.unpack(">I", raw)[0]
        report = classify(authenticated, read_u32, public)
    if source.checked_private_b0(session, data_root) != bank:
        raise SourceFailure
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-session", type=Path, required=True)
    parser.add_argument("--helper-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, default=(
        Path(__file__).resolve().parents[2] / "Wii-AI-Golf-Data"))
    args = parser.parse_args(argv)
    try:
        report = audit(args.private_session, args.data_root, args.helper_root)
    except Exception:
        print("P0_INTERVENING_BL_ABSTAIN: source, SHA, diagnostic, opcode or "
              "public code-unit mapping failed qualification.",
              file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
