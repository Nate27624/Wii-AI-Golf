#!/usr/bin/env python3
"""PRIVATE, read-only cross-hit recurrence by HUMAN-LABELED outcome.

Reuses the pinned S002 #199 strict per-shot audit for every local RAW/summary
pair. Never starts Dolphin, reads ROM, modifies game RAM, exposes raw words,
dynamic pointers, exact local capture IDs, or promotes a training variable.
"""
from __future__ import annotations
from collections import defaultdict
import argparse
import importlib.util
import json
from pathlib import Path
import sys

OUTCOMES = ("yes", "no", "unknown")
MAX_STUDIES = 30
MAX_FILE_BYTES = 6 * 1024 * 1024
AUDIT_KIND = "P0_PRIVATE_OUTCOME_SOURCE_RELATIVE_TRIAGE"
# Mirror exact fixed source-window bounds in S002 #199; fail closed when
# an apparent relative offset would be a dynamic guest pointer or out of range.
WINDOW_BYTES = {
    "golf_config": 0x1C74,
    "golf_field": 0x0A8,
    "sports_sequence": 0x0D0,
    "minimap_ball_effect": 0x200,
    "minimap_player_effect": 0x200,
    "minimap_shot_line_effect": 0x200,
}


def human_green_label(summary):
    value = summary.get("human_observation", {}).get("finished_on_green_human")
    return value if value in ("yes", "no") else "unknown"


def signature_for(candidate):
    locations = candidate.get("source_relative_locations")
    if not isinstance(locations, list) or not locations:
        raise ValueError("Missing source-relative evidence")
    parts = []
    families = set()
    for loc in locations:
        if not isinstance(loc, dict):
            raise ValueError("Malformed source-relative location")
        window, offset = loc.get("window"), loc.get("relative_word_offset")
        if (not isinstance(window, str) or not window.replace("_", "").isalnum()
                or not isinstance(offset, str) or not 6 <= len(offset) <= 11
                or not offset.startswith("+0x")
                or not all(c in "0123456789ABCDEFabcdef" for c in offset[3:])):
            raise ValueError("Malformed source window-relative offset")
        relative = int(offset[3:], 16)
        if (window not in WINDOW_BYTES or relative % 4 != 0
                or relative + 4 > WINDOW_BYTES[window]):
            raise ValueError("Source-relative candidate is out of bounded S002 window")
        parts.append(f"{window}{offset.upper().replace('X','x')}")
        families.add(loc.get("triage_family"))
    return " | ".join(sorted(set(parts))), families


def stratify(validated):
    """Aggregate already S002-validated sanitized audits; no raw numeric values."""
    if not isinstance(validated, list) or not 1 <= len(validated) <= MAX_STUDIES:
        raise ValueError("Expect 1..30 independently validated capture pairs")
    labels = defaultdict(int)
    support = defaultdict(lambda: defaultdict(set))
    pointer = defaultdict(set)
    types = defaultdict(set)
    counts = defaultdict(list)
    for i, rec in enumerate(validated):
        group, audit = rec["human_green_label"], rec["audit"]
        if group not in OUTCOMES or audit.get("kind") != AUDIT_KIND:
            raise ValueError("Unsupported human outcome or audit schema")
        if (audit.get("model_training_allowed") is not False
                or audit.get("verified_ball_xyz") is not False
                or audit.get("human_contact_yes") is not True):
            raise ValueError("Audit cannot be promoted to motion/training evidence")
        candidates = audit.get("candidates")
        if (not isinstance(candidates, list)
                or audit.get("stored_persistent_candidate_count") != len(candidates)):
            raise ValueError("Candidate list/count mismatch")
        labels[group] += 1
        counts[group].append(len(candidates))
        for c in candidates:
            key, families = signature_for(c)
            support[key][group].add(i)
            types[key].update(families)
            if c.get("before_or_after_pointer_shaped") is True:
                pointer[key].add(i)
    rows = []
    for key, groups in support.items():
        yes = len(groups["yes"])
        no = len(groups["no"])
        unknown = len(groups["unknown"])
        rows.append({
            "source_relative_alias_signature": key,
            "present_in_green_yes": yes,
            "present_in_green_no": no,
            "present_in_green_unknown": unknown,
            "present_in_total": yes + no + unknown,
            "pointer_shaped_run_count": len(pointer[key]),
            "source_families": sorted(types[key]),
            "rendering_only_classified": types[key] == {"visual_effect_confound"},
            "training_eligible": False,
        })
    rows.sort(key=lambda row: (
        -row["present_in_total"], -row["present_in_green_no"],
        row["source_relative_alias_signature"]))
    return {
        "kind": "PRIVATE-validated-crosshit-outcome-stratification",
        "validated_human_contact_captures": len(validated),
        "human_labeled_green_yes": labels["yes"],
        "human_labeled_green_no": labels["no"],
        "human_green_unknown": labels["unknown"],
        "candidate_count_by_outcome": {
            group: sorted(counts[group]) for group in OUTCOMES},
        "distinct_alias_signatures": len(rows),
        "signature_recurrence": rows,
        "single_green_positive_insufficient_for_specificity": labels["yes"] < 2,
        "independent_no_contact_control_checked": False,
        "guest_frame_atomicity_verified": False,
        "true_ball_xyz_verified": False,
        "model_training_allowed": False,
        "note": "Per-shot S002 audit proven only within fixed source windows; labels are HUMAN yes/no/unknown. Differences may reflect rendering, scenario, boot or pointer lifetime, not a physical outcome signal."
    }


def load_auditor(path: Path):
    if path.is_symlink() or path.name != "audit_p0_successful_shot_private.py":
        raise ValueError("Only existing S002 source-approved auditor accepted")
    if not path.is_file() or path.stat().st_size > 128 * 1024:
        raise ValueError("S002 auditor missing or unexpected size")
    spec = importlib.util.spec_from_file_location("pinned_s002_hit_auditor", path)
    if spec is None or spec.loader is None:
        raise ValueError("Unable to load S002 code")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "audit") or not hasattr(module, "PRIVATE_ROOT"):
        raise ValueError("Incompatible S002 auditor")
    return module


def scan_local(captures_dir: Path, auditor) -> dict:
    captures = captures_dir.resolve(strict=True)
    if (captures_dir.is_symlink() or captures.name != "captures"
            or captures.parent.name != "Wii-AI-Golf-Data"
            or captures != auditor.PRIVATE_ROOT.resolve(strict=True)):
        raise ValueError("Source-approved private capture directory mismatch")
    pairs = []
    for file in sorted(captures.glob("outcome-*-candidates.json")):
        if file.is_symlink() or file.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("Invalid summary bounds")
        summary = json.loads(file.read_text(encoding="utf-8-sig"))
        if not isinstance(summary, dict) or summary.get("human_observation", {}).get("contact_human") != "yes":
            continue
        stem = file.name[:-len("-candidates.json")]
        raw_path = captures / (stem + "-RAW-PRIVATE.jsonl")
        if (raw_path.is_symlink() or not raw_path.is_file()
                or raw_path.stat().st_size > MAX_FILE_BYTES):
            raise ValueError("Missing bounded paired PRIVATE raw shot")
        rows = []
        with raw_path.open("r", encoding="utf-8-sig") as reader:
            for line in reader:
                if line.strip():
                    rows.append(json.loads(line))
                if len(rows) > 60:
                    raise ValueError("More raw phase records than S002 accepts")
        report = auditor.audit(summary, rows)
        pairs.append({"human_green_label": human_green_label(summary), "audit": report})
        if len(pairs) > MAX_STUDIES:
            raise ValueError("Too many pairs; update studied scope deliberately")
    return stratify(pairs)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--captures", required=True, type=Path)
    p.add_argument("--s002-reader", required=True, type=Path)
    p.add_argument("--top", type=int, default=40)
    args = p.parse_args(argv)
    if not 1 <= args.top <= 200:
        p.error("--top must be 1..200")
    try:
        result = scan_local(args.captures, load_auditor(args.s002_reader))
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            UnicodeError, json.JSONDecodeError, ImportError):
        print("ABORT: source-validated private cross-hit comparison failed; no data published",
              file=sys.stderr)
        return 2
    result["total_signatures_omitted_from_stdout"] = max(
        0, len(result["signature_recurrence"]) - args.top)
    result["signature_recurrence"] = result["signature_recurrence"][:args.top]
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
