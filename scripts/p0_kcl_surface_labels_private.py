#!/usr/bin/env python3
"""Export SHA-bound OGWS surface IDs for the inspector, never an altered OBJ.

Reads only original private SHA-gated capture KCL and verifies unchanged
geometry OBJ's exact v/f records before associating each source prism attr.
Creates a separate PRIVATE JSON with no native coordinates, positions, source
pointers, source bank hashes, or original game binary asset data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import p0_kcl_obj_export_private as base

MAX_JSON_BYTES = 200_000
KIND = "P0_PRIVATE_KCL_FACE_LABELS"


class LabelsGate(ValueError):
    def __init__(self, stage: str):
        super().__init__("private labels provenance or filesystem rejected")
        self.stage = stage


def _check_project_private_path(path: Path, root: Path, *, kind: str) -> Path:
    if (root.name != "Wii-AI-Golf-Data" or root.is_symlink()
            or not root.is_dir()):
        raise LabelsGate("PRIVATE_DATA_ROOT")
    derived = root.resolve(strict=True) / "derived"
    if (not derived.is_dir() or derived.is_symlink()
            or path.parent.is_symlink() or not path.parent.is_dir()
            or path.parent.resolve(strict=True) != derived
            or not path.name.endswith("-PRIVATE." + kind)
            or path.is_symlink()):
        raise LabelsGate("PROJECT_PRIVATE_PATH")
    # A containing Git checkout is acceptable only with explicit ignored &
    # absent-from-index proofs for the exact requested file.
    if any((p / ".git").exists() for p in (derived, *derived.parents)):
        try:
            ignored = subprocess.run(
                ["git", "-C", str(derived), "check-ignore", "--no-index", "-q",
                 "--", str(path)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=5, check=False,
            )
            indexed = subprocess.run(
                ["git", "-C", str(derived), "ls-files", "--cached", "-z",
                 "--", str(path)],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                timeout=5, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise LabelsGate("GIT_PROOF_UNAVAILABLE") from None
        if ignored.returncode != 0:
            raise LabelsGate("GIT_IGNORE_REQUIRED")
        if indexed.returncode != 0 or indexed.stdout:
            raise LabelsGate("GIT_INDEX_NOT_UNTRACKED")
    return derived / path.name


def _mesh_records(blob: bytes) -> tuple[str, ...]:
    # A legacy geometry-only OBJ produced by this repo accepts v/f + comments.
    try:
        text = blob.decode("ascii")
    except UnicodeDecodeError:
        raise LabelsGate("ORIGINAL_OBJ_NON_ASCII") from None
    lines = tuple(line for line in text.splitlines()
                  if line.strip() and not line.lstrip().startswith("#"))
    if not lines or any(not line.startswith(("v ", "f ")) for line in lines):
        raise LabelsGate("ORIGINAL_OBJ_NOT_PLAIN_GEOMETRY")
    return lines


def _read_existing_obj(path: Path) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise LabelsGate("ORIGINAL_OBJ_NOT_REGULAR")
    a = path.stat()
    if not 1 <= a.st_size <= base.MAX_OBJ_BYTES:
        raise LabelsGate("ORIGINAL_OBJ_SIZE")
    blob = path.read_bytes()
    b = path.stat()
    if len(blob) != a.st_size or a.st_mtime_ns != b.st_mtime_ns or a.st_size != b.st_size:
        raise LabelsGate("ORIGINAL_OBJ_CHANGED_DURING_READ")
    return blob


def _safe_new_json(path: Path, blob: bytes) -> None:
    if not 1 <= len(blob) <= MAX_JSON_BYTES:
        raise LabelsGate("LABEL_JSON_SIZE")
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                     | getattr(os, "O_BINARY", 0), 0o600)
    except FileExistsError:
        raise LabelsGate("LABEL_OUTPUT_ALREADY_EXISTS") from None
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(blob)
            out.flush()
            os.fsync(out.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def make_labels(archive: Path, original_obj: Path, output: Path, *,
                capture: int = 5, controls: tuple[int,int] = (1,7)) -> dict:
    from audit_selected_ball_start_link_private import DATA_ROOT
    import audit_p0_seven_numbered_source_pairs_private as seven
    from audit_p0_seven_numbered_source_pairs_private import roster
    if (type(capture) is not int or capture not in range(1,8)
            or len(controls) != 2 or any(type(n) is not int or n not in range(1,8) for n in controls)
            or len({capture,*controls}) != 3):
        raise LabelsGate("CAPTURE_NUMBERS")
    root = DATA_ROOT
    mesh_path = _check_project_private_path(original_obj, root, kind="obj")
    labels_path = _check_project_private_path(output, root, kind="json")
    if labels_path.exists():
        raise LabelsGate("LABEL_OUTPUT_ALREADY_EXISTS")
    original = _read_existing_obj(mesh_path)
    original_sha = hashlib.sha256(original).hexdigest()
    try:
        folders = seven._check_archive(archive)
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        raise LabelsGate("ARCHIVE_SHA") from None
    findings = {}
    for number in (*controls,capture):
        try:
            findings[number] = base._source_qualified_mesh(
                folders, number, seven, roster, keep_mesh=(number == capture))
        except (OSError, ValueError, KeyError, IndexError, TypeError,
                AttributeError, OverflowError):
            raise LabelsGate("SOURCE_OR_FULL_PRISM_GATE") from None
    target = findings[capture]
    if any((findings[n]["hole"] != target["hole"]
            or findings[n]["count"] != target["count"]
            or findings[n]["private_geometry_fingerprint"] != target["private_geometry_fingerprint"])
            for n in controls):
        raise LabelsGate("CROSS_CAPTURE_GEOMETRY")
    attrs = target["attributes_PRIVATE"]
    tris = target["triangles_PRIVATE"]
    if (not 1 <= target["count"] <= base.MAX_OBJ_FACES
            or type(attrs) is not list or len(attrs) != target["count"]
            or any(type(v) is not int or not 0 <= v <= 0xFFFF for v in attrs)):
        raise LabelsGate("ORIGINAL_ATTRIBUTE_CARDINALITY")
    expected = base._obj_bytes(tris)
    if _mesh_records(original) != _mesh_records(expected):
        raise LabelsGate("ORIGINAL_OBJ_FACE_ORDER_OR_COORDINATES")
    payload = {
        "kind": KIND, "version": 1, "geometry_obj_sha256": original_sha,
        "source_hole_index": target["hole"], "faces": target["count"],
        "source_attributes": attrs,
        "training_approved": False, "allowed_to_publish": False,
    }
    encoded = (json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n").encode("ascii")
    # Recheck source originals immediately before output, plus existing OBJ SHA.
    seven._check_archive(archive)
    if hashlib.sha256(_read_existing_obj(mesh_path)).hexdigest() != original_sha:
        raise LabelsGate("ORIGINAL_OBJ_CHANGED_AFTER_SOURCE_READ")
    _safe_new_json(labels_path, encoded)
    return {
        "kind": KIND, "status": "PRIVATE_LABELS_CREATED",
        "source_capture": capture, "control_captures": list(controls),
        "source_hole_index": target["hole"], "faces": target["count"],
        "unique_source_attributes": len(set(attrs)),
        "original_obj_unchanged": True, "original_obj_sha256": original_sha,
        "output_filename": labels_path.name,
        "training_approved": False, "allowed_to_publish": False,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", required=True, type=Path)
    p.add_argument("--original-obj", required=True, type=Path)
    p.add_argument("--labels-output", required=True, type=Path)
    p.add_argument("--capture", type=int, default=5)
    p.add_argument("--controls", type=int, nargs=2, default=(1,7))
    a = p.parse_args(argv)
    try:
        report = make_labels(a.archive, a.original_obj, a.labels_output,
                             capture=a.capture, controls=tuple(a.controls))
        print(json.dumps(report, sort_keys=True))
        return 0
    except LabelsGate as e:
        print(json.dumps({
            "kind": KIND, "status": "ABSTAIN_PRIVATE_LABELS",
            "stage": e.stage, "source_capture": None,
            "original_obj_unchanged": True, "training_approved": False,
            "allowed_to_publish": False,
        }))
        return 4
    except (OSError, ValueError, TypeError, AttributeError, KeyError,
            IndexError, OverflowError):
        print(json.dumps({
            "kind": KIND, "status": "ABSTAIN_PRIVATE_LABELS",
            "stage": "UNCLASSIFIED_SAFE_ABSTAIN", "source_capture": None,
            "original_obj_unchanged": True, "training_approved": False,
            "allowed_to_publish": False,
        }))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
