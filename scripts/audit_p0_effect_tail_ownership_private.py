"""Offline source-pointer and overlap-coverage study of a known successful shot.

Requires the reviewed #209 parent branch's exact original source/phase validator.
NO Dolphin, no guest RPC, no RAM scan, no live inputs, no network, no publishing.

The 0x90 spacing is an observed pointer spacing only; this module does NOT
infer an RPSysEffect allocation size, instance count or real ball physics.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import struct
import sys

_DIR = Path(__file__).resolve().parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _DIR / filename)
    if spec is None or spec.loader is None:
        raise ValueError("Reviewed source validator unavailable")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


prior = _load("_p0_transient_source", "audit_p0_shot_transients_private.py")
settled = _load("_p0_settled_source", "audit_p0_settled_variability_private.py")

EXPECTED_WINDOWS = (
    "minimap_player_effect", "minimap_shot_line_effect", "minimap_ball_effect"
)
PTR_OFFSETS = (0x94, 0x98, 0x9C)
STRIDE = 0x90
EFFECT_READ_SIZE = 0x200  # Collector's exploratory read length, NOT object size.
TAIL_OFFSETS = (0x1EC, 0x1F0, 0x1F4, 0x1F8, 0x1FC)
SLOT_OFFSETS = (0x3C, 0x40, 0x44, 0x48, 0x4C)
TAIL_SLOT_INDEX = 5
MAX_LISTED_SLOTS = 6
OUTPUT_SUFFIX = "-EFFECT-TAIL-OWNERSHIP-SANITIZED.json"


def _word(buf_hex: str, offset: int) -> int:
    return struct.unpack_from(">I", bytes.fromhex(buf_hex), offset)[0]


def _locations(address: int, bases: tuple[int, int, int]) -> list[dict]:
    return [
        {"window": window, "offset": f"+0x{address-base:03X}"}
        for window, base in zip(EXPECTED_WINDOWS, bases)
        if base <= address <= base + EFFECT_READ_SIZE - 4
    ]


def audit(summary: dict, rows: list[dict]) -> dict:
    """Output safely bounded arithmetic/geometric and temporal evidence only."""
    original = prior.audit(summary, rows)
    unstable = settled.audit_settled(summary, rows)
    if (original["transient_unique_word_count"] != 0 or
            original["persistent_unique_word_count_crosscheck"] != 8 or
            unstable["unstable_settled_unique_word_count"] != 5 or
            unstable["non_effect_count"] != 0):
        raise ValueError("Not the verified original 0/8/5 private shot cohort")
    if (len(rows) != 8 or
            [r["phase"] for r in rows] != ["pre"] * 3 + ["post"] * 2 + ["settled"] * 3):
        raise ValueError("Unexpected phase cohort")

    decoded, max_span = prior._samples(summary, rows)
    pointer_relations = []
    first_bases = None
    for row in rows:
        fields = row["windows"]
        if any(name not in fields for name in EXPECTED_WINDOWS):
            raise ValueError("Missing source-selected effect snapshot")
        field = fields["golf_field"]
        if len(field["bytes_hex"]) != prior.WINDOWS["golf_field"] * 2:
            raise ValueError("Truncated source golf-field snapshot")
        bases = tuple(int(fields[name]["address"], 16) for name in EXPECTED_WINDOWS)
        if not (bases[1] - bases[0] == STRIDE and
                bases[2] - bases[1] == STRIDE):
            raise ValueError("Expected 0x90 effect window pointer spacing absent")
        if first_bases is None:
            first_bases = bases
        if first_bases != bases:
            raise ValueError("Effect pointers relocated across shot phases")
        for name, offset, base in zip(EXPECTED_WINDOWS, PTR_OFFSETS, bases):
            actual = _word(field["bytes_hex"], offset)
            if actual != base:
                raise ValueError("Source field pointer and sampled window disagree")
            if not prior._address(fields[name]["address"], EFFECT_READ_SIZE) == base:
                raise ValueError("Unrecognized effect source address")
        pointer_relations.append(True)
    if not all(pointer_relations) or first_bases is None:
        raise ValueError("Missing pointer provenance")

    # The first sampled window begins at A. Its three 0x200-byte slices are:
    # A..A+0x200, A+0x90..A+0x290, A+0x120..A+0x320.
    # A+0x30C..A+0x31C is covered by the *third window only*.
    ball_base = first_bases[2]
    expected_tail = {ball_base + off for off in TAIL_OFFSETS}
    settled_tails = set()
    for candidate in unstable["candidates"]:
        locations = candidate["source_relative_locations"]
        if len(locations) != 1 or locations[0]["window"] != "minimap_ball_effect":
            raise ValueError("One of five source tails is aliased or out of window")
        offset = int(locations[0]["offset"].removeprefix("+"), 16)
        settled_tails.add(ball_base + offset)
    if settled_tails != expected_tail:
        raise ValueError("Actual five original unsettled tail offsets differ")
    for offset in TAIL_OFFSETS:
        locs = _locations(ball_base + offset, first_bases)
        if len(locs) != 1 or locs[0]["window"] != "minimap_ball_effect":
            raise ValueError("Tail overlaps multiple windows; cannot apply coverage claim")

    # Compare the same five relative positions at the six *hypothetical* 0x90
    # stride indices (0..5), as far as the recorded windows reach. This is
    # numerical alignment, never proof of an array or source allocation.
    slots = []
    for idx in range(MAX_LISTED_SLOTS):
        stable_pre = 0
        changed_post = 0
        unstable_settled = 0
        equal_to_pre_last = 0
        coverage_hist = {"one_window": 0, "two_windows": 0, "three_windows": 0}
        for offset in SLOT_OFFSETS:
            absolute = first_bases[0] + idx * STRIDE + offset
            locs = _locations(absolute, first_bases)
            if not 1 <= len(locs) <= 3 or any(absolute not in s for s in decoded):
                raise ValueError("Missing comparable hypothetical slot-word coverage")
            coverage_hist[["one_window", "two_windows", "three_windows"][len(locs)-1]] += 1
            values = [sample[absolute][0] for sample in decoded]
            pre, post, last = values[:3], values[3:5], values[5:]
            if len(set(pre)) == 1:
                stable_pre += 1
                changed_post += int(any(v != pre[0] for v in post))
                equal_to_pre_last += int(last[-1] == pre[0])
            unstable_settled += int(len(set(last)) > 1)
        slots.append({
            "arithmetic_stride_index": idx,
            "relative_offsets": [f"+0x{x:02X}" for x in SLOT_OFFSETS],
            "five_words_fully_covered": True,
            "word_coverage_by_number_of_source_windows": coverage_hist,
            "stable_PRE_word_count": stable_pre,
            "words_with_any_POST_difference_from_stable_PRE": changed_post,
            "words_with_unstable_SETTLED": unstable_settled,
            "last_SETTLED_equals_stable_PRE_word_count": equal_to_pre_last,
            "hypothetical_stride_not_object_size_or_allocation": True,
        })
    if slots[TAIL_SLOT_INDEX]["words_with_unstable_SETTLED"] != 5:
        raise ValueError("Tail-relative 0x90 alignment inconsistent with real report")
    if slots[TAIL_SLOT_INDEX]["word_coverage_by_number_of_source_windows"] != {
        "one_window": 5, "two_windows": 0, "three_windows": 0
    }:
        raise ValueError("Tail sample coverage unexpected")

    return {
        "kind": "SANITIZED_P0_EFFECT_POINTER_TAIL_OWNERSHIP_V1",
        "source_class": "original_human_hit_multiframe_private_effect_windows",
        "source_pointer_offsets_in_golf_field": ["+0x094", "+0x098", "+0x09C"],
        "pointer_word_matches_window_start_in_all_samples": True,
        "pointer_bases_fixed_across_all_samples": True,
        "effect_pointer_start_spacing_bytes": STRIDE,
        "collector_per_window_read_bytes": EFFECT_READ_SIZE,
        "collector_bytes_are_not_verified_object_size": True,
        "last_five_ball_window_relative_offsets": [f"+0x{x:03X}" for x in TAIL_OFFSETS],
        "last_five_only_observed_in_ball_named_window": True,
        "tail_corresponds_to_hypothetical_stride_index": TAIL_SLOT_INDEX,
        "tail_relative_positions_in_hypothetical_stride": [
            f"+0x{x:02X}" for x in SLOT_OFFSETS],
        "six_hypothetical_slot_profiles": slots,
        "actual_unstable_settled_words_crosscheck": 5,
        "actual_post_restored_transients_crosscheck": 0,
        "actual_persistent_words_crosscheck": 8,
        "max_nonatomic_frame_span": max_span,
        "repeated_effect_instance_count_verified": False,
        "effect_allocation_ownership_verified": False,
        "ball_world_xyz_verified": False,
        "ball_velocity_verified": False,
        "swing_power_verified": False,
        "training_allowed": False,
        "private_guest_addresses_present": False,
        "raw_word_values_present": False,
        "automatic_github_publication": False,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--summary", required=True)
    p.add_argument("--raw", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args(argv)
    try:
        summary_file = prior._private_file(args.summary, prior.SUMMARY_SUFFIX)
        raw_file = prior._private_file(args.raw, prior.RAW_SUFFIX)
        if summary_file.name[:-len(prior.SUMMARY_SUFFIX)] != raw_file.name[:-len(prior.RAW_SUFFIX)]:
            raise ValueError("Wrong paired shot IDs")
        stem = summary_file.name[:-len(prior.SUMMARY_SUFFIX)]
        out = Path(args.output)
        root = prior.PRIVATE_ROOT.resolve(strict=True)
        if (out.is_symlink() or out.parent.resolve(strict=True) != root or
                out.name != stem + OUTPUT_SUFFIX):
            raise ValueError("Private output path refused")
        if raw_file.stat().st_size > prior.MAX_FILE or summary_file.stat().st_size > prior.MAX_FILE:
            raise ValueError("Oversized original private evidence")
        summary = json.loads(summary_file.read_text(encoding="utf-8"))
        rows = [json.loads(line) for line in raw_file.read_text(encoding="utf-8").splitlines()
                if line.strip()]
        report = audit(summary, rows)
        if out.exists():
            # Idempotent, read-only report verification, never replace or append.
            existing = json.loads(out.read_text(encoding="utf-8"))
            if existing != report:
                raise ValueError("Existing output does not match newly computed report")
            label = "P0_EFFECT_TAIL_EXISTING_RESULT_VERIFIED"
        else:
            with out.open("x", encoding="utf-8") as sink:
                json.dump(report, sink, indent=2, sort_keys=True, allow_nan=False)
                sink.write("\n")
            label = "P0_EFFECT_TAIL_RESULT_WRITTEN"
        print(label,
              "source_pointer_matches=8/8",
              "tail_words=5", "coverage_windows=1",
              "hypothetical_stride_index=5", "max_span="+str(report["max_nonatomic_frame_span"]),
              "object_size_verified=false", "training_allowed=false", "auto_upload=false")
        return 0
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, json.JSONDecodeError):
        print("P0_EFFECT_TAIL_REFUSED: unsafe source/pointer/overlap/report; no upload",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
