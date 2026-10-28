"""PRIVATE source-gated pre-shot versus visibly-displaced post-shot RAM contrast.

Requires a human-captured *same-boot* PRE/POST pair, each with native MEM1
and MEM2 exported under the same GUI pause, then copied into an ignored
private folder. Reuses existing S002 #160/#163 source/player/ball/field
validation. Does not control, boot, reset or interact with Dolphin.

No raw u32, float, pointer, private path, or SHA leaves stdout.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import mmap
from pathlib import Path
import re
import sys

import audit_golf_two_bank_roster_private as roster
import audit_selected_ball_start_link_private as selected

PHASES = ("PRE", "POST")
PHASE_LABELS = ("pre_shot_still", "post_shot_visible_displacement")
MANIFEST_NAME = "shot-checkpoint-manifest-PRIVATE.json"
MANIFEST_KIND = "local-private-golf-prepost-paired-checkpoints"
MAX_MANIFEST_BYTES = 32 * 1024
HEX_SHA = re.compile(r"^[0-9a-f]{64}$")


def _manifest(folder: Path):
    path = folder / MANIFEST_NAME
    if not path.is_file() or path.is_symlink() or not 1 <= path.stat().st_size <= MAX_MANIFEST_BYTES:
        raise ValueError("Missing, unsafe or oversized private shot manifest")
    with path.open("r", encoding="utf-8") as stream:
        obj = json.load(stream)
    if not isinstance(obj, dict) or obj.get("schema_version") != 1 or obj.get("kind") != MANIFEST_KIND:
        raise ValueError("Shot manifest schema unknown")
    if (obj.get("operator_reports_same_dolphin_process") is not True
            or obj.get("operator_reports_exactly_one_shot") is not True
            or obj.get("operator_reports_visible_ball_displacement") is not True
            or obj.get("operator_reports_no_hole_reset_or_transition") is not True):
        raise ValueError("Missing operator shot provenance; do not infer event")
    if not isinstance(obj.get("checkpoints"), dict) or set(obj["checkpoints"]) != set(PHASES):
        raise ValueError("Shot manifest must name PRE and POST")
    for phase, label in zip(PHASES, PHASE_LABELS):
        item = obj["checkpoints"][phase]
        if (not isinstance(item, dict)
                or item.get("phase_operator_label") != label
                or item.get("operator_reports_gui_paused") is not True
                or item.get("operator_reports_mem1_mem2_export_same_pause") is not True
                or (phase == "POST" and
                    item.get("operator_reports_game_was_running_between_phases") is not True)):
            raise ValueError("Shot checkpoint pause / phase provenance invalid")
        hashes = item.get("sha256")
        if (not isinstance(hashes, dict) or set(hashes) != {"MEM1", "MEM2"}
                or not all(isinstance(hashes[k], str) and HEX_SHA.fullmatch(hashes[k])
                           for k in ("MEM1", "MEM2"))):
            raise ValueError("Shot checkpoint requires two valid full bank hashes")
    return obj["checkpoints"]


def _approved_bank(folder: Path, filename: str, size: int):
    p = folder / filename
    if p.is_symlink() or not p.is_file() or p.stat().st_size != size:
        raise ValueError("Private shot native bank absent, symlinked or wrong size")
    return p


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot_candidate(read_u32, header: bytes):
    """Transient, NEVER serialized private owner tokens plus triplets."""
    safe, private = selected.analyze_one(read_u32, header)
    if not all(safe.get(k) is True for k in (
            "selected_record_pointer_matches_code_defined_stride",
            "selected_ball_translation_pointer_is_mem2",
            "selected_ball_translation_pointer_selfref_matches_base",
            "source_current_start_translation_pointer_is_mem2",
            "source_current_start_constructor_selfrefs_match",
            "record_candidate_triplet_finite_bounded",
            "nested_ball_candidate_triplet_finite_bounded",
            "source_current_start_triplet_finite_bounded",
    )):
        raise ValueError("Shot selected record / ball / current start gate failed")
    idx = private["selected_index"]
    pm = read_u32(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    record = pm + 4 + idx * roster.ROSTER_STRIDE
    if read_u32(pm + 0x334) != record:
        raise ValueError("Source selected player changed inside snapshot")
    ball = read_u32(record + 0x88)
    field = read_u32(roster.GOLF_FIELD_STATIC)
    start = read_u32(field + 0x50)
    return {
        "slot": idx, "hole": private["hole"],
        "owner": (pm, record, ball, field, start),
        "record_words": private["record"],
        "ball_words": private["ball"],
        "start_words": private["start"],
        "source_gates": True,
    }


def summarize(before: dict, after: dict, *,
              mem1_changed: bool, mem2_changed: bool) -> dict:
    """Only categorical bitwise component comparisons and abstention flags."""
    if type(mem1_changed) is not bool or type(mem2_changed) is not bool:
        raise ValueError("Missing full bank comparison provenance")
    for s in (before, after):
        if (s.get("source_gates") is not True or
                type(s.get("slot")) is not int or not 0 <= s["slot"] < 4 or
                type(s.get("hole")) is not int or not 0 <= s["hole"] < 9 or
                not isinstance(s.get("owner"), tuple) or len(s["owner"]) != 5 or
                any(not isinstance(s.get(k), tuple) or len(s[k]) != 3
                    for k in ("record_words", "ball_words", "start_words"))):
            raise ValueError("Shot source candidate unavailable")
    if before["slot"] != after["slot"] or before["hole"] != after["hole"]:
        raise ValueError("Shot changed active record or hole")
    owner_stable = before["owner"] == after["owner"]
    if not owner_stable:
        raise ValueError("Shot changed source owner pointers; no valid comparison")
    change_count = lambda key: sum(
        a != b for a, b in zip(before[key], after[key]))
    changes = {label: change_count(key) for label, key in (
        ("selected_nested_ball", "ball_words"),
        ("selected_player_record", "record_words"),
        ("source_current_start", "start_words"),
    )}
    start_stable = changes["source_current_start"] == 0
    ball_changed = changes["selected_nested_ball"] > 0
    both_banks_changed = mem1_changed and mem2_changed
    plausible = owner_stable and both_banks_changed and start_stable and ball_changed
    return {
        "kind": "local_private_selected_ball_prepost_shot_candidate",
        "schema_version": 1,
        "game_id": "RSPE01",
        "revision": 1,
        "mode": 4,
        "phase_labels": list(PHASES),
        "source_gates_verified_both_phases": True,
        "source_selected_owner_and_slot_stable": True,
        "source_hole_stable": True,
        "both_whole_banks_changed": both_banks_changed,
        "mem1_bank_changed": mem1_changed,
        "mem2_bank_changed": mem2_changed,
        "selected_nested_ball_changed_component_count": changes["selected_nested_ball"],
        "selected_player_record_changed_component_count": changes["selected_player_record"],
        "source_current_start_changed_component_count": changes["source_current_start"],
        "source_current_start_stable": start_stable,
        "selected_nested_ball_changed": ball_changed,
        "selected_record_vs_ball_equal_count_pre":
            sum(a == b for a, b in zip(before["record_words"], before["ball_words"])),
        "selected_record_vs_ball_equal_count_post":
            sum(a == b for a, b in zip(after["record_words"], after["ball_words"])),
        "candidate_change_consistent_with_operator_observed_displacement": plausible,
        "operator_reports_exactly_one_shot_and_visible_displacement": True,
        "operator_reports_pairwise_same_pause": True,
        "operator_reports_same_dolphin_process": True,
        "gameplay_event_independently_proven": False,
        "native_pair_same_guest_frame_verified": False,
        "same_boot_independently_proven": False,
        "ball_motion_world_xyz_verified": False,
        "ball_velocity_verified": False,
        "shot_contact_time_verified": False,
        "swing_power_verified": False,
        "approved_for_model_training": False,
        "allowed_to_publish": False,
        "warning": (
            "Before/after preserved GUI banks test only source-selected "
            "3-word field contrasts; even a difference is not an emulator-"
            "frame-accurate physical ball measurement. The human event and "
            "same-pause provenance remain operator-attested. If the game "
            "already reset the ball, unchanged bits are INCONCLUSIVE, not "
            "proof that the ball never moved."
        ),
    }


def run_local(folder: Path) -> dict:
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Shot folder missing or symlinked")
    root = selected.DATA_ROOT.resolve(strict=True)
    parent = folder.resolve(strict=True)
    if parent == root or not parent.is_relative_to(root):
        raise ValueError("Shot folder is outside ignored private Data root")
    m = _manifest(parent)
    snapshots, sha = [], []
    with ExitStack() as stack:
        for phase in PHASES:
            files = [
                _approved_bank(parent, f"{phase}-MEM1.bin", roster.MEM1_SIZE),
                _approved_bank(parent, f"{phase}-MEM2.bin", roster.MEM2_SIZE),
            ]
            digests = {bank: _sha256(path) for bank, path in zip(("MEM1", "MEM2"), files)}
            if any(digests[bank] != m[phase]["sha256"][bank]
                   for bank in ("MEM1", "MEM2")):
                raise ValueError("Shot private checkpoint modified since capture")
            images = []
            for path in files:
                fh = stack.enter_context(path.open("rb"))
                images.append(stack.enter_context(
                    mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)))
            rd = roster.TwoBankReader(*images)
            snapshots.append(snapshot_candidate(rd.u32, rd.header()))
            sha.append(digests)
    return summarize(snapshots[0], snapshots[1],
                     mem1_changed=sha[0]["MEM1"] != sha[1]["MEM1"],
                     mem2_changed=sha[0]["MEM2"] != sha[1]["MEM2"])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run_local(args.private_root)
    except (OSError, ValueError, KeyError, TypeError, OverflowError):
        print("Private PRE/POST source-gated shot audit FAILED CLOSED: "
              "check preserved same-pause native bank manifest and source "
              "identity. No private file paths, addresses or words disclosed.",
              file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
