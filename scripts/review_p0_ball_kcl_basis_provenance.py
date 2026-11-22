#!/usr/bin/env python3
"""S002 read-only, OFFLINE Ball/KCL coordinate-basis evidence classifier.

Only sanitized, already-reviewed anchor claims are admissible. A supplied
witness cannot certify actual Wii execution or game-world positions.
No raw coordinates, source paths, shot IDs, or archive hashes are printed.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

SCHEMA = "wii-golf-basis-claim-v1"
REVISION = "RSPE01 Rev1"
MAX_INPUT_BYTES = 65536
MAX_ANCHORS = 32
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}\Z")


def _fail(reason: str) -> dict[str, Any]:
    return _report("ABSTAIN", reason)


def _report(status: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": "wii-golf-basis-result-v1",
        "status": status,
        "reason": reason,
        "landmark_count": extra.get("landmark_count", 0),
        "supplied_witness_consistent": status == "CONDITIONALLY_CONSISTENT",
        "selected_ball_world_xyz_verified": False,
        "native_game_parity_verified": False,
        "training_approved": False,
    }


def _vec(value: Any) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError("XYZ_REQUIRED")
    out = []
    for x in value:
        if type(x) not in (int, float):
            raise ValueError("NONNUMERIC_COORDINATE")
        x = float(x)
        if not math.isfinite(x) or abs(x) > 1e9:
            raise ValueError("INVALID_COORDINATE")
        out.append(x)
    return tuple(out)  # type: ignore[return-value]


def _matrix(value: Any) -> tuple[tuple[float, float, float], ...]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError("MATRIX_REQUIRED")
    return tuple(_vec(row) for row in value)


def _det(m: tuple[tuple[float, float, float], ...]) -> float:
    a, b, c = m
    return (a[0] * (b[1]*c[2]-b[2]*c[1])
            - a[1] * (b[0]*c[2]-b[2]*c[0])
            + a[2] * (b[0]*c[1]-b[1]*c[0]))


def _volume(pts: list[tuple[float, float, float]]) -> bool:
    """Require four affinely independent points, not just three on terrain."""
    start = pts[0]
    differences = [tuple(x - y for x, y in zip(p, start)) for p in pts[1:]]
    length = max((abs(x) for p in differences for x in p), default=0.0)
    if length < 1e-10:
        return False
    unit = [tuple(x/length for x in p) for p in differences]
    for i in range(len(unit)):
        for j in range(i+1, len(unit)):
            for k in range(j+1, len(unit)):
                if abs(_det((unit[i],unit[j],unit[k]))) > 1e-8:
                    return True
    return False


def _side(entry: Any, expected_kind: str) -> tuple[dict[str, Any], dict[str, tuple[float,float,float]]]:
    if not isinstance(entry, dict):
        raise ValueError("SIDE_OBJECT_REQUIRED")
    for key in ("revision", "cohort_sha256", "scene_id", "shot_id", "basis_id",
                "units", "handedness", "source_kind", "source_qualified", "landmarks"):
        if key not in entry:
            raise ValueError("MISSING_PROVENANCE_FIELD")
    if entry["source_kind"] != expected_kind:
        raise ValueError("WRONG_SOURCE_OBJECT")
    if entry["revision"] != REVISION:
        raise ValueError("UNSUPPORTED_REVISION")
    if not isinstance(entry["cohort_sha256"],str) or not SHA256.fullmatch(entry["cohort_sha256"]):
        raise ValueError("UNQUALIFIED_ARCHIVE_ID")
    for key in ("scene_id", "shot_id", "basis_id", "units"):
        if not isinstance(entry[key],str) or not LABEL.fullmatch(entry[key]):
            raise ValueError("UNQUALIFIED_IDENTITY")
    if entry["handedness"] not in ("left", "right", "unknown"):
        raise ValueError("UNQUALIFIED_HANDEDNESS")
    if type(entry["source_qualified"]) is not bool:
        raise ValueError("UNQUALIFIED_SOURCE_FLAG")
    points = entry["landmarks"]
    if not isinstance(points,list) or not 4 <= len(points) <= MAX_ANCHORS:
        raise ValueError("INSUFFICIENT_MATCHED_LANDMARKS")
    landmarks: dict[str, tuple[float,float,float]] = {}
    for anchor in points:
        if not isinstance(anchor,dict) or set(anchor) != {"id","xyz"}:
            raise ValueError("INVALID_ANCHOR")
        key = anchor["id"]
        if not isinstance(key,str) or not LABEL.fullmatch(key) or key in landmarks:
            raise ValueError("INVALID_ANCHOR_ID")
        landmarks[key] = _vec(anchor["xyz"])
    return entry, landmarks


def assess_claim(data: Any) -> dict[str, Any]:
    """Classify supplied evidence, never certify it as independently native.

    ABSTAIN = missing/unjoined source identity or independent transform.
    INCONSISTENT = qualified supplied witness conflicts with supplied anchors.
    CONDITIONALLY_CONSISTENT = internally coherent claims only, not game proof.
    """
    if not isinstance(data,dict) or data.get("schema") != SCHEMA:
        return _fail("UNSUPPORTED_SCHEMA")
    try:
        ball, b = _side(data.get("ball"),"source_selected_ball_translation")
        terrain, k = _side(data.get("terrain"),"source_kcl_prism_vertex")
        tol = data.get("tolerance",1e-5)
        if type(tol) not in (int,float) or not math.isfinite(tol) or not 0 < tol <= 0.01:
            raise ValueError("INVALID_TOLERANCE")
        tol = float(tol)
        if any(ball[key] != terrain[key] for key in ("revision","cohort_sha256","scene_id","shot_id")):
            return _fail("SOURCE_SCENE_SHOT_COHORT_MISMATCH")
        if not ball["source_qualified"] or not terrain["source_qualified"]:
            return _fail("UNVERIFIED_SOURCE_ANCHOR")
        if set(b) != set(k):
            return _fail("UNMATCHED_LANDMARK_IDENTITIES")
        if not _volume(list(b.values())) or not _volume(list(k.values())):
            return _fail("NONCOPLANAR_3D_ANCHORS_NOT_ESTABLISHED")
        witness = data.get("transform_witness")
        if not isinstance(witness,dict) or witness.get("kind") != "independent_source_transform":
            return _fail("MISSING_INDEPENDENT_TRANSFORM_WITNESS")
        if type(witness.get("independently_qualified")) is not bool or not witness["independently_qualified"]:
            return _fail("UNQUALIFIED_TRANSFORM_WITNESS")
        if witness.get("from_basis_id") != ball["basis_id"] or witness.get("to_basis_id") != terrain["basis_id"]:
            return _fail("WRONG_TRANSFORM_BASIS")
        source_ref = witness.get("source_reference")
        if not isinstance(source_ref,str) or not LABEL.fullmatch(source_ref):
            return _fail("MISSING_TRANSFORM_SOURCE_REFERENCE")
        if witness.get("from_units") != ball["units"] or witness.get("to_units") != terrain["units"]:
            return _fail("UNQUALIFIED_UNIT_MAPPING")
        if ball["handedness"] == "unknown" or terrain["handedness"] == "unknown":
            return _fail("UNKNOWN_HANDEDNESS")
        m = _matrix(witness.get("matrix_xyz"))
        shift = _vec(witness.get("translation_xyz"))
        scale = witness.get("length_scale")
        if type(scale) not in (float,int) or not math.isfinite(scale) or not 1e-6 <= scale <= 1e6:
            raise ValueError("INVALID_SCALE")
        scale = float(scale)
        # Ensure declared transform is a similarity: no shear / nonuniform scale.
        normalized = [[x/scale for x in row] for row in m]
        for i in range(3):
            for j in range(3):
                actual = sum(normalized[i][n]*normalized[j][n] for n in range(3))
                if abs(actual-(1.0 if i==j else 0.0)) > 1e-6:
                    return _report("INCONSISTENT","NONUNIFORM_SCALE_OR_SHEAR",landmark_count=len(b))
        determinant = _det(m)
        same = ball["handedness"] == terrain["handedness"]
        if abs(determinant) < 1e-15:
            return _report("INCONSISTENT","DEGENERATE_TRANSFORM",landmark_count=len(b))
        if (determinant > 0) != same:
            return _report("INCONSISTENT","HANDEDNESS_REFLECTION_CONFLICT",landmark_count=len(b))
        for key, v in b.items():
            predicted = tuple(sum(m[i][j]*v[j] for j in range(3))+shift[i] for i in range(3))
            if any(not math.isfinite(x) for x in predicted):
                raise ValueError("NONFINITE_TRANSFORM")
            if math.dist(predicted,k[key]) > tol:
                return _report("INCONSISTENT","LANDMARK_TRANSFORM_RESIDUAL",landmark_count=len(b))
        return _report("CONDITIONALLY_CONSISTENT","SUPPLIED_WITNESS_AND_3D_ANCHORS_AGREE",landmark_count=len(b))
    except (ValueError,TypeError,OverflowError) as exc:
        reason = str(exc) if isinstance(exc,ValueError) and str(exc).isupper() else "INVALID_EVIDENCE"
        return _fail(reason)


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline sanitized source-basis falsifier; no native parity claim")
    parser.add_argument("--input", required=True, type=Path, help="local reviewed/synthetic JSON; contents never printed")
    args = parser.parse_args()
    try:
        if args.input.stat().st_size > MAX_INPUT_BYTES:
            report = _fail("INPUT_EXCEEDS_BOUNDED_LIMIT")
        else:
            report = assess_claim(json.loads(args.input.read_text(encoding="utf-8")))
    except (OSError,UnicodeError,json.JSONDecodeError):
        report = _fail("UNREADABLE_EVIDENCE_INPUT")
    print(json.dumps(report,sort_keys=True,separators=(",",":")))
    return 0 if report["status"] == "CONDITIONALLY_CONSISTENT" else 2


if __name__ == "__main__":
    raise SystemExit(main())
