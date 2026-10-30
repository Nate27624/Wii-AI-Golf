"""Strict private KCL-candidate OBJ viewer data, adapted from terrain PR #407.

OGWS surface IDs are original-game source labels; drawing colors are visual
hypotheses only. No textures, physical friction or collision contact inferred.
No source memory access, native RAM reads, or input/game writes.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import re

MAX_OBJ_BYTES = 16 * 1024 * 1024
MAX_VERTICES = 90_000
MAX_FACES = 30_000
MAX_DRAW_FACES = 1_200
MAX_GROUPS = MAX_FACES * 2

# Source: original Wii Sports Golf OGWS BE16 KCL prism attr +0x0E,
# confirmed by the private phase-7 KCL material inventory (#411).
# These are UI category colors, NOT reproduced game textures or physics.
# 0x0005 camera_lock and unsupported IDs deliberately remain neutral.
NEUTRAL = ('Unclassified', '#536778')
SURFACE_STYLE: dict[int, tuple[str, str]] = {
    0x0001: ('Fairway', '#42b979'),
    0x0002: ('Rough', '#85994c'),
    0x0003: ('Bunker', '#dbb66b'),
    0x0004: ('Out of bounds', '#cc7574'),
    0x0006: ('Green', '#73e998'),
    0x0007: ('Water', '#4ba9e8'),
    0x0009: ('Fringe', '#b9ce6f'),
    0x000C: ('Cliff', '#9da7ae'),
}
_GROUP = re.compile(r'KCL_OGWS_([0-9A-F]{4})\Z')


def surface_style(attr: int | None) -> tuple[str, str]:
    """Original Golf surface hypothesis, UNKNOWN remains neutral."""
    return SURFACE_STYLE.get(attr, NEUTRAL)


class TerrainError(ValueError):
    """Reject invalid, unsafe, or unverifiable OBJ content."""


@dataclass(frozen=True)
class TerrainMesh:
    vertices: tuple[tuple[float, float, float], ...]
    faces: tuple[tuple[int, int, int], ...]
    sha256: str
    source_name: str
    # Each entry corresponds to the exact OBJ face order. An unlabeled legacy
    # face remains None; never infer from flag/ball position or mesh slope.
    face_materials: tuple[int | None, ...] = ()

    def _draw_indices(self, landmarks: tuple[tuple[float, float, float], ...],
                      focused: bool, limit: int) -> tuple[int, ...]:
        if type(limit) is not int or not 1 <= limit <= MAX_DRAW_FACES:
            raise TerrainError('Invalid wireframe bound')
        if self.face_materials and len(self.face_materials) != len(self.faces):
            raise TerrainError('Material label count does not match triangles')
        chosen = range(len(self.faces))
        if focused and landmarks:
            valid = tuple(p for p in landmarks if len(p) == 3 and all(math.isfinite(x) for x in p))
            if valid:
                radius = max(120.0, max((math.hypot(a[0]-b[0],a[2]-b[2]) for a in valid for b in valid), default=0.0)*1.5)
                radius_sq = radius * radius
                chosen = tuple(idx for idx, face in enumerate(self.faces) if any(
                    (sum(self.vertices[i][0] for i in face)/3 - p[0])**2 +
                    (sum(self.vertices[i][2] for i in face)/3 - p[2])**2 <= radius_sq for p in valid))
        stride = max(1, (len(chosen)+limit-1)//limit)
        return tuple(chosen[::stride][:limit])

    def drawing_faces(self, landmarks: tuple[tuple[float, float, float], ...] = (),
                      *, focused: bool = True, limit: int = MAX_DRAW_FACES
                     ) -> tuple[tuple[tuple[float, float, float], ...], ...]:
        """Original uncolored public API; retained for previous callers."""
        return tuple(tuple(self.vertices[i] for i in self.faces[idx])
                     for idx in self._draw_indices(landmarks, focused, limit))

    def drawing_colored_faces(self, landmarks: tuple[tuple[float, float, float], ...] = (),
                              *, focused: bool = True, limit: int = MAX_DRAW_FACES
                             ) -> tuple[tuple[tuple[tuple[float, float, float], ...], int | None], ...]:
        """Bounded, ordered (vertices, original BE16 KCL attr) face pairs."""
        return tuple((tuple(self.vertices[i] for i in self.faces[idx]),
                      self.face_materials[idx] if self.face_materials else None)
                     for idx in self._draw_indices(landmarks, focused, limit))

    def material_counts(self) -> dict[int | None, int]:
        """Never replace unlabelled faces with inferred game category."""
        if self.face_materials and len(self.face_materials) != len(self.faces):
            raise TerrainError('Material label count does not match triangles')
        return dict(Counter(self.face_materials if self.face_materials
                            else (None for _ in self.faces)))


def load_private_obj(filename: str | Path) -> TerrainMesh:
    """Safe local ASCII OBJ: strict v/f + optional exact OGWS source group labels.

    An exporter may put `g KCL_OGWS_0006` before triangle faces. This does not
    certify its source attribution; file remains a private source hypothesis.
    Generic OBJ groups, materials, textures and links are still forbidden.
    """
    path = Path(filename)
    if path.suffix.lower() != '.obj' or path.is_symlink() or not path.is_file():
        raise TerrainError('Choose a regular local private .obj file')
    path = path.resolve(strict=True)
    if any((parent/'.git').exists() for parent in (path.parent, *path.parents)):
        raise TerrainError('Terrain OBJ must be located outside Git checkouts')
    start = path.stat()
    if not 1 <= start.st_size <= MAX_OBJ_BYTES:
        raise TerrainError('Terrain OBJ outside safe file bound')
    data = path.read_bytes()
    end = path.stat()
    if len(data) != start.st_size or end.st_size != start.st_size or end.st_mtime_ns != start.st_mtime_ns:
        raise TerrainError('Terrain OBJ changed while loading')
    sha = hashlib.sha256(data).hexdigest()
    try:
        lines = data.decode('ascii').splitlines()
    except UnicodeDecodeError as e:
        raise TerrainError('OBJ requires ASCII') from e
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    attrs: list[int | None] = []
    active_attr: int | None = None
    group_count = 0
    for line in lines:
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        parts = line.split()
        if parts[0] == 'g' and len(parts) == 2:
            if group_count >= MAX_GROUPS:
                raise TerrainError('Too many source attribute groups')
            match = _GROUP.fullmatch(parts[1])
            if not match:
                raise TerrainError('Unrecognized OBJ group: only source OGWS hex labels allowed')
            active_attr = int(match.group(1), 16)
            group_count += 1
        elif parts[0] == 'v' and len(parts) == 4:
            if len(vertices) >= MAX_VERTICES:
                raise TerrainError('Too many vertices')
            try:
                pos = tuple(float(v) for v in parts[1:])
            except ValueError as e:
                raise TerrainError('Malformed vertex') from e
            if any(not math.isfinite(v) or abs(v) >= 1e7 for v in pos):
                raise TerrainError('Unbounded/nonfinite vertex')
            vertices.append(pos)
        elif parts[0] == 'f' and len(parts) == 4:
            if len(faces) >= MAX_FACES:
                raise TerrainError('Too many faces')
            if any(not value.isdecimal() for value in parts[1:]):
                raise TerrainError('Require positive unadorned triangle indices')
            face = tuple(int(v)-1 for v in parts[1:])
            if len(set(face)) != 3 or any(v < 0 or v >= len(vertices) for v in face):
                raise TerrainError('Invalid face indices')
            a, b, c = (vertices[i] for i in face)
            e1 = (b[0]-a[0],b[1]-a[1],b[2]-a[2]);e2=(c[0]-a[0],c[1]-a[1],c[2]-a[2])
            cross=(e1[1]*e2[2]-e1[2]*e2[1],e1[2]*e2[0]-e1[0]*e2[2],e1[0]*e2[1]-e1[1]*e2[0])
            if sum(v*v for v in cross)<1e-12:
                raise TerrainError('Degenerate triangle')
            faces.append(face)
            attrs.append(active_attr)
        else:
            raise TerrainError('Unsupported OBJ record: only v/f triangles, strict OGWS g, or comments')
    if not vertices or not faces:
        raise TerrainError('No terrain triangles')
    return TerrainMesh(tuple(vertices), tuple(faces), sha, path.name, tuple(attrs))
