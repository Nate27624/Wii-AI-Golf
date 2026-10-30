"""Strict private KCL-candidate OBJ wireframe, adapted from terrain PR #407.

No geometry is inferred or fetched from Dolphin. In particular a local OBJ
cannot prove this is the rendered golf course or an active physics surface.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path

MAX_OBJ_BYTES = 16 * 1024 * 1024
MAX_VERTICES = 90_000
MAX_FACES = 30_000
MAX_DRAW_FACES = 1_200

class TerrainError(ValueError):
    """Reject invalid, unsafe, or unverifiable OBJ content."""

@dataclass(frozen=True)
class TerrainMesh:
    vertices: tuple[tuple[float,float,float], ...]
    faces: tuple[tuple[int,int,int], ...]
    sha256: str
    source_name: str

    def drawing_faces(self, landmarks: tuple[tuple[float,float,float], ...] = (),
                      *, focused: bool = True, limit: int = MAX_DRAW_FACES
                     ) -> tuple[tuple[tuple[float,float,float], ...], ...]:
        if type(limit) is not int or not 1 <= limit <= MAX_DRAW_FACES:
            raise TerrainError('Invalid wireframe bound')
        chosen = self.faces
        if focused and landmarks:
            valid = tuple(p for p in landmarks if len(p) == 3 and all(math.isfinite(x) for x in p))
            if valid:
                radius = max(120.0, max((math.hypot(a[0]-b[0],a[2]-b[2]) for a in valid for b in valid), default=0.0)*1.5)
                radius_sq = radius * radius
                chosen = tuple(f for f in chosen if any(
                    (sum(self.vertices[i][0] for i in f)/3 - p[0])**2 +
                    (sum(self.vertices[i][2] for i in f)/3 - p[2])**2 <= radius_sq for p in valid))
        stride = max(1, (len(chosen) + limit - 1) // limit)
        return tuple(tuple(self.vertices[i] for i in f) for f in chosen[::stride][:limit])


def load_private_obj(filename: str | Path) -> TerrainMesh:
    """Only ordinary local ASCII v/f triangle OBJ outside Git; SHA and size bound."""
    path = Path(filename)
    if path.suffix.lower() != '.obj' or path.is_symlink() or not path.is_file():
        raise TerrainError('Choose a regular local private .obj file')
    path = path.resolve(strict=True)
    if any((parent/'.git').exists() for parent in (path.parent,*path.parents)):
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
    vertices: list[tuple[float,float,float]] = []
    faces: list[tuple[int,int,int]] = []
    for line in lines:
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        parts = line.split()
        if parts[0] == 'v' and len(parts) == 4:
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
            a,b,c = (vertices[i] for i in face)
            e1 = (b[0]-a[0],b[1]-a[1],b[2]-a[2]);e2=(c[0]-a[0],c[1]-a[1],c[2]-a[2])
            cross=(e1[1]*e2[2]-e1[2]*e2[1],e1[2]*e2[0]-e1[0]*e2[2],e1[0]*e2[1]-e1[1]*e2[0])
            if sum(v*v for v in cross)<1e-12:
                raise TerrainError('Degenerate triangle')
            faces.append(face)
        else:
            raise TerrainError('Unsupported OBJ record: only v/f triangles or comments')
    if not vertices or not faces:
        raise TerrainError('No terrain triangles')
    return TerrainMesh(tuple(vertices),tuple(faces),sha,path.name)
