"""Offline cross-capture consensus for Wii Sports Rev1 memory snapshots.

Reads only the allowlisted private outcome JSONL files. Outputs aggregate
region-relative statistics, never the raw samples or pointer addresses.
This is not an identifier of ball location, club pose, or power.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("single_golf_memory_audit", HERE / "audit_golf_memory_regions.py")
_single = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_single)

PATTERN = "outcome-*-RAW-PRIVATE.jsonl"
MAX_FILES = 200


def aggregate(paths):
    files = list(paths)
    if not files or len(files) > MAX_FILES:
        raise ValueError("requires between 1 and 200 capture files")
    consensus = {}
    results = []
    skipped = []
    for path in files:
        try:
            summary = _single.analyze(_single.load(path), top=500)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            skipped.append({"capture_index": len(results) + len(skipped) + 1,
                            "reason": type(exc).__name__})
            continue
        results.append({"samples": summary["samples"],
                        "phase_counts": summary["phase_counts"],
                        "changed_words": summary["changed_word_count"],
                        "relocation_skips": summary["relocation_skips"]})
        for item in summary["top_changed_words"]:
            key = (item["window"], item["offset_hex"])
            group = consensus.setdefault(key, {
                "window": item["window"], "offset_hex": item["offset_hex"],
                "known_role": item["known_role"], "captures_changed": 0,
                "captures_within_phase": 0, "captures_across_phase": 0,
                "within_phase_transitions": 0, "across_phase_transitions": 0,
                "pointer_like_transitions": 0, "plausible_float_transitions": 0})
            group["captures_changed"] += 1
            group["captures_within_phase"] += int(item["within_phase"] > 0)
            group["captures_across_phase"] += int(item["across_phase"] > 0)
            for field in ("within_phase", "across_phase", "pointer_like_transitions",
                          "plausible_float_transitions"):
                dest = {"within_phase": "within_phase_transitions",
                        "across_phase": "across_phase_transitions"}.get(field, field)
                group[dest] += item[field]
    ranked = list(consensus.values())
    # Prioritize non-rendering candidates that repeatedly change *within*
    # a phase; phase boundaries are confounded by scene/UI transitions.
    ranked.sort(key=lambda v: (
        v["known_role"] == "rendering_effect_undocumented",
        -v["captures_within_phase"], -v["captures_changed"],
        -v["captures_across_phase"], v["window"], int(v["offset_hex"][3:], 16)))
    return {
        "schema_version": 1, "kind": "offline_cross_capture_memory_consensus",
        "files_considered": len(files), "files_analyzed": len(results),
        "files_skipped": skipped, "capture_summaries": results,
        "candidate_count": len(ranked), "candidates": ranked,
        "cautions": [
            "Only a relative-offset and transition consensus, not field identification",
            "Rendering-effect fields are demoted; they are not physics-ball coordinates",
            "No success/miss labels available; within-phase changes may be animation or UI",
            "Cross-capture comparison does not establish stable object identity",
            "Only valid same-instance adjacent snapshots count within each capture",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.limit <= MAX_FILES or not 1 <= args.top <= 500:
            raise ValueError("limit must be 1..200 and top 1..500")
        files = sorted(args.capture_dir.glob(PATTERN),
                       key=lambda p: p.stat().st_mtime, reverse=True)[:args.limit]
        summary = aggregate(files)
        summary["candidates"] = summary["candidates"][:args.top]
        payload = json.dumps(summary, sort_keys=True, indent=2, allow_nan=False) + "\n"
        if args.out:
            # Refuse writing into the raw input directory.
            if args.out.resolve().parent == args.capture_dir.resolve():
                raise ValueError("output must be outside raw capture directory")
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x", encoding="utf-8") as handle:
                handle.write(payload)
        print(payload, end="")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Cross-capture audit failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
