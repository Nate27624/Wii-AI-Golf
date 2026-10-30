"""Private KCL source-attribute overlay for an UNCHANGED source-coordinate OBJ.

Only the inspector applies palette/shading. This small JSON is not geometry,
not texture, not training evidence, and never mutates the original OBJ file.
The source exporter must prove SHA + original KCL face-index alignment first.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import subprocess

from .terrain import TerrainError, TerrainMesh

MAX_LABEL_BYTES = 200_000
LABEL_KIND = "P0_PRIVATE_KCL_FACE_LABELS"
MAX_FACES = 30_000


def _ignored_and_untracked(path: Path) -> bool:
    """Strict private Data/derived or standalone outside-Git Projects.

    The project-local geometry OBJ can live directly in D:\Projects; its
    labels stay beside it, and the inspector verifies the OBJ SHA separately.
    """
    folder = path.parent
    if (path.is_symlink() or folder.is_symlink()
            or not path.name.endswith("-PRIVATE.json")
            or not folder.is_dir()):
        return False
    in_private_data = (
        folder.name == "derived" and folder.parent.name == "Wii-AI-Golf-Data"
        and not folder.parent.is_symlink()
    )
    in_standalone_projects = folder.name == "Projects"
    if not in_private_data and not in_standalone_projects:
        return False
    containing_git = any((parent / ".git").exists()
                         for parent in (folder, *folder.parents))
    if in_standalone_projects:
        # No Git index exception for a user-owned root Projects directory;
        # the output is private and is never part of any repository.
        return not containing_git
    if not containing_git:
        return True
    try:
        ignored = subprocess.run(
            ["git", "-C", str(folder), "check-ignore", "--no-index", "-q",
             "--", str(path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False, timeout=5,
        )
        indexed = subprocess.run(
            ["git", "-C", str(folder), "ls-files", "--cached", "-z",
             "--", str(path)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=False, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return (ignored.returncode == 0 and indexed.returncode == 0
            and indexed.stdout == b"")

def apply_private_surface_labels(mesh: TerrainMesh, filename: str | Path) -> TerrainMesh:
    """Return a new in-memory mesh view, with original OBJ vertices unchanged."""
    path = Path(filename)
    if (path.suffix.lower() != ".json" or not path.is_file()
            or not _ignored_and_untracked(path)):
        raise TerrainError("Private source labels must be in standalone Projects or ignored/untracked Data/derived")
    path = path.resolve(strict=True)
    before = path.stat()
    if not 1 <= before.st_size <= MAX_LABEL_BYTES:
        raise TerrainError("Private source label file exceeds safe size limit")
    data = path.read_bytes()
    after = path.stat()
    if (len(data) != before.st_size or after.st_size != before.st_size
            or after.st_mtime_ns != before.st_mtime_ns):
        raise TerrainError("Private labels changed while reading")
    try:
        obj = json.loads(data.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        raise TerrainError("Private surface labels not strict ASCII JSON") from None
    if not isinstance(obj, dict) or set(obj) != {
        "kind", "version", "geometry_obj_sha256", "source_hole_index",
        "faces", "source_attributes", "training_approved",
        "allowed_to_publish",
    }:
        raise TerrainError("Private source label schema mismatch")
    if (obj["kind"] != LABEL_KIND or type(obj["version"]) is not int
            or obj["version"] != 1 or obj["training_approved"] is not False
            or obj["allowed_to_publish"] is not False):
        raise TerrainError("Private source labels have unapproved provenance")
    if (obj["geometry_obj_sha256"] != mesh.sha256
            or type(obj["source_hole_index"]) is not int
            or not 0 <= obj["source_hole_index"] < 32
            or type(obj["faces"]) is not int
            or obj["faces"] != len(mesh.faces)
            or not 1 <= obj["faces"] <= MAX_FACES):
        raise TerrainError("Private labels do not match the loaded OBJ's SHA/faces")
    attrs = obj["source_attributes"]
    if (not isinstance(attrs, list) or len(attrs) != len(mesh.faces)
            or any(type(x) is not int or not 0 <= x <= 0xFFFF for x in attrs)):
        raise TerrainError("Private labels have invalid original KCL attributes")
    # No OBJ writes: the inspector-only face-material mapping is immutable.
    return replace(mesh, face_materials=tuple(attrs))
