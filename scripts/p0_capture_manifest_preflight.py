#!/usr/bin/env python3
"""Read-only P0 MEM1/MEM2 capture provenance preflight; optional LOCAL private manifest.

This NEVER launches Dolphin, reads live process memory, interprets vectors,
publishes RAM, or approves physical/ML labels. Use source-gated field decoders
separately, after verifying the exact game/revision and owner/shot controls.
The manifest is a PRIVATE local artifact; never commit or upload it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

MEM1_SIZE = 24 * 1024 * 1024
MEM2_SIZE = 64 * 1024 * 1024
MAX_PAIRS = 20
MANIFEST_NAME = "p0-capture-manifest-PRIVATE.json"
_NUMBERED = re.compile(r"([1-9][0-9]?)\.(1|2)\.raw", re.ASCII)
_CHECKPOINT = re.compile(r"([A-Z][A-Z0-9_-]{0,15})-MEM([12])\.bin", re.ASCII)


def _safe_file(path: Path, expected_size: int) -> dict:
    """Hash a fixed-size original file; refuse links/changes between stat calls."""
    first = path.lstat()
    if not stat.S_ISREG(first.st_mode) or first.st_size != expected_size:
        raise ValueError("Capture file not a regular native-size bank")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        before = (first.st_dev, first.st_ino, first.st_size, first.st_mtime_ns)
        actual = (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
        if not stat.S_ISREG(opened.st_mode) or before != actual:
            raise ValueError("Capture identity changed before read")
        digest = hashlib.sha256()
        with os.fdopen(fd, "rb", closefd=False) as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
        end = os.fstat(fd)
        final = path.lstat()
        for item in (end, final):
            if (not stat.S_ISREG(item.st_mode) or
                (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns) != before):
                raise ValueError("Capture changed during read")
        return {"file": path.name, "bytes": expected_size, "sha256": digest.hexdigest()}
    finally:
        os.close(fd)


def _discover(root: Path, mode: str, sizes: tuple[int, int]) -> list[dict]:
    if mode not in {"numbered", "checkpoint"}:
        raise ValueError("Unknown capture naming format")
    pattern = _NUMBERED if mode == "numbered" else _CHECKPOINT
    matched: dict[str, dict[str, Path]] = {}
    for path in root.iterdir():
        label = pattern.fullmatch(path.name)
        if label is None:
            continue
        phase, bank_hint = label.groups()
        slot = matched.setdefault(phase, {})
        if bank_hint in slot:
            raise ValueError("Duplicate bank in capture phase")
        slot[bank_hint] = path
    if not 1 <= len(matched) <= MAX_PAIRS:
        raise ValueError("Capture cohort must contain 1-20 paired phases")

    result = []
    # Numeric phase order is explicit rather than filename lexical order.
    order = sorted(matched, key=lambda s: int(s) if mode == "numbered" else s)
    for phase in order:
        files = matched[phase]
        if set(files) != {"1", "2"}:
            raise ValueError("Incomplete MEM1/MEM2 capture pair")
        if mode == "numbered":
            # The historical .1/.2 extensions are not authoritative bank types.
            sizes_by_file = {n: p.lstat().st_size for n, p in files.items()}
            if sorted(sizes_by_file.values()) != sorted(sizes):
                raise ValueError("Numbered pair lacks exact native MEM1/MEM2 sizes")
            ordered = (next(p for p in files.values() if p.lstat().st_size == sizes[0]),
                       next(p for p in files.values() if p.lstat().st_size == sizes[1]))
        else:
            ordered = (files["1"], files["2"])
        mem1 = _safe_file(ordered[0], sizes[0])
        mem2 = _safe_file(ordered[1], sizes[1])
        result.append({"phase": str(phase), "MEM1": mem1, "MEM2": mem2})
    return result


def audit_capture_root(root: Path, mode: str, *,
                       sizes: tuple[int, int] = (MEM1_SIZE, MEM2_SIZE)) -> dict:
    """Local-only integrity inventory; no claim of synchronized guest frames."""
    if (len(sizes) != 2 or type(sizes[0]) is not int
            or type(sizes[1]) is not int or min(sizes) <= 0
            or sizes[0] == sizes[1]):
        raise ValueError("Invalid bank-size contract")
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Capture root absent or linked")
    # No recursive file discovery: operator supplies the precise private cohort.
    pairs = _discover(root.resolve(strict=True), mode, sizes)
    seen = {"MEM1": set(), "MEM2": set()}
    duplicates = {"MEM1": 0, "MEM2": 0}
    for pair in pairs:
        for bank in ("MEM1", "MEM2"):
            digest = pair[bank]["sha256"]
            if digest in seen[bank]:
                duplicates[bank] += 1
            seen[bank].add(digest)
    return {
        "kind": "local-private-wii-golf-bank-inventory",
        "schema_version": 1,
        "game_id": "RSPE01",
        "revision": 1,
        "naming_mode": mode,
        "pairs": pairs,
        "duplicate_full_bank_sha_counts": duplicates,
        "runtime_source_identity_verified": False,
        "same_game_boot_verified": False,
        "same_shot_verified": False,
        "guest_frame_verified": False,
        "rendered_ball_identity_verified": False,
        "training_approved": False,
    }


def _inside_git_checkout(root: Path) -> bool:
    return any((parent / ".git").exists() for parent in (root, *root.parents))


def write_local_manifest(root: Path, report: dict) -> None:
    """Create once in an OUTSIDE-REPO private folder; never overwrite."""
    resolved = root.resolve(strict=True)
    if root.is_symlink() or _inside_git_checkout(resolved):
        raise ValueError("Private manifest output must stay outside a Git checkout")
    target = resolved / MANIFEST_NAME
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(target, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            target.unlink()
        except OSError:
            pass
        raise


def sanitized_summary(report: dict) -> dict:
    """ONLY counts/booleans: never names, hashes, pointers, phase labels or paths."""
    return {
        "kind": "p0-capture-inventory-preflight",
        "game_id_declared_not_authenticated": report["game_id"],
        "naming_mode": report["naming_mode"],
        "pairs_with_native_size_and_stable_hash": len(report["pairs"]),
        "duplicate_MEM1_full_bank_count": report["duplicate_full_bank_sha_counts"]["MEM1"],
        "duplicate_MEM2_full_bank_count": report["duplicate_full_bank_sha_counts"]["MEM2"],
        "guest_frame_verified": False,
        "rendered_ball_identity_verified": False,
        "training_approved": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--mode", choices=("numbered", "checkpoint"), required=True)
    parser.add_argument("--write-private-manifest", action="store_true",
                        help="Write hashes to an outside-Git PRIVATE local sidecar.")
    args = parser.parse_args(argv)
    try:
        report = audit_capture_root(args.private_root, args.mode)
        if args.write_private_manifest:
            write_local_manifest(args.private_root, report)
    except (OSError, ValueError, TypeError, OverflowError):
        print("P0 capture inventory REFUSED: pair/size/identity/private-output gate failed.",
              file=sys.stderr)
        return 2
    print(json.dumps(sanitized_summary(report), sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
