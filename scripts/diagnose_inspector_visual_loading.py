#!/usr/bin/env python3
"""Diagnose missing original course textures without starting Dolphin or GUI.

Uses the same strict asset loaders as the inspector and prints only local
file/status/face/material information, NEVER source XYZ, UVs or textures.
No writes, no Git changes, no authentication, no game inputs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.inspector.asset_preferences import load_asset_selections
from wii_ai_golf.inspector.dae_visual import load_private_dae_visual_model
from wii_ai_golf.inspector.gui import _known_private_visual_candidate
from wii_ai_golf.inspector.texture_render import prepare_textures
from wii_ai_golf.inspector.visual_model import load_private_visual_model
from wii_ai_golf.inspector.fast_texture_render import accelerated_available


def diagnose(filename: str | None = None) -> dict:
    result = {
        "status": "VISUAL_PREFLIGHT",
        "source_qualified_game_hole": False,
        "native_shader_match_proven": False,
    }
    try:
        saved = load_asset_selections()
    except (OSError, ValueError) as exc:
        return dict(result, status="PREFERENCES_REJECTED",
                    reason=f"{type(exc).__name__}: {exc}")
    result["saved_terrain_path_present"] = bool(saved.terrain_obj)
    result["saved_tree_path_present"] = bool(saved.tree_json)
    result["saved_visual_path_present"] = bool(getattr(saved, "visual_dae", None))
    known = _known_private_visual_candidate(saved.terrain_obj or "")
    candidate = filename or getattr(saved, "visual_dae", None) or (
        str(known) if known is not None else None)
    if candidate is None:
        return dict(result, status="NO_VISUAL_CANDIDATE",
                    reason="No saved DAE and expected exact private FC1 DAE not found")
    path=Path(candidate)
    result["candidate_file"] = str(path)
    result["candidate_exists"] = path.is_file()
    if not path.is_file():
        return dict(result, status="VISUAL_FILE_MISSING",
                    reason="Saved or explicitly selected visual DAE/OBJ does not exist")
    try:
        model = (load_private_dae_visual_model(path)
                 if path.suffix.lower()==".dae"
                 else load_private_visual_model(path))
        rgba = prepare_textures(model)
    except (OSError, ValueError, ImportError, RuntimeError) as exc:
        return dict(result, status="VISUAL_IMPORT_FAILED",
                    reason=f"{type(exc).__name__}: {exc}")
    result.update(
        status="VISUAL_DAE_PNG_VERIFIED",
        original_visual_source_name=model.source_name,
        renderable_triangles=len(model.faces),
        original_texture_slots=len(model.textures),
        decoded_texture_slots=len(rgba),
        omitted_unknown_native_effect_faces=model.skipped_source_faces,
        compiled_numba_available=accelerated_available(),
    )
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--visual-dae",default=None)
    args=parser.parse_args(argv)
    report=diagnose(args.visual_dae)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"]=="VISUAL_DAE_PNG_VERIFIED" else 2


if __name__=="__main__":
    raise SystemExit(main())
