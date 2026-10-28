#!/usr/bin/env python3
"""P0 read-only identity check of TWO independently archived airborne bank pairs.

Do not infer a single physics frame or physical XYZ even if both bank files
are byte-for-byte identical. Print ONLY boolean/count evidence, not RAM, SHA,
private paths, archive IDs, guest pointers or numeric float positions.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
from pathlib import Path
import re
import sys

BANKS = (
    ("MEM1", "mem1.raw", "FLIGHT-MEM1.bin", 24 * 1024 * 1024),
    ("MEM2", "mem2.raw", "FLIGHT-MEM2.bin", 64 * 1024 * 1024),
)
HUMAN_ARCHIVE = "in-flight-human-20261028-054537477"
PRIVATE_COPY_PATTERN = "p0-airborne-*-PRIVATE"
LEFT_MANIFEST = "manifest-PRIVATE.json"
RIGHT_PROVENANCE = "provenance-PRIVATE.json"
SHA_HEX = re.compile(r"^[0-9a-fA-F]{64}$")


class Abstain(Exception):
    pass


def gate(ok: bool) -> None:
    if not ok:
        raise Abstain


def checked_archive(root: Path, path: Path) -> Path:
    gate(root.name == "captures" and root.is_dir() and not root.is_symlink())
    gate(path.is_dir() and not path.is_symlink())
    gate(path.parent == root and path != root)
    gate(path.resolve(strict=True).parent == root.resolve(strict=True))
    return path


def checked_file(folder: Path, name: str, expected_bytes: int) -> Path:
    path = folder / name
    gate(path.is_file() and not path.is_symlink()
         and path.stat().st_size == expected_bytes)
    return path


def checked_json(folder: Path, name: str, limit: int = 65536) -> dict:
    p = folder / name
    gate(p.is_file() and not p.is_symlink()
         and 8 <= p.stat().st_size <= limit)
    try:
        body = json.loads(p.read_text(encoding="utf-8-sig"))
    except (ValueError, UnicodeError):
        raise Abstain from None
    gate(type(body) is dict)
    return body


def digest_file(path: Path) -> bytes:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.digest()


def left_manifest_sha(manifest: dict, label: str, file: str, nbytes: int) -> bytes:
    gate(manifest.get("kind") == "private-human-observed-in-flight-dolphin-dump")
    gate(manifest.get("banks_same_physics_frame_verified") is False
         and manifest.get("ball_xyz_verified") is False
         and manifest.get("training_approved") is False)
    entries = manifest.get("files")
    gate(type(entries) is list and len(entries) == 2)
    matches = [
        item for item in entries
        if type(item) is dict and item.get("file") == file
    ]
    gate(len(matches) == 1)
    entry = matches[0]
    value = entry.get("sha256")
    gate(entry.get("bytes") == nbytes
         and entry.get("copy_verified") is True
         and type(value) is str and bool(SHA_HEX.fullmatch(value)))
    return bytes.fromhex(value)


def compare_archives(
    root: Path,
    left: Path,
    right: Path,
    *,
    banks=BANKS,
    left_manifest_name=LEFT_MANIFEST,
    right_manifest_name=RIGHT_PROVENANCE,
) -> dict:
    # No search beyond a single known ignored captures folder.
    gate(len(banks) == 2 and banks[0][0] == "MEM1"
         and banks[1][0] == "MEM2")
    left = checked_archive(root, left)
    right = checked_archive(root, right)
    gate(left != right)
    manifest = checked_json(left, left_manifest_name)
    # Right metadata schema is from a DIFFERENT agent and is not yet source
    # audited; existence and JSON syntax are checked, but not trusted as a
    # verified provenance assertion.
    provenance = checked_json(right, right_manifest_name)
    gate(len(provenance) <= 100)  # bounded metadata only
    equality = {}
    for label, left_name, right_name, expected_size in banks:
        gate(expected_size > 0)
        l = checked_file(left, left_name, expected_size)
        r = checked_file(right, right_name, expected_size)
        ldigest = digest_file(l)
        rdigest = digest_file(r)
        gate(hmac.compare_digest(ldigest, left_manifest_sha(
            manifest, label, left_name, expected_size
        )))
        equality[label] = hmac.compare_digest(ldigest, rdigest)

    return {
        "kind": "S002-P0-TWO-AIRBORNE-ARCHIVES-BYTE-IDENTITY",
        "schema_version": 1,
        "left_manifest_hashes_valid": True,
        "right_provenance_json_present": True,
        "right_provenance_hash_schema_verified": False,
        "MEM1_equal": equality["MEM1"],
        "MEM2_equal": equality["MEM2"],
        "both_archives_same_bank_pair_bytes": (
            equality["MEM1"] and equality["MEM2"]
        ),
        "any_bank_different": not all(equality.values()),
        "separate_capture_frame_identity_inferred": False,
        "same_boot_verified": False,
        "both_banks_same_guest_frame_verified": False,
        "source_selected_ball_world_xyz_verified": False,
        "ball_velocity_verified": False,
        "power_ram_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
        "github_observation": "NOT_UPLOADED_NO_TYPED_S000_S002_ADAPTER",
        "note": "Identical SHA256 per bank implies identical archived bytes, not "
                "time-atomic physical game capture or observed ball identity.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--captures-root", type=Path, required=True)
    parser.add_argument("--left-archive", type=Path)
    parser.add_argument("--right-archive", type=Path)
    args = parser.parse_args(argv)
    try:
        root = args.captures_root
        gate(root.name == "captures" and root.is_dir() and not root.is_symlink())
        left = args.left_archive or (root / HUMAN_ARCHIVE)
        if args.right_archive is not None:
            right = args.right_archive
        else:
            matches = [
                p for p in root.glob(PRIVATE_COPY_PATTERN)
                if p.is_dir() and not p.is_symlink()
            ]
            gate(len(matches) == 1)
            right = matches[0]
        result = compare_archives(root, left, right)
    except (OSError, ValueError, TypeError, KeyError, OverflowError,
            AttributeError, Abstain):
        print("P0_DUAL_ARCHIVE_IDENTITY=ABSTAIN_INVALID_PRIVATE_INPUT_OR_MULTIPLE_ARCHIVES",
              file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
