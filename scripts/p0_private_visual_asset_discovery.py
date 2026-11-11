#!/usr/bin/env python3
"""Offline inventory and handoff for original Wii Sports Golf visual assets.

Never reads game RAM, writes to Dolphin, extracts a disc, or uploads assets.
Inventory is bounded, and candidate archive names never prove active hole.
The only "ready" state is an actual UV OBJ/MTL/PNG set accepted by the
existing strict local inspector loader. All original assets remain private.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.inspector.visual_model import VisualAssetError, load_private_visual_model

EXTS = {".carc", ".arc", ".szs", ".brres", ".mdl0", ".tex0", ".dae", ".obj", ".mtl", ".png"}
MAX_FILES = 20_000
MAX_DEPTH = 9
MAX_REPORT_ITEMS = 80
MAX_FILE_SIZE = 512 * 1024 * 1024
MAGICS = (
    (b"bres", "BRRES"),
    (b"MDL0", "MDL0"),
    (b"TEX0", "TEX0"),
    (b"Yaz0", "YAZ0_COMPRESSED"),
    (b"Yay0", "YAY0_COMPRESSED"),
    (b"RARC", "RARC"),
    (b"\x55\xaa\x38\x2d", "U8_ARCHIVE"),
)


def _outside_git(folder: Path) -> bool:
    if folder.is_symlink() or not folder.is_dir():
        return False
    parent = folder.resolve(strict=True)
    if any((p / ".git").exists() for p in (parent, *parent.parents)):
        return False
    return True


def _classify(path: Path) -> str:
    try:
        if path.is_symlink() or not path.is_file():
            return "REJECT_LINK"
        if not 0 < path.stat().st_size <= MAX_FILE_SIZE:
            return "REJECT_SIZE"
        with path.open("rb") as stream:
            head = stream.read(8)
        for magic, label in MAGICS:
            if head.startswith(magic):
                return label
        return "UNRECOGNIZED_HEADER"
    except OSError:
        return "READ_FAILED"


def scan(root: Path) -> dict:
    if not _outside_git(root):
        raise ValueError("Source directory must be a real private directory outside Git")
    root = root.resolve(strict=True)
    counts: Counter[str] = Counter()
    formats: Counter[str] = Counter()
    names: list[dict] = []
    valid_models: list[dict] = []
    scanned = 0
    truncated = False
    raw_tex0: set[Path] = set()
    base_pngs: set[Path] = set()

    # Never follow symlinks, even when their target is inside the root.
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        base = Path(current)
        depth = len(base.relative_to(root).parts)
        dirs[:] = sorted(d for d in dirs
                         if depth < MAX_DEPTH and d.lower() != ".git"
                         and not (base / d).is_symlink())
        if depth > MAX_DEPTH:
            continue
        for filename in sorted(files):
            scanned += 1
            if scanned > MAX_FILES:
                truncated = True
                break
            source = base / filename
            if source.suffix.lower() not in EXTS or source.is_symlink():
                continue
            kind = source.suffix.lower().removeprefix(".")
            counts[kind] += 1
            status = _classify(source) if kind in {"carc", "arc", "szs", "brres", "mdl0", "tex0"} else "FILE_FOUND"
            if kind == "tex0":
                raw_tex0.add(source.relative_to(root))
            if kind == "png" and ".mm" not in source.stem:
                base_pngs.add(source.relative_to(root))
            if status != "FILE_FOUND":
                formats[status] += 1
            if len(names) < MAX_REPORT_ITEMS:
                names.append({
                    "path": str(source.relative_to(root)),
                    "type": kind,
                    "header": status,
                })
            if kind == "obj":
                try:
                    model = load_private_visual_model(source)
                except (VisualAssetError, OSError, ValueError):
                    continue
                valid_models.append({
                    "path": str(source.relative_to(root)),
                    "uv_faces": len(model.faces),
                    "png_textures": len(model.textures),
                    "sha256": model.obj_sha256,
                    "hole_verified": False,
                })
        if truncated:
            break
    unresolved_tex0 = sorted(str(p) for p in raw_tex0
                            if Path(str(p) + ".png") not in base_pngs)
    if valid_models:
        stage = "UV_VISUAL_MODELS_READY_TO_PREVIEW_HOLE_UNVERIFIED"
    elif counts["dae"]:
        stage = "DAE_FOUND_NEEDS_UV_OBJ_MTL_PNG_CONVERSION"
    elif counts["mdl0"] and counts["png"]:
        stage = "MDL0_WITH_EXTRACTED_PNG_NEEDS_UV_DAE_EXPORT"
    elif counts["mdl0"]:
        stage = "MDL0_FOUND_NEEDS_ORIGINAL_TEXTURE_EXPORT"
    elif counts["brres"]:
        stage = "BRRES_FOUND_NEEDS_MDL0_TEX0_EXPORT"
    elif counts["carc"] or counts["arc"] or counts["szs"]:
        stage = "ARCHIVES_FOUND_NEEDS_FORMAT_VERIFIED_EXTRACTION"
    else:
        stage = "NO_COURSE_VISUAL_ASSETS_FOUND"
    return {
        "kind": "P0_PRIVATE_VISUAL_ASSET_DISCOVERY",
        "stage": stage, "count_by_extension": dict(sorted(counts.items())),
        "archive_headers": dict(sorted(formats.items())),
        "files_examined": min(scanned, MAX_FILES),
        "truncated": truncated, "candidates": names,
        "ready_uv_models": valid_models[:MAX_REPORT_ITEMS],
        "raw_tex0_without_matching_base_png": unresolved_tex0[:MAX_REPORT_ITEMS],
        "unresolved_tex0_count": len(unresolved_tex0),
        "source_hole_and_alignment_verified": False,
        "training_approved": False, "allowed_to_publish": False,
    }


def check_model(filename: Path, open_window: bool = False) -> dict:
    model = load_private_visual_model(filename)
    report = {
        "kind": "P0_PRIVATE_VISUAL_MODEL_CHECK",
        "status": "READY_PRIVATE_TEXTURE_PREVIEW",
        "filename": filename.name,
        "uv_faces": len(model.faces),
        "texture_count": len(model.textures),
        "obj_sha256": model.obj_sha256,
        "source_hole_and_alignment_verified": False,
        "training_approved": False, "allowed_to_publish": False,
    }
    if open_window:
        # Dedicated Tk scene preview; never starts/connects to Dolphin.
        import tkinter as tk
        from wii_ai_golf.inspector.textured_preview import TexturedPreviewWindow
        window = tk.Tk()
        window.withdraw()
        try:
            TexturedPreviewWindow(window, model)
            window.mainloop()
        finally:
            if window.winfo_exists():
                window.destroy()
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--scan", type=Path, help="Existing outside-Git private asset directory")
    group.add_argument("--check-model", type=Path, help="UV OBJ with MTL and local PNGs")
    ap.add_argument("--preview", action="store_true", help="Open isolated private texture preview after check")
    a = ap.parse_args(argv)
    if a.preview and a.check_model is None:
        ap.error("--preview requires --check-model")
    try:
        report = scan(a.scan) if a.scan is not None else check_model(a.check_model, a.preview)
    except (OSError, ValueError, RuntimeError, ImportError):
        print(json.dumps({
            "kind": "P0_PRIVATE_VISUAL_ASSET_DISCOVERY",
            "status": "ABSTAIN_ASSET_PATH_OR_FORMAT",
            "training_approved": False, "allowed_to_publish": False,
        }, sort_keys=True))
        return 3
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
