"""Source-guided OFFLINE provisional first-terrain-contact solver, not game parity.

No native launch, clock, actor, triangle sidedness, or physical radius verification.
Coordinates are supplied by caller; times are NUMERICAL STEPS, not seconds.
"""
from __future__ import annotations
import argparse
import json
from dataclasses import dataclass
from math import isfinite, sqrt
from pathlib import Path
from typing import Iterable

Vec = tuple[float, float, float]
EPS = 1e-10
SOURCE_QUERY_RADIUS = 0.5  # Source Ball->KCol query on ONE path; NOT ball size.


def vec(v: Iterable[float]) -> Vec:
    t = tuple(float(x) for x in v)
    if len(t) != 3 or not all(isfinite(x) for x in t):
        raise ValueError("expected finite XYZ")
    return t  # type: ignore[return-value]


def add(a: Vec, b: Vec) -> Vec:
    return a[0]+b[0], a[1]+b[1], a[2]+b[2]


def sub(a: Vec, b: Vec) -> Vec:
    return a[0]-b[0], a[1]-b[1], a[2]-b[2]


def mul(a: Vec, k: float) -> Vec:
    return a[0]*k, a[1]*k, a[2]*k


def dot(a: Vec, b: Vec) -> float:
    return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]


def cross(a: Vec, b: Vec) -> Vec:
    return a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]


def norm(a: Vec) -> float:
    return sqrt(dot(a,a))


def unit(a: Vec) -> Vec:
    d = norm(a)
    return mul(a, 1/d) if d > EPS else (0., 0., 0.)


@dataclass(frozen=True)
class Triangle:
    a: Vec
    b: Vec
    c: Vec
    material: str | None = None
    face_id: int = 0

    def __post_init__(self) -> None:
        for p in (self.a, self.b, self.c):
            vec(p)
        if norm(cross(sub(self.b,self.a),sub(self.c,self.a))) <= EPS:
            raise ValueError("degenerate triangle")


@dataclass(frozen=True)
class State:
    position: Vec
    velocity: Vec
    acceleration: Vec = (0., -0.002, 0.)
    speed_like: float = 0.
    lift: float = 0.
    lateral: float = 0.
    spin_axis: Vec = (0., 0., 0.)

    def __post_init__(self) -> None:
        for p in (self.position, self.velocity, self.acceleration, self.spin_axis):
            vec(p)
        if not all(isfinite(x) for x in (self.speed_like,self.lift,self.lateral)):
            raise ValueError("nonfinite motion scalar")


def step_airborne(s: State) -> State:
    """Partial source-guided order v1=v+a; position+=v1; next v=.999000013*v1.

    Optional spin forces are illustrative, not source-perfect fn_80297A00.
    """
    a = s.acceleration
    if s.lift or s.lateral:
        side = unit(cross(s.spin_axis, s.velocity))
        up = unit(cross(s.velocity, side))
        a = add(a, add(mul(up,0.0012*s.speed_like*s.lift),
                       mul(side,0.001*s.speed_like*s.lateral)))
    v = add(s.velocity, a)
    return State(add(s.position,v),mul(v,0.999000013),s.acceleration,
                 s.speed_like,s.lift*0.9985,s.lateral*0.997,s.spin_axis)


def _inside(p: Vec, tri: Triangle, n: Vec) -> bool:
    return all(dot(cross(sub(b,a),sub(p,a)),n)>=-1e-8 for a,b in
               ((tri.a,tri.b),(tri.b,tri.c),(tri.c,tri.a)))


def _roots(a: float, b: float, c: float) -> list[float]:
    if abs(a)<EPS:
        return [-c/b] if abs(b)>EPS else []
    disc=b*b-4*a*c
    if disc < -EPS:
        return []
    d=sqrt(max(0.,disc))
    return sorted(((-b-d)/(2*a),(-b+d)/(2*a)))


def closest_on_triangle(p: Vec, tri: Triangle) -> tuple[Vec,str]:
    """Closest point using vertex/edge/face Voronoi regions."""
    a,b,c=tri.a,tri.b,tri.c
    ab,ac,ap=sub(b,a),sub(c,a),sub(p,a)
    d1,d2=dot(ab,ap),dot(ac,ap)
    if d1<=0 and d2<=0: return a,"vertex"
    bp=sub(p,b); d3,d4=dot(ab,bp),dot(ac,bp)
    if d3>=0 and d4<=d3: return b,"vertex"
    vc=d1*d4-d3*d2
    if vc<=0 and d1>=0 and d3<=0: return add(a,mul(ab,d1/(d1-d3))),"edge"
    cp=sub(p,c); d5,d6=dot(ab,cp),dot(ac,cp)
    if d6>=0 and d5<=d6: return c,"vertex"
    vb=d5*d2-d1*d6
    if vb<=0 and d2>=0 and d6<=0: return add(a,mul(ac,d2/(d2-d6))),"edge"
    va=d3*d6-d5*d4
    if va<=0 and d4-d3>=0 and d5-d6>=0:
        return add(b,mul(sub(c,b),(d4-d3)/((d4-d3)+(d5-d6)))),"edge"
    inv=1/(va+vb+vc)
    return add(a,add(mul(ab,vb*inv),mul(ac,vc*inv))),"face"


def segment_hit(p: Vec, q: Vec, tri: Triangle, radius: float=0.) -> tuple[float,Vec,Vec,str] | None:
    """Two-sided generic straight-segment CCD: face, edge, vertex.

    Initial contact/penetration raises rather than manufacturing a first hit.
    Radius .5 is only valid as a SOURCE-QUERY-TAGGED modeling hypothesis.
    """
    p,q=vec(p),vec(q)
    if not isfinite(radius) or radius<0: raise ValueError("invalid radius")
    if norm(sub(p,closest_on_triangle(p,tri)[0])) <= radius+1e-9:
        raise ValueError("initial overlap/contact; entry time unknown")
    v=sub(q,p); n=unit(cross(sub(tri.b,tri.a),sub(tri.c,tri.a)))
    candidates=[]
    def take(t:float,surface:Vec,feature:str) -> None:
        if -1e-9<=t<=1+1e-9:
            t=max(0.,min(1.,t)); center=add(p,mul(v,t))
            if norm(sub(center,surface))<=radius+1e-7:
                candidates.append((t,center,surface,feature))
    dist=dot(sub(p,tri.a),n); speed=dot(v,n)
    if abs(speed)>EPS:
        for signed in ((-1,1) if radius>0 else (0,)):
            t=(signed*radius-dist)/speed
            if 0<=t<=1:
                center=add(p,mul(v,t));surface=sub(center,mul(n,signed*radius))
                if _inside(surface,tri,n): take(t,surface,"face")
    if radius>0:
        for a,b in ((tri.a,tri.b),(tri.b,tri.c),(tri.c,tri.a)):
            e=sub(b,a); ee=dot(e,e)
            along0=dot(sub(p,a),e)/ee; alongv=dot(v,e)/ee
            w0=sub(sub(p,a),mul(e,along0)); wv=sub(v,mul(e,alongv))
            for t in _roots(dot(wv,wv),2*dot(w0,wv),dot(w0,w0)-radius*radius):
                along=along0+t*alongv
                if 0<=t<=1 and 0<along<1: take(t,add(a,mul(e,along)),"edge")
        for corner in (tri.a,tri.b,tri.c):
            w=sub(p,corner)
            for t in _roots(dot(v,v),2*dot(w,v),dot(w,w)-radius*radius):
                if 0<=t<=1: take(t,corner,"vertex")
    if not candidates: return None
    return min(candidates,key=lambda h:(h[0],{"face":0,"edge":1,"vertex":2}[h[3]]))


def read_obj(path: str | Path,max_faces:int=200000) -> list[Triangle]:
    """Read existing local mesh ONLY. No KCL exporter, transform or publication."""
    vertices=[]; faces=[]; material=None
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            row=line.strip().split()
            if not row or row[0].startswith("#"): continue
            if row[0]=="v":
                if len(row)<4: raise ValueError("bad vertex")
                vertices.append(vec(map(float,row[1:4])))
            elif row[0]=="usemtl":
                material=" ".join(row[1:]) or None
            elif row[0]=="f":
                if len(row)<4: raise ValueError("bad face")
                indices=[]
                for token in row[1:]:
                    i=int(token.split("/")[0])
                    idx=i-1 if i>0 else len(vertices)+i
                    if not 0<=idx<len(vertices): raise ValueError("invalid OBJ index")
                    indices.append(idx)
                for j in range(1,len(indices)-1):
                    if len(faces)>=max_faces: raise ValueError("face limit")
                    faces.append(Triangle(vertices[indices[0]],vertices[indices[j]],
                                          vertices[indices[j+1]],material,len(faces)))
    if not faces: raise ValueError("empty OBJ")
    return faces


def predict_first_contact(start_xyz:Vec, initial_velocity:Vec, terrain:Iterable[Triangle], *,
                          acceleration:Vec=(0.,-0.002,0.),speed_like:float=0.,
                          lift:float=0.,lateral:float=0.,spin_axis:Vec=(0.,0.,0.),
                          contact_mode:str="point_center",assume_tree_free:bool=False,
                          max_steps:int=2500) -> dict:
    """Earliest modeled contact; numerical step time (not game seconds).

    Missing tree clearance abstains. No native ball radius, clock or parity claim.
    """
    if contact_mode not in ("point_center","swept_kcol_query_0p5"):
        raise ValueError("unknown mode")
    if type(max_steps) is not int or not 1<=max_steps<=100000:
        raise ValueError("invalid horizon")
    radius=SOURCE_QUERY_RADIUS if contact_mode=="swept_kcol_query_0p5" else 0.
    if not assume_tree_free:
        return {"status":"ABSTAIN_TREE_CLEARANCE_UNKNOWN","native_game_parity_verified":False,
                "training_approved":False}
    tris=list(terrain)
    if not tris or len(tris)>200000 or not all(isinstance(t,Triangle) for t in tris):
        raise ValueError("invalid terrain")
    state=State(vec(start_xyz),vec(initial_velocity),vec(acceleration),
                speed_like,lift,lateral,vec(spin_axis))
    for step in range(max_steps):
        nxt=step_airborne(state)
        low=[min(state.position[k],nxt.position[k])-radius-1e-8 for k in range(3)]
        high=[max(state.position[k],nxt.position[k])+radius+1e-8 for k in range(3)]
        hits=[]
        for tri in tris:
            if any(max(tri.a[k],tri.b[k],tri.c[k])<low[k] or
                   min(tri.a[k],tri.b[k],tri.c[k])>high[k] for k in range(3)):
                continue
            hit=segment_hit(state.position,nxt.position,tri,radius)
            if hit: hits.append((hit[0],tri.face_id,tri,hit))
        if hits:
            fraction,_,tri,hit=min(hits,key=lambda h:(h[0],h[1]))
            return {"status":"PROVISIONAL_FIRST_CONTACT",
                    "time_numerical_steps":step+fraction,"step_index":step,
                    "fraction_within_step":fraction,"ball_center_xyz":hit[1],
                    "surface_contact_xyz":hit[2],"face_id":tri.face_id,
                    "material_uninterpreted":tri.material,"contact_feature":hit[3],
                    "contact_mode":contact_mode,"query_radius":radius,
                    "provenance":"SOURCE_GUIDED_PARTIAL_AIRBORNE__GENERIC_TWO_SIDED_CCD",
                    "uncertainties":["native_guest_clock_unknown","native_launch_transfer_unknown",
                                     "native_collision_sidedness_unknown","tree_clearance_assumed",
                                     "full_native_integrator_unknown"],
                    "native_game_parity_verified":False,"training_approved":False}
        state=nxt
    return {"status":"NO_CONTACT_IN_HORIZON","horizon_numerical_steps":max_steps,
            "contact_mode":contact_mode,"native_game_parity_verified":False,
            "training_approved":False}


def main() -> None:
    parser=argparse.ArgumentParser(description="Offline provisional first-contact predictor")
    parser.add_argument("--obj",type=Path,help="operator-local existing collision OBJ")
    parser.add_argument("--mode",choices=["point_center","swept_kcol_query_0p5"],
                        default="point_center")
    parser.add_argument("--start",type=float,nargs=3,default=[0,2,0])
    parser.add_argument("--velocity",type=float,nargs=3,default=[0,-.1,0])
    parser.add_argument("--max-steps",type=int,default=250)
    parser.add_argument("--assume-tree-free",action="store_true")
    args=parser.parse_args()
    terrain=read_obj(args.obj) if args.obj else [
        Triangle((-10,0,-10),(0,0,10),(10,0,-10))]
    result=predict_first_contact(tuple(args.start),tuple(args.velocity),terrain,
                                 contact_mode=args.mode,max_steps=args.max_steps,
                                 assume_tree_free=args.assume_tree_free)
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
