"""Inspect, but never apply, original Collada controller bind-shape scales.

A Wii Golf BrawlCrate <instance_controller> may reference a <skin> with an
authored bind_shape_matrix. That is not sufficient to reconstruct bone
skinning, scene/world transforms or the course KCL coordinate system. This
read-only diagnostic reports only bounded scale summaries, not the original
mesh vertices, skin weights or private art.
"""
from __future__ import annotations
from pathlib import Path
import math
import xml.etree.ElementTree as ET

from .visual_model import (
    VisualAssetError, MAX_OBJ_BYTES, _within_private_dir, _read_local)


def _tag(element):
    return element.tag.rsplit("}",1)[-1]


def controller_scale_audit(filename: str | Path) -> dict:
    path=_within_private_dir(Path(filename))
    if path.suffix.lower()!=".dae":
        raise VisualAssetError("Controller scale audit requires original DAE")
    raw=_read_local(path,MAX_OBJ_BYTES)
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise VisualAssetError("Collada DTD/entities forbidden")
    try:
        root=ET.fromstring(raw)
    except ET.ParseError as exc:
        raise VisualAssetError("Invalid original Collada XML") from exc
    if _tag(root)!="COLLADA":
        raise VisualAssetError("Missing original Collada root")
    controllers=[element for n in root if _tag(n)=="library_controllers"
                 for element in n if _tag(element)=="controller"]
    if len(controllers)>8192:
        raise VisualAssetError("Source controller count out of bounds")
    scene_instances=[n for n in root.iter() if _tag(n)=="instance_controller"]
    if len(scene_instances)>8192:
        raise VisualAssetError("Source scene controller instances out of bounds")
    geometry_ids={g.get("id") for lib in root if _tag(lib)=="library_geometries"
                  for g in lib if _tag(g)=="geometry"}
    controller_ids=set()
    skin_count=0
    morph_count=0
    missing_bind_matrix=0
    nonidentity=0
    nonuniform=0
    shape_scales=[]
    missing_geometry_refs=0
    for controller in controllers:
        cid=controller.get("id")
        if not cid or len(cid)>128 or cid in controller_ids:
            raise VisualAssetError("Duplicate/missing original controller id")
        controller_ids.add(cid)
        skins=[n for n in controller if _tag(n)=="skin"]
        morphs=[n for n in controller if _tag(n)=="morph"]
        if len(skins)+len(morphs)!=1:
            raise VisualAssetError("Original Collada controller is ambiguous")
        if morphs:
            morph_count+=1
            continue
        skin_count+=1
        skin=skins[0]
        geometry_ref=skin.get("source","")
        if not geometry_ref.startswith("#") or len(geometry_ref)<2:
            raise VisualAssetError("External/invalid original skin geometry")
        if geometry_ref[1:] not in geometry_ids:
            missing_geometry_refs+=1
        elements=[node for node in skin if _tag(node)=="bind_shape_matrix"]
        if len(elements)>1:
            raise VisualAssetError("Duplicate original bind_shape_matrix")
        if not elements:
            missing_bind_matrix+=1
            continue
        parts=(elements[0].text or "").split()
        if len(parts)!=16:
            raise VisualAssetError("Invalid original bind_shape_matrix arity")
        try:
            vals=[float(v) for v in parts]
        except ValueError as exc:
            raise VisualAssetError("Non-numeric original bind_shape_matrix") from exc
        if any(not math.isfinite(v) or abs(v)>1e7 for v in vals):
            raise VisualAssetError("Nonfinite/unbounded original bind_shape_matrix")
        if max(abs(vals[i]-([1. if j%5==0 else 0. for j in range(16)][i]))
               for i in range(16))>1e-6:
            nonidentity+=1
        # Collada matrices list COLUMN-major; 3 column lengths are the
        # native authored local axis scales, NOT game-world units.
        scales=tuple(math.hypot(*vals[axis*4:axis*4+3]) for axis in range(3))
        if any(x<=1e-8 for x in scales):
            raise VisualAssetError("Singular original bind_shape_matrix")
        if max(scales)/min(scales)>1.001:
            nonuniform+=1
        if len(shape_scales)<16:
            shape_scales.append([round(x,7) for x in scales])
    invalid_controller_refs=0
    for inst in scene_instances:
        ref=inst.get("url","")
        if not ref.startswith("#") or ref[1:] not in controller_ids:
            invalid_controller_refs+=1
    return {
        "original_controller_count":len(controllers),
        "original_scene_controller_instances":len(scene_instances),
        "skin_controller_count":skin_count,
        "morph_controller_count":morph_count,
        "skin_missing_bind_shape_matrix_count":missing_bind_matrix,
        "skin_nonidentity_bind_shape_count":nonidentity,
        "skin_nonuniform_axis_scale_count":nonuniform,
        "first_bind_shape_xyz_axis_scales":shape_scales,
        "missing_internal_geometry_reference_count":missing_geometry_refs,
        "unresolved_internal_scene_controller_reference_count":invalid_controller_refs,
        "bind_shape_is_not_complete_skinning_or_kcl_mapping":True,
        "native_game_world_transform_proven":False,
    }
