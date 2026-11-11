"""Bounded original Collada 1.5 scene graph transforms (no guessed axes).

The Wii visual renderer previously loaded library_geometries POSITION arrays
without respecting library_visual_scenes node transforms. Collada nodes can
translate/rotate/scale geometry instances. Apply only authored scene
transforms, never an invented KCL/texture correction or guessed game matrix.

4x4 internal representation is ROW-major; Collada <matrix> text is
COLUMN-major. Vectors are homogeneous columns, world=parent @ local.
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET

from .visual_model import VisualAssetError

MAX_SCENE_NODES = 20_000
MAX_SCENE_DEPTH = 64
MAX_TRANSFORMS_PER_NODE = 64
MAX_GEOMETRY_INSTANCES = 20_000
IDENTITY = (
    1., 0., 0., 0.,
    0., 1., 0., 0.,
    0., 0., 1., 0.,
    0., 0., 0., 1.,
)


def _tag(node: ET.Element) -> str:
    return node.tag.rsplit("}", 1)[-1]


def _numbers(node: ET.Element, count: int) -> tuple[float, ...]:
    words = (node.text or "").split()
    if len(words) != count:
        raise VisualAssetError("Original Collada node transform arity mismatch")
    try:
        nums = tuple(float(w) for w in words)
    except ValueError as exc:
        raise VisualAssetError("Original Collada node transform malformed") from exc
    if any(not math.isfinite(v) or abs(v) > 1e7 for v in nums):
        raise VisualAssetError("Original Collada node transform out of bounds")
    return nums


def _mul(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, ...]:
    out = tuple(sum(a[i*4+k]*b[k*4+j] for k in range(4))
                for i in range(4) for j in range(4))
    if any(not math.isfinite(v) or abs(v) > 1e10 for v in out):
        raise VisualAssetError("Original Collada model transform overflow")
    return out


def _node_transform(node: ET.Element) -> tuple[float, ...]:
    kind = _tag(node)
    if kind == "matrix":
        vals = _numbers(node, 16)
        matrix = tuple(vals[c*4+r] for r in range(4) for c in range(4))
    elif kind in ("translate", "scale"):
        x,y,z = _numbers(node, 3)
        matrix = (1.,0.,0.,x, 0.,1.,0.,y, 0.,0.,1.,z, 0.,0.,0.,1.) if kind == "translate" else (
            x,0.,0.,0., 0.,y,0.,0., 0.,0.,z,0., 0.,0.,0.,1.)
    elif kind == "rotate":
        x,y,z,degrees = _numbers(node, 4)
        norm = math.sqrt(x*x+y*y+z*z)
        if not 1e-8 < norm < 1e7:
            raise VisualAssetError("Original Collada rotation axis invalid")
        x,y,z = x/norm,y/norm,z/norm
        radians = math.radians(degrees)
        c, sn = math.cos(radians), math.sin(radians)
        d=1.-c
        matrix=(
            c+x*x*d, x*y*d-z*sn, x*z*d+y*sn, 0.,
            y*x*d+z*sn, c+y*y*d, y*z*d-x*sn, 0.,
            z*x*d-y*sn, z*y*d+x*sn, c+z*z*d, 0.,
            0.,0.,0.,1.,
        )
    else:
        raise VisualAssetError("Unsupported authored Collada scene transform")
    if any(abs(matrix[12+i] - expected) > 1e-5
           for i, expected in enumerate((0.,0.,0.,1.))):
        raise VisualAssetError("Original Collada matrix is not affine")
    return matrix


def source_scene_instances(root: ET.Element) -> dict[str, tuple[tuple[float, ...], ...]] | None:
    """Return source geometry instance matrices or None if no original scene.

    An explicit scene binding is required when multiple visual scenes exist.
    Unreferenced mesh library entries are not rendered when an authored visual
    scene exists. Support ONLY source-verified static single-joint controller
    instances; ambiguous/multi-influence skins, morphs and external scene
    nodes ABSTAIN rather than being flattened or skipped.
    """
    scenes = [n for lib in root if _tag(lib)=="library_visual_scenes"
              for n in lib if _tag(n)=="visual_scene"]
    bindings = [(child.get("url") or "") for scene in root if _tag(scene)=="scene"
                for child in scene if _tag(child)=="instance_visual_scene"]
    if not scenes:
        if bindings:
            raise VisualAssetError("Original Collada active scene has no graph")
        return None
    if len(bindings)>1:
        raise VisualAssetError("Ambiguous original Collada active scene")
    if bindings:
        if not bindings[0].startswith("#"):
            raise VisualAssetError("External original Collada scene ref forbidden")
        active = [n for n in scenes if n.get("id")==bindings[0][1:]]
    elif len(scenes)==1:
        active = scenes
    else:
        raise VisualAssetError("Original Collada active scene not uniquely bound")
    if len(active)!=1:
        raise VisualAssetError("Original Collada active scene unresolved")

    refs: dict[str,list[tuple[float,...]]] = {}
    scene_node_worlds: dict[ET.Element, tuple[float,...]] = {}
    pending_skin_instances: list[ET.Element] = []
    count=[0,0]
    def visit(node: ET.Element, parent: tuple[float,...], depth:int) -> None:
        if depth>MAX_SCENE_DEPTH:
            raise VisualAssetError("Original Collada scene nesting exceeds bound")
        count[0]+=1
        if count[0]>MAX_SCENE_NODES:
            raise VisualAssetError("Original Collada scene node count exceeds bound")
        transforms = [n for n in node if _tag(n) in ("matrix", "translate", "rotate", "scale")]
        if len(transforms)>MAX_TRANSFORMS_PER_NODE:
            raise VisualAssetError("Original Collada transform stack exceeds bound")
        if any(_tag(n) in ("lookat","skew","instance_node")
               for n in node):
            raise VisualAssetError("Unsupported original scene graph transform/controller")
        local = IDENTITY
        for el in transforms:
            local = _mul(local, _node_transform(el))
        world = _mul(parent, local)
        scene_node_worlds[node] = world
        for element in node:
            tag=_tag(element)
            if tag=="instance_geometry":
                ref=element.get("url","")
                if not ref.startswith("#") or len(ref)>130:
                    raise VisualAssetError("Invalid original geometry instance reference")
                key=ref[1:]
                count[1]+=1
                if count[1]>MAX_GEOMETRY_INSTANCES:
                    raise VisualAssetError("Original Collada instance count exceeds bound")
                refs.setdefault(key,[]).append(world)
            elif tag=="instance_controller":
                pending_skin_instances.append(element)
                if count[1]+len(pending_skin_instances)>MAX_GEOMETRY_INSTANCES:
                    raise VisualAssetError("Original Collada controller count exceeds bound")
            elif tag=="node":
                visit(element, world, depth+1)

    for child in active[0]:
        if _tag(child)=="node":
            visit(child, IDENTITY, 1)
    if pending_skin_instances:
        # COLLADA world-space skinning: joint_world @ inverse_bind @ bind_shape.
        # The source joint/skeleton and every original vertex weight must
        # pass explicit gates. Never silently substitute raw library geometry.
        from .collada_rigid_skin import rigid_skin_instance
        for instance in pending_skin_instances:
            geometry_id, authored_world = rigid_skin_instance(
                root, instance, scene_node_worlds)
            refs.setdefault(geometry_id, []).append(authored_world)
    # Some exporters include a visual_scene with no instance geometry at all.
    # Do not fabricate source scene transformations or render unrelated models.
    if not refs:
        raise VisualAssetError("Original Collada scene has no supported geometry instances")
    return {key:tuple(matrices) for key,matrices in refs.items()}


def apply_source_node_transform(point: tuple[float,float,float],
                                matrix: tuple[float,...]) -> tuple[float,float,float]:
    if len(point)!=3 or len(matrix)!=16:
        raise VisualAssetError("Invalid original source matrix or vertex")
    x,y,z=point
    result=tuple(matrix[i*4]*x+matrix[i*4+1]*y+
                 matrix[i*4+2]*z+matrix[i*4+3] for i in range(3))
    if any(not math.isfinite(v) or abs(v)>1e7 for v in result):
        raise VisualAssetError("Original Collada geometry world vertex invalid")
    return result
