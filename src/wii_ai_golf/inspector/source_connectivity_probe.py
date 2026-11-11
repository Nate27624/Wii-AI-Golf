"""Bounded, read-only probe of source OBJ/DAE triangle-soup connectivity.

All conclusions are explicitly source-local. Coincident endpoints of
independently exported KCL triangles and original DAE UV seam vertices need
not reuse vertex *indices*. The probe tests exact and several conservative
source-relative coordinate tolerances. It never welds/rewrites source assets,
guesses game transforms, infers native triangle adjacency or exports XYZ.
"""
from __future__ import annotations

import math

MAX_PROBE_TRIANGLES = 30000
# Relative to each mesh's own XZ bounding-box diagonal; deliberately report
# all thresholds because matching at a loose tolerance is NOT source topology.
RELATIVE_WELD_STEPS = (0.0, 1e-8, 1e-6, 1e-4)


def _union_find_components(faces: tuple[tuple[int, int, int], ...],
                           vertices: tuple[tuple[float, float, float], ...],
                           epsilon: float) -> dict:
    parent = list(range(len(faces)))
    size = [1] * len(faces)

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def join(a: int, b: int) -> None:
        a, b = find(a), find(b)
        if a == b:
            return
        if size[a] < size[b]:
            a, b = b, a
        parent[b] = a
        size[a] += size[b]

    # Separate edge versus vertex adjacency; full edges are a much stricter
    # notion of mesh continuity than a single shared corner.
    edge_parent = parent
    edge_size = size
    first_point: dict[tuple, int] = {}
    first_edge: dict[tuple, int] = {}
    edge_matches = 0
    vertex_matches = 0
    degenerate_quantized_edges = 0

    def encode(point):
        if epsilon == 0.0:
            return point
        return tuple(round(float(v) / epsilon) for v in point)

    # Disjoint-set for vertex-touch connectivity is intentionally independent.
    vertex_parent = list(range(len(faces)))
    vertex_size = [1] * len(faces)

    def vertex_find(a):
        while vertex_parent[a] != a:
            vertex_parent[a] = vertex_parent[vertex_parent[a]]
            a = vertex_parent[a]
        return a

    def vertex_join(a, b):
        a, b = vertex_find(a), vertex_find(b)
        if a == b:
            return
        if vertex_size[a] < vertex_size[b]:
            a, b = b, a
        vertex_parent[b] = a
        vertex_size[a] += vertex_size[b]

    for i, face in enumerate(faces):
        points = [encode(vertices[k]) for k in face]
        for point in set(points):
            if point in first_point:
                vertex_matches += 1
                vertex_join(i, first_point[point])
            else:
                first_point[point] = i
        for a, b in ((points[0], points[1]), (points[1], points[2]),
                     (points[2], points[0])):
            if a == b:
                degenerate_quantized_edges += 1
                continue
            key = (a, b) if a < b else (b, a)
            if key in first_edge:
                edge_matches += 1
                join(i, first_edge[key])
            else:
                first_edge[key] = i
    return {
        "shared_full_edge_occurrences": edge_matches,
        "shared_vertex_contact_occurrences": vertex_matches,
        "edge_connected_component_count": len({
            find(i) for i in range(len(faces))
        }),
        "vertex_touch_component_count": len({
            vertex_find(i) for i in range(len(faces))
        }),
        "quantized_degenerate_edge_occurrences": degenerate_quantized_edges,
    }


def probe_connectivity(vertices, faces, source_diagonal) -> dict:
    """Return source-derived topology sensitivity only; never original XYZ."""
    if not faces:
        return {"status": "NO_SOURCE_FACES", "source_triangle_count": 0}
    if (len(faces) > MAX_PROBE_TRIANGLES
            or not math.isfinite(source_diagonal)
            or source_diagonal <= 1e-7 or source_diagonal >= 1e10):
        return {"status": "ABSTAIN_SOURCE_GEOMETRY_BOUND"}
    try:
        indices = [i for face in faces for i in face]
        if any(len(face) != 3 for face in faces):
            return {"status": "ABSTAIN_NONTRIANGLE_SOURCE_FACE"}
        if any(type(i) is not int or i < 0 or i >= len(vertices)
               for i in indices):
            return {"status": "ABSTAIN_INVALID_SOURCE_INDEX"}
        used = {i for i in indices}
        if any(len(vertices[i]) != 3 or any(
               not math.isfinite(c) or abs(c) >= 1e7 for c in vertices[i])
               for i in used):
            return {"status": "ABSTAIN_INVALID_SOURCE_COORDINATE"}
        trials = []
        for ratio in RELATIVE_WELD_STEPS:
            eps = 0.0 if ratio == 0.0 else source_diagonal * ratio
            trial = _union_find_components(faces, vertices, eps)
            trial["source_relative_endpoint_tolerance"] = ratio
            trials.append(trial)
    except (OverflowError, ValueError, TypeError, IndexError):
        return {"status": "ABSTAIN_SOURCE_COORDINATE_PROBE"}
    return {
        "status": "SOURCE_LOCAL_CONNECTIVITY_SENSITIVITY_ONLY",
        "source_triangle_count": len(faces),
        "source_index_count": len(indices),
        "unique_referenced_source_vertex_indices": len(used),
        "one_distinct_source_vertex_index_per_triangle_corner": (
            len(used) == len(indices)),
        "trial_tolerances_relative_to_each_source_mesh": trials,
        "native_adjacency_verified": False,
        "same_original_game_hole_verified": False,
        "safety_note": "LOOSE_ENDPOINT_MATCHING_IS_NOT_NATIVE_TOPOLOGY",
    }
