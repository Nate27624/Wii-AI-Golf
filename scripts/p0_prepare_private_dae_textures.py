#!/usr/bin/env python3
"""Stage authentic source-linked Golf DAE and PNGs in a new private folder.

No generated textures, game writes, network access, or original OBJ edits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import xml.etree.ElementTree as ET

MAX_DAE = 24 * 1024 * 1024
MAX_PNG = 12 * 1024 * 1024
MAX_IMAGES = 24
NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}\Z")
PNG = b"\x89PNG\r\n\x1a\n"


def tag(node):
    return node.tag.rsplit("}", 1)[-1]


def private(path: Path, *, must_exist: bool = True) -> Path:
    path = path.absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Symlink in private asset path")
    if must_exist and not path.exists():
        raise ValueError("Private asset path missing")
    resolved = path.resolve(strict=must_exist)
    if any((p / ".git").exists() for p in (resolved, *resolved.parents)):
        raise ValueError("Original visual assets must remain outside Git")
    return resolved


def bindings_from_dae(blob: bytes) -> tuple[dict[str, str], tuple[str, ...]]:
    if not 1 <= len(blob) <= MAX_DAE:
        raise ValueError("DAE exceeds size bound")
    if b"<!DOCTYPE" in blob.upper() or b"<!ENTITY" in blob.upper():
        raise ValueError("DAE external entities/DTD not permitted")
    try:
        root = ET.fromstring(blob)
    except ET.ParseError as exc:
        raise ValueError("Invalid Collada XML") from exc
    if tag(root) != "COLLADA":
        raise ValueError("Not a Collada document")
    nodes = list(root.iter())
    if not any(tag(n) == "geometry" for n in nodes):
        raise ValueError("No actual DAE geometry")
    if not any(tag(n) == "input" and n.get("semantic") == "TEXCOORD" for n in nodes):
        raise ValueError("No original DAE UV input")
    images = {}
    for node in nodes:
        if tag(node) != "image":
            continue
        image_id, name = node.get("id", ""), node.get("name", "")
        init = next((c.text.strip() for c in node if tag(c) == "init_from" and c.text), "")
        if not (NAME.fullmatch(image_id) and NAME.fullmatch(name) and init == name + ".png"):
            raise ValueError("Unsupported DAE image reference")
        if image_id in images:
            raise ValueError("Duplicate DAE image id")
        images[image_id] = init
    effects = {n.get("id"): n for n in nodes if tag(n) == "effect"}
    mapping = {}
    untextured = []
    for node in nodes:
        if tag(node) != "material":
            continue
        material = node.get("id", "")
        if not NAME.fullmatch(material):
            raise ValueError("Bad source material name")
        refs = [c for c in node if tag(c) == "instance_effect"]
        if len(refs) != 1 or not refs[0].get("url", "").startswith("#"):
            raise ValueError("No exact material-to-effect linkage")
        effect = effects.get(refs[0].get("url")[1:])
        if effect is None:
            raise ValueError("Unknown material effect")
        slots = [n for n in effect.iter() if tag(n) == "texture"]
        if not slots:
            untextured.append(material)
            continue
        if len(slots) != 1:
            raise ValueError("Multi-TEX0 material needs Wii TEV research")
        name = slots[0].get("texture", "")
        if (slots[0].get("texcoord") != "TEXCOORD0"
                or not NAME.fullmatch(name) or not name.endswith("-sampler")):
            raise ValueError("Unknown material texture sampler")
        image = images.get(name[:-len("-sampler")] + "-image")
        if image is None or material in mapping:
            raise ValueError("Missing source image for DAE material")
        mapping[material] = image
    if not 1 <= len(mapping) <= MAX_IMAGES:
        raise ValueError("Invalid count of original DAE texture slots")
    return mapping, tuple(untextured)


def stage(dae: Path, texture_dir: Path, output: Path) -> dict:
    dae = private(dae)
    texture_dir = private(texture_dir)
    output = private(output, must_exist=False)
    if not dae.is_file() or dae.suffix.lower() != ".dae":
        raise ValueError("Original DAE not found")
    if not texture_dir.is_dir() or output.exists() or not output.parent.is_dir():
        raise ValueError("Texture folder missing or new output already exists")
    blob = dae.read_bytes()
    mapping, untextured = bindings_from_dae(blob)
    matched = {}
    for name in sorted(set(mapping.values())):
        if not name.endswith(".png"):
            raise ValueError("Only original PNG diffuse textures supported")
        source_name = name[:-4] + ".tex0.png"
        source = private(texture_dir / source_name)
        if not source.is_file() or not 8 <= source.stat().st_size <= MAX_PNG:
            raise ValueError("Original TEX0 base image missing: " + source_name)
        data = source.read_bytes()
        if not data.startswith(PNG):
            raise ValueError("Invalid original TEX0 PNG: " + source_name)
        matched[name] = (source, hashlib.sha256(data).hexdigest())
    if not NAME.fullmatch(dae.name):
        raise ValueError("Invalid DAE filename")
    output.mkdir(exist_ok=False)
    (output / dae.name).write_bytes(blob)
    for filename, (source, digest) in matched.items():
        target = output / filename
        shutil.copyfile(source, target)
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError("PNG changed during private staging")
    result = {
        "status": "ORIGINAL_UV_DAE_TEXTURES_STAGED",
        "dae": dae.name,
        "material_png": mapping,
        "untextured_materials": list(untextured),
        "source_png_count": len(matched),
        "hole_and_render_alignment_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }
    (output / "source-material-mapping-PRIVATE.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dae", type=Path, required=True)
    ap.add_argument("--texture-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args(argv)
    try:
        result = stage(a.dae, a.texture_dir, a.output)
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "ABSTAIN_PRIVATE_TEXTURE_STAGING",
                          "reason": str(exc),
                          "training_approved": False, "allowed_to_publish": False}))
        return 3
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
