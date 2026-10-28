#!/usr/bin/env python3
"""Offline direct PPC callsite audit for the Rev1 ball XYZ writer/readers.

Uses only ORIGINAL SHA256-verified private B0 MEM1. No Dolphin, RAM
modification, native code bytes, float words, pointer addresses or uploads.
Branch calls are static edges, NOT evidence the game invoked them in flight.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

GAME_ID = b"RSPE01"
MEM1_START = 0x80000000
MEM1_LEN = 0x01800000
SHA = re.compile(r"^[a-fA-F0-9]{64}$")

# Published object-file Rev1 splits, NOT heap addresses, from
# doldecomp/ogws/config/RSPE01_01/splits.txt
UNITS = (
    ("RPGolMain", 0x8028E098, 0x8028E900),
    ("RPGolFieldManager", 0x80290B44, 0x80294184),
    ("RPGolMapObjBall", 0x80296FD8, 0x8029B240),
    ("RPGolSimulateManager", 0x8029B240, 0x8029BBB4),
    ("RPGolPlayer", 0x8029E62C, 0x802A2210),
    ("RPGolPlayerManager", 0x802A2210, 0x802A3560),
)
# Three source-identified position/dataflow routines from S002 #162/#183.
# A region may be a function *interior*, so BL==0 does not establish 'unused'.
# Boundaries are corroborated by public ogws RSPE01_01 symbols.txt.
# A BL to a FUNCTION ENTRY of a function containing stores does not prove
# those internal conditional stores executed (especially during flight).
TARGETS = (
    ("player_to_ball_translation_write", 0x802A0318, 0x802A0674,
     "fn_802A0318 8-byte thunk and fn_802A0320 contain +0x0388..03C8 position stores"),
    ("ball_to_player_position_read", 0x8029F0A0, 0x8029F41C,
     "fn_8029F0A0 contains +0xF300..F31C ball-to-player reads"),
    ("ball_unit_goal_cache_update", 0x80299C70, 0x8029A038,
     "fn_80299C70 contains +0xCC/F0/FC position-cache update paths"),
    ("field_target_or_pin_position", 0x80292294, 0x802922B4,
     "fn_80292294 returns target or pin translation pointer"),
    ("field_start_position_getter", 0x802922EC, 0x802922F8,
     "fn_802922EC returns current-start translation pointer"),
)
# Exact function starts (source addresses only), not all possible entries.
FUNCTION_ENTRY_POINTS = {
    "player_to_ball_translation_write": (0x802A0318, 0x802A0320),
    "ball_to_player_position_read": (0x8029F0A0,),
    "ball_unit_goal_cache_update": (0x80299C70,),
    "field_target_or_pin_position": (0x80292294,),
    "field_start_position_getter": (0x802922EC,),
}
# Published ogws Rev1 function entries containing our first-hop BL callsites.
# A second hop is still STATIC source reachability, never an executed frame.
UPSTREAM_ENTRIES = (
    ("player_manager_short_entry_caller", 0x802A28DC),
    ("player_manager_main_writer_caller", 0x802A30F8),
    ("ball_unit_cache_caller_a", 0x80299ACC),
    ("ball_unit_cache_caller_b", 0x80299C20),
)
# Limit output to a few source offsets per unit. These are CODE offsets only.
OUTPUT_CALLSITE_LIMIT = 16

# Immutable PUBLIC source ownership map from ogws RSPE01_01 splits.txt.
# Only code-unit metadata, not private game bytes/heap addresses.
PUBLIC_SPLITS_SHA = "df4085de5285b0d188fdfec8c097b301382263d3"
PUBLIC_INDEX = (Path(__file__).resolve().parents[1] /
                "research" / "source_maps" / "RSPE01_01_public_text_units.json")
PUBLIC_UNIT_COUNT = 832


class UntrustedInput(Exception):
    """Does not echo a private filename/hash/native byte value."""


def ensure(ok: bool) -> None:
    if not ok:
        raise UntrustedInput


def source_unit(pc: int) -> tuple[str, int] | None:
    for name, lo, hi in UNITS:
        if lo <= pc < hi:
            return name, pc - lo
    return None


def decode_ppc_branch(pc: int, word: int) -> tuple[int, bool] | None:
    """Decode only PowerPC unconditional b/bl (major op 18), not bc/blr/bctr."""
    if type(word) is not int or (word >> 26) != 18:
        return None
    immediate = word & 0x03FFFFFC  # 24-bit LI with bottom two bits zero
    if immediate & 0x02000000:  # 26-bit sign extension
        immediate -= 0x04000000
    absolute = (word & 2) != 0
    target = (immediate if absolute else pc + immediate) & 0xFFFFFFFF
    link = bool(word & 1)
    return target, link


def source_thunk_forwards_to_writer(data: bytes, start: int) -> bool | None:
    """Check 8-byte fn_802A0318 thunk for nonlink b to fn_802A0320.

    Returns None on partial synthetic windows; never infer a thunk alias from
    a nearby address without an actual PPC branch in the verified executable.
    """
    thunk = 0x802A0318
    main = 0x802A0320
    if start > thunk or start + len(data) < main:
        return None
    return any(
        decode_ppc_branch(pc, struct.unpack_from(">I", data, pc - start)[0])
        == (main, False)
        for pc in (thunk, thunk + 4)
    )


def classify_short_writer_entry(data: bytes, start: int) -> str:
    """Conservatively classify the 8-byte fn_802A0318 entry's transfer path.

    A lack of a direct 'b fn_802A0320' does NOT imply there is no
    straight-line fallthrough: 0x802A0320 is exactly its next address.
    This inspects two native PPC words without returning instruction bytes.
    """
    entry, next_entry = 0x802A0318, 0x802A0320
    if start > entry or start + len(data) < next_entry:
        return "not_captured"
    words = struct.unpack_from(">II", data, entry - start)
    if 0 in words:
        return "unclassified_zero_word"
    for delta, word in zip((0, 4), words):
        pc = entry + delta
        op = word >> 26
        if op == 18:
            decoded = decode_ppc_branch(pc, word)
            if decoded is None:
                return "unclassified"
            dest, link = decoded
            if link:
                # A BL can return to a following instruction; call effects
                # may change control before any adjacent fallthrough.
                return "linked_call_before_entry_end_unresolved"
            return ("direct_branch_into_main_writer_entry" if
                    dest == next_entry else "unconditional_branch_elsewhere")
        if op == 16:
            return "conditional_branch_or_fallthrough_unresolved"
        if op == 19 and ((word >> 1) & 0x3FF) in (16, 50, 528):
            return "return_exception_or_indirect_branch"
        if op == 17:
            return "system_call_unresolved"
    return "straightline_fallthrough_to_adjacent_entry_candidate"


def short_entry_unconditional_destination(data: bytes, start: int) -> dict:
    """Decode first control-transfer in 8-byte 0x802A0318 function.

    Report source-code UNIT-relative addresses, never original native words,
    raw runtime pointers, hashes or private paths. This is static PPC only.
    """
    entry = 0x802A0318
    if start > entry or start + len(data) < entry + 8:
        return {"found": False, "reason": "not_captured"}
    for index in range(2):
        pc = entry + 4 * index
        word = struct.unpack_from(">I", data, pc - start)[0]
        branch = decode_ppc_branch(pc, word)
        if branch is None:
            continue
        dest, link = branch
        if link:
            return {"found": False, "reason": "linked_call_not_direct_jump"}
        unit = source_unit(dest)
        if unit is None:
            return {
                "found": True,
                "instruction_index": index,
                "destination_in_scanned_golf_units": False,
                "destination_source_unit": None,
                "destination_source_relative_offset": None,
                "is_main_writer_function_entry": False,
                "is_main_writer_function_interior": False,
            }
        return {
            "found": True,
            "instruction_index": index,
            "destination_in_scanned_golf_units": True,
            "destination_source_unit": unit[0],
            "destination_source_relative_offset": f"+0x{unit[1]:04X}",
            "is_main_writer_function_entry": dest == 0x802A0320,
            "is_main_writer_function_interior": 0x802A0320 < dest < 0x802A0674,
        }
    return {"found": False, "reason": "no_direct_unconditional_branch"}


def load_public_text_units(file: Path = PUBLIC_INDEX) -> tuple[tuple[int, int, str], ...]:
    """Load version-pinned source-only ogws .text splits with strict fail-close."""
    try:
        ensure(file.is_file() and not file.is_symlink() and
               0 < file.stat().st_size <= 128 * 1024)
        payload = json.loads(file.read_text("utf-8"))
        ensure(isinstance(payload, dict) and
               payload.get("kind") == "PUBLIC-RSPE01-REV1-TEXT-OBJECT-SPLITS" and
               payload.get("game_id") == "RSPE01" and
               payload.get("disc_revision") == 1 and
               payload.get("source_repo") == "doldecomp/ogws" and
               payload.get("source_file") == "config/RSPE01_01/splits.txt" and
               payload.get("source_blob_sha") == PUBLIC_SPLITS_SHA)
        rows = payload.get("intervals")
        ensure(type(rows) is list and len(rows) == PUBLIC_UNIT_COUNT)
        tuples = []
        previous_end = 0
        for item in rows:
            ensure(type(item) is list and len(item) == 3)
            a, b, name = item
            ensure(type(a) is int and type(b) is int and
                   0x80000000 <= a < b <= 0x81000000 and a % 4 == 0 and
                   b % 4 == 0 and a >= previous_end and
                   type(name) is str and 1 <= len(name) <= 180 and
                   name.endswith((".cpp", ".c", ".S", ".s", ".o")))
            tuples.append((a, b, name))
            previous_end = b
        for _name, start, end in UNITS:
            ensure(any(a <= start and end <= b for a, b, _n in tuples))
        return tuple(tuples)
    except (OSError, TypeError, KeyError, ValueError, AttributeError):
        raise UntrustedInput from None


def public_branch_destination(data: bytes, start: int,
                              intervals: tuple[tuple[int, int, str], ...]) -> dict:
    """Classify the actual 2-instruction PPC jump by PUBLIC code unit only."""
    entry = 0x802A0318
    if start > entry or start + len(data) < entry + 8:
        return {"public_code_owner_found": False, "reason": "entry_not_captured"}
    jump = short_entry_unconditional_destination(data, start)
    if jump.get("found") is not True:
        return {"public_code_owner_found": False,
                "reason": "no_direct_nonlink_unconditional_branch"}
    pc = entry + 4 * jump["instruction_index"]
    word = struct.unpack_from(">I", data, pc - start)[0]
    decoded = decode_ppc_branch(pc, word)
    ensure(decoded is not None and decoded[1] is False)
    dest = decoded[0]
    for a, b, name in intervals:
        if a <= dest < b:
            return {
                "public_code_owner_found": True,
                "destination_public_source_file": name,
                "destination_public_source_relative_offset": f"+0x{dest-a:04X}",
                "within_original_six_golf_units": source_unit(dest) is not None,
                "source_execution_during_shot_verified": False,
            }
    return {
        "public_code_owner_found": False,
        "reason": "outside_all_832_published_rev1_text_units",
        "source_execution_during_shot_verified": False,
    }


def summarize_code(data: bytes, start: int, *, maximum: int = OUTPUT_CALLSITE_LIMIT) -> dict:
    ensure(start % 4 == 0 and len(data) % 4 == 0 and 0 <= maximum <= 32)
    # Full B0 windows are read as one continuous source-only .text range.
    edges = {name: [] for name, *_ in TARGETS}
    upstream = {name: [] for name, _ in UPSTREAM_ENTRIES}
    for offset in range(0, len(data), 4):
        pc = start + offset
        unit = source_unit(pc)
        if unit is None:
            continue  # other code is deliberately outside scope
        decoded = decode_ppc_branch(pc, struct.unpack_from(">I", data, offset)[0])
        if decoded is None:
            continue
        dest, link = decoded
        if link:
            for source_name, entry in UPSTREAM_ENTRIES:
                if dest == entry:
                    upstream[source_name].append((unit[0], unit[1]))
        for name, low, high, _meaning in TARGETS:
            if low <= dest < high:
                # Only static SOURCE relative code offsets and branch types.
                edges[name].append((unit[0], unit[1], link, dest - low))
    results = []
    for name, low, high, meaning in TARGETS:
        hits = edges[name]
        unit_summaries = []
        for unit_name, _a, _b in UNITS:
            from_unit = [h for h in hits if h[0] == unit_name]
            if not from_unit:
                continue
            unit_summaries.append({
                "source_unit": unit_name,
                "direct_bl_count": sum(h[2] for h in from_unit),
                "nonlink_branch_count": sum(not h[2] for h in from_unit),
                "source_relative_callsite_offsets": [
                    f"+0x{h[1]:04X}" for h in from_unit if h[2]
                ][:maximum],
                "target_window_relative_offsets": [
                    f"+0x{h[3]:03X}" for h in from_unit if h[2]
                ][:maximum],
                "direct_bl_at_known_function_entry_count": sum(
                    h[2] and low + h[3] in FUNCTION_ENTRY_POINTS[name]
                    for h in from_unit
                ),
                "direct_bl_to_function_interior_count": sum(
                    h[2] and low + h[3] not in FUNCTION_ENTRY_POINTS[name]
                    for h in from_unit
                ),
                "additional_callsites_omitted": max(
                    0, sum(h[2] for h in from_unit) - maximum),
            })
        results.append({
            "target": name,
            "source_meaning_hypothesis": meaning,
            "window_size_bytes": high - low,
            "direct_bl_into_window_count": sum(h[2] for h in hits),
            "direct_bl_at_known_function_entry_count": sum(
                h[2] and low + h[3] in FUNCTION_ENTRY_POINTS[name]
                for h in hits
            ),
            "direct_bl_to_function_interior_count": sum(
                h[2] and low + h[3] not in FUNCTION_ENTRY_POINTS[name]
                for h in hits
            ),
            "nonlink_branches_into_window_count": sum(not h[2] for h in hits),
            "source_units": unit_summaries,
            "no_direct_call_cannot_disprove_indirect_dispatch": True,
        })
    upstream_results = []
    for caller_name, _entry in UPSTREAM_ENTRIES:
        hits = upstream[caller_name]
        units = []
        for unit_name, _a, _b in UNITS:
            found = [off for name, off in hits if name == unit_name]
            if found:
                units.append({
                    "source_unit": unit_name,
                    "direct_bl_count": len(found),
                    "source_relative_callsite_offsets": [
                        f"+0x{off:04X}" for off in found[:maximum]
                    ],
                    "additional_callsites_omitted": max(0, len(found) - maximum),
                })
        upstream_results.append({
            "callee": caller_name,
            "direct_bl_at_exact_entry_count": len(hits),
            "source_units": units,
            "indirect_and_other_unit_callers_unresolved": True,
        })
    return {
        "kind": "S002-REV1-BALL-XYZ-SOURCE-CALLER-AUDIT",
        "schema_version": 1,
        "game_id": "RSPE01",
        "disc_revision": 1,
        "code_scan_limited_to_published_golf_source_units": True,
        "direct_ppc_b_bl_only": True,
        "source_function_boundaries": "public_ogws_RSPE01_01_symbols_txt",
        "short_player_writer_entry_thunk_branches_to_main_function":
            source_thunk_forwards_to_writer(data, start),
        "short_writer_entry_control_flow_class":
            classify_short_writer_entry(data, start),
        "short_writer_entry_direct_branch_destination":
            short_entry_unconditional_destination(data, start),
        "upstream_function_entry_calls": upstream_results,
        "upstream_calls_do_not_prove_actual_game_update": True,
        "source_function_call_does_not_prove_conditional_stores_executed": True,
        "conditional_indirect_and_dynamic_calls_unresolved": True,
        "source_scan_word_count": sum((hi - lo) // 4 for _, lo, hi in UNITS),
        "targets": results,
        "executed_during_actual_shot_verified": False,
        "source_receiver_is_visible_active_ball_verified": False,
        "real_inflight_ball_world_xyz_verified": False,
        "same_guest_frame_verified": False,
        "ball_velocity_verified": False,
        "approved_for_model_training": False,
        "allowed_to_publish": False,
        "github_observation": "NOT_UPLOADED_S000_S002_ADAPTER_MISSING",
    }


def checked_private_b0(session: Path, data_root: Path) -> Path:
    ensure(data_root.name == "Wii-AI-Golf-Data" and
           data_root.is_dir() and not data_root.is_symlink())
    ensure(session.is_dir() and not session.is_symlink()
           and session.resolve().is_relative_to(data_root.resolve())
           and session != data_root)
    manifest = session / "checkpoint-manifest-PRIVATE.json"
    ensure(manifest.is_file() and not manifest.is_symlink()
           and 0 < manifest.stat().st_size <= 1024 * 1024)
    try:
        payload = json.loads(manifest.read_text("utf-8-sig"))
    except (UnicodeError, ValueError):
        raise UntrustedInput from None
    ensure(payload.get("kind") == "local-private-golf-paired-checkpoints"
           and payload.get("schema_version") == 1
           and isinstance(payload.get("checkpoints"), dict))
    b0 = payload["checkpoints"].get("B0")
    ensure(isinstance(b0, dict) and b0.get("phase_operator_label") == "idle_baseline"
           and b0.get("native_sizes_valid") is True
           and b0.get("scene_source_chain_gated") is True
           and b0.get("operator_reports_gui_paused") is True
           and b0.get("observed_game_mode") == 4)
    checksums = b0.get("sha256")
    ensure(isinstance(checksums, dict))
    expected = checksums.get("MEM1")
    ensure(isinstance(expected, str) and SHA.fullmatch(expected) is not None)
    bank = session / "B0-MEM1.bin"
    ensure(bank.is_file() and not bank.is_symlink()
           and bank.stat().st_size == MEM1_LEN)
    digest = hashlib.sha256()
    with bank.open("rb") as fh:
        for part in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(part)
    ensure(digest.hexdigest() == expected.lower())
    return bank


def audit(session: Path, data_root: Path) -> dict:
    file = checked_private_b0(session, data_root)
    with file.open("rb") as f:
        ensure(f.read(8)[:6] == GAME_ID)
        f.seek(7)
        ensure(f.read(1) == b"\x01")
        lo = min(a for _, a, _ in UNITS)
        hi = max(b for _, _, b in UNITS)
        f.seek(lo - MEM1_START)
        block = f.read(hi - lo)
        ensure(len(block) == hi - lo)
        # Some genuine instruction words must occur in ALL three source sites.
        for _, left, right, _ in TARGETS[:3]:
            region = block[left - lo:right - lo]
            ensure(len(region) == right - left and
                   any(region[i:i+4] != b"\x00\x00\x00\x00"
                       for i in range(0, len(region), 4)))
        result = summarize_code(block, lo)
        source_units = load_public_text_units()
        result["short_writer_entry_public_source_destination"] = (
            public_branch_destination(block, lo, source_units)
        )
        result["public_rev1_text_split_index"] = {
            "public_source": "doldecomp/ogws RSPE01_01 splits.txt",
            "source_blob_sha_matches_pinned_public_index": True,
            "text_unit_count": len(source_units),
            "private_native_data_in_public_index": False,
        }
    result["native_source_b0_sha256_verified"] = True
    result["capture_phase_is_idle_not_flight"] = True
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default = Path(__file__).resolve().parents[2] / "Wii-AI-Golf-Data"
    parser.add_argument("--data-root", type=Path, default=default)
    parser.add_argument("--private-session", type=Path)
    opts = parser.parse_args(argv)
    session = opts.private_session or opts.data_root / "ball-study-20261027-212633"
    try:
        safe = audit(session, opts.data_root)
    except (OSError, ValueError, TypeError, AttributeError, KeyError,
            UntrustedInput):
        print("P0 XYZ SOURCE CALLER AUDIT: ABSTAIN; native source, manifest or "
              "private path failed a safety gate. No RAM values printed.",
              file=sys.stderr)
        return 2
    print(json.dumps(safe, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
