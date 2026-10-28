"""S002 offline-only selected player-record +0x24 writer/null-control hypothesis.

Extends canonical #160/#163 private paired-bank B0..B3 analysis WITHOUT
new data capture, memory scans, Dolphin/RPC/controller calls, stdout values,
hashes, addresses, private paths, publication or training.

The five code stores show a candidate state-like word but DO NOT identify
swing phase, impact, velocity, score, club or power semantics.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

import audit_golf_two_bank_roster_private as roster
import audit_selected_ball_start_link_private as selected
import audit_selected_ball_four_phase_private as phase

# Source PPC sites documented in S002 #162 (RSPE01 Rev1).
# Exact register/owner provenance must agree on every observation.
RECEIVER_SITE = 0x8029F0C0
LITERAL_AND_STORE = (
    (0x8029F0C8, 0x8029F0CC, 5),
    (0x8029F0D8, 0x8029F0DC, 1),
    (0x8029F0F4, 0x8029F0F8, 2),
    (0x8029F134, 0x8029F138, 3),
    (0x8029F1BC, 0x8029F1C0, 4),
)
STATE_LITERALS = frozenset(x[2] for x in LITERAL_AND_STORE)
STATE_MEMBER = 0x24


def source_write_sites_match(read_u32) -> bool:
    # This is a BOUNDED PPC instruction-shape test, not a dynamic execution
    # trace. Even a source match DOES NOT imply the word is gameplay "state".
    if not roster._mr_matches(read_u32, RECEIVER_SITE, 29, 3):
        return False
    return all(
        roster._dform_matches(read_u32, li_pc, 14, 0, 0, imm)
        and roster._dform_matches(read_u32, store_pc, 36, 0, 29, STATE_MEMBER)
        for li_pc, store_pc, imm in LITERAL_AND_STORE
    )


def inspect_one(read_u32, header):
    """Return only transient local word/owner and source-gated safe metadata."""
    safe, private = selected.analyze_one(read_u32, header)
    if not source_write_sites_match(read_u32):
        raise ValueError("source state writer PPC instructions not verified")
    if not safe["selected_record_pointer_matches_code_defined_stride"]:
        raise ValueError("selected inline record source provenance missing")
    idx = private["selected_index"]
    manager = read_u32(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    record = manager + 4 + idx * roster.ROSTER_STRIDE
    if read_u32(manager + 0x334) != record or roster._bank(record + STATE_MEMBER) != "MEM2":
        raise ValueError("record selector state writer receiver changed")
    val = read_u32(record + STATE_MEMBER)
    if type(val) is not int or not 0 <= val <= 0xFFFFFFFF:
        raise ValueError("selected state word not native 32-bit")
    return {
        "safe": safe,
        "private": private,
        "state_word": val,
        "in_written_literal_set": val in STATE_LITERALS,
    }


def summarize_state_controls(states, bank_changed, *,
                             aim_visibly_moved=False, operator_same_session=False):
    if len(states) != 4:
        raise ValueError("four source-verified selected-record phases required")
    if not all(type(x.get("state_word")) is int
               and 0 <= x["state_word"] <= 0xFFFFFFFF
               and type(x.get("in_written_literal_set")) is bool
               and x["in_written_literal_set"] == (x["state_word"] in STATE_LITERALS)
               for x in states):
        raise ValueError("private state word/membership mismatch")
    baseline = phase.summarize_four_selected(
        [(x["safe"], x["private"]) for x in states], bank_changed,
        aim_visibly_moved=aim_visibly_moved,
        operator_same_session=operator_same_session,
    )
    words = [x["state_word"] for x in states]
    changes = [words[i] != words[i+1] for i in range(3)]
    return {
        "kind": "local-private-source-backed-player-record-member24-no-shot",
        "schema_version": 1,
        "disc_id": "RSPE01",
        "disc_revision": 1,
        "game_mode": 4,
        "source_player_receiver_register_shape_matches": True,
        "source_stores_to_record_member24_match_count": len(LITERAL_AND_STORE),
        "source_literals_identified_are_not_gameplay_labels": True,
        "selected_slot_and_hole_stable": True,
        "null_control_source_ball_triplets_stable":
            baseline["no_shot_controls_consistent_with_stationary_ball_candidate"],
        "operator_reports_same_session": operator_same_session,
        "operator_reports_aim_visibly_moved": aim_visibly_moved,
        "record_member24_in_known_code_literal_set_by_phase": [
            x["in_written_literal_set"] for x in states
        ],
        "record_member24_changes_by_transition": [
            {"transition": phase.PHASES[i] + "_to_" + phase.PHASES[i+1],
             "word_changed": changes[i],
             "full_MEM1_changed": bank_changed[i]["MEM1"],
             "full_MEM2_changed": bank_changed[i]["MEM2"]}
            for i in range(3)
        ],
        "record_member24_distinct_word_class_count": len(set(words)),
        "record_member24_stable_across_all_four_no_shot_phases": not any(changes),
        "candidate_is_gameplay_phase_state_verified": False,
        "impact_or_landing_event_verified": False,
        "ball_world_xyz_verified": False,
        "swing_power_verified": False,
        "same_guest_frame_proven": False,
        "training_approved": False,
        "allowed_to_publish": False,
        "warning": (
            "Source instruction shape and equality across idle/aim checkpoints "
            "DO NOT identify a gameplay enum, phase, contact, dynamics or power. "
            "No human-observed ball motion exists in these four controls."),
    }


def run_local(private_root, *, aim_visibly_moved=False,
              operator_same_session=False):
    """Read exactly the user's preserved four paired native bank files ONCE."""
    if private_root.is_symlink() or not private_root.is_dir():
        raise ValueError("invalid private checkpoint directory")
    root = selected.DATA_ROOT.resolve(strict=True)
    folder = private_root.resolve(strict=True)
    if folder == root or not folder.is_relative_to(root):
        raise ValueError("no nonprivate or top-level input allowed")
    manifest = phase._validate_manifest(folder)
    with ExitStack() as stack:
        states, hashes = [], []
        for name in phase.PHASES:
            paths = [
                phase._approved_bank(folder, name + "-MEM1.bin", roster.MEM1_SIZE),
                phase._approved_bank(folder, name + "-MEM2.bin", roster.MEM2_SIZE),
            ]
            h = {key: phase._hash(file) for key, file
                 in zip(("MEM1", "MEM2"), paths)}
            if any(h[k] != manifest[name]["sha256"][k] for k in ("MEM1", "MEM2")):
                raise ValueError("preserved raw bank checksum mismatch")
            banks = []
            for file in paths:
                stream = stack.enter_context(file.open("rb"))
                banks.append(stack.enter_context(mmap.mmap(
                    stream.fileno(), 0, access=mmap.ACCESS_READ)))
            rd = roster.TwoBankReader(*banks)
            states.append(inspect_one(rd.u32, rd.header()))
            hashes.append(h)
        transitions = [
            {bank: hashes[i][bank] != hashes[i+1][bank]
             for bank in ("MEM1", "MEM2")}
            for i in range(3)
        ]
        return summarize_state_controls(
            states, transitions, aim_visibly_moved=aim_visibly_moved,
            operator_same_session=operator_same_session)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root", required=True, type=Path)
    p.add_argument("--aim-visibly-moved", action="store_true")
    p.add_argument("--operator-same-session", action="store_true")
    args = p.parse_args(argv)
    try:
        result = run_local(
            args.private_root, aim_visibly_moved=args.aim_visibly_moved,
            operator_same_session=args.operator_same_session)
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        print("Source-gated selected member24 offline control refused: "
              "private checkpoint/source/revision/selected-record gate failed. "
              "No private path, words or memory bytes disclosed.", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
