"""PRIVATE B0-stationary vs human-observed in-flight fullbank comparison.

Uses source-checked S002 #160/#163 player->ball and start fields independently
in each snapshot. No Dolphin, bridge, input, writes to RAM, raw floats, game
bytes, runtime pointers, absolute paths, or private hashes on stdout.
Cross-session differences are correlations, NOT physical XYZ or same-frame proof.
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
import audit_selected_ball_four_phase_private as four

MEMBERS = (
    ("record_0x054", "record", 0x54),
    ("record_0x060", "record", 0x60),
    ("ball_nested_plus_0x4c", "nested", 0),
    ("ball_object_0x030", "ball", 0x30),
    ("ball_cache_0x0cc", "ball", 0xCC),
    ("ball_cache_0x0f0", "ball", 0xF0),
    ("ball_cache_0x0fc", "ball", 0xFC),
    ("source_current_start", "start", 0),
)
SIZES = {"mem1.raw": roster.MEM1_SIZE, "mem2.raw": roster.MEM2_SIZE}
PRIVATE_MANIFEST = "manifest-PRIVATE.json"


def _hash_file(path: Path) -> str:
    hashobj = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hashobj.update(chunk)
    return hashobj.hexdigest().lower()


def _under_data(folder: Path, private_root: Path) -> Path:
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError("not a regular private session directory")
    resolved = folder.resolve(strict=True)
    root = private_root.resolve(strict=True)
    if resolved == root or not resolved.is_relative_to(root):
        raise ValueError("private inputs must be nested in ignored Data")
    return resolved


def _file(folder: Path, filename: str, size: int) -> Path:
    p = folder / filename
    if p.is_symlink() or not p.is_file() or p.stat().st_size != size:
        raise ValueError("private bank missing, linked or wrong size")
    return p


def _flight_manifest(folder: Path) -> dict:
    p = folder / PRIVATE_MANIFEST
    if p.is_symlink() or not p.is_file() or p.stat().st_size > 16384:
        raise ValueError("in-flight private manifest missing/oversized")
    manifest = json.loads(p.read_text(encoding="utf-8-sig"))
    if (type(manifest) is not dict
            or manifest.get("kind") != "private-human-observed-in-flight-dolphin-dump"
            or manifest.get("banks_same_physics_frame_verified") is not False
            or manifest.get("ball_xyz_verified") is not False
            or manifest.get("training_approved") is not False
            or type(manifest.get("files")) is not list
            or len(manifest["files"]) != 2):
        raise ValueError("unknown or falsely certified in-flight manifest")
    entries = {}
    for item in manifest["files"]:
        if type(item) is not dict or item.get("file") not in SIZES:
            raise ValueError("unexpected flight bank identity")
        label = item["file"]
        if label in entries:
            raise ValueError("duplicate flight bank")
        if (item.get("bytes") != SIZES[label] or
                item.get("copy_verified") is not True or
                type(item.get("original_modified_utc")) is not str or
                type(item.get("sha256")) is not str or
                len(item["sha256"]) != 64):
            raise ValueError("flight bank manifest identity incomplete")
        entries[label] = item["sha256"].lower()
    if set(entries) != set(SIZES):
        raise ValueError("flight bank pair incomplete")
    for label, digest in entries.items():
        if _hash_file(_file(folder, label, SIZES[label])) != digest:
            raise ValueError("flight bank has changed since preservation")
    return manifest


def _read_triplet(u32, base: int) -> tuple[int, int, int]:
    if roster._bank(base, 12) != "MEM2":
        raise ValueError("source triplet not in full MEM2")
    return tuple(u32(base + 4 * j) for j in range(3))


def _sample(rd: roster.TwoBankReader) -> dict:
    # This independently verifies original RSPE01 Rev1 PPC source, manager,
    # selected index, vtable intervals, golf mode, ball and start chain.
    safe, private = selected.analyze_one(rd.u32, rd.header())
    keys = (
        "selected_record_pointer_matches_code_defined_stride",
        "selected_ball_translation_pointer_is_mem2",
        "source_current_start_translation_pointer_is_mem2",
        "record_candidate_triplet_finite_bounded",
        "nested_ball_candidate_triplet_finite_bounded",
        "source_current_start_triplet_finite_bounded",
        "all_candidate_slots_pairwise_distinct",
    )
    if not all(safe.get(key) is True for key in keys[:-1]):
        raise ValueError("source-gated selected object incomplete")
    u = rd.u32
    pm = u(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    rec = pm + 4 + private["selected_index"] * roster.ROSTER_STRIDE
    if u(pm + 0x334) != rec or u(rec + 0x88) == 0:
        raise ValueError("selected record pointer changed before object comparison")
    ball = u(rec + 0x88)
    nested = u(ball + 0x4C)
    field = u(roster.GOLF_FIELD_STATIC)
    start_obj = u(field + 0x50)
    start = u(start_obj + 0x4C)
    if (roster._bank(ball, 0x108) != "MEM2" or
            roster._bank(rec, roster.ROSTER_STRIDE) != "MEM2" or
            roster._bank(nested, 12) != "MEM2" or
            roster._bank(start, 12) != "MEM2"):
        raise ValueError("full candidate object bounds invalid")
    roots = {"record": rec, "nested": nested, "ball": ball, "start": start}
    triplets = {name: _read_triplet(u, roots[root] + offset)
                for name, root, offset in MEMBERS}
    whole = tuple(u(rec + 4 * j) for j in range(roster.ROSTER_STRIDE // 4))
    if triplets["record_0x054"] != private["record"] or triplets["ball_nested_plus_0x4c"] != private["ball"]:
        raise ValueError("source-selected private triplets disagree")
    return {
        "selected_index": private["selected_index"],
        "hole": private["hole"],
        "triplets": triplets,
        "whole_record": whole,
        "ball_constructor_translation_selfref": safe["selected_ball_translation_pointer_selfref_matches_base"],
        "start_constructor_selfrefs": safe["source_current_start_constructor_selfrefs_match"],
    }


def _diff_components(a, b) -> int:
    return sum(x != y for x, y in zip(a, b))


def compare(b0: dict, flight: dict, *, mem1_diff: bool, mem2_diff: bool) -> dict:
    if (b0["selected_index"] != flight["selected_index"] or
            b0["hole"] != flight["hole"]):
        raise ValueError("different selected owner or hole; not comparable")
    same_keys = tuple(name for name, _, _ in MEMBERS)
    if set(b0["triplets"]) != set(same_keys) or set(flight["triplets"]) != set(same_keys):
        raise ValueError("source triplet set incomplete")
    start_b0 = b0["triplets"]["source_current_start"]
    start_f = flight["triplets"]["source_current_start"]
    rows = {}
    for name in same_keys:
        b, f = b0["triplets"][name], flight["triplets"][name]
        rows[name] = {
            "changed_components_between_stationary_and_airborne": _diff_components(b, f),
            "stationary_components_equal_own_start": sum(x == y for x, y in zip(b, start_b0)),
            "airborne_components_equal_own_start": sum(x == y for x, y in zip(f, start_f)),
            "source_unit_or_physical_meaning_verified": False,
        }
    changed_words = [f"+0x{j * 4:03X}" for j, (a,b) in enumerate(
        zip(b0["whole_record"], flight["whole_record"])) if a != b]
    if len(b0["whole_record"]) != 51 or len(flight["whole_record"]) != 51:
        raise ValueError("expected 51 selected-player words per snapshot")
    start_stable = rows["source_current_start"]["changed_components_between_stationary_and_airborne"] == 0
    ball_ch = rows["ball_nested_plus_0x4c"]["changed_components_between_stationary_and_airborne"]
    rec_ch = rows["record_0x054"]["changed_components_between_stationary_and_airborne"]
    return {
        "kind": "PRIVATE-SANITIZED-B0-VS-HUMAN-IN_FLIGHT-SOURCE-COMPARE",
        "schema_version": 1,
        "game_id": "RSPE01",
        "disc_revision": 1,
        "golf_mode": 4,
        "human_labeled_phases": ["B0_stationary_original", "airborne_operator"],
        "source_gated_both_snapshots": True,
        "selected_slot_and_hole_match": True,
        "whole_bank_differences": {"MEM1": mem1_diff, "MEM2": mem2_diff},
        "candidate_triplet_component_checks": rows,
        "selected_player_record_changed_words_count": len(changed_words),
        "selected_player_record_changed_relative_offsets": changed_words,
        "candidate_ball_triplet_changed_while_start_stable": ball_ch > 0 and start_stable,
        "candidate_record_triplet_changed_while_start_stable": rec_ch > 0 and start_stable,
        "position_confounded_by_different_start": not start_stable,
        "b0_ball_selfref_matches_base": b0["ball_constructor_translation_selfref"],
        "airborne_ball_selfref_matches_base": flight["ball_constructor_translation_selfref"],
        "b0_start_selfrefs_match": b0["start_constructor_selfrefs"],
        "airborne_start_selfrefs_match": flight["start_constructor_selfrefs"],
        "human_airborne_observed": True,
        "mem1_mem2_exports_same_guest_frame_verified": False,
        "same_boot_verified": False,
        "actual_ball_world_xyz_verified": False,
        "ball_velocity_verified": False,
        "impact_frame_verified": False,
        "power_ram_variable_verified": False,
        "approved_for_training": False,
        "allowed_to_publish": False,
        "note": "Only source-relative offsets/counts and bitwise change relationships. Airborne is a human phase annotation; cross-phase change may be time, screen or object cache.",
    }


def run_local(baseline: Path, flight: Path, out: Path | None = None) -> dict:
    private_root = selected.DATA_ROOT.resolve(strict=True)
    b0 = _under_data(baseline, private_root)
    inflight = _under_data(flight, private_root)
    if b0 == inflight:
        raise ValueError("cannot compare same private directory")
    baseline_manifest = four._validate_manifest(b0)
    _flight_manifest(inflight)
    if out is not None and (out.exists() or out.is_symlink()
                            or out.suffix.lower() != ".json"
                            or out.parent.resolve(strict=True) != inflight):
        raise ValueError("optional local sanitized output must be new in flight directory")
    before = [("B0-MEM1.bin", roster.MEM1_SIZE),
              ("B0-MEM2.bin", roster.MEM2_SIZE)]
    after = [("mem1.raw", roster.MEM1_SIZE), ("mem2.raw", roster.MEM2_SIZE)]
    for (name, size), bank in zip(before, ("MEM1", "MEM2")):
        if _hash_file(_file(b0, name, size)) != baseline_manifest["B0"]["sha256"][bank].lower():
            raise ValueError("B0 bank hash does not match original checkpoint manifest")
    with ExitStack() as stack:
        snapshots = []
        for folder, files in ((b0, before), (inflight, after)):
            maps = []
            for name, size in files:
                fp = stack.enter_context(_file(folder, name, size).open("rb"))
                maps.append(stack.enter_context(mmap.mmap(fp.fileno(), 0, access=mmap.ACCESS_READ)))
            snapshots.append(tuple(maps))
        b0bank, fbank = snapshots
        baseline_sample = _sample(roster.TwoBankReader(*b0bank))
        flight_sample = _sample(roster.TwoBankReader(*fbank))
        report = compare(
            baseline_sample, flight_sample,
            mem1_diff=hashlib.sha256(b0bank[0]).digest() != hashlib.sha256(fbank[0]).digest(),
            mem2_diff=hashlib.sha256(b0bank[1]).digest() != hashlib.sha256(fbank[1]).digest(),
        )
    if out is not None:
        with out.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
    return report


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--flight", type=Path, required=True)
    p.add_argument("--output", type=Path)
    args=p.parse_args(argv)
    try:
        result=run_local(args.baseline, args.flight, args.output)
    except (OSError, ValueError, TypeError, KeyError, OverflowError, json.JSONDecodeError):
        print("P0 in-flight source comparison FAILED CLOSED: private manifest, bank layout, Rev1 source, selection or same-scene proof missing. No raw data printed.", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
