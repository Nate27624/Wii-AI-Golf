"""Source-derived COLLADA rigid, one-joint, static-skin instance resolution.

This is NOT an animation evaluator and NOT a native Wii world transform. The
only supported controller is a single joint with one valid influence per
source POSITION and a source-resolved joint/skeleton and inverse-bind matrix.
Any unsupported controller, missing source data, or ambiguous joint fails
closed instead of falling back to raw library geometry.
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET

from .collada_scene_graph import IDENTITY, _mul, _tag
from .visual_model import VisualAssetError

MAX_SKIN_VERTICES = 200_000
MAX_SKIN_ARRAY = 2_000_000


def _one(node: ET.Element, kind: str) -> ET.Element:
    matches = [c for c in node if _tag(c) == kind]
    if len(matches) != 1:
        raise VisualAssetError("Source rigid skin needs exactly one " + kind)
    return matches[0]


def _ref(value: str | None) -> str:
    if (not value or len(value) > 130 or not value.startswith("#")
            or not value[1:] or any(c.isspace() for c in value)):
        raise VisualAssetError("Source rigid skin external/invalid reference")
    return value[1:]


def _as_int(value: str | None, *, maximum: int) -> int:
    try:
        answer = int(value or "")
    except ValueError as exc:
        raise VisualAssetError("Source rigid skin integer invalid") from exc
    if not 0 <= answer <= maximum:
        raise VisualAssetError("Source rigid skin integer outside bound")
    return answer


def _floats(raw: str | None, *, max_size: int) -> tuple[float, ...]:
    words = (raw or "").split()
    if len(words) > max_size:
        raise VisualAssetError("Source rigid skin float array exceeds bound")
    try:
        values = tuple(float(word) for word in words)
    except ValueError as exc:
        raise VisualAssetError("Source rigid skin float malformed") from exc
    if any(not math.isfinite(f) or abs(f) > 1e7 for f in values):
        raise VisualAssetError("Source rigid skin float outside bound")
    return values


def _source_values(source: ET.Element, *, kind: str,
                   stride: int) -> tuple:
    arrays = [c for c in source if _tag(c) == kind]
    if len(arrays) != 1:
        raise VisualAssetError("Source rigid skin array kind/arity mismatch")
    arr = arrays[0]
    raw = ((arr.text or "").split() if kind in ("Name_array", "IDREF_array")
           else _floats(arr.text, max_size=MAX_SKIN_ARRAY))
    if len(raw) != _as_int(arr.get("count"), maximum=MAX_SKIN_ARRAY):
        raise VisualAssetError("Source rigid skin source array count mismatch")
    accessors = [c for c in source.iter() if _tag(c) == "accessor"]
    if len(accessors) != 1 or _ref(accessors[0].get("source")) != arr.get("id"):
        raise VisualAssetError("Source rigid skin accessor not source-bound")
    accessor = accessors[0]
    count = _as_int(accessor.get("count"), maximum=MAX_SKIN_VERTICES)
    st = _as_int(accessor.get("stride", "1"), maximum=16)
    offset = _as_int(accessor.get("offset", "0"), maximum=MAX_SKIN_ARRAY)
    if (st != stride or count == 0
            or offset + (count-1)*st + stride > len(raw)):
        raise VisualAssetError("Source rigid skin accessor dimension invalid")
    return tuple(tuple(raw[offset+i*st: offset+(i+1)*st])
                 for i in range(count))


def _matrix(vals: tuple[float, ...]) -> tuple[float, ...]:
    if len(vals) != 16:
        raise VisualAssetError("Source rigid skin matrix arity invalid")
    out = tuple(vals[c*4+r] for r in range(4) for c in range(4))
    if any(abs(out[12+i]-expected) > 1e-5 for i, expected
           in enumerate((0., 0., 0., 1.))):
        raise VisualAssetError("Source rigid skin matrix nonaffine")
    return out


def _geometry_position_count(geometry: ET.Element) -> int:
    mesh = _one(geometry, "mesh")
    verts = _one(mesh, "vertices")
    positions = [c for c in verts if _tag(c)=="input"
                 and c.get("semantic")=="POSITION"]
    if len(positions)!=1:
        raise VisualAssetError("Source rigid skin POSITION binding invalid")
    source_id = _ref(positions[0].get("source"))
    sources = [c for c in mesh if _tag(c)=="source"
               and c.get("id")==source_id]
    if len(sources)!=1:
        raise VisualAssetError("Source rigid skin POSITION array unresolved")
    accessor = _one(_one(sources[0], "technique_common"), "accessor")
    return _as_int(accessor.get("count"), maximum=MAX_SKIN_VERTICES)


def rigid_skin_instance(root: ET.Element, controller_instance: ET.Element,
                        scene_nodes: dict[ET.Element, tuple[float, ...]]
                        ) -> tuple[str, tuple[float, ...]]:
    """Resolve one source-authored static single-joint skin to geometry/matrix.

    Matrix uses COLLADA skin equation, column vectors:
    joint_world @ inverse_bind @ bind_shape. No guessing of model transforms
    or changing the original KCL frame. Joint is resolved under the exact
    skeleton referenced by the *active* scene controller instance.
    """
    cid = _ref(controller_instance.get("url"))
    controller = [c for lib in root if _tag(lib)=="library_controllers"
                  for c in lib if _tag(c)=="controller" and c.get("id")==cid]
    if len(controller)!=1:
        raise VisualAssetError("Original skin controller unresolved or duplicated")
    skin = _one(controller[0], "skin")
    if any(_tag(c)=="morph" for c in controller[0]):
        raise VisualAssetError("Original morph/skin mixture unsupported")
    mesh_id = _ref(skin.get("source"))
    geometries = [g for lib in root if _tag(lib)=="library_geometries"
                  for g in lib if _tag(g)=="geometry" and g.get("id")==mesh_id]
    if len(geometries)!=1:
        raise VisualAssetError("Original rigid skin geometry reference ambiguous")
    position_count = _geometry_position_count(geometries[0])
    if position_count<1:
        raise VisualAssetError("Source rigid skin POSITION count invalid")

    skeletons = [c for c in controller_instance if _tag(c)=="skeleton"]
    if len(skeletons)!=1:
        raise VisualAssetError("Source rigid skin requires one skeleton")
    sid = _ref((skeletons[0].text or "").strip())
    root_matches = [n for n in scene_nodes if n.get("id")==sid]
    if len(root_matches)!=1:
        raise VisualAssetError("Source rigid skin skeleton unresolved")
    root_node = root_matches[0]

    sources = {c.get("id"): c for c in skin if _tag(c)=="source"}
    if None in sources or len(sources) != sum(_tag(c)=="source" for c in skin):
        raise VisualAssetError("Source rigid skin source IDs ambiguous")
    joints = _one(skin, "joints")
    jinputs = [c for c in joints if _tag(c)=="input"]
    if len(jinputs)!=2 or {c.get("semantic") for c in jinputs} != {
        "JOINT", "INV_BIND_MATRIX"
    }:
        raise VisualAssetError("Source rigid skin joint binding unsupported")
    joints_by_name = {c.get("semantic"): c for c in jinputs}
    joint_source = sources.get(_ref(joints_by_name["JOINT"].get("source")))
    ibm_source = sources.get(_ref(joints_by_name["INV_BIND_MATRIX"].get("source")))
    if joint_source is None or ibm_source is None:
        raise VisualAssetError("Source rigid skin joint arrays unresolved")
    names = [c for c in joint_source if _tag(c) in ("Name_array", "IDREF_array")]
    if len(names)!=1:
        raise VisualAssetError("Source rigid skin joint-name array ambiguous")
    joint_names = _source_values(joint_source, kind=_tag(names[0]), stride=1)
    matrices = _source_values(ibm_source, kind="float_array", stride=16)
    if len(joint_names)!=1 or len(matrices)!=1:
        raise VisualAssetError("Source rigid skin supports exactly one joint")
    joint_id = joint_names[0][0]
    # Name_array tokens normally refer to SIDs. IDREF_array refers to IDs.
    key = "id" if _tag(names[0])=="IDREF_array" else "sid"
    descendants = [n for n in root_node.iter() if _tag(n)=="node"
                   and n in scene_nodes]
    matched = [n for n in descendants if n.get(key)==joint_id]
    if not matched and key == "sid":
        # Some original-game exporters store an XML ID in Name_array rather
        # than a SID. This is an exact, unique, same-skeleton source reference
        # fallback, never an inferred bone position/translation.
        matched = [n for n in descendants if n.get("id")==joint_id]
    if len(matched)!=1:
        raise VisualAssetError("Source rigid skin joint unresolved or ambiguous")
    joint_world = scene_nodes[matched[0]]

    bind = [c for c in skin if _tag(c)=="bind_shape_matrix"]
    if len(bind)>1:
        raise VisualAssetError("Source rigid skin bind-shape ambiguous")
    bind_shape = (_matrix(_floats(bind[0].text, max_size=16))
                  if bind else IDENTITY)
    inverse_bind = _matrix(tuple(matrices[0]))

    vw = _one(skin, "vertex_weights")
    count = _as_int(vw.get("count"), maximum=MAX_SKIN_VERTICES)
    if count != position_count:
        raise VisualAssetError("Source rigid skin vertex counts mismatch")
    inputs = [c for c in vw if _tag(c)=="input"]
    semantics = {c.get("semantic") for c in inputs}
    if len(inputs)!=2 or semantics!={"JOINT","WEIGHT"}:
        raise VisualAssetError("Source rigid skin vertex semantics unsupported")
    offsets = {c.get("semantic"): _as_int(c.get("offset"), maximum=15)
               for c in inputs}
    if offsets["JOINT"]==offsets["WEIGHT"]:
        raise VisualAssetError("Source rigid skin vertex offsets overlap")
    wref = next(c for c in inputs if c.get("semantic")=="WEIGHT")
    weight_source = sources.get(_ref(wref.get("source")))
    if weight_source is None:
        raise VisualAssetError("Source rigid skin weight source missing")
    weights = _source_values(weight_source, kind="float_array", stride=1)
    vcounts = [c for c in vw if _tag(c)=="vcount"]
    vectors = [c for c in vw if _tag(c)=="v"]
    if len(vcounts)!=1 or len(vectors)!=1:
        raise VisualAssetError("Source rigid skin vcount/v count invalid")
    counts = (vcounts[0].text or "").split()
    if len(counts)!=count or any(v!="1" for v in counts):
        raise VisualAssetError("Source rigid skin requires one influence per vertex")
    index_words = (vectors[0].text or "").split()
    width = max(offsets.values())+1
    if len(index_words)!=count*width:
        raise VisualAssetError("Source rigid skin weight index count invalid")
    for i in range(count):
        try:
            joint_index = int(index_words[i*width+offsets["JOINT"]])
            weight_index = int(index_words[i*width+offsets["WEIGHT"]])
        except ValueError as exc:
            raise VisualAssetError("Source rigid skin weight index malformed") from exc
        if (joint_index!=0 or not 0 <= weight_index < len(weights)
                or weights[weight_index][0] <= 0):
            raise VisualAssetError("Source rigid skin joint/weight unverified")
    # A sole positive weight normalizes to one by COLLADA skin semantics.
    return mesh_id, _mul(_mul(joint_world, inverse_bind), bind_shape)
