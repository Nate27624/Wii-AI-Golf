#!/usr/bin/env python3
"""Read-only ORIGINAL FC3 geometry-to-KCL display transform investigation.

The script never alters source game files, viewer settings, game RAM, Git
worktrees or remembered camera/trees. By default it looks ONLY at an explicit
operator-known FC3 DAE location and at the previously selected local KCL OBJ.
It requires original per-face OGWS labels from a SHA-verified sidecar (or from
the original KCL OBJ groups). Results are scalar diagnostic measurements;
no copyrighted vertex, texture, tree XYZ or animation payloads are printed.

Use --terrain-obj and --labels if the inspector ran before the new label
settings were integrated from PR #432 into the FC3 review checkout.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/"src"))

from wii_ai_golf.inspector.asset_preferences import load_asset_selections
from wii_ai_golf.inspector.dae_visual import load_private_dae_visual_model
from wii_ai_golf.inspector.collada_scene_graph import UnsupportedSceneFeature
from wii_ai_golf.inspector.material_alignment import source_class_counts
from wii_ai_golf.inspector.source_geometry_fit import (
    private_fit_report, SurfaceFitError)
from wii_ai_golf.inspector.terrain import load_private_obj
from wii_ai_golf.inspector.terrain_labels import apply_private_surface_labels


FC3_DEFAULT=Path(
    "D:/Projects/WiiGolfVisualPrivate/visual_exports/"
    "glf_course_fc3/glf_course_fc3.dae")


def inspect(dae: str | Path | None = None,
            terrain: str | Path | None = None,
            labels: str | Path | None = None,
            *, manual_scale: float = 2.0789,
            manual_x: float = .020,
            manual_z: float = .010,
            yaw: int = 0) -> dict:
    report = {
        "status":"ORIGINAL_FC3_TRANSFORM_PREFLIGHT",
        "native_world_transform_verified":False,
        "source_collision_gameplay_owner_verified":False,
        "training_approved":False,
    }
    try:
        settings=load_asset_selections()
    except (OSError,ValueError):
        settings=None
    dae_path=Path(dae) if dae is not None else FC3_DEFAULT
    terrain_path=(Path(terrain) if terrain is not None else
                  Path(settings.terrain_obj) if settings and settings.terrain_obj
                  else None)
    if terrain_path is None:
        report.update(status="NO_SAVED_SOURCE_KCL_OBJ",
                      instruction="Pass --terrain-obj with exact private "
                                  "2498-face FC3 KCL export.")
        return report
    if not dae_path.is_file():
        report.update(status="NO_SOURCE_FC3_DAE",
                      instruction="Export original glf_course_fc3.dae under "
                                  "WiiGolfVisualPrivate/visual_exports/glf_course_fc3")
        return report
    try:
        kcl=load_private_obj(terrain_path)
    except (OSError,ValueError) as exc:
        report.update(status="KCL_OBJ_REJECTED",reason=str(exc))
        return report
    if len(kcl.faces)!=2498:
        # 2,498 original exact FC3 KCL prisms found by the operator. This
        # sanity gate prevents fitting an unrelated hole by accident.
        report.update(status="KCL_ORIGINAL_FACE_COUNT_MISMATCH",
                      source_kcl_triangle_count=len(kcl.faces))
        return report
    report["source_kcl_triangle_count"]=len(kcl.faces)
    report["source_kcl_sha256"]=kcl.sha256
    saved_label=getattr(settings,"terrain_labels",None) if settings else None
    path=(Path(labels) if labels else
          Path(saved_label) if saved_label else
          terrain_path.with_name(
              terrain_path.name.removesuffix("-PRIVATE.obj")+
              "-labels-PRIVATE.json")
          if terrain_path.name.endswith("-PRIVATE.obj") else None)
    if path is not None and (labels or saved_label or path.is_file()):
        try:
            kcl=apply_private_surface_labels(kcl,path)
            report["original_kcl_surface_ids"]="SHA_BOUND_SIDECAR_ACCEPTED"
        except (OSError,ValueError) as exc:
            report.update(status="SOURCE_KCL_LABELS_REJECTED",
                          reason=str(exc))
            return report
    else:
        report["original_kcl_surface_ids"]="OBJ_EMBEDDED_ONLY_OR_MISSING"
    try:
        visual=load_private_dae_visual_model(dae_path)
        report["original_dae_scene_graph"]="SOURCE_GRAPH_APPLIED"
    except UnsupportedSceneFeature as exc:
        try:
            visual=load_private_dae_visual_model(
                dae_path,allow_geometry_only_for_unsupported_scene=True)
        except (OSError,ValueError) as reason:
            report.update(status="FC3_DAE_IMPORT_REJECTED",reason=str(reason))
            return report
        report["original_dae_scene_graph"]="PARTIAL_OR_GEOMETRY_ONLY"
        report["source_scene_limitation"]=str(exc)
    except (OSError,ValueError) as exc:
        report.update(status="FC3_DAE_IMPORT_REJECTED",reason=str(exc))
        return report
    report["original_visual_name"]=visual.source_name
    report["source_dae_sha256"]=visual.obj_sha256
    report["source_dae_renderable_triangle_count"]=len(visual.faces)
    report["original_source_class_counts"]=source_class_counts(kcl,visual)[
        "categories"]
    fit=private_fit_report(
        kcl,visual,initial_multiplier=manual_scale,
        initial_offset_x=manual_x,initial_offset_z=manual_z,
        yaw_degrees=yaw)
    report["surface_fit"]=fit
    report["status"]=(
        "SOURCE_GEOMETRY_FIT_DIAGNOSED" if
        fit["status"]=="ORIGINAL_SURFACE_DISPLAY_FIT_CANDIDATE"
        else "SOURCE_GEOMETRY_FIT_BLOCKED")
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--visual-dae",type=Path,default=None)
    parser.add_argument("--terrain-obj",type=Path,default=None)
    parser.add_argument("--labels",type=Path,default=None)
    parser.add_argument("--manual-scale",type=float,default=2.0789)
    parser.add_argument("--manual-x",type=float,default=.020)
    parser.add_argument("--manual-z",type=float,default=.010)
    parser.add_argument("--yaw",type=int,default=0,choices=(0,90,180,270))
    args=parser.parse_args(argv)
    result=inspect(args.visual_dae,args.terrain_obj,args.labels,
                   manual_scale=args.manual_scale,
                   manual_x=args.manual_x,
                   manual_z=args.manual_z,yaw=args.yaw)
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))
    return 0 if result["status"]=="SOURCE_GEOMETRY_FIT_DIAGNOSED" else 2


if __name__=="__main__":
    raise SystemExit(main())
