"""P0 offline source-gated join: preserved seven banks -> outer and inner PPC.

Combines #231 canonical 14-bank SHA/Rev1 reader, #254 inner caller CFG and
#255 outer caller source hints. Neither helper authenticates native bytes:
this owner-reviewed runner does so before/after. No Dolphin, game inputs,
file writes, private values/hashes/pointers or raw code words in stdout.
Source-only chains do NOT establish executed receiver or rendered-ball role.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
import hashlib
import importlib.util
import json
import mmap
from pathlib import Path
import sys

import review_p0_outer_receiver_argument_source as outer

FIRST_SOURCE_PC = 0x80299EE4
GLOBAL_LOAD_PC = 0x80299CD0
TRANSLATION_PC = 0x80299CD4
# Source-proven r13 FieldManager load in #240. Cannot infer from r13
# without the exact PPC anchor.
FIELD_SDA_DISPLACEMENT = -23320
CAPTURES = tuple(range(1, 8))


def _source_regions(cfg):
    # Exact bounded source ranges, not function extents. These source
    # instructions MUST match across the seven original paired memories.
    regions = [(entry, entry + outer.WINDOW)
               for _, entry, _, _, _ in outer.SOURCES]
    regions.extend((entry, call + 4) for _, entry, call in cfg.CALLERS)
    regions.extend((pc, pc + 4) for pc in
                   (FIRST_SOURCE_PC, GLOBAL_LOAD_PC, TRANSLATION_PC))
    return tuple(regions)


def _signed16(x):
    return x - 65536 if x & 0x8000 else x


def _source_global_slot(read, roster):
    """Local address stays private; all three exact Rev1 PPC forms gated."""
    anchor = read(FIRST_SOURCE_PC)
    load = read(GLOBAL_LOAD_PC)
    follow = read(TRANSLATION_PC)
    d = lambda w: ((w >> 26) & 63, (w >> 21) & 31,
                   (w >> 16) & 31, _signed16(w & 65535))
    if d(anchor) != (32, 3, 13, FIELD_SDA_DISPLACEMENT):
        raise ValueError("source FieldManager SDA anchor changed")
    if d(follow) != (32, 3, 3, 0x4C):
        raise ValueError("source global translation follow changed")
    op, rt, ra, imm = d(load)
    if (op, rt, ra) != (32, 3, 13):
        raise ValueError("source global load form changed")
    slot = roster.GOLF_FIELD_STATIC - FIELD_SDA_DISPLACEMENT + imm
    if roster._bank(slot, 4) != "MEM1":
        raise ValueError("source global slot out of native MEM1")
    return slot, imm


def _native_roster_global_gate(rd, seven, slot):
    """Selected 4-slot roster and fifth global object identity only.

    This does NOT link either PPC caller's incoming r3 to any real object.
    """
    roster = seven.roster
    sample = seven._get(rd)
    read = rd.u32
    pm = read(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    if roster._bank(pm, 4 + 4 * roster.ROSTER_STRIDE) != "MEM2":
        raise ValueError("roster manager invalid")
    players = []
    for index in range(4):
        record = pm + 4 + index * roster.ROSTER_STRIDE
        if roster._bank(record, 0x90) != "MEM2":
            raise ValueError("roster player record invalid")
        ptr = read(record + 0x88)
        if roster._bank(ptr, 0x1AC) != "MEM2" or read(ptr + 0x4C) != ptr + 0x30:
            raise ValueError("roster ball missing source self-reference")
        players.append(ptr)
    if len(set(players)) != 4:
        raise ValueError("source roster balls alias")
    chosen = sample["selected_index"]
    if type(chosen) is not int or chosen not in range(4):
        raise ValueError("selected slot invalid")
    if read(pm + 0x334) != pm + 4 + chosen * roster.ROSTER_STRIDE:
        raise ValueError("selected player pointer drift")
    global_ball = read(slot)
    if (roster._bank(global_ball, 0x50) != "MEM2"
            or read(global_ball + 0x4C) != global_ball + 0x30):
        raise ValueError("source global ball chain invalid")
    return {
        "all_four_source_roster_balls_valid_and_distinct": True,
        "source_global_ball_is_outside_four_roster_balls":
            global_ball not in players,
        "source_global_ball_equals_source_selected_ball":
            global_ball == players[chosen],
        # No native pointers, slot number, private words or vector values.
    }


def _digest_code(read, regions):
    digest = hashlib.sha256()
    for low, high in regions:
        if low % 4 or high % 4 or low >= high or high-low > 0x400:
            raise ValueError("invalid authenticated PPC code region")
        for pc in range(low, high, 4):
            word = read(pc)
            if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
                raise ValueError("invalid Rev1 instruction in snapshot")
            digest.update(word.to_bytes(4, "big"))
    return digest.digest()


def _classification(row, read, source_disp, outer_cfg):
    """Only a syntactic DIRECT r13 slot-load can point at global object.

    Incomplete function extents and no outer CFG leave all *runtime* object
    associations UNKNOWN even with an exact source-register-class match.
    """
    if row["exact_direct_calls_found_within_window"] != 1:
        return "UNRESOLVED_OUTER_CALLSITE"
    offset = row["candidate_callsite_source_entry_offset"]
    distance = row["nearest_r3_definition_distance_words"]
    if offset is None or distance is None:
        return "UNRESOLVED_R3_INPUT"
    label = row["outer_source_function_entry_label"]
    entries = {name: entry for name, entry, _, _, _ in outer.SOURCES}
    if label not in entries:
        raise ValueError("unexpected source owner label")
    pc = entries[label] + int(offset, 16) - 4 * distance
    w = read(pc)
    op, rt, ra, imm = ((w >> 26) & 63, (w >> 21) & 31,
                        (w >> 16) & 31, _signed16(w & 65535))
    if (op, rt, ra, imm) == (32, 3, 13, source_disp):
        return "DIRECT_GLOBAL_R13_LOAD_SYNTAX_CANDIDATE"
    if op in (32, 33) and rt == 3 and imm == 0x88:
        return "BALL_CHILD_OFFSET_0x88_UNOWNED_BASE_CANDIDATE"
    if row["nearest_supported_r3_definition_class"] is not None:
        return "OTHER_OR_UNRESOLVED_GPR_R3_SOURCE"
    return "UNRESOLVED_R3_INPUT"


def synthesize(outer_result, inner_result, native_rows, read_u32, source_disp):
    if (type(native_rows) is not list or len(native_rows) != 7
            or any(not x["all_four_source_roster_balls_valid_and_distinct"]
                   for x in native_rows)):
        raise ValueError("native roster/slot source evidence incomplete")
    first = outer_result["outer_call_windows"]
    second = inner_result["sources"]
    if len(first) != 2 or len(second) != 2:
        raise ValueError("two exact static source chains required")
    rows = []
    for upstream, inner in zip(first, second):
        hint = _classification(upstream, read_u32, source_disp, inner)
        rows.append({
            "outer_source_function": upstream["outer_source_function_entry_label"],
            "outer_direct_call_count_bounded": upstream["exact_direct_calls_found_within_window"],
            "outer_source_status": upstream["status"],
            "near_call_r3_class": upstream["nearest_supported_r3_definition_class"],
            "near_call_r3_provenance_hint": hint,
            "inner_source_function": inner["published_source_function"],
            "inner_cfg_status": inner["status"],
            "inner_all_path_entry_r3_must_flow": inner[
                "all_reaching_paths_pass_entry_r3_through_r31_to_call_r3"],
            "whole_chain_source_receiver_proven": False,
            "actual_receiver_is_global_or_roster_ball_verified": False,
        })
    return {
        "kind": "P0-SANITIZED-SOURCE-GATED-OUTER-INNER-RECEIVER-JOIN",
        "seven_original_sha_verified_before_and_after": True,
        "rev1_selected_golf_scene_gate_each_capture": True,
        "source_code_same_across_original_seven_captures": True,
        "phase_labels_used_or_time_order_assumed": False,
        "source_global_outside_four_roster_in_all_captures":
            all(x["source_global_ball_is_outside_four_roster_balls"]
                for x in native_rows),
        "both_inner_static_cfg_must_flow":
            inner_result["both_static_proofs_succeeded"],
        "any_static_source_global_load_candidate":
            any(r["near_call_r3_provenance_hint"] ==
                "DIRECT_GLOBAL_R13_LOAD_SYNTAX_CANDIDATE" for r in rows),
        "selected_player_ball_as_runtime_receiver_verified": False,
        "global_ball_as_runtime_receiver_verified": False,
        "cache_writer_executed_in_captured_frame_verified": False,
        "real_rendered_ball_xyz_or_velocity_verified": False,
        "power_contact_score_outcome_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
        "receiver_chains": rows,
    }


def analyze(archive, seven, cfg):
    folders = seven._check_archive(archive)
    first_digest = None
    outer_result = inner_result = last_read = None
    global_disp = None
    native = []
    regions = _source_regions(cfg)
    with ExitStack() as stack:
        for number in CAPTURES:
            pairs = []
            for bank_index, size in enumerate(seven.SIZE):
                path = seven.src._file(
                    folders[number], f"{number}.{bank_index+1}.raw", size)
                fh = stack.enter_context(path.open("rb"))
                pairs.append(stack.enter_context(mmap.mmap(
                    fh.fileno(), 0, access=mmap.ACCESS_READ)))
            read = seven.roster.TwoBankReader(*pairs).u32
            digest = _digest_code(read, regions)
            if first_digest is None:
                first_digest = digest
            elif digest != first_digest:
                raise ValueError("source PPC differs between original captures")
            slot, disp = _source_global_slot(read, seven.roster)
            if global_disp is None:
                global_disp = disp
            elif disp != global_disp:
                raise ValueError("source global r13 load changed")
            native.append(_native_roster_global_gate(seven.roster.TwoBankReader(*pairs), seven, slot))
            current_outer = outer.inspect_upstream(read)
            current_inner = cfg.inspect_known_callers(read)
            if outer_result is None:
                outer_result = current_outer
                inner_result = current_inner
            elif current_outer != outer_result or current_inner != inner_result:
                raise ValueError("same Rev1 code gave different static source analysis")
            last_read = read
        report = synthesize(outer_result, inner_result, native,
                            last_read, global_disp)
    seven._check_archive(archive)  # full original manifest and 14 SHA hashes
    return report


def _import_from_path(name, path):
    target = Path(path).resolve(strict=True)
    if not target.is_file() or target.is_symlink():
        raise ValueError("private source helper must be a regular script")
    spec = importlib.util.spec_from_file_location(name, target)
    if spec is None or spec.loader is None:
        raise ValueError("unknown source helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--canonical-source-scripts", required=True, type=Path)
    parser.add_argument("--cfg-script", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        source = args.canonical_source_scripts.resolve(strict=True)
        if not source.is_dir():
            raise ValueError("source scripts directory missing")
        sys.path.insert(0, str(source))
        seven = _import_from_path(
            "seven_canonical_receiver_source",
            source / "audit_p0_seven_numbered_source_pairs_private.py")
        cfg = _import_from_path("cfg_owner_checked_receiver_source", args.cfg_script)
        report = analyze(args.archive, seven, cfg)
    except (OSError, ValueError, TypeError, KeyError, OverflowError,
            AttributeError, ImportError, RuntimeError, IndexError):
        print("P0 RECEIVER JOIN ABSTAIN: original private SHA/Rev1 source"
              " or source code/owner/caller gate failed.", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
