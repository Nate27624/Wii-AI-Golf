"""Strict, opt-in local OBJ collision mesh reader for source-coordinate inspector.

Only private local geometry. Does not access Dolphin, game RAM, network or files
other than the operator-selected OBJ. No texture model or terrain alignment claim.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path

MAX_OBJ_BYTES = 16 * 1024 * 1024
MAX_VERTICES = 90000
MAX_FACES = 30000
MAX_DRAW_FACES = 1200


class TerrainError(ValueError):
    """Terrain file declined rather than drawing ambiguous geometry."""


@dataclass(frozen=True)
class TerrainMesh:
    vertices: tuple[tuple[float, float, float], ...]
    faces: tuple[tuple[int, int, int], ...]
    sha256: str
    source_name: str

    def drawing_faces(self, landmarks: tuple[tuple[float, float, float], ...] = (),
                      *, focused: bool = True, limit: int = MAX_DRAW_FACES
                      ) -> tuple[tuple[tuple[float, float, float], ...], ...]:
        """Deterministic decimated triangles, optionally near confirmed tee/pin.

        Spatial proximity is *not* proof that an OBJ shares the game's model
        transform or hole. No arbitrary translation or unit conversion applied.
        """
        if not 1 <= limit <= MAX_DRAW_FACES:
            raise TerrainError("Invalid wireframe draw bound")
        chosen = self.faces
        if focused and landmarks:
            # Source coordinates only: component0/component2 are candidate plane.
            valid = tuple(p for p in landmarks if len(p) == 3 and
                          all(math.isfinite(x) for x in p))
            if valid:
                extent = max(
                    (math.hypot(a[0] - b[0], a[2] - b[2])
                     for a in valid for b in valid), default=0.0)
                radius = max(120.0, extent * 1.5)
                radius2 = radius * radius
                chosen = tuple(face for face in chosen if any(
                    (sum(self.vertices[i][0] for i in face) / 3 - p[0]) ** 2 +
                    (sum(self.vertices[i][2] for i in face) / 3 - p[2]) ** 2 <= radius2
                    for p in valid))
        stride = max(1, (len(chosen) + limit - 1) // limit)
        return tuple(tuple(self.vertices[i] for i in face) for face in chosen[::stride][:limit])


def _private_location(path: Path) -> Path:
    if path.suffix.lower() != ".obj" or path.is_symlink() or not path.is_file():
        raise TerrainError("Choose an ordinary private .obj file")
    real = path.resolve(strict=True)
    if any((parent / ".git").exists() for parent in (real.parent, *real.parents)):
        raise TerrainError("Private terrain file must be outside any Git checkout")
    return real


def load_private_obj(filename: str | Path) -> TerrainMesh:
    """Read only strict 'v x y z' / 'f i j k' OBJ; SHA bytes; fail closed."""
    path = _private_location(Path(filename))
    before = path.stat()
    if not 1 <= before.st_size <= MAX_OBJ_BYTES:
        raise TerrainError("Terrain OBJ size is outside safe bounds")
    data = path.read_bytes()
    after = path.stat()
    if (len(data) != before.st_size or after.st_size != before.st_size
            or after.st_mtime_ns != before.st_mtime_ns):
        raise TerrainError("Terrain OBJ changed during load")
    sha = hashlib.sha256(data).hexdigest()
    try:
        content = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise TerrainError("Terrain OBJ requires ASCII coordinates") from exc
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    for line in content.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split()
        if fields[0] == "v" and len(fields) == 4:
            if len(vertices) >= MAX_VERTICES:
                raise TerrainError("Too many terrain vertices")
            try:
                v = tuple(float(x) for x in fields[1:])
            except ValueError as exc:
                raise TerrainError("Malformed terrain coordinate") from exc
            if not all(math.isfinite(x) and abs(x) < 1e7 for x in v):
                raise TerrainError("Nonfinite or unbounded terrain coordinate")
            vertices.append(v)
        elif fields[0] == "f" and len(fields) == 4:
            if len(faces) >= MAX_FACES:
                raise TerrainError("Too many terrain triangles")
            if any(not n.isdecimal() for n in fields[1:]):
                raise TerrainError("Only positive, undecorated triangular OBJ faces allowed")
            face = tuple(int(n) - 1 for n in fields[1:])
            if len(set(face)) != 3 or any(n < 0 or n >= len(vertices) for n in face):
                raise TerrainError("Invalid or degenerate terrain vertex indices")
            vertices_t = [vertices[i] for i in face]
            a, b, c = vertices_t
            e1 = tuple(b[i] - a[i] for i in range(3))
            e2 = tuple(c[i] - a[i] for i in range(3))
            area = (e1[1] * e2[2] - e1[2] * e2[1],
                    e1[2] * e2[0] - e1[0] * e2[2],
                    e1[0] * e2[1] - e1[1] * e2[0])
            if sum(x*x for x in area) < 1e-12:
                raise TerrainError("Degenerate terrain triangle")
            faces.append(face)
        else:
            raise TerrainError("Unsupported OBJ record (only v/f triangles and comments)")
    if not vertices or not faces:
        raise TerrainError("Terrain OBJ contains no triangles")
    return TerrainMesh(tuple(vertices), tuple(faces), sha, path.name)
