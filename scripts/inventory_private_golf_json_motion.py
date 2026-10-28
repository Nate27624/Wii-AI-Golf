#!/usr/bin/env python3
"""PRIVATE read-only inventory of existing Wii Golf JSON / JSONL captures.

Identifies where useful phase, shot, ball-position and velocity hints exist.
Never interprets human recollections as measured velocity or reads raw RAM.
Writes a LOCAL-ONLY index under Wii-AI-Golf-Data; terminal omits raw values.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys

DEFAULT_MAX_FILE_BYTES = 8 * 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 128 * 1024 * 1024
DEFAULT_MAX_FILES = 2000
LIMIT_RECORDS = 500
MAX_NODES = 4000
PHASE_TERMS = {"pre", "post", "idle", "aim", "aim_only", "a_hold", "club_motion",
               "shot_attempt", "flight", "moving", "settled", "result", "landing"}
MOTION_TERMS = ("velocity", "vel_xyz", "vel_", "ball_speed", "movement", "falling")
POSITION_TERMS = ("position", "pos", "xyz", "trans", "translation", "center", "location")


def rel_identifier(rel: str) -> str:
    return hashlib.sha256(rel.encode("utf-8", "replace")).hexdigest()[:12]


def walk_capture_fields(value: object, found: dict, path: str = "", depth: int = 0) -> None:
    if depth > 8 or found["nodes"] >= MAX_NODES:
        return
    found["nodes"] += 1
    if isinstance(value, dict):
        keys = set(str(x).lower() for x in value)
        if {"x", "y", "z"} <= keys and "ball" in path.lower():
            vals = [value.get(k) for k in ("x", "y", "z")]
            if all(isinstance(n, (int, float)) and not isinstance(n, bool) and
                   math.isfinite(n) for n in vals):
                found["vectors"][path].add(tuple(float(n) for n in vals))
                found["vector_observations"][path] += 1
        for key, item in value.items():
            if not isinstance(key, str):
                continue
            low = key.lower()
            field = f"{path}.{key}" if path else key
            if "ball" in low:
                found["ball_keys"].add(field)
            if any(x in low for x in MOTION_TERMS):
                found["velocity_keys"].add(field)
            if any(x in low for x in ("frame", "timestamp", "shot_id", "run_id", "phase")):
                found["timing_keys"].add(field)
            if low in ("phase", "shot_phase", "state", "stage") and isinstance(item, str):
                norm = item.strip().lower().replace("-", "_")
                if norm in PHASE_TERMS:
                    found["phase_terms"].add(norm)
            if (isinstance(item, (list, tuple)) and len(item) == 3 and
                    all(isinstance(n, (int, float)) and not isinstance(n, bool) and
                        math.isfinite(n) for n in item) and
                    "ball" in field.lower() and any(x in field.lower() for x in POSITION_TERMS)):
                found["vectors"][field].add(tuple(float(n) for n in item))
                found["vector_observations"][field] += 1
            walk_capture_fields(item, found, field, depth + 1)
    elif isinstance(value, list):
        for item in value[:LIMIT_RECORDS]:
            walk_capture_fields(item, found, path + "[]", depth + 1)


def summarize_records(records: list[object]) -> dict:
    found = {"nodes": 0, "ball_keys": set(), "velocity_keys": set(),
             "timing_keys": set(), "phase_terms": set(),
             "vectors": defaultdict(set), "vector_observations": Counter()}
    for rec in records[:LIMIT_RECORDS]:
        walk_capture_fields(rec, found)
    varying_paths = sorted(p for p, vs in found["vectors"].items()
                           if len(vs) > 1 and found["vector_observations"][p] > 1)
    return {
        "records_inspected": min(len(records), LIMIT_RECORDS),
        "ball_related_paths": sorted(found["ball_keys"])[:30],
        "velocity_related_paths": sorted(found["velocity_keys"])[:30],
        "timing_or_provenance_paths": sorted(found["timing_keys"])[:30],
        "declared_phase_terms": sorted(found["phase_terms"]),
        "candidate_changing_ball_vector_paths": varying_paths[:30],
        "possible_motion_annotation": bool(found["velocity_keys"] or varying_paths),
        "numeric_values_emitted": False,
        "motion_or_vertical_velocity_verified": False,
        "ball_world_xyz_verified": False,
        "shot_to_RAM_pair_verified": False
    }


def parse_capture(path: Path) -> tuple[list[object], str]:
    if path.suffix.lower() == ".jsonl":
        records = []
        with path.open("r", encoding="utf-8-sig") as f:
            for line in f:
                if not line.strip():
                    continue
                if len(records) >= LIMIT_RECORDS:
                    break
                try:
                    records.append(json.loads(line))
                except ValueError:
                    return records, "partial_invalid_jsonl"
        return records, "jsonl"
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except ValueError:
        return [], "invalid_json"
    # Do not flatten a top-level nested vector or phase array; recursive walk
    # still detects repeated record dictionaries with their field paths.
    return [obj], "json"


def audit_directory(root: Path, max_files: int = DEFAULT_MAX_FILES,
                    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
                    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES) -> dict:
    root = root.resolve(strict=True)
    scanned, skipped, total = [], Counter(), 0
    skipped_file_refs = []
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(base) / d).is_symlink())
        for filename in sorted(names):
            path = Path(base) / filename
            if path.suffix.lower() not in (".json", ".jsonl"):
                continue
            # Never recursively ingest the inventory's own private output.
            if filename.startswith("json-motion-inventory-PRIVATE-"):
                skipped["self_generated_report"] += 1
                continue
            rel = path.relative_to(root).as_posix()
            file_id = rel_identifier(rel)
            if path.is_symlink() or not path.is_file():
                skipped["symlink_or_unreadable"] += 1
                skipped_file_refs.append({"file_id": file_id, "reason": "symlink_or_unreadable"})
                continue
            size = path.stat().st_size
            if size > max_file_bytes:
                skipped["oversize"] += 1
                skipped_file_refs.append({"file_id": file_id, "reason": "oversize", "bytes": size,
                                          "relative_path_PRIVATE": rel})
                continue
            if len(scanned) >= max_files or total + size > max_total_bytes:
                skipped["budget"] += 1
                skipped_file_refs.append({"file_id": file_id, "reason": "budget", "bytes": size,
                                          "relative_path_PRIVATE": rel})
                continue
            total += size
            records, kind = parse_capture(path)
            result = summarize_records(records)
            score = (len(result["ball_related_paths"]) +
                     2 * len(result["velocity_related_paths"]) +
                     len(result["timing_or_provenance_paths"]) +
                     4 * len(result["candidate_changing_ball_vector_paths"]))
            scanned.append({"relative_path_PRIVATE": rel, "file_id": file_id,
                            "file_bytes": size, "file_kind": kind, "evidence_score": score, **result})
    scanned.sort(key=lambda row: (-row["evidence_score"], row["relative_path_PRIVATE"]))
    return {"kind": "PRIVATE-local-json-motion-provenance-inventory",
            "files_scanned": len(scanned), "bytes_scanned": total,
            "files_skipped_by_reason": dict(skipped),
            "skipped_file_refs_PRIVATE": skipped_file_refs,
            "training_approved": False, "no_raw_vector_values_in_report": True,
            "candidate_files": scanned}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument("--max-file-mib", type=int, default=8)
    parser.add_argument("--max-total-mib", type=int, default=128)
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args(argv)
    try:
        if args.data_root.name != "Wii-AI-Golf-Data" or args.data_root.is_symlink():
            raise ValueError("data-root must be the real private Wii-AI-Golf-Data directory")
        if not 1 <= args.max_files <= 10000 or not 1 <= args.max_file_mib <= 64 or not 1 <= args.max_total_mib <= 1024:
            raise ValueError("invalid bounded scan limits")
        result = audit_directory(args.data_root, args.max_files,
                                 args.max_file_mib * 1024 * 1024,
                                 args.max_total_mib * 1024 * 1024)
        report_name = "json-motion-inventory-PRIVATE-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json"
        report_path = args.data_root / report_name
        with report_path.open("x", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except (ValueError, OSError, UnicodeError) as exc:
        print(f"ABORT: private data inventory failed: {type(exc).__name__}", file=sys.stderr)
        return 2
    print("Scanned:", result["files_scanned"],
          "candidate JSON/JSONL files; skipped:", result["files_skipped_by_reason"])
    print("Local private report:", report_path)
    if result["skipped_file_refs_PRIVATE"]:
        print("Skipped capture file IDs (paths only inside PRIVATE report):")
        for item in result["skipped_file_refs_PRIVATE"][:20]:
            print(item["file_id"], "reason=",item["reason"], "bytes=",item.get("bytes","unknown"))
    print("Highest-ranked records (field names only; no raw values):")
    for row in result["candidate_files"][:max(0, min(args.top, 40))]:
        print(row["file_id"], "score=", row["evidence_score"],
              "ball_keys=",len(row["ball_related_paths"]),
              "velocity_keys=",len(row["velocity_related_paths"]),
              "phase=",",".join(row["declared_phase_terms"]) or "unknown",
              "varying_vector_paths=",len(row["candidate_changing_ball_vector_paths"]),
              "format=",row["file_kind"])
    print("All apparent motion remains unverified; manually trace phase/shot/frame linkage.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
