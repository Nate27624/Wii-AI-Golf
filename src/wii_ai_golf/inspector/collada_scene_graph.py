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

class UnsupportedSceneFeature(VisualAssetError):
    """Known original Collada scene feature not yet rendered correctly.

    GUI may explicitly use labeled geometry-library *diagnostic* mode.
    Other malformed assets / external references remain hard failures.
    """


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


def source_scene_instances(
    root: ET.Element, *, omit_unsupported: bool = False,
    limitations: list[str] | None = None,
) -> dict[str, tuple[tuple[float, ...], ...]] | None:
    """Source-authored scene hierarchy and internal static node references.

    Every instance_node resolves only an internal, uniquely defined <node>.
    Parent and nested transforms compose in Collada document order.
    Source-validated static single-joint skin controllers are evaluated with
    their authored joint/IBM/shape matrices; all other controllers, lookat
    and skew remain refused or explicitly labeled geometry-only previews.
    """
    if type(omit_unsupported) is not bool:
        raise VisualAssetError("Invalid scene compatibility mode")
    if limitations is None:
        limitations = []
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

    # Source original library_nodes and unique scene-node IDs support legal
    # COLLADA <instance_node url="#id"> without flattening source transforms.
    nodes: dict[str, ET.Element] = {}
    for lib in root:
        if _tag(lib)=="library_nodes":
            candidates=(n for n in lib.iter() if _tag(n)=="node")
        elif _tag(lib)=="library_visual_scenes":
            candidates=(n for n in lib.iter() if _tag(n)=="node")
        else:
            continue
        for node in candidates:
            key=node.get("id")
            if key is None:
                continue
            if not key or len(key)>128 or key in nodes:
                raise VisualAssetError("Duplicate/invalid Collada scene node ID")
            nodes[key]=node
            if len(nodes)>MAX_SCENE_NODES:
                raise VisualAssetError("Excessive original Collada node catalog")

    refs: dict[str,list[tuple[float,...]]] = {}
    source_node_worlds: dict[ET.Element, tuple[float,...]] = {}
    pending_rigid_skins: list[ET.Element] = []
    controller_ids = [
        n.get("id") for lib in root if _tag(lib) == "library_controllers"
        for n in lib if _tag(n) == "controller"]
    count=[0,0]

    def visit(node: ET.Element, parent: tuple[float,...], depth:int,
              chain: frozenset[int]) -> None:
        if depth>MAX_SCENE_DEPTH:
            raise VisualAssetError("Original Collada scene nesting exceeds bound")
        # Cycle checks cover direct and indirect internal library_node links.
        identity=id(node)
        if identity in chain:
            raise VisualAssetError("Original Collada instance_node cycle")
        chain=chain | {identity}
        count[0]+=1
        if count[0]>MAX_SCENE_NODES:
            raise VisualAssetError("Original Collada scene node count exceeds bound")
        transforms = [n for n in node if _tag(n) in ("matrix", "translate", "rotate", "scale")]
        if len(transforms)>MAX_TRANSFORMS_PER_NODE:
            raise VisualAssetError("Original Collada transform stack exceeds bound")
        for element in node:
            kind=_tag(element)
            if kind == "instance_controller":
                # A known unsupported *local* source controller can enter
                # explicitly labeled static geometry preview. Never allow an
                # external controller URL to be bypassed by that mode.
                url=element.get("url","")
                if not url.startswith("#") or not 2 <= len(url) <= 130:
                    raise VisualAssetError("External/invalid Collada controller reference")
                if omit_unsupported:
                    limitations.append("instance_controller skin/joint draw omitted")
                    continue
                if url[1:] not in controller_ids:
                    raise UnsupportedSceneFeature(
                        "Unsupported original scene graph <instance_controller>; "
                        "source controller definition absent")
                if controller_ids.count(url[1:]) != 1:
                    raise VisualAssetError("Duplicate original Collada controller ID")
            if kind in ("lookat","skew"):
                # Validate numeric original transforms; skip their *entire*
                # affected node, not its geometry with an invented matrix.
                _numbers(element,9 if kind=="lookat" else 7)
                if omit_unsupported:
                    limitations.append(kind+" node omitted (unknown transform)")
                    return
                raise UnsupportedSceneFeature(
                    "Unsupported original scene graph <"+kind+">; "
                    "native node transform not inferred")
        local = IDENTITY
        for element in transforms:
            local = _mul(local, _node_transform(element))
        world = _mul(parent, local)
        if (controller_ids and node in source_node_worlds
                and source_node_worlds[node] != world):
            # Reused geometry nodes may legally have multiple transforms.
            # Strict static skinning needs unique source JOINT world matrices.
            raise VisualAssetError(
                "Original rigid skin node instanced with ambiguous world transforms")
        source_node_worlds[node] = world
        for element in node:
            tag=_tag(element)
            if tag=="instance_geometry":
                ref=element.get("url","")
                if not ref.startswith("#") or len(ref)>130 or len(ref)<2:
                    raise VisualAssetError("Invalid original geometry instance reference")
                key=ref[1:]
                count[1]+=1
                if count[1]>MAX_GEOMETRY_INSTANCES:
                    raise VisualAssetError("Original Collada instance count exceeds bound")
                refs.setdefault(key,[]).append(world)
            elif tag=="instance_controller" and not omit_unsupported:
                pending_rigid_skins.append(element)
                if count[1]+len(pending_rigid_skins)>MAX_GEOMETRY_INSTANCES:
                    raise VisualAssetError("Original Collada controller count exceeds bound")
            elif tag=="node":
                visit(element, world, depth+1, chain)
            elif tag=="instance_node":
                ref=element.get("url","")
                if not ref.startswith("#") or len(ref)>130 or len(ref)<2:
                    raise VisualAssetError("External/invalid Collada instance_node ref")
                target=nodes.get(ref[1:])
                if target is None:
                    raise VisualAssetError("Collada instance_node target unavailable")
                visit(target, world, depth+1, chain)

    for child in active[0]:
        if _tag(child)=="node":
            visit(child, IDENTITY, 1, frozenset())
        elif _tag(child)=="instance_node":
            ref=child.get("url","")
            if not ref.startswith("#") or len(ref)>130 or len(ref)<2:
                raise VisualAssetError("External/invalid Collada visual scene node ref")
            target=nodes.get(ref[1:])
            if target is None:
                raise VisualAssetError("Collada root instance_node target unavailable")
            visit(target, IDENTITY, 1, frozenset())
    if pending_rigid_skins:
        # Geometry-only fallback never reaches here. Every source controller
        # must have a unique skeleton/joint and valid original vertex weights,
        # or the strict visual model abstains instead of guessing a placement.
        from .collada_rigid_skin import rigid_skin_instance
        for instance in pending_rigid_skins:
            geometry_id, authored_world = rigid_skin_instance(
                root, instance, source_node_worlds)
            refs.setdefault(geometry_id, []).append(authored_world)
    if not refs:
        if omit_unsupported and limitations:
            raise UnsupportedSceneFeature(
                "Unsupported original scene leaves no static geometry instances")
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
