"""Private, opt-in Wii Golf *visual* mesh loader (not the collision KCL mesh).

Read an existing user-extracted OBJ/MTL/PNG set from disk only. Never extract
ROM data, issue Dolphin RPCs, or upload original models or Nintendo textures.
An OBJ export must preserve UV coordinates *and* material-to-image bindings.
Nothing here proves original-game ownership, native render shader settings,
world alignment or actual physics collision.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import re
import struct

MAX_OBJ_BYTES = 24 * 1024 * 1024
MAX_MTL_BYTES = 2 * 1024 * 1024
MAX_PNG_BYTES = 12 * 1024 * 1024
MAX_TOTAL_TEXTURE_BYTES = 48 * 1024 * 1024
MAX_IMAGE_SIDE = 4096
MAX_TEXTURES = 24
MAX_VERTICES = 180_000
MAX_UVS = 220_000
MAX_TRIANGLES = 100_000
MAX_MODEL_COMPONENT = 10_000_000
_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}\Z")
_PNG_HEADER = b"\x89PNG\r\n\x1a\n"


class VisualAssetError(ValueError):
    """Fail closed on missing/private-boundary, malformed or unsupported assets."""


@dataclass(frozen=True)
class VisualFace:
    vertices: tuple[int, int, int]
    uvs: tuple[int, int, int]
    material: str


@dataclass(frozen=True)
class PrivateTexture:
    filename: Path
    sha256: str
    size: tuple[int, int]


@dataclass(frozen=True)
class PrivateVisualModel:
    vertices: tuple[tuple[float, float, float], ...]
    uvs: tuple[tuple[float, float], ...]
    faces: tuple[VisualFace, ...]
    textures: dict[str, PrivateTexture]
    obj_sha256: str
    mtl_sha256: str
    source_name: str

    @property
    def textured_face_count(self) -> int:
        return sum(face.material in self.textures for face in self.faces)


def _read_local(path: Path, max_bytes: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise VisualAssetError("Only regular private local files are supported")
    try:
        start = path.stat()
        if not 0 < start.st_size <= max_bytes:
            raise VisualAssetError("Visual asset exceeds safe size bound")
        data = path.read_bytes()
        end = path.stat()
    except OSError as exc:
        raise VisualAssetError("Private file cannot be read") from exc
    if (len(data) != start.st_size or end.st_size != start.st_size
            or end.st_mtime_ns != start.st_mtime_ns):
        raise VisualAssetError("Private asset changed during read")
    return data


def _within_private_dir(path: Path) -> Path:
    """Prevent accidental use of game images tracked by source repositories.

    A user should export assets into a separate private folder (e.g.
    D:/Projects/WiiGolfVisualPrivate), never into Git or public project assets.
    """
    if path.is_symlink() or not path.is_file():
        raise VisualAssetError("Select an existing regular local file")
    resolved = path.resolve(strict=True)
    if any((ancestor / ".git").exists() for ancestor in (resolved.parent, *resolved.parents)):
        raise VisualAssetError("Visual models must remain outside Git checkouts")
    return resolved


def _sibling(base: Path, relative: str, suffixes: tuple[str, ...]) -> Path:
    """Allow safe relative paths into texture subfolders, no traversal or links."""
    norm = relative.replace("\\", "/")
    chunks = norm.split("/")
    if not 1 <= len(chunks) <= 4 or any(not _NAME.fullmatch(x) or x in (".", "..") for x in chunks):
        raise VisualAssetError("Unsafe relative texture/material filename")
    result = base.joinpath(*chunks)
    if result.suffix.lower() not in suffixes:
        raise VisualAssetError("Unsupported material/texture extension")
    if any(p.is_symlink() for p in (result, *tuple(result.parents)[:len(chunks)])):
        raise VisualAssetError("Symbolic links are not allowed in private asset paths")
    parent = base.resolve(strict=True)
    if not result.resolve(strict=False).is_relative_to(parent):
        raise VisualAssetError("Private asset path escapes model directory")
    return result


def _utf8(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise VisualAssetError("OBJ/MTL text must be UTF-8") from exc


def _float_tuple(parts: list[str], count: int, *, bound: float) -> tuple[float, ...]:
    if len(parts) < count:
        raise VisualAssetError("Missing model component")
    try:
        vals = tuple(float(v) for v in parts[:count])
    except ValueError as exc:
        raise VisualAssetError("Malformed model coordinate") from exc
    if any(not math.isfinite(v) or abs(v) > bound for v in vals):
        raise VisualAssetError("Unbounded/nonfinite model coordinate")
    return vals


def _png_info(data: bytes) -> tuple[int, int]:
    if (len(data) < 33 or data[:8] != _PNG_HEADER or data[12:16] != b"IHDR"
            or struct.unpack_from(">I", data, 8)[0] != 13):
        raise VisualAssetError("Texture is not a PNG with a valid IHDR header")
    w, h = struct.unpack_from(">II", data, 16)
    if not (1 <= w <= MAX_IMAGE_SIDE and 1 <= h <= MAX_IMAGE_SIDE and w*h <= 8_388_608):
        raise VisualAssetError("Texture dimensions exceed safe bound")
    if data[25] not in (0, 2, 3, 4, 6):
        raise VisualAssetError("Unsupported PNG color format")
    return w, h


def _parse_mtl(base: Path, rel: str) -> tuple[dict[str, PrivateTexture], str]:
    path = _sibling(base, rel, (".mtl",))
    blob = _read_local(path, MAX_MTL_BYTES)
    current: str | None = None
    texture_names: dict[str, str] = {}
    for raw in _utf8(blob).splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        command, *args = stripped.split()
        if command == "newmtl" and len(args) == 1 and _NAME.fullmatch(args[0]):
            current = args[0]
        elif command == "map_Kd":
            if current is None or len(args) != 1:
                raise VisualAssetError("Only one local PNG diffuse image per material is supported")
            if current in texture_names:
                raise VisualAssetError("Material has more than one diffuse image")
            texture_names[current] = args[0]
        elif command in {"Kd", "Ka", "Ks", "Ke", "Ns", "Ni", "illum", "d", "Tr", "Tf", "Pr", "Pm", "Ps", "aniso"}:
            # Other render/shader parameters are not emulated. These are safe
            # to ignore; image/UV association remains explicit.
            if not args or len(args) > 4:
                raise VisualAssetError("Malformed unsupported MTL shading record")
        else:
            raise VisualAssetError("Unsupported MTL record (no includes or external assets)")
    if not texture_names or len(texture_names) > MAX_TEXTURES:
        raise VisualAssetError("MTL must reference a bounded number of diffuse PNGs")
    textures: dict[str, PrivateTexture] = {}
    total = 0
    for material, name in texture_names.items():
        img_path = _sibling(base, name, (".png",))
        data = _read_local(img_path, MAX_PNG_BYTES)
        total += len(data)
        if total > MAX_TOTAL_TEXTURE_BYTES:
            raise VisualAssetError("Textures exceed total private data bound")
        textures[material] = PrivateTexture(img_path, hashlib.sha256(data).hexdigest(), _png_info(data))
    return textures, hashlib.sha256(blob).hexdigest()


def load_private_visual_model(filename: str | Path) -> PrivateVisualModel:
    """Load bounded user-extracted UV model and local texture references.

    - Independent of and never a replacement for source-qualified KCL terrain.
    - No arbitrary MTL paths, remote URLs, symlinks, or file uploads.
    - Standard OBJ positive triangle/quad vertex/UV indices; quads fan-split.
    - Other Nintendo shader channels/animations not reconstructed.
    """
    path = _within_private_dir(Path(filename))
    if path.suffix.lower() != ".obj":
        raise VisualAssetError("Select a locally exported .obj visual model")
    data = _read_local(path, MAX_OBJ_BYTES)
    vertices: list[tuple[float, float, float]] = []
    uvs: list[tuple[float, float]] = []
    faces: list[VisualFace] = []
    mat_file: str | None = None
    material: str | None = None
    for raw in _utf8(data).splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        command, *fields = stripped.split()
        if command == "v":
            # Some exporters include a 4th homogeneous coordinate or vertex RGB.
            if len(vertices) >= MAX_VERTICES or len(fields) not in (3, 4, 6, 7):
                raise VisualAssetError("Unsupported or excessive OBJ vertex")
            vertices.append(_float_tuple(fields, 3, bound=MAX_MODEL_COMPONENT))
        elif command == "vt":
            if len(uvs) >= MAX_UVS or len(fields) not in (2, 3):
                raise VisualAssetError("Unsupported or excessive OBJ UV")
            uvs.append(_float_tuple(fields, 2, bound=10_000))
        elif command == "vn":
            if len(fields) != 3:
                raise VisualAssetError("Malformed OBJ normal")
            _float_tuple(fields, 3, bound=10_000)
        elif command == "mtllib":
            if mat_file is not None or len(fields) != 1:
                raise VisualAssetError("Exactly one private MTL is supported")
            mat_file = fields[0]
        elif command == "usemtl":
            if len(fields) != 1 or not _NAME.fullmatch(fields[0]):
                raise VisualAssetError("Invalid OBJ material name")
            material = fields[0]
        elif command == "f":
            if not 3 <= len(fields) <= 4 or len(faces)+len(fields)-2 > MAX_TRIANGLES:
                raise VisualAssetError("Only bounded triangle/quad OBJ faces are supported")
            corners: list[tuple[int, int]] = []
            for token in fields:
                parts = token.split("/")
                if (len(parts) not in (2, 3) or not parts[0].isdecimal()
                        or not parts[1].isdecimal() or not parts[0] or not parts[1]):
                    raise VisualAssetError("Every visual face needs explicit positive vertex/UV indices")
                if len(parts) == 3 and parts[2] and not parts[2].isdecimal():
                    raise VisualAssetError("Unsupported OBJ normal index")
                vi, ti = int(parts[0])-1, int(parts[1])-1
                if not (0 <= vi < len(vertices) and 0 <= ti < len(uvs)):
                    raise VisualAssetError("OBJ face references invalid vertex or UV")
                corners.append((vi, ti))
            if material is None:
                raise VisualAssetError("Visual faces require an explicit material")
            for i in range(1, len(corners)-1):
                pair = (corners[0], corners[i], corners[i+1])
                if len({p[0] for p in pair}) != 3:
                    raise VisualAssetError("Degenerate visual triangle indices")
                points = [vertices[p[0]] for p in pair]
                a, b, c = points
                cross = ((b[1]-a[1])*(c[2]-a[2])-(b[2]-a[2])*(c[1]-a[1]),
                         (b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2]),
                         (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))
                if not (1e-16 < sum(v*v for v in cross) < 1e27):
                    raise VisualAssetError("Degenerate visual model triangle")
                faces.append(VisualFace(tuple(p[0] for p in pair), tuple(p[1] for p in pair), material))
        elif command in {"g", "o", "s"}:
            if not 1 <= len(fields) <= 4 or any(len(x) > 128 for x in fields):
                raise VisualAssetError("Unsupported OBJ object/group name")
        else:
            raise VisualAssetError("Unsupported OBJ record, no external includes or commands")
    if not vertices or not uvs or not faces or mat_file is None:
        raise VisualAssetError("Visual OBJ needs vertices, UVs, faces, one MTL and textures")
    textures, mtl_digest = _parse_mtl(path.parent, mat_file)
    material_names = {f.material for f in faces}
    if not material_names.issubset(textures):
        raise VisualAssetError("Face references a material with no local PNG texture")
    return PrivateVisualModel(tuple(vertices), tuple(uvs), tuple(faces), textures,
                              hashlib.sha256(data).hexdigest(), mtl_digest, path.name)
