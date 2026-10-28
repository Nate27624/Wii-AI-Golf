"""Fail-closed original-archive provenance gate for S002 #236 writer-input analysis.

The #236 analyzer checks every file before/after local sampling, but does not
compare each file to the original numbered-capture manifest. This additive
wrapper checks all 14 original banks against the #231 manifest BEFORE and AFTER
running #236. Never prints file paths, SHA values, RAM, or raw float/word data.

No Dolphin launch, shot, memory write, score claim, or training approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

_SCRIPTS = str(Path(__file__).resolve().parent)
if _SCRIPTS in sys.path:
    sys.path.remove(_SCRIPTS)
sys.path.insert(0, _SCRIPTS)

import audit_p0_inflight_vs_b0_private as source
import audit_golf_two_bank_roster_private as roster
import audit_p0_seven_writer_inputs_private as writer

SIZES = (roster.MEM1_SIZE, roster.MEM2_SIZE)
PHASES = tuple(range(1, 8))
ARCHIVE_KIND = "p0-private-numbered-capture-inventory"


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_original_archive(archive: Path) -> tuple[Path, str]:
    """Validate exactly seven numbered pairs against their local original manifest.

    The returned manifest digest is an *internal* change detector, not a
    public signature or proof of screenshot/game-frame association.
    """
    root = source.selected.DATA_ROOT.resolve(strict=True)
    folder = source._under_data(archive, root)
    if folder.parent != root / "captures":
        raise ValueError("not a directly preserved private capture archive")
    if not (folder.name.startswith("p0-new-cohort-")
            and folder.name.endswith("-PRIVATE")):
        raise ValueError("unexpected preserved archive kind")
    manifest_path = folder / "manifest-PRIVATE.json"
    if (manifest_path.is_symlink() or not manifest_path.is_file()
            or not 0 < manifest_path.stat().st_size <= 65536):
        raise ValueError("invalid private archive manifest")
    manifest_digest = _hash(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if type(manifest) is not dict:
        raise ValueError("manifest not an object")
    if (manifest.get("kind") != ARCHIVE_KIND
            or manifest.get("training_approved") is not False
            or manifest.get("human_phase_file_mapping_verified") is not False
            or type(manifest.get("capture_count")) is not int
            or manifest["capture_count"] != 7
            or type(manifest.get("capture_numbers")) is not list
            or manifest["capture_numbers"] != list(PHASES)
            or type(manifest.get("captures")) is not list
            or len(manifest["captures"]) != 7):
        raise ValueError("unexpected archive identity, count, or claims")
    seen = set()
    for capture in manifest["captures"]:
        if type(capture) is not dict:
            raise ValueError("invalid capture entry")
        phase = capture.get("capture_number")
        if type(phase) is not int or phase not in PHASES or phase in seen:
            raise ValueError("duplicate or invalid phase")
        seen.add(phase)
        banks = capture.get("banks")
        if type(banks) is not list or len(banks) != 2:
            raise ValueError("incomplete native bank pair")
        for index, entry in enumerate(banks):
            if type(entry) is not dict:
                raise ValueError("invalid bank descriptor")
            filename = f"{phase}.{index + 1}.raw"
            if (entry.get("file") != filename
                    or entry.get("bank") != ("MEM1", "MEM2")[index]
                    or type(entry.get("bytes")) is not int
                    or entry["bytes"] != SIZES[index]
                    or entry.get("copy_verified") is not True):
                raise ValueError("bank metadata inconsistent with original pairing")
            sha = entry.get("sha256")
            if type(sha) is not str or re.fullmatch(r"[0-9A-Fa-f]{64}", sha) is None:
                raise ValueError("invalid original SHA descriptor")
            bank_path = source._file(folder, filename, SIZES[index])
            if _hash(bank_path) != sha.lower():
                raise ValueError("archive bank differs from original manifest")
    if seen != set(PHASES):
        raise ValueError("incomplete numbered cohort")
    if _hash(manifest_path) != manifest_digest:
        raise ValueError("manifest changed during validation")
    return folder, manifest_digest


def run_local(archive: Path) -> dict:
    folder, expected_manifest_digest = verify_original_archive(archive)
    report = writer.run_local(folder)
    folder_after, manifest_digest_after = verify_original_archive(archive)
    if folder_after != folder or manifest_digest_after != expected_manifest_digest:
        raise ValueError("archive manifest changed while analyzing")
    if (type(report) is not dict
            or report.get("approved_for_training") is not False
            or report.get("allowed_to_publish") is not False
            or report.get("sample_count_source_gated") != 7):
        raise ValueError("writer output lacks mandatory source or safety flags")
    return {
        **report,
        "original_seven_archive_14_bank_manifest_sha_matched_before_after": True,
        "archive_manifest_unchanged_during_source_analysis": True,
        "human_phase_mapping_independently_verified": False,
        "rendered_ball_actor_or_game_frames_verified": False,
        "approved_for_training": False,
        "allowed_to_publish": False,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        result = run_local(args.archive)
    except (OSError, ValueError, KeyError, TypeError, OverflowError,
            json.JSONDecodeError):
        print("P0_WRITER_MANIFEST_ABSTAIN: private archive identity, 14-bank SHA, "
              "source selection or safety guard failed. No evidence promoted.",
              file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
