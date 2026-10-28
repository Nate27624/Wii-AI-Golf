"""Offline P0 *transient* word discovery from ONE existing positive-hit capture.

Complements (does NOT replace) the existing persistent PRE->SETTLED S002 ranker.
Only local, ignored, exact-pair PRIVATE raw JSONL + summary are inputs.
Never starts Dolphin, sends input, reads live memory or uploads private evidence.
Only bounded source-relative offsets, counts and evidence-quality flags are output.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOT = ROOT.parent / "Wii-AI-Golf-Data" / "captures"
WINDOWS = {
    "golf_config": 0x1C74,
    "golf_field": 0xA8,
    "sports_sequence": 0xD0,
    "minimap_player_effect": 0x200,
    "minimap_shot_line_effect": 0x200,
    "minimap_ball_effect": 0x200,
}
EFFECTS = {n for n in WINDOWS if n.startswith("minimap_")}
REF_HINTS = {
    ("golf_config", 0x94): "game_mode_not_power",
    ("golf_config", 0x98): "hole_index_not_power",
    ("golf_field", 0x44): "pin_ptr_not_xyz",
    ("golf_field", 0x50): "start_ptr_not_ball_xyz",
    ("golf_field", 0x54): "cup_ptr_not_landing_distance",
    ("golf_field", 0x94): "visual_player_effect_ptr",
    ("golf_field", 0x98): "visual_shotline_effect_ptr",
    ("golf_field", 0x9C): "visual_ball_effect_ptr",
}
PHASES = ("pre", "post", "settled")
_PHASE_ORDER = {"pre": 0, "post": 1, "settled": 2}
MAX_FILE = 6 * 1024 * 1024
MAX_ROWS = 60
MAX_PUBLIC_CANDIDATES = 40
_ADDR = re.compile(r"0x[0-9A-Fa-f]{8}\Z")
SUMMARY_SUFFIX = "-candidates.json"
RAW_SUFFIX = "-RAW-PRIVATE.jsonl"


def _address(text: object, length: int) -> int:
    if not isinstance(text, str) or not _ADDR.fullmatch(text):
        raise ValueError("Invalid address encoding")
    n = int(text, 16)
    if n % 4 or not (0x80000000 <= n and n + length <= 0x81800000 or
                    0x90000000 <= n and n + length <= 0x94000000):
        raise ValueError("Invalid RAM region")
    return n


def _pointer_like(value: int) -> bool:
    return 0x80000000 <= value < 0x81800000 or 0x90000000 <= value < 0x94000000


def _float_like(value: int) -> bool:
    f = struct.unpack(">f", struct.pack(">I", value))[0]
    return math.isfinite(f) and (f == 0.0 or 1e-6 <= abs(f) <= 1e6)


def _samples(summary: dict, rows: list[dict]) -> tuple[list[dict[int, tuple[int, tuple]]], int]:
    if (not isinstance(summary, dict) or
            summary.get("study_id") != "S002-HG-OUTCOME-TRANSITION-EXPLORATORY" or
            summary.get("raw_data_created") is not True or
            not isinstance(rows, list) or not 7 <= len(rows) <= MAX_ROWS):
        raise ValueError("Unrecognized positive-hit capture")
    human = summary.get("human_observation")
    if not isinstance(human, dict) or human.get("contact_human") != "yes":
        raise ValueError("No human-confirmed shot contact")
    swing = summary.get("known_good_swing_request")
    if (not isinstance(swing, dict) or
            swing.get("generated_trace_frames") != 89 or
            swing.get("a_lead_requested_frames") != 45 or
            swing.get("a_button_only_prime_requests") != 1):
        raise ValueError("Wrong historical V1 shot profile")
    observed = swing.get("a_lead_observed_frame_delta")
    if type(observed) is not int or observed < 45:
        raise ValueError("A lead observed-frame provenance not verified")
    rank = summary.get("candidate_ranking")
    if not isinstance(rank, dict):
        raise ValueError("Missing existing ranking")
    counts = {p: sum(r.get("phase") == p for r in rows if isinstance(r, dict))
              for p in PHASES}
    if any(counts[p] < 2 or counts[p] != rank.get(p + "_samples") for p in PHASES):
        raise ValueError("Missing phase controls")
    if rank.get("sample_count") != len(rows) or rank.get("candidates_truncated") is True:
        raise ValueError("Truncated/inconsistent earlier source ranking")
    if any(not isinstance(r, dict) or r.get("phase") not in PHASES for r in rows):
        raise ValueError("Unknown snapshot phase")
    if rows != sorted(rows, key=lambda r: _PHASE_ORDER[r["phase"]]):
        raise ValueError("Nonchronological phases")
    if (any(r.get("game_id") != "RSPE01" or r.get("disc_revision") != 1 or
            r.get("game_mode_raw") != 4 or
            r.get("schema_version") != 1 for r in rows)):
        raise ValueError("Wrong game/revision or snapshot schema")

    decoded = []
    max_span = 0
    previous_frame_start = -1
    first_bases: dict[str, int] | None = None
    excluded_aliases: set[int] = set()
    for row in rows:
        start, end = row.get("frame_start"), row.get("frame_end")
        if type(start) is not int or type(end) is not int or start < 0 or end < start:
            raise ValueError("Unverified frame bracket")
        if start < previous_frame_start:
            raise ValueError("Frame start moved backward; phase order invalid")
        previous_frame_start = start
        if row.get("source") != "Felk-read-only-US-Rev1-unverified-golf-windows":
            raise ValueError("Unexpected live collector schema")
        max_span = max(max_span, end - start)
        windows = row.get("windows")
        if not isinstance(windows, dict) or not windows or not set(windows).issubset(WINDOWS):
            raise ValueError("Unexpected source window")
        if not {"golf_config", "golf_field", "sports_sequence"}.issubset(windows):
            raise ValueError("Missing static negative-control region")
        if first_bases is not None and set(windows) != set(first_bases):
            raise ValueError("Window set changed across phases")
        bases: dict[str, int] = {}
        words: dict[int, tuple[int, set[tuple[str, int]]]] = {}
        conflict: set[int] = set()
        total = 0
        for name, sample in windows.items():
            if not isinstance(sample, dict) or not isinstance(sample.get("bytes_hex"), str):
                raise ValueError("Malformed bounded source window")
            length = WINDOWS[name]
            if len(sample["bytes_hex"]) != length * 2:
                raise ValueError("Incomplete source window")
            base = _address(sample.get("address"), length)
            if first_bases is not None and first_bases[name] != base:
                raise ValueError("Window relocated; cannot compare by source offset")
            bases[name] = base
            raw = bytes.fromhex(sample["bytes_hex"])
            total += len(raw)
            for offset in range(0, length, 4):
                address = base + offset
                bits = struct.unpack_from(">I", raw, offset)[0]
                if address in conflict:
                    continue
                if address in words:
                    if words[address][0] != bits:
                        conflict.add(address)
                        words.pop(address)
                        excluded_aliases.add(address)
                    else:
                        words[address][1].add((name, offset))
                else:
                    words[address] = (bits, {(name, offset)})
        if total > 12 * 1024 or (row.get("bytes_read") is not None and
                                row.get("bytes_read") != total):
            raise ValueError("Malformed total snapshot size")
        if first_bases is None:
            first_bases = bases
        decoded.append(words)

    # A cross-window contradictory reading must remain excluded in ALL phases.
    for row in decoded:
        for address in excluded_aliases:
            row.pop(address, None)
    return decoded, max_span


def audit(summary: dict, rows: list[dict]) -> dict:
    samples, max_span = _samples(summary, rows)
    phases = [r["phase"] for r in rows]
    common = set.intersection(*(set(s) for s in samples))
    transient = []
    persistent_count = 0
    unstable_pre = 0
    unstable_settled = 0
    post_changed_only_one = 0
    for address in sorted(common):
        observations = [s[address][0] for s in samples]
        pre = [v for v, p in zip(observations, phases) if p == "pre"]
        post = [v for v, p in zip(observations, phases) if p == "post"]
        settled = [v for v, p in zip(observations, phases) if p == "settled"]
        if len(set(pre)) != 1:
            unstable_pre += 1
            continue
        if len(set(settled)) != 1:
            unstable_settled += 1
            continue
        if pre[0] != settled[0]:
            persistent_count += 1
            continue
        changed = sum(v != pre[0] for v in post)
        if changed == 0:
            continue
        if changed != len(post):
            post_changed_only_one += 1
        locations = sorted(set.union(*(s[address][1] for s in samples)))
        is_effect = all(n in EFFECTS for n, _ in locations)
        pointer_like = any(_pointer_like(v) for v in observations)
        float_like = all(_float_like(v) for v in observations)
        # Two post samples changing independently is stronger than one;
        # these multi-frame windows still do not establish contact frame.
        transient.append({
            "type": ("all_POST_changed_and_SETTLED_restored"
                     if changed == len(post) else "some_POST_changed_and_SETTLED_restored"),
            "source_relative_locations": [
                {"window": name, "offset": f"+0x{offset:03X}",
                 "source_hint": REF_HINTS.get((name, offset), "untyped")}
                for name, offset in locations
            ],
            "visual_effect_only": is_effect,
            "pointer_shaped_confound": pointer_like,
            "finite_bounded_f32_bit_pattern": float_like,
            "post_differing_count": changed,
            "post_sample_count": len(post),
            "post_values_change_again": len(set(post)) > 1,
            "training_eligible": False,
            "ball_xyz_verified": False,
            "swing_power_verified": False,
        })
    rank = summary["candidate_ranking"]
    if rank.get("all_phase_stable_change_count") != persistent_count:
        raise ValueError("New read disagrees with existing persistent ranker")
    transient.sort(key=lambda v: (
        v["visual_effect_only"],
        v["post_differing_count"] != v["post_sample_count"],
        v["pointer_shaped_confound"],
        not v["finite_bounded_f32_bit_pattern"],
        v["source_relative_locations"][0]["window"],
        v["source_relative_locations"][0]["offset"]
    ))
    result = []
    for i, item in enumerate(transient[:MAX_PUBLIC_CANDIDATES], 1):
        result.append({"candidate_id": f"T{i:03d}", **item})
    return {
        "kind": "SANITIZED_P0_EXISTING_SHOT_POST_TRANSIENTS_V1",
        "source_class": "private_human_contact_positive_nonatomic_multiframe",
        "phase_counts": {p: phases.count(p) for p in PHASES},
        "max_snapshot_frame_span": max_span,
        "transient_unique_word_count": len(transient),
        "persistent_unique_word_count_crosscheck": persistent_count,
        "unstable_PRE_absolute_word_count_excluded": unstable_pre,
        "unstable_SETTLED_absolute_word_count_excluded": unstable_settled,
        "post_changed_in_only_subset_count": post_changed_only_one,
        "candidate_list_truncated": len(transient) > MAX_PUBLIC_CANDIDATES,
        "candidates": result,
        "source_field_semantics_unverified": True,
        "post_snapshot_atomicity_verified": False,
        "ball_world_xyz_verified": False,
        "ball_velocity_verified": False,
        "swing_power_verified": False,
        "training_allowed": False,
        "private_guest_addresses_present": False,
        "raw_word_values_present": False,
        "automatic_github_publication": False,
    }


def _private_file(text: str, suffix: str) -> Path:
    path = Path(text)
    if path.is_symlink():
        raise ValueError("Linked evidence refused")
    root = PRIVATE_ROOT.resolve(strict=True)
    resolved = path.resolve(strict=True)
    if (resolved.parent != root or not resolved.is_file() or
            not resolved.name.endswith(suffix) or
            resolved.stat().st_size > MAX_FILE):
        raise ValueError("Private source gate refused")
    return resolved


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--summary", required=True)
    p.add_argument("--raw", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args(argv)
    try:
        summary = _private_file(args.summary, SUMMARY_SUFFIX)
        raw = _private_file(args.raw, RAW_SUFFIX)
        if summary.name[:-len(SUMMARY_SUFFIX)] != raw.name[:-len(RAW_SUFFIX)]:
            raise ValueError("Capture pair mismatch")
        out = Path(args.output)
        root = PRIVATE_ROOT.resolve(strict=True)
        if (out.is_symlink() or out.parent.resolve(strict=True) != root or
                out.exists() or out.name !=
                summary.name[:-len(SUMMARY_SUFFIX)] + "-POST-TRANSIENTS-SANITIZED.json"):
            raise ValueError("Invalid exclusive private output path")
        data = json.loads(summary.read_text(encoding="utf-8"))
        lines = raw.read_text(encoding="utf-8")
        if len(lines.encode("utf-8")) > MAX_FILE:
            raise ValueError("Oversize raw source")
        rows = [json.loads(l) for l in lines.splitlines() if l.strip()]
        result = audit(data, rows)
        with out.open("x", encoding="utf-8") as sink:
            json.dump(result, sink, indent=2, sort_keys=True, allow_nan=False)
            sink.write("\n")
        print("P0_TRANSIENT_AUDIT_OK",
              "unique_transients=" + str(result["transient_unique_word_count"]),
              "persistent_crosscheck=" + str(result["persistent_unique_word_count_crosscheck"]),
              "non_effect_candidates=" + str(sum(not c["visual_effect_only"] for c in result["candidates"])),
              "truncated=" + str(result["candidate_list_truncated"]),
              "training_allowed=false", "automatic_upload=false")
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        print("P0_TRANSIENT_AUDIT_REFUSED: wrong capture/phase/alias/provenance or unsafe path; no output published",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
