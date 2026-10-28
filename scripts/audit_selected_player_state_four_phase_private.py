"""Read-only PRIVATE Rev1 selected-player state-word B0-B3 contrast.

Source field candidate: selected player record +0x24. The Rev1 PPC code
writes literal integers 1..5 into a receiver's +0x24 through five
different branches; those literals are NOT verified to exhaust states or
mean aim, swing, impact, in-flight, landed, or power.

Uses canonical #160 roster source/PPC & #163 selected/start/ball links
and the existing verified private checkpoint manifest. Never launches
Dolphin, sends controller/RPC, exports raw memory, prints a state value
or heap pointer, commits data or authorizes model training.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import mmap
from pathlib import Path

import audit_golf_two_bank_roster_private as roster
import audit_selected_ball_start_link_private as selected
import audit_selected_ball_four_phase_private as previous

KNOWN_BRANCH_LITERALS = frozenset((1, 2, 3, 4, 5))
PHASES = ("B0", "B1", "B2", "B3")
# The candidate store offsets/receiver regs are sourced from the existing
# RSPE01_01 Rev1 PPC analysis in #162, not a global memory float search.
WRITES = (
    (0x8029F0C8, 0x8029F0CC, 5, 3),
    (0x8029F0D4, 0x8029F0DC, 1, 3),
    (0x8029F0F4, 0x8029F0F8, 2, 29),
    (0x8029F134, 0x8029F138, 3, 29),
    (0x8029F1BC, 0x8029F1C0, 4, 29),
)


def _state_writer_proven(read_u32):
    # Check actual instructions, including the required receiver move.
    # Neither code unit nor static stores alone prove runtime method call.
    return (roster._mr_matches(read_u32, 0x8029F0C0, 29, 3)
            and all(
                roster._dform_matches(read_u32, load_pc, 14, 0, 0, literal)
                and roster._dform_matches(read_u32, store_pc, 36, 0, reg, 0x24)
                for load_pc, store_pc, literal, reg in WRITES))


def _one(read_u32, header):
    source_summary, private = selected.analyze_one(read_u32, header)
    if not _state_writer_proven(read_u32):
        raise ValueError("Rev1 candidate state PPC store path did not match")
    index = private["selected_index"]
    manager = read_u32(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    record = manager + 4 + roster.ROSTER_STRIDE * index
    if (roster._bank(record + 0x24) != "MEM2"
            or read_u32(manager + 0x334) != record):
        raise ValueError("Active roster-record identity changed")
    value = read_u32(record + 0x24)
    if type(value) is not int or not 0 <= value < (1 << 32):
        raise ValueError("Bad source-related state word")
    safe = {
        "source_five_literal_write_patterns_match_rev1": True,
        "selected_record_source_layout_consistent": True,
        "raw_state_in_source_written_literal_set": value in KNOWN_BRANCH_LITERALS,
        "selected_record_and_start_triplets_equal":
            source_summary["all_three_candidate_triplets_bitwise_equal"],
        "selected_index_unchanged_within_capture": True,
        "semantic_state_name_verified": False,
        "all_possible_states_known": False,
    }
    return safe, {
        "value": value, "selected_index": index,
        "hole": private["hole"], "ball": private["ball"],
        "start": private["start"], "record": private["record"],
    }


def summarize_four(reports, changes, *, visible_aim=False, same_session=False):
    if (len(reports) != 4 or len(changes) != 3
            or type(visible_aim) is not bool
            or type(same_session) is not bool):
        raise ValueError("Exactly four source-gated stages required")
    safe = [s for s, _ in reports]
    raw = [p for _, p in reports]
    if not all(s["source_five_literal_write_patterns_match_rev1"] for s in safe):
        raise ValueError("PPC candidate source not verified")
    if not all(x["selected_index"] == raw[0]["selected_index"]
               and x["hole"] == raw[0]["hole"] for x in raw):
        raise ValueError("Selected index or current hole changed")
    if any(type(d.get("MEM1")) is not bool or
           type(d.get("MEM2")) is not bool for d in changes):
        raise ValueError("Unverified bank-change flag")
    transitions = []
    for i in range(3):
        before, after = raw[i:i+2]
        transitions.append({
            "phase": f"{PHASES[i]}_to_{PHASES[i+1]}",
            "selected_player_state_word_changed":
                before["value"] != after["value"],
            "ball_candidate_components_changed": sum(
                a != b for a,b in zip(before["ball"],after["ball"])),
            "source_start_components_changed": sum(
                a != b for a,b in zip(before["start"],after["start"])),
            "both_native_memory_banks_changed":
                changes[i]["MEM1"] and changes[i]["MEM2"],
        })
    no_shot_stability = all(
        t["ball_candidate_components_changed"] == 0
        and t["source_start_components_changed"] == 0 for t in transitions)
    both_banks_distinct = all(t["both_native_memory_banks_changed"]
                              for t in transitions)
    return {
        "schema_version": 1,
        "kind": "local-private-selected-player-untyped-state-four-phase",
        "game_id": "RSPE01", "revision": 1, "mode": 4,
        "source_code_player_state_writers": "five_literal_stores_in_player_unit",
        "selected_record_relative_member": "+0x024",
        "all_five_static_writer_paths_verified": True,
        "known_source_literal_value_set": "1_to_5_nonexhaustive",
        "observed_value_in_source_literal_set": [
            s["raw_state_in_source_written_literal_set"] for s in safe],
        "selected_record_identity_and_hole_stable": True,
        "selected_player_state_word_stable_in_no_shot": not any(
            t["selected_player_state_word_changed"] for t in transitions),
        "selected_player_state_word_changed_during_aim": transitions[1][
            "selected_player_state_word_changed"],
        "source_current_start_and_ball_candidate_stable_in_no_shot":
            no_shot_stability,
        "all_three_transitions_have_distinct_both_banks": both_banks_distinct,
        "operator_reports_aim_visibly_moved": visible_aim,
        "operator_reports_same_session": same_session,
        "transitions": transitions,
        "phase_labels_independently_verified": False,
        "same_emulator_frame_proven": False,
        "state_word_runtime_writer_PC_observed": False,
        "state_word_semantics_verified": False,
        "shot_or_ball_motion_recorded": False,
        "power_or_velocity_verified": False,
        "training_allowed": False,
        "allowed_to_publish": False,
        "next_action": (
            "If state changes during no-shot, investigate clock/aim/control "
            "ownership and alternative states before labeling anything; if "
            "unchanged, future S001 one-shot source-gated frame watcher may "
            "consider one extra selected record+0x24 u32 read only after "
            "S001/S002/S000 overhead/source/privacy approval. "
            "No physical power or shot lifecycle label from this audit."
        ),
    }


def _digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()


def run_local(private_root, *, visible_aim=False, same_session=False):
    folder = Path(private_root)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Private session folder unavailable")
    root = selected.DATA_ROOT.resolve(strict=True)
    exact = folder.resolve(strict=True)
    if exact == root or not exact.is_relative_to(root):
        raise ValueError("Selected player study requires ignored private folder")
    entries = previous._validate_manifest(exact)
    reports = []
    digests = []
    with ExitStack() as stack:
        for phase in PHASES:
            paths = [
                previous._approved_bank(exact, f"{phase}-MEM1.bin", roster.MEM1_SIZE),
                previous._approved_bank(exact, f"{phase}-MEM2.bin", roster.MEM2_SIZE),
            ]
            hashes = dict(zip(("MEM1", "MEM2"), map(_digest, paths)))
            if any(hashes[k] != entries[phase]["sha256"][k]
                   for k in ("MEM1", "MEM2")):
                raise ValueError("Private checkpoint digest changed after capture")
            images = []
            for path in paths:
                fp = stack.enter_context(path.open("rb"))
                images.append(stack.enter_context(
                    mmap.mmap(fp.fileno(), 0, access=mmap.ACCESS_READ)))
            reader = roster.TwoBankReader(*images)
            reports.append(_one(reader.u32, reader.header()))
            digests.append(hashes)
        transitions = [{
            k: digests[i][k] != digests[i+1][k] for k in ("MEM1", "MEM2")
        } for i in range(3)]
        return summarize_four(reports, transitions,
                              visible_aim=visible_aim, same_session=same_session)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root", type=Path, required=True)
    p.add_argument("--aim-visibly-moved", action="store_true")
    p.add_argument("--operator-same-session", action="store_true")
    a = p.parse_args(argv)
    try:
        result = run_local(
            a.private_root, visible_aim=a.aim_visibly_moved,
            same_session=a.operator_same_session)
    except (OSError, UnicodeError, ValueError, TypeError, OverflowError, KeyError):
        print("Private selected-state source audit refused malformed or "
              "unverified checkpoints. No RAM data or paths printed.",
              file=__import__("sys").stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
