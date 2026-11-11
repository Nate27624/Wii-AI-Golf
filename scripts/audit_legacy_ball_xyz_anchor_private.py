#!/usr/bin/env python3
"""Falsify a published Rev0 golf-ball XYZ address against Rev1 native RAM.

READ ONLY. Never changes a guest byte, launches Dolphin, or uploads a result.
The historical address is not asserted to be valid for RSPE01 Revision 1.
Outputs categorical counts/booleans only; all native bytes and addresses local.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

MEM1_BASE, MEM1_SIZE = 0x80000000, 24 * 1024 * 1024
MEM2_BASE, MEM2_SIZE = 0x90000000, 64 * 1024 * 1024
LEGACY_V0_XYZ = 0x91BF3E94  # v1.00 only, public third-party cheat, NOT Rev1 locator
PHASES = {
    "B0": "idle_baseline", "B1": "idle_delayed",
    "B2": "wasd_aim_only", "B3": "idle_after_aim",
}
PRIVATE_ROOT_NAME = "Wii-AI-Golf-Data"


class InvalidEvidence(Exception):
    """Avoid forwarding native paths, addresses, or decoded memory contents."""


def require(condition: bool, _reason: str = "") -> None:
    if not condition:
        raise InvalidEvidence


def in_bank(addr: int, n: int, bank: int, size: int) -> bool:
    return type(addr) is int and n > 0 and addr % 4 == 0 and bank <= addr < bank + size and addr + n <= bank + size


class Banks:
    def __init__(self, mem1, mem2):
        self.mem1, self.mem2 = mem1, mem2

    def read(self, address: int, count: int) -> bytes:
        if in_bank(address, count, MEM1_BASE, MEM1_SIZE):
            file, offset = self.mem1, address - MEM1_BASE
        elif in_bank(address, count, MEM2_BASE, MEM2_SIZE):
            file, offset = self.mem2, address - MEM2_BASE
        else:
            raise InvalidEvidence
        file.seek(offset)
        payload = file.read(count)
        require(len(payload) == count)
        return payload

    def u32(self, addr: int) -> int:
        return struct.unpack(">I", self.read(addr, 4))[0]

    def words(self, addr: int) -> tuple[int, int, int]:
        return struct.unpack(">III", self.read(addr, 12))


def finite_xyz(words: tuple[int, int, int]) -> bool:
    values = (struct.unpack(">f", struct.pack(">I", w))[0] for w in words)
    return all(math.isfinite(v) and abs(v) <= 100_000 for v in values)


def matching_components(a, b) -> int:
    require(len(a) == len(b) == 3)
    return sum(x == y for x, y in zip(a, b))


def read_source_identity(banks: Banks) -> dict:
    # Gate exact executable/game revision and owner chain before any comparison.
    disc = banks.read(MEM1_BASE, 8)
    require(disc[:6] == b"RSPE01" and disc[7] == 1)
    manager = banks.u32(0x804BF4D8)
    require(in_bank(manager, 0x20, MEM1_BASE, MEM1_SIZE))
    scene = banks.u32(manager + 0x0C)
    require(in_bank(scene, 0xA0, MEM2_BASE, MEM2_SIZE))
    require(banks.u32(manager + 0x18) == 5
            and banks.u32(scene + 0x1C) == 5
            and banks.u32(scene + 0x20) == manager
            and banks.u32(scene + 0x54) == 2)
    config = banks.u32(0x804BF8C4)
    require(in_bank(config, 0x9C, MEM2_BASE, MEM2_SIZE))
    hole = banks.u32(config + 0x98)
    require(banks.u32(config + 0x94) == 4 and 0 <= hole <= 8)
    pm = banks.u32(0x804BF8D0)
    require(in_bank(pm, 0x340, MEM2_BASE, MEM2_SIZE))
    require(0x803C7DD0 <= banks.u32(pm) < 0x803C7DE0)
    rec = banks.u32(pm + 0x334)
    slots = [i for i in range(4) if rec == pm + 4 + 0xCC * i]
    require(len(slots) == 1 and in_bank(rec, 0xCC, MEM2_BASE, MEM2_SIZE))
    ball = banks.u32(rec + 0x88)
    require(in_bank(ball, 0x1AC, MEM2_BASE, MEM2_SIZE))
    require(0x803C7918 <= banks.u32(ball) < 0x803C7A50)
    translation = banks.u32(ball + 0x4C)
    require(translation == ball + 0x30)
    field = banks.u32(0x804BF868)
    require(in_bank(field, 0x58, MEM2_BASE, MEM2_SIZE))
    tee = banks.u32(field + 0x50)
    require(in_bank(tee, 0x50, MEM2_BASE, MEM2_SIZE))
    require(banks.u32(tee + 0x4C) == tee + 0x30
            and banks.u32(tee + 0x48) == tee + 0x0C)
    pin = banks.u32(field + 0x44)
    require(in_bank(pin, 0x50, MEM2_BASE, MEM2_SIZE))
    require(banks.u32(pin + 0x4C) == pin + 0x30)
    legacy = banks.words(LEGACY_V0_XYZ)
    selected = banks.words(translation)
    rec_initial = banks.words(rec + 0x54)
    rec_start = banks.words(rec + 0x60)
    tee_vec = banks.words(tee + 0x30)
    pin_vec = banks.words(pin + 0x30)
    for vec in (selected, rec_initial, rec_start, tee_vec, pin_vec):
        require(finite_xyz(vec))
    # No assumption that an absolute Rev0 cheat address is a valid Rev1 float.
    return {
        "_identity": (manager, scene, config, pm, rec, ball, translation,
                      field, tee, pin, hole, slots[0]),
        "_legacy_words": legacy,
        "_selected_words": selected,
        "_record_words": rec_initial,
        "_tee_words": tee_vec,
        "historical_triplet_finite_bounded": finite_xyz(legacy),
        "historical_location_is_source_selected_ball_translation":
            LEGACY_V0_XYZ == translation,
        "historical_matches_selected_ball_components": matching_components(legacy, selected),
        "historical_matches_record_initial_components": matching_components(legacy, rec_initial),
        "historical_matches_record_start_components": matching_components(legacy, rec_start),
        "historical_matches_tee_components": matching_components(legacy, tee_vec),
        "historical_matches_pin_components": matching_components(legacy, pin_vec),
        "selected_source_vector_equals_tee_components": matching_components(selected, tee_vec),
    }


def classify(snapshots: list[dict]) -> dict:
    require(1 <= len(snapshots) <= 4)
    first = snapshots[0]
    require(all(s["_identity"] == first["_identity"] for s in snapshots[1:]))
    candidate_changed = [matching_components(first["_legacy_words"], s["_legacy_words"])
                         for s in snapshots[1:]]
    selected_changed = [matching_components(first["_selected_words"], s["_selected_words"])
                        for s in snapshots[1:]]
    # Deliberately do not interpret B0–B3 as pre-contact/flight/settled.
    return {
        "kind": "S002-LEGACY-REV0-TO-REV1-BALL-XYZ-ANCHOR-OFFLINE",
        "schema_version": 1,
        "game_id": "RSPE01",
        "capture_revision": 1,
        "historical_cheat_revision": 0,
        "historical_address_cross_version_verified": False,
        "source_selected_owner_gates_passed": True,
        "snapshot_count": len(snapshots),
        "phase_identity_unchanged": True,
        "historical_triplet_finite_bounded_all": all(s["historical_triplet_finite_bounded"] for s in snapshots),
        "legacy_equals_resolved_ball_vector_all": all(
            s["historical_location_is_source_selected_ball_translation"] for s in snapshots),
        "legacy_selected_component_matches": [
            s["historical_matches_selected_ball_components"] for s in snapshots],
        "legacy_tee_component_matches": [
            s["historical_matches_tee_components"] for s in snapshots],
        "legacy_pin_component_matches": [
            s["historical_matches_pin_components"] for s in snapshots],
        "selected_tee_component_matches": [
            s["selected_source_vector_equals_tee_components"] for s in snapshots],
        "legacy_changed_components_from_first": [3 - x for x in candidate_changed],
        "source_selected_changed_components_from_first": [3 - x for x in selected_changed],
        "comparison_class": "unverified_legacy_version_address_only",
        "confirmed_inflight_ball_xyz": False,
        "verified_physical_axes_or_units": False,
        "same_guest_frame_verified": False,
        "shot_motion_observed_in_this_study": False,
        "ball_velocity_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
        "github_observation": "NOT_UPLOADED_REQUIRES_S000_S002_ALLOWLIST",
    }


def _trusted_path(base: Path, path: Path) -> Path:
    require(base.is_dir() and not base.is_symlink() and base.name == PRIVATE_ROOT_NAME)
    require(path.is_dir() and not path.is_symlink() and path.resolve().is_relative_to(base.resolve()))
    return path


def _check_file(path: Path, expected_size: int, digest: str) -> None:
    require(path.is_file() and not path.is_symlink())
    require(path.stat().st_size == expected_size)
    require(type(digest) is str and len(digest) == 64 and
            all(c in "0123456789abcdefABCDEF" for c in digest))
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            part = stream.read(1024 * 1024)
            if not part:
                break
            sha.update(part)
    require(sha.hexdigest().lower() == digest.lower())


def audit(session: Path, data_root: Path, phases: list[str]) -> dict:
    _trusted_path(data_root, session)
    require(phases and len(phases) == len(set(phases)) and all(p in PHASES for p in phases))
    mf = session / "checkpoint-manifest-PRIVATE.json"
    require(mf.is_file() and not mf.is_symlink() and mf.stat().st_size <= 1024 * 1024)
    try:
        manifest = json.loads(mf.read_text(encoding="utf-8-sig"))
    except (ValueError, UnicodeError):
        raise InvalidEvidence from None
    require(manifest.get("schema_version") == 1 and
            manifest.get("kind") == "local-private-golf-paired-checkpoints")
    result = []
    for phase in phases:
        info = manifest.get("checkpoints", {}).get(phase)
        require(isinstance(info, dict) and info.get("phase_operator_label") == PHASES[phase])
        require(info.get("operator_reports_gui_paused") is True
                and info.get("scene_source_chain_gated") is True
                and info.get("native_sizes_valid") is True
                and info.get("observed_game_mode") == 4)
        try:
            checksums = info["sha256"]
        except (KeyError, TypeError):
            raise InvalidEvidence from None
        p1, p2 = session / f"{phase}-MEM1.bin", session / f"{phase}-MEM2.bin"
        _check_file(p1, MEM1_SIZE, checksums.get("MEM1"))
        _check_file(p2, MEM2_SIZE, checksums.get("MEM2"))
        with p1.open("rb") as a, p2.open("rb") as b:
            result.append(read_source_identity(Banks(a, b)))
    safe = classify(result)
    safe["native_bank_sha256_verified"] = True
    safe["phase_labels"] = phases
    return safe


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_data = Path(__file__).resolve().parents[2] / PRIVATE_ROOT_NAME
    parser.add_argument("--data-root", type=Path, default=default_data)
    parser.add_argument("--private-session", type=Path)
    parser.add_argument("--phases", nargs="+", choices=tuple(PHASES), default=["B0", "B1", "B2", "B3"])
    args = parser.parse_args(argv)
    session = args.private_session or args.data_root / "ball-study-20261027-212633"
    try:
        result = audit(session, args.data_root, args.phases)
    except (InvalidEvidence, OSError, TypeError, AttributeError, KeyError, struct.error, ValueError):
        print("S002 LEGACY BALL XYZ: ABSTAIN — private source/revision/provenance/bounds gate failed; no bytes or paths printed.", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
