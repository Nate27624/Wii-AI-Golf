"""Read-only, source-qualified course registration diagnostics.

This is NOT a registration solver. It tests whether a source-verified tee/pin
pair lives in the KCL coordinate frame and whether an original Collada
visual_scene transform was omitted by the UV renderer. No guessed rotation,
trainable surface, model transform or asset bytes are written.
"""
from __future__ import annotations

from collections import Counter
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from .visual_model import MAX_OBJ_BYTES, VisualAssetError, _within_private_dir, _read_local


class RegistrationAuditError(ValueError):
    pass


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _float_array(raw: str | None, count: int) -> tuple[float, ...]:
    if not isinstance(raw, str):
        raise RegistrationAuditError("Missing source Collada scene transform")
    parts = raw.split()
    if len(parts) != count:
        raise RegistrationAuditError("Source Collada scene transform length mismatch")
    try:
        nums = tuple(float(p) for p in parts)
    except ValueError as exc:
        raise RegistrationAuditError("Source Collada scene transform not numeric") from exc
    if any(not math.isfinite(v) or abs(v) > 1e7 for v in nums):
        raise RegistrationAuditError("Source Collada scene transform out of safe range")
    return nums


_IDENTITY_4 = (1., 0., 0., 0.,
               0., 1., 0., 0.,
               0., 0., 1., 0.,
               0., 0., 0., 1.)


def audit_collada_scene(filename: str | Path) -> dict[str, object]:
    """Inspect actual source-authored Collada scene transforms without exporting art.

    Report only transform types/counts and whether a scene transform is
    nonidentity. Collada matrix is column-major; translation is slots 12..14.
    Current DAE UV loader does not apply library_visual_scenes node matrices.
    """
    path = _within_private_dir(Path(filename))
    if path.suffix.lower() != ".dae":
        raise RegistrationAuditError("Original visual path must be DAE")
    raw = _read_local(path, MAX_OBJ_BYTES)
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise RegistrationAuditError("Collada DTD/entities forbidden")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise RegistrationAuditError("Invalid original Collada XML") from exc
    if _local_name(root.tag) != "COLLADA":
        raise RegistrationAuditError("Not a Collada source file")
    asset = next((n for n in root if _local_name(n.tag) == "asset"), None)
    up_axes = [] if asset is None else [
        (n.text or "").strip() for n in asset if _local_name(n.tag) == "up_axis"]
    if len(up_axes) > 1:
        raise RegistrationAuditError("Ambiguous original Collada up axis")
    up_axis = up_axes[0] if up_axes else "UNSPECIFIED"
    if up_axis not in ("X_UP", "Y_UP", "Z_UP", "UNSPECIFIED"):
        raise RegistrationAuditError("Unknown source Collada up axis")
    libraries = [n for n in root if _local_name(n.tag) == "library_visual_scenes"]
    scenes = [v for lib in libraries for v in lib if _local_name(v.tag) == "visual_scene"]
    binding = [n for n in root if _local_name(n.tag) == "scene"]
    targets = [(ch.get("url") or "") for n in binding for ch in n
               if _local_name(ch.tag) == "instance_visual_scene"]
    geometry_refs = []
    transforms = Counter()
    nonidentity = 0
    nodes = 0
    matrix_rotations = []
    for scene in scenes:
        for node in scene.iter():
            if _local_name(node.tag) != "node":
                continue
            nodes += 1
            for child in node:
                kind = _local_name(child.tag)
                if kind == "instance_geometry":
                    geometry_refs.append(child.get("url") or "")
                if kind in ("matrix", "translate", "rotate", "scale", "lookat", "skew"):
                    transforms[kind] += 1
                    if kind in ("lookat", "skew"):
                        nonidentity += 1
                        continue
                    expected = {"matrix":16, "translate":3, "scale":3, "rotate":4}[kind]
                    nums = _float_array(child.text, expected)
                    if kind == "matrix":
                        if any(abs(v - x) > 1e-6 for v, x in zip(nums, _IDENTITY_4)):
                            nonidentity += 1
                        # Angle of matrix's local +X axis in XZ (diagnostic only).
                        # Do not confuse this with confirmed game/root yaw.
                        yaw = math.degrees(math.atan2(nums[2], nums[0]))
                        if math.isfinite(yaw) and abs(yaw) > 1e-5:
                            matrix_rotations.append(round(yaw, 3))
                    elif kind == "rotate":
                        if abs(nums[3] % 360.) > 1e-6:
                            nonidentity += 1
                    elif kind == "translate":
                        if any(abs(v) > 1e-6 for v in nums):
                            nonidentity += 1
                    elif kind == "scale":
                        if any(abs(v - 1.) > 1e-6 for v in nums):
                            nonidentity += 1
    if nodes > 20000 or len(geometry_refs) > 20000:
        raise RegistrationAuditError("Unbounded source scene graph")
    return {
        "visual_scene_count": len(scenes),
        "scene_bindings_count": len(targets),
        "active_scene_target_present": len(targets) == 1,
        "geometry_instance_count": len(geometry_refs),
        "unique_geometry_refs": len(set(geometry_refs)),
        "node_count": nodes,
        "transform_counts": dict(sorted(transforms.items())),
        "nonidentity_transform_count": nonidentity,
        "matrix_xz_yaw_degrees_hypotheses": sorted(set(matrix_rotations))[:12],
        "up_axis": up_axis,
        "current_loader_applies_visual_scene_transforms": False,
    }


def _cross(a, b) -> tuple[float, float, float]:
    return (a[1]*b[2]-a[2]*b[1],
            a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def _centroids(vertices, faces, chosen) -> tuple[tuple[float, float, float], int] | None:
    acc = [0., 0., 0.]
    total = 0.
    count = 0
    for face in chosen:
        a, b, c = (vertices[i] for i in face)
        ab = [b[i]-a[i] for i in range(3)]
        ac = [c[i]-a[i] for i in range(3)]
        axis = _cross(ab, ac)
        weight = math.sqrt(sum(x*x for x in axis)) * .5
        if not 0 < weight < 1e15:
            continue
        for i in range(3):
            acc[i] += (a[i]+b[i]+c[i])/3 * weight
        count += 1
        total += weight
    if count == 0 or total <= 0:
        return None
    result = tuple(x/total for x in acc)
    if any(not math.isfinite(v) or abs(v) > 1e7 for v in result):
        raise RegistrationAuditError("Unbounded source surface centroid")
    return result, count


def _heading(a, b) -> float | None:
    dx, dz = b[0]-a[0], b[2]-a[2]
    if math.hypot(dx, dz) < 1e-6:
        return None
    return (math.degrees(math.atan2(dz, dx)) + 360.) % 360.


def _angle_diff(a: float, b: float) -> float:
    return ((a-b+180.) % 360.)-180.


def audit_surface_registration(terrain, visual, *,
                               tee: tuple[float, float, float] | None = None,
                               pin: tuple[float, float, float] | None = None) -> dict:
    """Source category comparison with optional selected-actor RAM anchors.

    Surface centroids are *summaries* and cannot be used as precise scene
    correspondences; never apply calculated angle to native geometry.
    """
    if not terrain.vertices or not terrain.faces or not visual.vertices or not visual.faces:
        raise RegistrationAuditError("Source geometry missing")
    k = {}
    for name, attr in (("green", 6), ("fairway", 1), ("bunker", 3)):
        chosen = (f for f, material in zip(
            terrain.faces, terrain.face_materials or (None,)*len(terrain.faces))
            if material == attr)
        k[name] = _centroids(terrain.vertices, terrain.faces, chosen)
    v = {}
    for name, material in (("green", "M_Green"), ("fairway", "M_Fairway"),
                           ("bunker", "M_Bunker")):
        v[name] = _centroids(visual.vertices, (), (face.vertices for face in visual.faces
                                                   if face.material == material))
    report = {
        "kcl_vertices": len(terrain.vertices),
        "kcl_faces": len(terrain.faces),
        "kcl_source_surface_triangle_counts": {
            n: result[1] if result is not None else 0 for n, result in k.items()},
        "visual_vertices": len(visual.vertices),
        "visual_faces": len(visual.faces),
        "visual_source_surface_triangle_counts": {
            n: result[1] if result is not None else 0 for n, result in v.items()},
        "source_geometry_identity_proven": False,
        "native_game_world_transform_proven": False,
    }
    # Green-to-fairway centroids yield only a coarse relative heading, not
    # an exact tee/pin correspondence. Do not silently optimize/draw from it.
    if all(k.get(n) is not None and v.get(n) is not None for n in ("green", "fairway")):
        kh = _heading(k["fairway"][0], k["green"][0])
        vh = _heading(v["fairway"][0], v["green"][0])
        if kh is not None and vh is not None:
            report["coarse_surface_heading_delta_deg"] = round(_angle_diff(vh, kh), 2)
            report["heading_is_not_a_source_matrix"] = True
    if tee is not None and pin is not None:
        if any(len(p) != 3 or any(not math.isfinite(x) or abs(x) > 1e7 for x in p)
               for p in (tee, pin)):
            raise RegistrationAuditError("Invalid source-selected tee/pin vector")
        report["ram_tee_to_pin_distance_xz"] = round(math.hypot(
            pin[0]-tee[0], pin[2]-tee[2]), 4)
        if k["green"] is not None:
            c = k["green"][0]
            report["ram_pin_to_kcl_green_centroid_xz"] = round(
                math.hypot(pin[0]-c[0], pin[2]-c[2]), 4)
        if k["fairway"] is not None:
            c = k["fairway"][0]
            report["ram_tee_to_kcl_fairway_centroid_xz"] = round(
                math.hypot(tee[0]-c[0], tee[2]-c[2]), 4)
        report["ram_vectors_source_gated_but_world_axes_unverified"] = True
    else:
        report["ram_anchors_status"] = "NO_LIVE_SOURCE_GATED_TEE_PIN"
    return report
