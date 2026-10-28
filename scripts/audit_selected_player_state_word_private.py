"""PRIVATE read-only selected-player state-word study for existing B0..B3.

Rev1 RPGolPlayer.cpp shows five immediate state assignments to receiver+0x24.
Their name, completeness, game meaning and connection to ball motion are UNKNOWN.
Reuse the strict source, scene and selected-ball gates from S002 #160/#163.
Do not launch Dolphin, read live RPC, write memory or print raw integer words.
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
import audit_selected_ball_four_phase_private as four

# Exact Rev1 PPC sites from the same private-DOL source audit documented by
# S002 #162. PPC li r0,imm is addi r0,r0,imm; stw r0,0x24(receiver).
# Code addresses are constants from the compiled text, NOT dynamic heap words.
_SOURCE_WRITERS = (
    (0x8029F0C8, 5, 0x8029F0CC, 3),
    (0x8029F0D4, 1, 0x8029F0DC, 3),
    (0x8029F0F4, 2, 0x8029F0F8, 29),
    (0x8029F134, 3, 0x8029F138, 29),
    (0x8029F1BC, 4, 0x8029F1C0, 29),
)
_LITERAL_STATES = frozenset(range(1, 6))


def source_state_writer_gate(read_u32) -> bool:
    """Fail closed unless ALL named li/stw pairs match Rev1 encoded operands."""
    return all(
        roster._dform_matches(read_u32, li, 14, 0, 0, literal)
        and roster._dform_matches(read_u32, stw, 36, 0, base, 0x24)
        for li, literal, stw, base in _SOURCE_WRITERS
    )


def summarize(entries: list[dict], *, all_bank_pairs_changed: bool) -> dict:
    """Only emit booleans and counts, never literal state words or pointers."""
    if len(entries) != 4 or type(all_bank_pairs_changed) is not bool:
        raise ValueError("Exactly four verified phases and bank metadata required")
    if any(type(e.get("state")) is not int or not 0 <= e["state"] <= 0xFFFFFFFF
           or type(e.get("slot")) is not int or type(e.get("hole")) is not int
           or type(e.get("record")) is not int or
           e.get("source_gate") is not True for e in entries):
        raise ValueError("Malformed or ungated state sample")
    if len({e["slot"] for e in entries}) != 1 or len({e["hole"] for e in entries}) != 1:
        raise ValueError("Selected source slot/hole changed across no-shot phases")
    if len({e["record"] for e in entries}) != 1:
        raise ValueError("Selected object pointer changed; no continuity claim")
    words = [e["state"] for e in entries]
    changes = [words[i] != words[i + 1] for i in range(3)]
    known = [w in _LITERAL_STATES for w in words]
    return {
        "kind": "local-private-selected-player-candidate-state-word-no-shot",
        "schema_version": 1,
        "game_id": "RSPE01",
        "disc_revision": 1,
        "game_mode": 4,
        "phase_names": list(four.PHASE_LABELS),
        "source_PPC_five_writer_signature_passed_all_phases": True,
        "selected_record_hole_slot_stable": True,
        "all_three_transitions_have_distinct_full_banks": all_bank_pairs_changed,
        "candidate_state_in_five_source_literals_each_phase": known,
        "candidate_state_change_by_transition": changes,
        "candidate_state_changed_during_idle_before_aim": changes[0],
        "candidate_state_changed_during_aim_without_shot": changes[1],
        "candidate_state_changed_during_idle_after_aim": changes[2],
        "candidate_state_stable_all_four_no_shot_phases": not any(changes),
        "candidate_state_has_verified_gameplay_semantics": False,
        "candidate_state_exhaustive_enum_verified": False,
        "observed_contact_or_ball_motion": False,
        "guest_frame_alignment_verified": False,
        "same_boot_independently_proven": False,
        "active_ball_world_xyz_verified": False,
        "velocity_verified": False,
        "power_verified": False,
        "training_allowed": False,
        "allowed_to_publish": False,
        "next_action": (
            "S002 review whether state word varies during visible aim or idle. "
            "Do not assign labels like contact/flight/landing without a separately "
            "approved human-observed dynamic experiment."
        ),
    }


def run_local(folder: Path) -> dict:
    """Reinspect preserved B0..B3; original files and manifest remain untouched."""
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Missing private session directory")
    root = selected.DATA_ROOT.resolve(strict=True)
    folder = folder.resolve(strict=True)
    if folder == root or not folder.is_relative_to(root):
        raise ValueError("Input must be existing session inside ignored Data root")
    manifest = four._validate_manifest(folder)
    entries = []
    hash_sets = []
    with ExitStack() as stack:
        for phase in four.PHASES:
            files = {
                key: four._approved_bank(
                    folder, f"{phase}-{key}.bin",
                    roster.MEM1_SIZE if key == "MEM1" else roster.MEM2_SIZE
                )
                for key in ("MEM1", "MEM2")
            }
            digests = {k: four._hash(file) for k, file in files.items()}
            if digests != {k: manifest[phase]["sha256"][k] for k in files}:
                raise ValueError("Private image differs from preserved manifest")
            hash_sets.append(digests)
            mmaps = []
            for file in files.values():
                source = stack.enter_context(file.open("rb"))
                mmaps.append(stack.enter_context(mmap.mmap(
                    source.fileno(), 0, access=mmap.ACCESS_READ
                )))
            reader = roster.TwoBankReader(*mmaps)
            safe, private = selected.analyze_one(reader.u32, reader.header())
            if not source_state_writer_gate(reader.u32):
                raise ValueError("Rev1 selected player state writer PPC mismatch")
            if any(safe.get(k) is not True for k in (
                "selected_record_pointer_matches_code_defined_stride",
                "selected_ball_translation_pointer_is_mem2",
                "source_current_start_translation_pointer_is_mem2",
            )):
                raise ValueError("Source-gated selected actor identity not established")
            manager = reader.u32(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
            rec = manager + 4 + private["selected_index"] * roster.ROSTER_STRIDE
            if roster._bank(rec, 0x28) != "MEM2":
                raise ValueError("Selected record not in expected MEM2 range")
            if reader.u32(manager + 0x334) != rec:
                raise ValueError("Selected record source selector moved")
            entries.append({
                "slot": private["selected_index"],
                "hole": private["hole"],
                "record": rec,
                "state": reader.u32(rec + 0x24),
                "source_gate": True,
            })
        banks_differ = all(
            all(hash_sets[i][k] != hash_sets[i + 1][k]
                for k in ("MEM1", "MEM2"))
            for i in range(3)
        )
    return summarize(entries, all_bank_pairs_changed=banks_differ)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        result = run_local(args.private_root)
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        print("Private source-selected state-word audit FAILED CLOSED; "
              "no game action, raw data or pointers disclosed.", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
