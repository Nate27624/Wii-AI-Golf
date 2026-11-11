"""Read-only original course material-region footprint audit.

Investigate whether global green/fairway/bunker centroid comparisons are
confounded by multiple disconnected patches, UV seams, or different source
coverage. No KCL↔DAE registration is estimated or applied; no original source
positions, centroids, asset IDs or face indices are printed.

"Connected" below means triangles share a full edge with both endpoints
quantized to 1e-4 in original source-local coordinates. This is a diagnostic
weld only, NOT evidence of native geometry topology or physical collision.
"""
from __future__ import annotations

import math

CATEGORY_SOURCE_MAP = (("green", 6, "M_Green"),
                       ("fairway", 1, "M_Fairway"),
                       ("bunker", 3, "M_Bunker"))
MAX_MATERIAL_TRIANGLES = 30000
_VERTEX_DIGITS = 4


def _edge_key(a, b):
    pa = tuple(round(float(x), _VERTEX_DIGITS) for x in a)
    pb = tuple(round(float(x), _VERTEX_DIGITS) for x in b)
    return (pa, pb) if pa <= pb else (pb, pa)


def _region(verts, faces, diagonal):
    """Summarize only aggregate scalar area/connectivity evidence.

    Strict source mesh input was already validated by its respective
    original OBJ/DAE readers. Degenerate or nonfinite category subsets
    abstain; no fabricated point or pseudo-material is substituted.
    """
    if not faces:
        return {"status": "NO_SOURCE_FACES", "source_triangle_count": 0}
    if len(faces) > MAX_MATERIAL_TRIANGLES or not 1e-7 < diagonal < 1e10:
        return {"status": "ABSTAIN_UNBOUNDED_MATERIAL_REGION"}
    n = len(faces)
    parents = list(range(n))
    sizes = [1] * n

    def find(i):
        while i != parents[i]:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    def union(a, b):
        a, b = find(a), find(b)
        if a == b:
            return
        if sizes[a] < sizes[b]:
            a, b = b, a
        parents[b] = a
        sizes[a] += sizes[b]

    edges = {}
    areas = []
    centers = []
    mins = [float("inf"), float("inf")]
    maxs = [-float("inf"), -float("inf")]
    for fidx, face in enumerate(faces):
        if len(face) != 3 or any(i < 0 or i >= len(verts) for i in face):
            return {"status": "ABSTAIN_INVALID_MATERIAL_FACE"}
        a, b, c = (verts[i] for i in face)
        if any(len(p) != 3 or any(not math.isfinite(v) or abs(v) >= 1e7
                                 for v in p) for p in (a, b, c)):
            return {"status": "ABSTAIN_NONFINITE_MATERIAL_FACE"}
        for point in (a, b, c):
            for axis, out_axis in ((0, 0), (2, 1)):
                mins[out_axis] = min(mins[out_axis], point[axis])
                maxs[out_axis] = max(maxs[out_axis], point[axis])
        for p, q in ((a, b), (b, c), (c, a)):
            edge = _edge_key(p, q)
            other = edges.setdefault(edge, fidx)
            if other != fidx:
                union(other, fidx)
        ab = [b[i] - a[i] for i in range(3)]
        ac = [c[i] - a[i] for i in range(3)]
        normal = (ab[1]*ac[2]-ab[2]*ac[1],
                  ab[2]*ac[0]-ab[0]*ac[2],
                  ab[0]*ac[1]-ab[1]*ac[0])
        area = 0.5 * math.sqrt(sum(x*x for x in normal))
        if not math.isfinite(area) or area < 0:
            return {"status": "ABSTAIN_NONFINITE_SOURCE_AREA"}
        areas.append(area)
        centers.append(((a[0]+b[0]+c[0])/3,
                        (a[2]+b[2]+c[2])/3))

    component_areas = {}
    component_triangles = {}
    component_weighted = {}
    for i, area in enumerate(areas):
        root = find(i)
        component_areas[root] = component_areas.get(root, 0.) + area
        component_triangles[root] = component_triangles.get(root, 0) + 1
        acc = component_weighted.setdefault(root, [0., 0.])
        acc[0] += centers[i][0] * area
        acc[1] += centers[i][1] * area
    total = sum(component_areas.values())
    if not 1e-12 < total < 1e18:
        return {"status": "ABSTAIN_ZERO_OR_UNBOUNDED_AREA"}
    weighted_center = (
        sum(t[0] for t in component_weighted.values()) / total,
        sum(t[1] for t in component_weighted.values()) / total,
    )
    variance = sum(
        area * sum((component_weighted[root][i]/area -
                    weighted_center[i])**2 for i in (0,1))
        for root, area in component_areas.items() if area > 0
    ) / total
    if not math.isfinite(variance):
        return {"status": "ABSTAIN_NONFINITE_COMPONENT_DISPERSION"}
    ordered = sorted(component_areas, key=lambda root: (
        -component_areas[root], root))
    return {
        "status": "SOURCE_LOCAL_MATERIAL_FOOTPRINT_DIAGNOSTIC_ONLY",
        "source_triangle_count": n,
        "edge_weld_precision_decimal_places": _VERTEX_DIGITS,
        "source_edge_connected_component_count": len(ordered),
        "component_count_over_1pct_area": sum(
            area >= 0.01*total for area in component_areas.values()),
        "largest_component_area_fraction": round(
            component_areas[ordered[0]] / total, 5),
        "top_three_component_area_fractions": [
            round(component_areas[r] / total, 5) for r in ordered[:3]],
        "top_three_component_triangle_counts": [
            component_triangles[r] for r in ordered[:3]],
        "component_centroid_dispersion_over_source_diagonal": round(
            math.sqrt(variance) / diagonal, 6),
        "material_surface_bbox_diagonal_over_source_diagonal": round(
            math.hypot(maxs[0]-mins[0], maxs[1]-mins[1]) / diagonal, 6),
        "native_topology_or_alignment_proven": False,
    }


def audit_material_footprints(terrain, visual) -> dict:
    from .scene_camera import playable_source_vertices
    from .source_connectivity_probe import probe_connectivity

    def diagonal(vertices):
        if not vertices:
            return None
        dx = max(v[0] for v in vertices) - min(v[0] for v in vertices)
        dz = max(v[2] for v in vertices) - min(v[2] for v in vertices)
        return math.hypot(dx, dz)

    kdiag = diagonal(terrain.vertices)
    vdiag = diagonal(playable_source_vertices(visual))
    output = {
        "status": "SOURCE_LOCAL_COMPONENT_INVENTORY_ONLY",
        "component_edges_welded_to_four_decimal_places": True,
        "same_hole_or_same_source_extent_verified": False,
        "source_visual_registration_verified": False,
        "categories": {},
    }
    if kdiag is None or vdiag is None:
        output["status"] = "ABSTAIN_MISSING_SOURCE_GEOMETRY"
        return output
    # Distinguish an all-material per-triangle OBJ export with no shared
    # vertex indices from truly disconnected reconstructed *surfaces*. Probe
    # exactly the same source triangles at several explicitly-disclosed
    # tolerances; never use those welds in the viewer or collision physics.
    output["whole_mesh_connectivity"] = {
        "kcl": probe_connectivity(terrain.vertices, terrain.faces, kdiag),
        "dae": probe_connectivity(
            visual.vertices,
            tuple(face.vertices for face in visual.faces), vdiag),
    }
    for label, source_id, material in CATEGORY_SOURCE_MAP:
        kfaces = [face for face, attr in zip(
            terrain.faces,
            terrain.face_materials or (None,)*len(terrain.faces)
        ) if attr == source_id]
        vfaces = [face.vertices for face in visual.faces
                  if face.material == material]
        output["categories"][label] = {
            "kcl": _region(terrain.vertices, kfaces, kdiag),
            "dae": _region(visual.vertices, vfaces, vdiag),
            "source_triangle_contact_sensitivity": {
                "kcl": probe_connectivity(terrain.vertices, kfaces, kdiag),
                "dae": probe_connectivity(visual.vertices, vfaces, vdiag),
            },
        }
    return output
