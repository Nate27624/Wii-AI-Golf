"""Read-only original terrain-surface registration diagnostic (never game physics).

Given source-matched OGWS KCL and a BrawlCrate DAE of the SAME FC archive,
search locally near an operator-provided display-only similarity. Use green
and fairway patches for fit and reserve bunker (or rough) as independent
validation. All inputs are original strict local loaders. Source coordinates,
textures and game code are neither written nor returned by the diagnostic.

The KCL surface and rendered DAE can have distinct triangulation/coverage,
so a low nearest-neighbor score is not proof of native world transformation.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .scene_camera import playable_source_vertices
from .material_alignment import SURFACES

MAX_SAMPLE_FACES = 220
MAX_CANDIDATE_EVALUATIONS = 1600


class SurfaceFitError(ValueError):
    """Source material correspondence absent or inconsistent."""


@dataclass(frozen=True)
class SurfaceFit:
    multiplier: float
    offset_x: float
    offset_z: float
    yaw_degrees: int
    absolute_scale: float
    source_kcl_to_visual_offset: tuple[float, float, float]
    training_score_fraction: float
    holdout_score_fraction: float
    holdout_class: str
    training_scores: dict[str, float]
    source_counts: dict[str, Any]
    initial_training_fraction: float
    initial_holdout_fraction: float
    improvement_fraction: float
    native_world_verified: bool = False


def source_class_counts(terrain, visual) -> dict:
    """Original material sample population, even before #432 rebase.

    No geometry, private position or texture data is returned.
    A 2,498-entry array of None is NOT proof of original KCL IDs.
    """
    source_ids=getattr(terrain,"face_materials",())
    kcl_faces=getattr(terrain,"faces",())
    if source_ids and len(source_ids)!=len(kcl_faces):
        raise SurfaceFitError("KCL original material ID/face count mismatch")
    result={}
    for name,(source_id,materials) in SURFACES.items():
        result[name]={
            "kcl_source_faces":sum(x==source_id for x in source_ids),
            "visual_source_faces":sum(
                f.material in materials for f in visual.faces)}
    return {
        "categories":result,
        "source_kcl_has_recognized_ogws_ids":any(
            v["kcl_source_faces"]>0 for v in result.values()),
        "source_dae_has_corresponding_materials":any(
            v["visual_source_faces"]>0 for v in result.values()),
        "native_scene_alignment_proven":False,
    }


def _source_points(terrain, visual):
    """Deterministic capped ORIGINAL triangle centroid samples per class."""
    import numpy as np

    if not terrain.face_materials or len(terrain.face_materials) != len(terrain.faces):
        raise SurfaceFitError(
            "KCL face IDs missing: attach original SHA-verified -labels-PRIVATE.json")
    if not visual.faces or not terrain.faces:
        raise SurfaceFitError("Original source geometry missing")
    labels=source_class_counts(terrain, visual)
    groups={}
    for name,(attr,visual_materials) in SURFACES.items():
        k_indices=[i for i,code in enumerate(terrain.face_materials) if code==attr]
        v_indices=[i for i,face in enumerate(visual.faces) if face.material in visual_materials]
        if not k_indices or not v_indices:
            continue

        def samples(vertices, faces, indices, *, visual_faces):
            take=np.linspace(0,len(indices)-1,min(MAX_SAMPLE_FACES,len(indices)),dtype=int)
            samples=[]
            for ind in take:
                face=faces[indices[int(ind)]]
                tri=face.vertices if visual_faces else face
                a,b,c=(vertices[q] for q in tri)
                twice=abs((b[0]-a[0])*(c[2]-a[2])-
                          (b[2]-a[2])*(c[0]-a[0]))
                if twice <= 1e-9:
                    continue
                samples.append(tuple((a[dim]+b[dim]+c[dim])/3. for dim in (0,1,2)))
            if len(samples)<3:
                return None
            pts=np.asarray(samples,dtype=np.float64)
            if not np.isfinite(pts).all() or np.max(np.abs(pts)) >= 1e7:
                raise SurfaceFitError("Invalid original source surface samples")
            return pts

        kp=samples(terrain.vertices,terrain.faces,k_indices,visual_faces=False)
        vp=samples(visual.vertices,visual.faces,v_indices,visual_faces=True)
        if kp is not None and vp is not None:
            groups[name]=(kp,vp)
    if "green" not in groups or "fairway" not in groups:
        counts=labels["categories"]
        raise SurfaceFitError(
            "Need original green+fairway on BOTH files. "
            f"KCL green={counts['green']['kcl_source_faces']} "
            f"fairway={counts['fairway']['kcl_source_faces']}; "
            f"DAE green={counts['green']['visual_source_faces']} "
            f"fairway={counts['fairway']['visual_source_faces']}. "
            "Verify exact FC3 DAE and SHA-bound KCL labels")
    holdout="bunker" if "bunker" in groups else (
        "rough" if "rough" in groups else None)
    if holdout is None:
        raise SurfaceFitError(
            "No separately source-labeled bunker/rough to hold out; "
            "refusing unverifiable geometry-fit claim")
    return groups,holdout,labels


def fit_source_surface_display(terrain, visual, *,
                               initial_multiplier: float=2.0789,
                               initial_offset_x: float=0.020,
                               initial_offset_z: float=0.010,
                               yaw_degrees: int=0) -> SurfaceFit:
    """Optimize source-labeled 2D terrain similarity near operator trial.

    Returns a VISUAL PREVIEW candidate, not an original Wii scene matrix.
    KCL and exact 94 source tree bases must eventually receive same transform.
    Independent bunker/rough patch NEVER participates in the fit.
    """
    import numpy as np

    if (type(yaw_degrees) is not int or yaw_degrees not in (0,90,180,270)
            or any(type(x) not in (int,float) or not math.isfinite(x)
                   for x in (initial_multiplier,initial_offset_x,initial_offset_z))
            or not .25<=initial_multiplier<=4.
            or not -1.<=initial_offset_x<=1.
            or not -1.<=initial_offset_z<=1.):
        raise SurfaceFitError("Invalid bounded operator source display trial")
    groups,holdout,counts=_source_points(terrain,visual)
    k=np.asarray(terrain.vertices,dtype=np.float64)
    v=np.asarray(playable_source_vertices(visual),dtype=np.float64)
    if (len(k)<3 or len(v)<3 or not np.isfinite(k).all()
            or not np.isfinite(v).all()):
        raise SurfaceFitError("Source bounds unavailable")
    kmin,kmax=np.min(k,axis=0),np.max(k,axis=0)
    vmin,vmax=np.min(v,axis=0),np.max(v,axis=0)
    ks=kmax-kmin
    vs=vmax-vmin
    source_x=(ks[2] if yaw_degrees in (90,270) else ks[0])
    source_z=(ks[0] if yaw_degrees in (90,270) else ks[2])
    if min(source_x,source_z,vs[0],vs[2])<=1e-8:
        raise SurfaceFitError("Degenerate original source bounds")
    base=min(float(vs[0]/source_x),float(vs[2]/source_z))
    diagonal=float(math.hypot(vs[0],vs[2]))
    kcenter=(kmin+kmax)*.5
    vcenter=(vmin+vmax)*.5
    if not 1e-6<base<1e6 or not 1e-6<diagonal<1e7:
        raise SurfaceFitError("Unbounded original source display frame")

    theta=math.radians(yaw_degrees)
    c,s=math.cos(theta),math.sin(theta)
    # The 0/90/180/270 trial is the SAME yaw as PR436 x-ray display.
    rotated={}
    for name,(kp,vp) in groups.items():
        delta=kp[:,(0,2)]-kcenter[[0,2]]
        rot=np.column_stack((c*delta[:,0]-s*delta[:,1],
                             s*delta[:,0]+c*delta[:,1]))
        rotated[name]=(rot,vp[:,(0,2)])

    def nearest_metric(source,reference):
        # Small bounded nearest-neighbor comparison on ORIGINAL material
        # triangle centroids, not arbitrary pixels or illustrative crowns.
        if len(source)>MAX_SAMPLE_FACES or len(reference)>MAX_SAMPLE_FACES:
            raise SurfaceFitError("Source material sample count unbounded")
        dif=source[:,None,:]-reference[None,:,:]
        sq=np.einsum("ijk,ijk->ij",dif,dif)
        distances=np.sqrt(np.maximum(0.,sq.min(axis=1)))
        # Trim distant scenery / non-identical KCL-vs-DAE tessellation,
        # but evaluate the independent holdout *untrimmed* as a safeguard.
        return float(np.mean(np.sort(distances)[:max(3,math.ceil(len(distances)*.85))]))

    def measures(mult,offx,offz,names):
        scale=base*mult
        shift=np.array([vcenter[0]+offx*diagonal,
                        vcenter[2]+offz*diagonal])
        return {name: nearest_metric(rot*scale+shift,ref)/diagonal
                for name,(rot,ref) in rotated.items() if name in names}

    # The independent holdout is NEVER consulted inside this search.
    calls=0
    def train(candidate):
        nonlocal calls
        calls+=1
        if calls>MAX_CANDIDATE_EVALUATIONS:
            raise SurfaceFitError("Source fit candidate search exceeded bound")
        m,x,z=candidate
        d=measures(m,x,z,("green","fairway"))
        return (d["green"]+d["fairway"])*.5

    initial=(float(initial_multiplier),float(initial_offset_x),
             float(initial_offset_z))
    first_score=train(initial)
    # Deterministic coarse-to-fine search around operator's visible good
    # fit and a 1x automatic initial guess. No blind enormous global ICP
    # whose spurious correspondence can move the KCL off the fairway.
    best=initial
    best_score=first_score
    for seed in (initial,(1.,0.,0.)):
        current=seed
        score=train(seed)
        for scale_step,offset_step in (
                (.25,.04),(.12,.020),(.06,.010),(.025,.004),(.009,.0015)):
            winner=current
            win_score=score
            for a in (-1,0,1):
                for b in (-1,0,1):
                    for d in (-1,0,1):
                        candidate=(round(current[0]*math.exp(a*scale_step),9),
                                   round(current[1]+b*offset_step,9),
                                   round(current[2]+d*offset_step,9))
                        if not .25<=candidate[0]<=4. or any(
                                abs(v)>1. for v in candidate[1:]):
                            continue
                        metric=train(candidate)
                        if metric < win_score:
                            winner,win_score=candidate,metric
            current,score=winner,win_score
        if score<best_score:
            best,best_score=current,score
    chosen_train=measures(*best,("green","fairway"))
    original_hold=measures(*initial,(holdout,))[holdout]
    new_hold=measures(*best,(holdout,))[holdout]
    # If a train-driven optimization hurts held-out bunker/rough,
    # refuse to promote it even as a data-supported display candidate.
    improvement=float(first_score-best_score)
    if new_hold>original_hold*1.15+0.002:
        raise SurfaceFitError(
            "Fit improved training faces but WORSENED independent "
            f"{holdout} by more than 15%: not a reliable transform")
    m,x,z=best
    effective_scale=base*m
    displacement=(
        float(vcenter[0]-effective_scale*(c*kcenter[0]-s*kcenter[2])+
              x*diagonal),
        float(vcenter[1]-effective_scale*kcenter[1]),
        float(vcenter[2]-effective_scale*(s*kcenter[0]+c*kcenter[2])+
              z*diagonal))
    return SurfaceFit(
        m,x,z,yaw_degrees,effective_scale,displacement,
        best_score,new_hold,holdout,chosen_train,counts,
        first_score,original_hold,improvement)


def private_fit_report(terrain, visual, **kwargs) -> dict:
    """Only scalar scores, source SHA pointers and categorical provenance."""
    try:
        fit=fit_source_surface_display(terrain,visual,**kwargs)
    except (SurfaceFitError,ValueError) as exc:
        return {"status":"SOURCE_GEOMETRY_FIT_DECLINED",
                "reason":str(exc),"native_world_verified":False,
                "game_collision_or_training_approved":False}
    # Quality thresholds are conservative heuristic gates, NOT native
    # transform proof: compare both training and a truly held-out region.
    passed=(fit.training_score_fraction<=.035 and
            fit.holdout_score_fraction<=.06 and
            fit.holdout_score_fraction<=fit.initial_holdout_fraction*1.15+.002)
    return {
        "status":("ORIGINAL_SURFACE_DISPLAY_FIT_CANDIDATE" if passed
                  else "ORIGINAL_SURFACE_FIT_FAILED_HOLDOUT_GATE"),
        "independent_surface_heldout_gate_passed":passed,
        "original_kcl_sha256":terrain.sha256,
        "original_dae_sha256":visual.obj_sha256,
        "original_visual_name":visual.source_name,
        "display_scale_multiplier_of_initial_bounds":round(fit.multiplier,6),
        "display_absolute_scale":round(fit.absolute_scale,8),
        "display_yaw_degrees":fit.yaw_degrees,
        "display_offset_fraction_of_visual_diagonal":{
            "x":round(fit.offset_x,6),"z":round(fit.offset_z,6)},
        "initial_manual_green_fairway_error_percent_of_diagonal":
            round(fit.initial_training_fraction*100,4),
        "optimized_green_fairway_error_percent_of_diagonal":
            round(fit.training_score_fraction*100,4),
        "initial_held_out_error_percent_of_diagonal":
            round(fit.initial_holdout_fraction*100,4),
        "optimized_held_out_error_percent_of_diagonal":
            round(fit.holdout_score_fraction*100,4),
        "held_out_material":fit.holdout_class,
        "source_category_face_counts":fit.source_counts["categories"],
        "interpretation":"Display-only surface centroid nearest-neighbor fit; "
            "not native geometry/skinning/world coordinate registration.",
        "native_world_verified":False,
        "game_collision_or_training_approved":False,
    }
