"""Strict local-only source-qualified Wii Sports Golf tree-position artifact loader.

This is display data for optional experimental 3D markers, NOT native tree
models, physical tree hitboxes, validated visual-course alignment, or labels
for an ML training pipeline. It never touches Dolphin or writes game RAM.

Consumes the separate #411 source-gated offline exporter contract. The JSON
must remain outside Git, in a private Wii-AI-Golf-Data/derived folder.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

MAX_TREE_BYTES = 64 * 1024
SOURCE_TREE_COUNT = 94
EXPECTED_NAME = "golf-tree-positions-source-94-PRIVATE.json"
SCHEMA_KIND = "wii_sports_golf_private_tree_positions_v1"
EXPECTED_FIELDS = frozenset({
    "kind", "schema_version", "game_id", "disc_revision",
    "source_captures", "source_count", "source_element_stride_bytes",
    "source_translation_offset_bytes", "position_frame",
    "tree_positions", "source_positions_bitwise_identical_across_captures",
    "world_visual_alignment_verified", "original_tree_meshes_verified",
    "collision_hitboxes_verified", "training_approved",
})


class TreePositionsError(ValueError):
    """Local tree artifact is missing, unsafe, or fails source-schema checks."""


@dataclass(frozen=True)
class TreePositions:
    """Exact 94 source-coordinate positions; no inferred model dimensions."""

    positions: tuple[tuple[float, float, float], ...]
    sha256: str
    source_name: str
    source_captures: tuple[int, ...] = (1, 5, 7)
    # These deliberately remain false until separately validated elsewhere.
    visual_alignment_verified: bool = False
    tree_models_verified: bool = False
    collision_hitboxes_verified: bool = False
    training_approved: bool = False

    def drawing_positions(self) -> tuple[tuple[float, float, float], ...]:
        """Return the complete 94-point source-frame marker layer."""
        return self.positions


def _unique_object_pairs(pairs: list[tuple[str, object]]) -> dict:
    """Refuse duplicate JSON keys that could obscure provenance or safety flags."""
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise TreePositionsError("Duplicate tree JSON key")
        obj[key] = value
    return obj


def _reject_nonfinite_constant(value: str) -> None:
    raise TreePositionsError("Invalid numeric constant in tree JSON")


def _check_local_path(filename: str | Path) -> Path:
    path = Path(filename)
    if path.name != EXPECTED_NAME or path.suffix.lower() != ".json":
        raise TreePositionsError("Choose the specific source-qualified PRIVATE tree JSON")
    if not path.is_file() or path.is_symlink():
        raise TreePositionsError("Private tree JSON must be a regular, nonsymlink file")
    resolved = path.resolve(strict=True)
    if resolved != path.absolute():
        # Avoid junction/link resolution surprises and path relocation.
        raise TreePositionsError("Private tree file contains a linked path component")
    if resolved.parent.name != "derived" or resolved.parent.parent.name != "Wii-AI-Golf-Data":
        raise TreePositionsError("Tree JSON must be in Wii-AI-Golf-Data/derived")
    if any(part.is_symlink() for part in (resolved.parent, resolved.parent.parent)):
        raise TreePositionsError("Private Data directory cannot be a symlink")
    if any((parent / ".git").exists() for parent in resolved.parents):
        raise TreePositionsError("Private tree JSON must be outside Git checkout")
    return resolved


def _validate_payload(data: object) -> tuple[tuple[float, float, float], ...]:
    if type(data) is not dict or frozenset(data) != EXPECTED_FIELDS:
        raise TreePositionsError("Unexpected tree JSON fields or missing required fields")
    requirements = {
        "kind": SCHEMA_KIND,
        "schema_version": 1,
        "game_id": "RSPE01",
        "disc_revision": 1,
        "source_captures": [1, 5, 7],
        "source_count": SOURCE_TREE_COUNT,
        "source_element_stride_bytes": 84,
        "source_translation_offset_bytes": 48,
        "position_frame": "original_source_components_no_transform",
        "source_positions_bitwise_identical_across_captures": True,
        "world_visual_alignment_verified": False,
        "original_tree_meshes_verified": False,
        "collision_hitboxes_verified": False,
        "training_approved": False,
    }
    for key, expected in requirements.items():
        if type(data[key]) is not type(expected) or data[key] != expected:
            raise TreePositionsError("Tree source provenance or safety flag mismatch")
    raw_positions = data["tree_positions"]
    if type(raw_positions) is not list or len(raw_positions) != SOURCE_TREE_COUNT:
        raise TreePositionsError("Tree JSON must contain exactly 94 positions")
    points: list[tuple[float, float, float]] = []
    unique = set()
    for raw in raw_positions:
        if type(raw) is not list or len(raw) != 3:
            raise TreePositionsError("Tree marker must be a 3-component source position")
        if any(type(v) not in (int, float) or not math.isfinite(v)
               or abs(v) >= 1e7 for v in raw):
            raise TreePositionsError("Invalid or unbounded tree coordinate")
        point = tuple(float(v) for v in raw)
        key = tuple(round(v, 3) for v in point)
        if key in unique:
            raise TreePositionsError("Non-distinct tree positions")
        unique.add(key)
        points.append(point)
    return tuple(points)


def load_private_tree_positions(filename: str | Path) -> TreePositions:
    """Read source-verified private tree marker JSON with strict size and hash.

    A matching self-described schema is not independent game provenance.
    The upstream #411 SHA/source-gated exporter remains responsible for that.
    """
    path = _check_local_path(filename)
    before = path.stat()
    if not 1 <= before.st_size <= MAX_TREE_BYTES:
        raise TreePositionsError("Private tree JSON outside safe byte bound")
    contents = path.read_bytes()
    after = path.stat()
    if (len(contents) != before.st_size or after.st_size != before.st_size or
            after.st_mtime_ns != before.st_mtime_ns):
        raise TreePositionsError("Private tree JSON changed while loading")
    try:
        data = json.loads(contents.decode("utf-8"),
                          object_pairs_hook=_unique_object_pairs,
                          parse_constant=_reject_nonfinite_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TreePositionsError("Invalid UTF-8/JSON private tree file") from exc
    points = _validate_payload(data)
    return TreePositions(
        positions=points,
        sha256=hashlib.sha256(contents).hexdigest(),
        source_name=path.name,
    )
