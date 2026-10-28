"""PRIVATE US Rev1 selected-player +0x24 state-word B0..B3 null-control.

ONE bounded u32 field, after the existing S002 #160/#163 source-gated
selected-record checks. Does NOT look for new pointers, scan RAM, upload,
launch Dolphin, or infer contact, flight, landing, swing power or score.
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

# Every word independently checked against operator-supplied US Rev1 main.dol
# PPC .text. (li r0, literal); (stw r0, 0x24(r3 or r29)).
# The Five store sites are source code witnesses, NOT observed execution.
STATE_WRITES = (
    (0x8029F0C8, 0x38000005, 0x8029F0CC, 0x90030024),
    (0x8029F0D4, 0x38000001, 0x8029F0DC, 0x90030024),
    (0x8029F0F4, 0x38000002, 0x8029F0F8, 0x901D0024),
    (0x8029F134, 0x38000003, 0x8029F138, 0x901D0024),
    (0x8029F1BC, 0x38000004, 0x8029F1C0, 0x901D0024),
)
WRITER_LITERALS = frozenset((1, 2, 3, 4, 5))


def read_selected_state(read_u32, header: bytes):
    """Transient private state and full source-based identity validation."""
    safe, priv = selected.analyze_one(read_u32, header)
    for li_pc, li_opcode, st_pc, st_opcode in STATE_WRITES:
        if read_u32(li_pc) != li_opcode or read_u32(st_pc) != st_opcode:
            raise ValueError("Rev1 source state writer instruction mismatch")
    idx = priv["selected_index"]
    if type(idx) is not int or not 0 <= idx < roster.ROSTER_SLOTS:
        raise ValueError("Unverified selected roster slot")
    manager = read_u32(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    rec = manager + 4 + roster.ROSTER_STRIDE * idx
    if (roster._bank(rec, 0xCC) != "MEM2"
            or read_u32(manager + 0x334) != rec):
        raise ValueError("Unstable selected record identity")
    if not all(safe[k] for k in (
            "selected_record_pointer_matches_code_defined_stride",
            "record_candidate_triplet_finite_bounded",
            "nested_ball_candidate_triplet_finite_bounded",
            "source_current_start_triplet_finite_bounded",
        )):
        raise ValueError("Source-gated current player record missing")
    state_word = read_u32(rec + 0x24)
    if type(state_word) is not int or not 0 <= state_word <= 0xFFFFFFFF:
        raise ValueError("Invalid source state-word read")
    # Return only to our local in-memory computation, NEVER directly print.
    return {
        "state": state_word, "record_pointer": rec,
        "selected_index": idx, "hole": priv["hole"],
        "writer_instruction_sites_checked": len(STATE_WRITES),
    }


def summarize(states: list[dict], *,
              aim_visibly_moved: bool = False,
              operator_same_session: bool = False) -> dict:
    if (not isinstance(states, list) or len(states) != 4
            or type(aim_visibly_moved) is not bool
            or type(operator_same_session) is not bool):
        raise ValueError("Expected four source-gated state observations")
    if any(type(s.get("writer_instruction_sites_checked")) is not int
           or s["writer_instruction_sites_checked"] != len(STATE_WRITES)
           for s in states):
        raise ValueError("State PPC writer chain unverified")
    if (any(type(s.get("state")) is not int
            or not 0 <= s["state"] <= 0xFFFFFFFF for s in states)
            or len({s["selected_index"] for s in states}) != 1
            or len({s["hole"] for s in states}) != 1):
        raise ValueError("State observations not comparable")
    values = [s["state"] for s in states]
    changed = [values[i] != values[i+1] for i in range(3)]
    pointer_stable = len({s["record_pointer"] for s in states}) == 1
    return {
        "kind": "local_private_selected_player_state_word_four_phase",
        "schema_version": 1,
        "game_id": "RSPE01",
        "revision": 1,
        "mode": 4,
        "phases": list(phase.PHASES),
        "source_selected_record_unchanged": pointer_stable,
        "source_selected_slot_and_hole_unchanged": True,
        "writer_literal_site_count_verified_each_phase": len(STATE_WRITES),
        "candidate_word_is_zero_per_phase": [v == 0 for v in values],
        "candidate_word_matches_one_of_five_writer_literals_per_phase":
            [v in WRITER_LITERALS for v in values],
        "candidate_word_distinct_value_count": len(set(values)),
        "candidate_word_changed_across_transitions": changed,
        "candidate_word_stable_during_no_shot":
            pointer_stable and not any(changed),
        "operator_reports_aim_visibly_moved": aim_visibly_moved,
        "operator_reports_same_dolphin_session": operator_same_session,
        "source_code_writer_sites_verified_not_executed": True,
        "writer_literal_set_exhaustive_verified": False,
        "actual_state_enum_names_verified": False,
        "gameplay_state_verified": False,
        "contact_or_landing_verified": False,
        "swing_power_verified": False,
        "ball_world_xyz_verified": False,
        "guest_frame_alignment_verified": False,
        "approved_for_model_training": False,
        "allowed_to_publish": False,
        "warning": (
            "A source-backed player-record +0x24 integer and five literal "
            "store sites are CODE-identified only. Zero, matching a literal, "
            "or changing during no-shot controls does not establish actual "
            "play phase, impact, flight, landing, swing power or physics."
        ),
    }


def run_local(folder: Path, *, aim_visibly_moved: bool = False,
              operator_same_session: bool = False) -> dict:
    """Reuses #163 exact B0..B3 manifest SHA/size/source gates."""
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Invalid B0-B3 session folder")
    root = selected.DATA_ROOT.resolve(strict=True)
    p = folder.resolve(strict=True)
    if p == root or not p.is_relative_to(root):
        raise ValueError("B0-B3 session outside private Data root")
    manifest = phase._validate_manifest(p)
    states = []
    with ExitStack() as stack:
        for name in phase.PHASES:
            banks = [
                phase._approved_bank(p, f"{name}-MEM1.bin", roster.MEM1_SIZE),
                phase._approved_bank(p, f"{name}-MEM2.bin", roster.MEM2_SIZE),
            ]
            for key, path in zip(("MEM1", "MEM2"), banks):
                if phase._hash(path) != manifest[name]["sha256"][key]:
                    raise ValueError("Private native bank changed since capture")
            mapped = []
            for path in banks:
                fh = stack.enter_context(path.open("rb"))
                mapped.append(stack.enter_context(mmap.mmap(
                    fh.fileno(), 0, access=mmap.ACCESS_READ)))
            reader = roster.TwoBankReader(*mapped)
            states.append(read_selected_state(reader.u32, reader.header()))
    return summarize(
        states, aim_visibly_moved=aim_visibly_moved,
        operator_same_session=operator_same_session
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--aim-visibly-moved", action="store_true")
    parser.add_argument("--operator-same-session", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = run_local(args.private_root,
                           aim_visibly_moved=args.aim_visibly_moved,
                           operator_same_session=args.operator_same_session)
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        print("Private selected-player state audit FAILED CLOSED; "
              "check existing private B0-B3 source/manifest integrity. "
              "No paths or RAM words disclosed.", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
