"""Read-only local Collada (.dae) source UV preview for original Wii Golf.

No Blender, model conversion, private asset writes, Dolphin or KCL changes.
Select the original BrawlCrate DAE; source textures are loaded from sibling
Textures(NW4R)/name.tex0.png exported by Wiimms SZS Tools.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from .visual_model import (
    MAX_OBJ_BYTES, MAX_PNG_BYTES, MAX_TOTAL_TEXTURE_BYTES, MAX_TEXTURES,
    MAX_VERTICES, MAX_UVS, MAX_TRIANGLES, MAX_MODEL_COMPONENT,
    PrivateTexture, PrivateVisualModel, VisualAssetError, VisualFace,
    _within_private_dir, _read_local, _png_info,
)

_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}\Z")
_MAX_NUMBERS = 2_000_000


def _tag(n: ET.Element) -> str:
    return n.tag.rsplit("}", 1)[-1]


def _children(n: ET.Element, kind: str) -> list[ET.Element]:
    return [c for c in n if _tag(c) == kind]


def _one(n: ET.Element, kind: str) -> ET.Element:
    cs = _children(n, kind)
    if len(cs) != 1:
        raise VisualAssetError("Collada expected exactly one " + kind)
    return cs[0]


def _id(v: str | None) -> str:
    if not v or not _NAME.fullmatch(v):
        raise VisualAssetError("Unsafe/unsupported Collada identifier")
    return v


def _ref(v: str | None) -> str:
    if not v or not v.startswith("#"):
        raise VisualAssetError("External Collada links are forbidden")
    return _id(v[1:])


def _numbers(raw: str | None, *, integer: bool = False, limit: int = _MAX_NUMBERS):
    if not raw:
        raise VisualAssetError("Missing Collada number array")
    words = raw.split()
    if len(words) > limit:
        raise VisualAssetError("Collada numeric array exceeds limit")
    try:
        values = tuple(int(v) if integer else float(v) for v in words)
    except ValueError as exc:
        raise VisualAssetError("Malformed Collada numeric value") from exc
    if integer and any(v < 0 for v in values):
        raise VisualAssetError("Collada negative index")
    if not integer and any(not math.isfinite(v) or abs(v) > MAX_MODEL_COMPONENT for v in values):
        raise VisualAssetError("Nonfinite or unbounded Collada value")
    return values


def _source_arrays(mesh: ET.Element):
    arrays = {}
    for source in _children(mesh, "source"):
        sid = _id(source.get("id"))
        floats = _children(source, "float_array")
        if not floats:
            continue
        if len(floats) != 1:
            raise VisualAssetError("Ambiguous Collada source arrays")
        raw = _numbers(floats[0].text)
        try:
            declared = int(floats[0].get("count", "-1"))
        except ValueError as exc:
            raise VisualAssetError("Invalid Collada float count") from exc
        if len(raw) != declared:
            raise VisualAssetError("Collada float count mismatch")
        accessors = [n for n in source.iter() if _tag(n) == "accessor"]
        if len(accessors) != 1 or _ref(accessors[0].get("source")) != _id(floats[0].get("id")):
            raise VisualAssetError("Collada accessor missing or mismatched")
        accessor = accessors[0]
        try:
            count = int(accessor.get("count", "-1"))
            stride = int(accessor.get("stride", "1"))
            offset = int(accessor.get("offset", "0"))
        except ValueError as exc:
            raise VisualAssetError("Invalid Collada accessor dimension") from exc
        if not (1 <= stride <= 16 and 0 <= offset <= len(raw)
                and 0 <= count <= _MAX_NUMBERS // stride
                and offset + count * stride <= len(raw)):
            raise VisualAssetError("Collada accessor outside float array")
        arrays[sid] = tuple(
            tuple(raw[offset + j * stride: offset + (j + 1) * stride])
            for j in range(count))
    return arrays


def _materials(root: ET.Element, dae: Path):
    images = {}
    for lib in (n for n in root.iter() if _tag(n) == "library_images"):
        for image in _children(lib, "image"):
            iid = _id(image.get("id"))
            init = _one(image, "init_from")
            # Collada 1.4 allows direct text; Collada 1.5 may wrap in <ref>.
            refs = _children(init, "ref")
            if refs and len(refs) != 1:
                raise VisualAssetError("Ambiguous Collada 1.5 image reference")
            path = ((refs[0].text if refs else init.text) or "").strip()
            if iid in images or not path.endswith(".png") or not _NAME.fullmatch(path):
                raise VisualAssetError("Unsafe or duplicate Collada image reference")
            images[iid] = path

    effects = {}
    for lib in (n for n in root.iter() if _tag(n) == "library_effects"):
        for effect in _children(lib, "effect"):
            eid = _id(effect.get("id"))
            if eid in effects:
                raise VisualAssetError("Duplicate Collada effect")
            slots = [n for n in effect.iter() if _tag(n) == "texture"]
            if len(slots) > 1:
                raise VisualAssetError("Multi-texture Wii TEV effect unsupported")
            if slots:
                sampler = _id(slots[0].get("texture"))
                if slots[0].get("texcoord") not in ("TEXCOORD0", None):
                    raise VisualAssetError("Source texture requires a different UV layer")
                params = {n.get("sid"): n for n in effect.iter() if _tag(n) == "newparam"}
                if sampler in params:
                    surface_sid = (_one(_one(params[sampler], "sampler2D"), "source").text or "").strip()
                    surface = params.get(surface_sid)
                    if surface is None:
                        raise VisualAssetError("Collada sampler has no source surface")
                    image_id = (_one(_one(surface, "surface"), "init_from").text or "").strip()
                else:
                    if not sampler.endswith("-sampler"):
                        raise VisualAssetError("Unsupported original source sampler")
                    image_id = sampler[:-len("-sampler")] + "-image"
                if image_id not in images:
                    raise VisualAssetError("Original DAE sampler does not match image")
                effects[eid] = (images[image_id], None)
            else:
                diffuse = [n for n in effect.iter() if _tag(n) == "diffuse"]
                colors = [c for d in diffuse for c in _children(d, "color") if c.text]
                if len(colors) != 1:
                    raise VisualAssetError("Untextured original material has no diffuse color")
                rgba = _numbers(colors[0].text, limit=4)
                if len(rgba) not in (3, 4) or any(not 0 <= x <= 1 for x in rgba):
                    raise VisualAssetError("Invalid original source diffuse color")
                effects[eid] = (None, tuple(round(c * 255) for c in rgba[:3]))

    materials = {}
    for lib in (n for n in root.iter() if _tag(n) == "library_materials"):
        for material in _children(lib, "material"):
            mid = _id(material.get("id"))
            eid = _ref(_one(material, "instance_effect").get("url"))
            if mid in materials or eid not in effects:
                raise VisualAssetError("Unknown or repeated source material effect")
            materials[mid] = effects[eid]
    if not materials:
        raise VisualAssetError("Original DAE has no materials")

    aliases = {m: m for m in materials}
    for node in root.iter():
        if _tag(node) != "instance_material":
            continue
        symbol, target = _id(node.get("symbol")), _ref(node.get("target"))
        if target not in materials or (symbol in aliases and aliases[symbol] != target):
            raise VisualAssetError("Ambiguous visual scene material alias")
        aliases[symbol] = target

    textures, solid = {}, {}
    total = 0
    for material, (image, color) in materials.items():
        if image is None:
            solid[material] = color
            continue
        # The exact local Wiimms output already exists for this user.
        candidates = (
            dae.parent / image,
            dae.parent / "Textures(NW4R)" / (image[:-4] + ".tex0.png"),
        )
        matches = [p for p in candidates if p.is_file()]
        if len(matches) != 1:
            raise VisualAssetError("Missing or ambiguous original TEX0 PNG: " + image)
        path = _within_private_dir(matches[0])
        data = _read_local(path, MAX_PNG_BYTES)
        total += len(data)
        if total > MAX_TOTAL_TEXTURE_BYTES:
            raise VisualAssetError("Original PNG assets exceed bound")
        textures[material] = PrivateTexture(
            path, hashlib.sha256(data).hexdigest(), _png_info(data))
    if len(textures) > MAX_TEXTURES:
        raise VisualAssetError("Too many source textures")
    return aliases, textures, solid


def load_private_dae_visual_model(filename: str | Path) -> PrivateVisualModel:
    """Read original BrawlCrate DAE directly; preserve source UV and material IDs."""
    path = _within_private_dir(Path(filename))
    if path.suffix.lower() != ".dae":
        raise VisualAssetError("Choose a Collada .dae visual model")
    blob = _read_local(path, MAX_OBJ_BYTES)
    if b"<!DOCTYPE" in blob.upper() or b"<!ENTITY" in blob.upper():
        raise VisualAssetError("Collada DTD/entities forbidden")
    try:
        root = ET.fromstring(blob)
    except ET.ParseError as exc:
        raise VisualAssetError("Invalid original Collada XML") from exc
    if _tag(root) != "COLLADA":
        raise VisualAssetError("Not a Collada visual model")
    aliases, textures, solid = _materials(root, path)

    vertices, uvs, faces = [], [], []
    for lib in (n for n in root.iter() if _tag(n) == "library_geometries"):
        for geometry in _children(lib, "geometry"):
            mesh = _one(geometry, "mesh")
            floats = _source_arrays(mesh)
            bindings = {}
            for vertex in _children(mesh, "vertices"):
                bindings[_id(vertex.get("id"))] = {
                    item.get("semantic"): _ref(item.get("source"))
                    for item in _children(vertex, "input")}
            for triangles in _children(mesh, "triangles"):
                try:
                    count = int(triangles.get("count", "-1"))
                except ValueError as exc:
                    raise VisualAssetError("Invalid original triangle count") from exc
                if not 0 < count <= MAX_TRIANGLES - len(faces):
                    raise VisualAssetError("Collada triangle count exceeds limit")
                symbol = triangles.get("material")
                if symbol not in aliases:
                    raise VisualAssetError("Unknown source triangle material: " + str(symbol))
                material = aliases[symbol]
                inputs = []
                for item in _children(triangles, "input"):
                    try:
                        off = int(item.get("offset", "0"))
                    except ValueError as exc:
                        raise VisualAssetError("Malformed source face index offset") from exc
                    if not 0 <= off <= 15:
                        raise VisualAssetError("Source index offset exceeds bound")
                    inputs.append((item.get("semantic"), _ref(item.get("source")),
                                   off, item.get("set")))
                if not inputs:
                    raise VisualAssetError("Source triangles have no coordinate inputs")
                stride = max(inp[2] for inp in inputs) + 1
                idx = _numbers(_one(triangles, "p").text,
                               integer=True, limit=MAX_TRIANGLES * 3 * 16)
                if len(idx) != count * 3 * stride:
                    raise VisualAssetError("Source face indexes/count inconsistent")
                vertex_input = [i for i in inputs if i[0] == "VERTEX"]
                if len(vertex_input) != 1:
                    raise VisualAssetError("Source triangle VERTEX input invalid")
                target = bindings.get(vertex_input[0][1], {})
                positions = floats.get(target.get("POSITION"))
                if positions is None:
                    raise VisualAssetError("Original POSITION array unavailable")
                tex_inputs = [i for i in inputs if i[0] == "TEXCOORD"]
                chosen = next((i for i in tex_inputs if i[3] in (None, "0")), None)
                if material in textures and chosen is None:
                    raise VisualAssetError("Textured source triangle missing UV0")
                texcoords = floats.get(chosen[1]) if chosen else None
                if chosen and texcoords is None:
                    raise VisualAssetError("Original texture coordinate array missing")
                # Bounded duplication per primitive; preserves per-corner UV seams.
                used_v, used_t = {}, {}
                for f in range(count):
                    vi_out, ti_out = [], []
                    for corner in range(3):
                        k = (3 * f + corner) * stride
                        vi = idx[k + vertex_input[0][2]]
                        if vi >= len(positions) or len(positions[vi]) < 3:
                            raise VisualAssetError("Source POSITION index invalid")
                        if vi not in used_v:
                            if len(vertices) >= MAX_VERTICES:
                                raise VisualAssetError("Visual model exceeds vertex limit")
                            used_v[vi] = len(vertices)
                            vertices.append(tuple(positions[vi][:3]))
                        vi_out.append(used_v[vi])
                        if chosen:
                            ti = idx[k + chosen[2]]
                            if ti >= len(texcoords) or len(texcoords[ti]) < 2:
                                raise VisualAssetError("Original TEXCOORD index invalid")
                            if ti not in used_t:
                                if len(uvs) >= MAX_UVS:
                                    raise VisualAssetError("Visual UVs exceed limit")
                                used_t[ti] = len(uvs)
                                uvs.append(tuple(texcoords[ti][:2]))
                            ti_out.append(used_t[ti])
                        else:
                            if len(uvs) >= MAX_UVS:
                                raise VisualAssetError("Visual UVs exceed limit")
                            ti_out.append(len(uvs))
                            uvs.append((0., 0.))  # Only source-untextured faces.
                    if len(set(vi_out)) != 3:
                        raise VisualAssetError("Degenerate original source triangle")
                    faces.append(VisualFace(tuple(vi_out), tuple(ti_out), material))
    if not faces:
        raise VisualAssetError("No supported original Collada source triangles")
    used = {face.material for face in faces}
    return PrivateVisualModel(
        tuple(vertices), tuple(uvs), tuple(faces),
        {k: v for k, v in textures.items() if k in used},
        hashlib.sha256(blob).hexdigest(), "COLLADA_DIRECT", path.name,
        {k: v for k, v in solid.items() if k in used})
