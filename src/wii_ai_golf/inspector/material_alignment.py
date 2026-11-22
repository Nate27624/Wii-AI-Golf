"""Read-only material-landmark *display* registration of original KCL and DAE.

The legacy overlay fits whole-model bounding boxes, including large original
sky/scenery backgrounds. That scale cannot match an individual playable hole.
Use independent source-labeled green/fairway centroids and a HELD-OUT bunker
(or, where available, rough) to measure a 2D uniform similarity transform.
Reject incomplete/ambiguous sources instead of showing a grossly overscaled
blue KCL + 94 illustrative trees. Never claim game native world coordinates.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


class MaterialAlignmentError(ValueError):
    """Original source landmarks are missing, ambiguous or inconsistent."""


@dataclass(frozen=True)
class Surface:
    area_xz: float
    centroid: tuple[float, float, float]
    triangle_count: int


@dataclass(frozen=True)
class MaterialAlignment:
    scale: float
    cos_yaw: float
    sin_yaw: float
    translation: tuple[float, float, float]
    yaw_degrees: float
    holdout_name: str
    holdout_error_fraction: float
    green_area_ratio: float

    def apply(self, point):
        x,y,z=point
        tx,ty,tz=self.translation
        return (self.scale*(self.cos_yaw*x-self.sin_yaw*z)+tx,
                self.scale*y+ty,
                self.scale*(self.sin_yaw*x+self.cos_yaw*z)+tz)


# Verified KCol original label IDs vs original DAE material names.
SURFACES = {
    "green":(0x0006, ("M_Green",)),
    "fairway":(0x0001, ("M_Fairway",)),
    "bunker":(0x0003, ("M_Bunker",)),
    "rough":(0x0002, ("M_Rough",)),
}


def surface_from_faces(vertices, faces) -> Surface | None:
    """Area-weighted original horizontal footprint (not mesh world units)."""
    area=0.0
    sums=[0.,0.,0.]
    count=0
    for a,b,c in faces:
        p,q,r=vertices[a],vertices[b],vertices[c]
        twice=abs((q[0]-p[0])*(r[2]-p[2])-
                  (q[2]-p[2])*(r[0]-p[0]))
        if not math.isfinite(twice) or twice>1e15:
            raise MaterialAlignmentError("Invalid source surface triangle")
        weight=twice*.5
        if weight<=1e-10:
            continue
        for i in range(3):
            sums[i]+=weight*(p[i]+q[i]+r[i])/3.
        area+=weight
        count+=1
    if area<=1e-8 or count==0 or not math.isfinite(area):
        return None
    center=tuple(s/area for s in sums)
    if any(not math.isfinite(x) or abs(x)>=1e9 for x in center):
        raise MaterialAlignmentError("Invalid source category centroid")
    return Surface(area,center,count)


def source_class_counts(terrain, visual) -> dict:
    """Source face counts ONLY (not original vectors, camera, private art).

    Crucially, `face_materials=(None, ...)` from a plain original OBJ is
    *non-empty*. Treating that as proof of source OGWS material labels hid
    the missing SHA-bound KCL labels after inspector restarts.
    """
    terrain_materials = getattr(terrain, "face_materials", ())
    terrain_faces = getattr(terrain, "faces", ())
    if terrain_materials and len(terrain_materials) != len(terrain_faces):
        raise MaterialAlignmentError("KCL face/source-ID record count mismatch")
    visual_faces = getattr(visual, "faces", ())
    categories = {}
    for label, (kcl_id, materials) in SURFACES.items():
        categories[label] = {
            "kcl_source_faces": sum(
                x == kcl_id for x in terrain_materials),
            "visual_source_faces": sum(
                face.material in materials for face in visual_faces),
        }
    return {
        "status": "ORIGINAL_SOURCE_CLASS_COUNTS",
        "categories": categories,
        "kcl_source_ogws_labels_recognized": any(
            item["kcl_source_faces"] > 0 for item in categories.values()),
        "visual_source_material_labels_recognized": any(
            item["visual_source_faces"] > 0 for item in categories.values()),
        "scene_or_course_identity_proven": False,
    }


def _landmarks(terrain, visual):
    if (len(terrain.faces)>30000 or len(visual.faces)>100000 or
            not terrain.face_materials or
            len(terrain.face_materials)!=len(terrain.faces)):
        raise MaterialAlignmentError("Need exact KCL per-face source category labels")
    out={}
    for category,(kcl_id,visual_ids) in SURFACES.items():
        k=surface_from_faces(terrain.vertices,(
            face for face,material in zip(terrain.faces,terrain.face_materials)
            if material==kcl_id))
        v=surface_from_faces(visual.vertices,(
            face.vertices for face in visual.faces
            if face.material in visual_ids))
        if k is not None and v is not None:
            out[category]=(k,v)
    return out


def derive_material_alignment(terrain, visual) -> MaterialAlignment:
    """Use 2 source correspondences, validate against an independent 3rd.

    2-D XZ similarities preserve the relative scale of ALL source KCL
    triangles and all 94 original tree bases. They do not prove the original
    game root transform, texture unit scale, tree size or native Y axes.
    """
    counts = source_class_counts(terrain, visual)
    green = counts["categories"]["green"]
    fairway = counts["categories"]["fairway"]
    if any(n <= 0 for n in (
            green["kcl_source_faces"], fairway["kcl_source_faces"],
            green["visual_source_faces"], fairway["visual_source_faces"])):
        hint = (
            "KCL has no usable OGWS IDs: load the matching SHA-bound "
            "-labels-PRIVATE.json (or choose Load KCL source IDs)."
            if green["kcl_source_faces"] == fairway["kcl_source_faces"] == 0
            else "DAE material regions and source KCL must be checked "
                 "against the SAME course, not assumed from FC1 filename.")
        raise MaterialAlignmentError(
            "Cannot measure scale: original green/fairway labels missing. " +
            f"KCL green={green['kcl_source_faces']} "
            f"fairway={fairway['kcl_source_faces']}; "
            f"DAE green={green['visual_source_faces']} "
            f"fairway={fairway['visual_source_faces']}. " + hint)
    pairs=_landmarks(terrain,visual)
    if not all(name in pairs for name in ("green","fairway")):
        raise MaterialAlignmentError(
            "Cannot measure scale: green/fairway source patches have "
            "degenerate or zero horizontal footprint. Verify KCL source "
            "geometry and original Collada skin transforms.")
    k_green,v_green=pairs["green"]
    k_fair,v_fair=pairs["fairway"]
    kg,kf=k_green.centroid,k_fair.centroid
    vg,vf=v_green.centroid,v_fair.centroid
    dx,dz=kg[0]-kf[0],kg[2]-kf[2]
    ex,ez=vg[0]-vf[0],vg[2]-vf[2]
    base=math.hypot(dx,dz)
    target=math.hypot(ex,ez)
    if not 1e-4<base<1e7 or not 1e-4<target<1e7:
        raise MaterialAlignmentError("Green/fairway source centroids are not separable")
    scale=target/base
    if not 1e-4<scale<1e4:
        raise MaterialAlignmentError("Measured source material scale out of bounds")
    cosine=(dx*ex+dz*ez)/(base*target)
    sine=(dx*ez-dz*ex)/(base*target)
    norm=math.hypot(cosine,sine)
    if norm<1e-6:
        raise MaterialAlignmentError("Source directional fit degenerate")
    cosine,sine=cosine/norm,sine/norm
    tx=vg[0]-scale*(cosine*kg[0]-sine*kg[2])
    tz=vg[2]-scale*(sine*kg[0]+cosine*kg[2])
    ty=vg[1]-scale*kg[1]
    area_ratio=v_green.area_xz/(k_green.area_xz*scale*scale)
    if not .5<=area_ratio<=2.:
        raise MaterialAlignmentError(
            "Independent green footprint disagrees with fairway/green "
            "centroid scale; refusing distorted overlay")
    if "bunker" in pairs:
        holdout="bunker"
    elif "rough" in pairs:
        holdout="rough"
    else:
        raise MaterialAlignmentError(
            "No independent source-labeled bunker/rough holdout. "
            "Two landmarks cannot validate visual scale.")
    k_h,v_h=pairs[holdout]
    fit=MaterialAlignment(
        scale,cosine,sine,(tx,ty,tz),
        math.degrees(math.atan2(sine,cosine)),
        holdout,0.,area_ratio)
    projected=fit.apply(k_h.centroid)
    residual=math.hypot(projected[0]-v_h.centroid[0],
                        projected[2]-v_h.centroid[2])
    normalized=residual/target
    if not math.isfinite(normalized) or normalized>.12:
        raise MaterialAlignmentError(
            f"Independent {holdout} location residual {normalized:.1%} "
            "of green-to-fairway distance exceeds 12% tolerance")
    return MaterialAlignment(
        scale,cosine,sine,(tx,ty,tz),fit.yaw_degrees,
        holdout,normalized,area_ratio)


def alignment_diagnostic(terrain, visual) -> dict:
    """Pure derived scalar summary, no original game vector/UV exposure."""
    try:
        counts = source_class_counts(terrain, visual)
        a=derive_material_alignment(terrain,visual)
    except MaterialAlignmentError as exc:
        counts = source_class_counts(terrain, visual)
        return {"status":"SOURCE_DISPLAY_REGISTRATION_DECLINED",
                "reason":str(exc),
                "source_class_counts":counts,
                "native_world_proven":False}
    return {"status":"SOURCE_MATERIAL_DISPLAY_FIT_CANDIDATE",
            "source_class_counts":counts,
            "uniform_scale":round(a.scale,6),
            "display_yaw_degrees":round(a.yaw_degrees,3),
            "independent_holdout_material":a.holdout_name,
            "holdout_error_percent":round(a.holdout_error_fraction*100,2),
            "green_footprint_area_ratio":round(a.green_area_ratio,4),
            "native_world_proven":False,
            "game_collision_or_training_approved":False}
