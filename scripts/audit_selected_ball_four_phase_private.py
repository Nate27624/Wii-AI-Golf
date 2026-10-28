"""PRIVATE four-phase selected ball/start no-shot null-control audit.

Consumes existing B0/B1/B2/B3 native MEM1+MEM2 snapshots made with the
operator's paused Dolphin GUI and saved using S002's checkpoint keeper.
REUSES the canonical #160 roster source+PPC validator and #163 source-gated
selected record/ball/start comparator. No Dolphin actions, no controller
commands, no raw words, no runtime addresses, no network, no publication.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import mmap
from pathlib import Path
import sys

import audit_golf_two_bank_roster_private as roster
import audit_selected_ball_start_link_private as selected

PHASES = ("B0", "B1", "B2", "B3")
PHASE_LABELS = ("idle_baseline", "idle_delayed",
                "wasd_aim_only", "idle_after_aim")
MANIFEST_NAME = "checkpoint-manifest-PRIVATE.json"
MAX_MANIFEST_BYTES = 32768


def _component_changes(a, b):
    return sum(x != y for x, y in zip(a, b))


def summarize_four_selected(reports, bank_changed, *,
                            aim_visibly_moved: bool = False,
                            operator_same_session: bool = False):
    """Summarize only boolean/count contrasts; no tuple of 32-bit RAM words."""
    if (len(reports) != 4 or len(bank_changed) != 3
            or type(aim_visibly_moved) is not bool
            or type(operator_same_session) is not bool):
        raise ValueError("Four selected checks and three bank transitions required")
    safe_list = [x[0] for x in reports]
    private_list = [x[1] for x in reports]
    if not all(
        all(safe.get(key) is True for key in (
            "selected_record_pointer_matches_code_defined_stride",
            "selected_ball_translation_pointer_is_mem2",
            "source_current_start_translation_pointer_is_mem2",
            "record_candidate_triplet_finite_bounded",
            "nested_ball_candidate_triplet_finite_bounded",
            "source_current_start_triplet_finite_bounded",
        ))
        for safe in safe_list
    ):
        raise ValueError("Selected record / source position gate failed")
    if not all(x["selected_index"] == private_list[0]["selected_index"]
               and x["hole"] == private_list[0]["hole"]
               for x in private_list):
        raise ValueError("Selected record or hole changed: not comparable no-shot phases")
    if any(type(x.get("MEM1")) is not bool or
           type(x.get("MEM2")) is not bool for x in bank_changed):
        raise ValueError("Whole-bank change indicators must be boolean")
    changes = []
    for i in range(3):
        old, new = private_list[i], private_list[i+1]
        whole = bank_changed[i]
        changes.append({
            "transition": f"{PHASES[i]}_to_{PHASES[i+1]}",
            "full_MEM1_changed": whole["MEM1"],
            "full_MEM2_changed": whole["MEM2"],
            "selected_ball_vector_changed_components":
                _component_changes(old["ball"], new["ball"]),
            "selected_record_vector_changed_components":
                _component_changes(old["record"], new["record"]),
            "source_current_start_vector_changed_components":
                _component_changes(old["start"], new["start"]),
            "selected_index_unchanged": True,
            "source_hole_index_unchanged": True,
        })
    stable_ball = all(x["selected_ball_vector_changed_components"] == 0
                      for x in changes)
    stable_start = all(x["source_current_start_vector_changed_components"] == 0
                       for x in changes)
    stable_record = all(x["selected_record_vector_changed_components"] == 0
                        for x in changes)
    b0_initial_link = safe_list[0]["all_three_candidate_triplets_bitwise_equal"]
    all_phases_independently_distinct = all(
        d["full_MEM1_changed"] and d["full_MEM2_changed"] for d in changes)
    return {
        "kind": "local-private-selected-ball-four-phase-null-control",
        "schema_version": 1,
        "game_id": "RSPE01",
        "revision": 1,
        "mode": 4,
        "phases": list(PHASES),
        "source_and_PPC_roster_checks_passed_each_phase": True,
        "selected_slot_and_hole_stable_across_phases": True,
        "selected_record_index_candidate": private_list[0]["selected_index"],
        "B0_selected_record_ball_and_start_equal":
            b0_initial_link,
        "per_phase_ball_equals_start_component_count": [
            x["selected_nested_ball_vs_current_start_component_equal_count"]
            for x in safe_list
        ],
        "per_phase_record_equals_ball_component_count": [
            x["selected_record_vs_nested_ball_component_equal_count"]
            for x in safe_list
        ],
        "transitions": changes,
        "selected_ball_vector_stable_during_no_shot": stable_ball,
        "selected_record_vector_stable_during_no_shot": stable_record,
        "source_start_vector_stable_during_no_shot": stable_start,
        "all_three_transitions_have_distinct_whole_banks":
            all_phases_independently_distinct,
        "operator_reports_aim_visibly_moved": aim_visibly_moved,
        "operator_reports_same_dolphin_session": operator_same_session,
        "no_shot_controls_consistent_with_stationary_ball_candidate": bool(
            stable_ball and stable_start and stable_record and b0_initial_link
            and all_phases_independently_distinct and aim_visibly_moved
            and operator_same_session),
        "ball_world_xyz_verified": False,
        "ball_motion_verified": False,
        "velocity_verified": False,
        "swing_power_verified": False,
        "same_emulated_frame_pair_verified": False,
        "same_boot_independently_proven": False,
        "approved_for_model_training": False,
        "allowed_to_publish": False,
        "warning": (
            "Null controls test position stability, NOT real ball motion or physics. "
            "Operator-reported aim and session provenance are not independently "
            "verified. Do not commit private full RAM or this unreviewed kind."),
        "next_action": (
            "If stationary-source checks pass, have S001/S002 review ONE "
            "operator-approved observed ball movement experiment. If they fail, "
            "investigate actor selection, rendering proxy and initialization "
            "without fabricating position/velocity semantics."),
    }


def _validate_manifest(folder):
    path = folder / MANIFEST_NAME
    if (not path.is_file() or path.is_symlink() or
            path.stat().st_size > MAX_MANIFEST_BYTES):
        raise ValueError("Missing or unsafe checkpoint manifest")
    with path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if (not isinstance(manifest, dict) or manifest.get("schema_version") != 1
            or manifest.get("kind") != "local-private-golf-paired-checkpoints"
            or not isinstance(manifest.get("checkpoints"), dict)):
        raise ValueError("Checkpoint manifest identity invalid")
    checkpoints = manifest["checkpoints"]
    if tuple(checkpoints)[:4] != PHASES:
        raise ValueError("Missing, mislabeled or disordered B0-B3")
    for phase, label in zip(PHASES, PHASE_LABELS):
        entry = checkpoints.get(phase)
        if (not isinstance(entry, dict)
                or entry.get("phase_operator_label") != label
                or entry.get("operator_reports_gui_paused") is not True
                or entry.get("scene_source_chain_gated") is not True
                or entry.get("native_sizes_valid") is not True
                or entry.get("observed_game_mode") != 4):
            raise ValueError("Invalid paused native checkpoint metadata")
        hashes = entry.get("sha256")
        if (not isinstance(hashes, dict)
                or any(not isinstance(hashes.get(k), str)
                       or len(hashes[k]) != 64
                       for k in ("MEM1", "MEM2"))):
            raise ValueError("Missing source hashes")
    return checkpoints


def _approved_bank(folder, name, length):
    path = folder / name
    if (path.is_symlink() or not path.is_file()
            or path.stat().st_size != length):
        raise ValueError("Missing, symlink or wrong-sized memory checkpoint")
    return path


def _hash(file):
    h = hashlib.sha256()
    with file.open("rb") as stream:
        for data in iter(lambda: stream.read(1 << 20), b""):
            h.update(data)
    return h.hexdigest()


def run_local(folder, *, aim_visibly_moved=False,
              operator_same_session=False):
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Invalid private session folder")
    root = selected.DATA_ROOT.resolve(strict=True)
    p = folder.resolve(strict=True)
    if not p.is_relative_to(root) or p == root:
        raise ValueError("Private session folder must be within ignored Data root")
    checkpoints = _validate_manifest(p)
    with ExitStack() as stack:
        pairs = []
        hashes = []
        reports = []
        for phase in PHASES:
            files = [
                _approved_bank(p, f"{phase}-MEM1.bin", roster.MEM1_SIZE),
                _approved_bank(p, f"{phase}-MEM2.bin", roster.MEM2_SIZE),
            ]
            checkhash = {key: _hash(file)
                         for key, file in zip(("MEM1", "MEM2"), files)}
            if any(checkhash[k] != checkpoints[phase]["sha256"][k]
                   for k in ("MEM1", "MEM2")):
                raise ValueError("Private checkpoint changed after preservation")
            images = []
            for file in files:
                stream = stack.enter_context(file.open("rb"))
                images.append(stack.enter_context(mmap.mmap(
                    stream.fileno(), 0, access=mmap.ACCESS_READ)))
            rd = roster.TwoBankReader(*images)
            reports.append(selected.analyze_one(rd.u32, rd.header()))
            pairs.append(tuple(images))
            hashes.append(checkhash)
        changed = [
            {key: hashes[i][key] != hashes[i+1][key]
             for key in ("MEM1", "MEM2")}
            for i in range(3)
        ]
        return summarize_four_selected(
            reports, changed, aim_visibly_moved=aim_visibly_moved,
            operator_same_session=operator_same_session)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", required=True, type=Path)
    parser.add_argument("--aim-visibly-moved", action="store_true")
    parser.add_argument("--operator-same-session", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_local(
            args.private_root,
            aim_visibly_moved=args.aim_visibly_moved,
            operator_same_session=args.operator_same_session)
    except (OSError, ValueError, TypeError, OverflowError, KeyError):
        print("Selected ball four-phase audit FAILED CLOSED; check private "
              "B0-B3 pair integrity, selected actor or revision. "
              "No private paths or RAM bytes disclosed.", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
