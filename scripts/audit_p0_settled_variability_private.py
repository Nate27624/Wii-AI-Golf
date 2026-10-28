"""Read-only triage of words excluded for unstable SETTLED in original V1 shot.

Uses exactly the existing private capture validator from audit_p0_shot_transients_private.
No Dolphin, live RPC, Git, ROM, raw/public RAM or training feature promotion.
Reports source-window-relative offsets, counts and flags only; raw stays local.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

MODULE = Path(__file__).with_name("audit_p0_shot_transients_private.py")
_SPEC = importlib.util.spec_from_file_location("_original_p0_shot_transients", MODULE)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Existing P0 source validator unavailable")
p0 = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(p0)

REPORT_SUFFIX = "-SETTLED-VARIABILITY-SANITIZED.json"
MAX_PUBLIC = 30


def audit_settled(summary: dict, rows: list[dict]) -> dict:
    """Explore PRE-stable/SETTLED-unstable words; not proof of shot physics."""
    # First run the exact verified original shot detector, to ensure this is
    # one coherent study and that the S002 8 persistent words still crosscheck.
    baseline = p0.audit(summary, rows)
    samples, max_span = p0._samples(summary, rows)
    phases = [row["phase"] for row in rows]
    common = set.intersection(*(set(sample) for sample in samples))
    candidates = []
    for address in sorted(common):
        words = [sample[address][0] for sample in samples]
        pre = [v for v, phase in zip(words, phases) if phase == "pre"]
        if len(set(pre)) != 1:
            continue
        post = [v for v, phase in zip(words, phases) if phase == "post"]
        settled = [v for v, phase in zip(words, phases) if phase == "settled"]
        if len(set(settled)) < 2:
            continue
        locations = sorted(set.union(*(sample[address][1] for sample in samples)))
        effect_only = all(name in p0.EFFECTS for name, _ in locations)
        candidates.append({
            "source_relative_locations": [
                {"window": name, "offset": f"+0x{offset:03X}",
                 "source_hint": p0.REF_HINTS.get((name, offset), "untyped")}
                for name, offset in locations
            ],
            "effect_only_confound": effect_only,
            "pointer_shaped_pattern": any(p0._pointer_like(v) for v in words),
            "finite_bounded_f32_bit_pattern": all(p0._float_like(v) for v in words),
            "post_samples_different_from_PRE": sum(v != pre[0] for v in post),
            "settled_samples_different_from_PRE": sum(v != pre[0] for v in settled),
            "settled_distinct_word_patterns": len(set(settled)),
            "last_settled_equals_PRE": settled[-1] == pre[0],
            "training_eligible": False,
            "ball_position_or_velocity_verified": False,
            "shot_power_verified": False,
        })
    if len(candidates) != baseline["unstable_SETTLED_absolute_word_count_excluded"]:
        raise ValueError("Original unstable-settled count disagrees with detailed triage")
    # Prioritize potential non-effect source windows; do not interpret their
    # numerical bits as distance, state or physics.
    candidates.sort(key=lambda row: (
        row["effect_only_confound"],
        row["pointer_shaped_pattern"],
        row["source_relative_locations"][0]["window"],
        row["source_relative_locations"][0]["offset"]
    ))
    limited = [{"candidate_id": f"S{i:03d}", **r}
               for i, r in enumerate(candidates[:MAX_PUBLIC], 1)]
    return {
        "kind": "SANITIZED_P0_EXISTING_SHOT_UNSTABLE_SETTLED_V1",
        "source_class": "single_human_contact_positive_nonatomic_multiframe",
        "original_transients_crosscheck": baseline["transient_unique_word_count"],
        "original_persistent_crosscheck": baseline["persistent_unique_word_count_crosscheck"],
        "unstable_settled_unique_word_count": len(candidates),
        "effect_only_count": sum(c["effect_only_confound"] for c in candidates),
        "non_effect_count": sum(not c["effect_only_confound"] for c in candidates),
        "max_snapshot_frame_span": max_span,
        "sample_counts": baseline["phase_counts"],
        "candidate_list_truncated": len(candidates) > MAX_PUBLIC,
        "candidates": limited,
        "source_semantics_verified": False,
        "phase_atomicity_verified": False,
        "ball_world_xyz_verified": False,
        "ball_velocity_verified": False,
        "swing_power_verified": False,
        "training_allowed": False,
        "private_guest_addresses_present": False,
        "raw_word_values_present": False,
        "automatic_github_publication": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--raw", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        summary = p0._private_file(args.summary, p0.SUMMARY_SUFFIX)
        raw = p0._private_file(args.raw, p0.RAW_SUFFIX)
        if summary.name[:-len(p0.SUMMARY_SUFFIX)] != raw.name[:-len(p0.RAW_SUFFIX)]:
            raise ValueError("Private capture pair mismatch")
        root = p0.PRIVATE_ROOT.resolve(strict=True)
        out = Path(args.output)
        if (out.is_symlink() or out.exists() or out.parent.resolve(strict=True) != root
                or out.name != summary.name[:-len(p0.SUMMARY_SUFFIX)] + REPORT_SUFFIX):
            raise ValueError("Invalid exclusive private output name")
        data = json.loads(summary.read_text(encoding="utf-8"))
        raw_text = raw.read_text(encoding="utf-8")
        if len(raw_text.encode("utf-8")) > p0.MAX_FILE:
            raise ValueError("Oversize private capture")
        rows = [json.loads(line) for line in raw_text.splitlines() if line.strip()]
        report = audit_settled(data, rows)
        with out.open("x", encoding="utf-8") as sink:
            json.dump(report, sink, sort_keys=True, indent=2, allow_nan=False)
            sink.write("\n")
        print("P0_SETTLED_VARIABILITY_OK",
              "count=" + str(report["unstable_settled_unique_word_count"]),
              "non_effect=" + str(report["non_effect_count"]),
              "effect_only=" + str(report["effect_only_count"]),
              "original_transients=" + str(report["original_transients_crosscheck"]),
              "persistent=" + str(report["original_persistent_crosscheck"]),
              "truncated=" + str(report["candidate_list_truncated"]),
              "training_allowed=false", "automatic_upload=false")
        return 0
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, json.JSONDecodeError):
        print("P0_SETTLED_VARIABILITY_REFUSED: invalid capture or unsafe destination; no upload",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
