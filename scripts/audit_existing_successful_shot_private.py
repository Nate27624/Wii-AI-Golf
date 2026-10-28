"""Retrospectively audit an ALREADY CAPTURED successful golf shot, offline only.

Cross-check the original private RAW-PRIVATE.jsonl against its original
-candidates.json; emit ONLY source-relative field offsets, phases and
classification flags. Never print RAM addresses, u32 words, f32, pointers,
raw JSON, file path, hash or private capture bytes.

No game, Dolphin, RPC, controller, savestate, network or file writes.
A candidate changing after contact is NOT verified physical ball XYZ, swing
power, a shot heading, meter reading or official score.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.audit.outcome_transition import (
    EFFECT_POINTER_OFFSETS, STATIC_STRUCTS, _words, rank_outcome_candidates,
)

DATA_ROOT = ROOT.parent / "Wii-AI-Golf-Data"
DEFAULT_CAPTURES = DATA_ROOT / "captures"
RUN_ID = re.compile(r"^outcome-\d{8}T\d{6}Z-[0-9a-f]{8}$")
MAX_RAW_BYTES = 6 * 1024 * 1024
MAX_SUMMARY_BYTES = 8 * 1024 * 1024
MAX_ROWS = 60
KNOWN_REGIONS = frozenset(STATIC_STRUCTS) | frozenset(EFFECT_POINTER_OFFSETS)


def _inside_data(path: Path) -> Path:
    if path.is_symlink():
        raise ValueError("Symlink inputs are not permitted")
    resolved = path.resolve(strict=True)
    data = DATA_ROOT.resolve(strict=True)
    if resolved == data or not resolved.is_relative_to(data):
        raise ValueError("Capture must be inside the private Wii-AI-Golf-Data root")
    return resolved


def _read_one_json(path: Path, max_bytes: int) -> dict:
    if not path.is_file() or path.stat().st_size > max_bytes:
        raise ValueError("Private input is missing or too large")
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError("Expected one JSON object")
    return result


def _read_raw(path: Path) -> list[dict]:
    if not path.is_file() or path.stat().st_size > MAX_RAW_BYTES:
        raise ValueError("Private raw JSONL is missing or oversized")
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if len(rows) >= MAX_ROWS:
                raise ValueError("Too many snapshots")
            row = json.loads(line)
            if not isinstance(row, dict) or row.get("source") != (
                    "Felk-read-only-US-Rev1-unverified-golf-windows"):
                raise ValueError("Unexpected snapshot provenance")
            if row.get("game_mode_raw") != 4:
                raise ValueError("Not Hitting the Green training mode")
            if not isinstance(row.get("windows"), dict) or (
                    set(row["windows"]) - KNOWN_REGIONS):
                raise ValueError("Unrecognized or invalid RAM region")
            rows.append(row)
    if not rows:
        raise ValueError("Empty snapshot cohort")
    return rows


def _pointer_like(value: int) -> bool:
    return type(value) is int and value % 4 == 0 and (
        0x80000000 <= value < 0x81800000
        or 0x90000000 <= value < 0x94000000
    )


def _relative_owners(rows: list[dict], address: int) -> list[dict]:
    """Require identical source-relative ownership in EVERY snapshot."""
    shared = None
    for row in rows:
        refs = set()
        for name, info in row["windows"].items():
            base = int(info["address"], 16)
            length = len(info["bytes_hex"]) // 2
            if base <= address < base + length:
                refs.add((name, address-base))
        shared = refs if shared is None else shared & refs
    return [
        {"source_window": name, "relative_offset": f"+0x{offset:03X}"}
        for name, offset in sorted(shared or set())
    ]



def _effect_stride_layout(rows: list[dict]) -> bool:
    """Check real window bases, in ALL phases, without exposing their values.

    This confirms 0x90 *pointer spacing*, not type, record size, ball physics,
    or that successive effect owners are independently allocated objects.
    """
    names = ("minimap_player_effect", "minimap_shot_line_effect",
             "minimap_ball_effect")
    for row in rows:
        windows = row["windows"]
        if not all(name in windows for name in names):
            return False
        bases = [int(windows[name]["address"], 16) for name in names]
        if bases[1] - bases[0] != 0x90 or bases[2] - bases[1] != 0x90:
            return False
    return True


def _effect_slot(rows: list[dict], address: int, *, layout: bool) -> dict:
    """Infer a repeated 0x90 stride only when all source bases corroborate."""
    if not layout:
        return {
            "inferred_effect_slot_index": None,
            "inferred_effect_slot_field": None,
        }
    identity = None
    for row in rows:
        player = int(row["windows"]["minimap_player_effect"]["address"], 16)
        distance = address - player - 0x78
        slot, field = divmod(distance, 0x90)
        if not 0 <= slot <= 3 or field not in (0, 4):
            return {
                "inferred_effect_slot_index": None,
                "inferred_effect_slot_field": None,
            }
        next_identity = (slot, field)
        if identity is not None and identity != next_identity:
            return {
                "inferred_effect_slot_index": None,
                "inferred_effect_slot_field": None,
            }
        identity = next_identity
    return {
        "inferred_effect_slot_index": identity[0],
        "inferred_effect_slot_field": (
            "+0x078" if identity[1] == 0 else "+0x07C"),
    }


def audit(rows: list[dict], summary: dict) -> dict:
    """Pure offline validator; summarized output is safe for chat/PR review."""
    if summary.get("study_id") != "S002-HG-OUTCOME-TRANSITION-EXPLORATORY":
        raise ValueError("Wrong source-study summary")
    if summary.get("raw_data_created") is not True:
        raise ValueError("Summary does not claim a saved raw cohort")
    label = summary.get("human_observation", {})
    if not isinstance(label, dict) or label.get("contact_human") != "yes":
        raise ValueError("This analysis is strictly for the witnessed-contact cohort")
    if label.get("game_distance_verified_by_memory") is not False:
        raise ValueError("Unexpected memory-verified distance claim")
    if label.get("displayed_power_verified_by_memory", False) is not False:
        raise ValueError("Unexpected memory-verified power claim")
    req = summary.get("known_good_swing_request", {})
    if not isinstance(req, dict):
        raise ValueError("Missing controller provenance")
    lead = req.get("a_lead_requested_frames")
    observed = req.get("a_lead_observed_frame_delta")
    if type(lead) is not int or type(observed) is not int or lead < 0 or observed < lead:
        raise ValueError("Observed A-lead provenance missing or inconsistent")
    swing = summary.get("swing_dispatch", {})
    if not isinstance(swing, dict) or swing.get("state") != "complete":
        raise ValueError("Swing dispatch must be complete (contact still human labeled)")
    applied = swing.get("applied_frames")
    if type(applied) is not int or applied < 1 or applied != swing.get("total_frames"):
        raise ValueError("Incomplete or untrusted controller trace")

    distance = label.get("displayed_distance_human")
    if distance is not None and (type(distance) not in (float, int)
                                 or not math.isfinite(distance) or distance < 0):
        raise ValueError("Invalid display annotation")
    recomputed = rank_outcome_candidates(rows, human_distance=distance, top_n=500)
    saved = summary.get("candidate_ranking")
    if not isinstance(saved, dict) or saved.get("candidates_truncated") is not False:
        raise ValueError("Original candidate list truncated/missing")
    if saved.get("all_phase_stable_change_count") != recomputed["all_phase_stable_change_count"]:
        raise ValueError("Candidate count disagrees with original private snapshot")
    original = saved.get("candidates")
    if not isinstance(original, list) or len(original) != len(recomputed["candidates"]):
        raise ValueError("Saved candidate rows disagree with recomputed cohort")
    original_keys = {
        (c["address"], c["before"]["u32"], c["settled"]["u32"])
        for c in original
    }
    current_keys = {
        (c["address"], c["before"]["u32"], c["settled"]["u32"])
        for c in recomputed["candidates"]
    }
    if original_keys != current_keys or len(original_keys) != len(original):
        raise ValueError("Original candidate content differs from raw cohort")
    all_words = [_words(s) for s in rows]
    pre = [a for a, r in zip(all_words, rows) if r["phase"] == "pre"]
    post = [a for a, r in zip(all_words, rows) if r["phase"] == "post"]
    settled = [a for a, r in zip(all_words, rows) if r["phase"] == "settled"]
    effect_spacing = _effect_stride_layout(rows)
    records = []
    for candidate in recomputed["candidates"]:
        address = int(candidate["address"], 16)
        baseline = pre[0][address][0]
        post_bits = [r[address][0] for r in post]
        settled_value = settled[0][address][0]
        change_count = sum(w != baseline for w in post_bits)
        temporal = ("post_all_changed" if change_count == len(post_bits)
                    else "post_partially_changed" if change_count
                    else "settled_only_change")
        region_refs = _relative_owners(rows, address)
        effect_slot = _effect_slot(rows, address, layout=effect_spacing)
        records.append({
            "source_relative_owners": region_refs,
            **effect_slot,
            "source_owner_stable_across_all_snapshots": bool(region_refs),
            "temporal_pattern": temporal,
            "pointer_like_word_any_phase": any(
                _pointer_like(x) for x in [baseline, *post_bits, settled_value]),
            "literal_match_to_displayed_number_only": bool(
                candidate["matches_displayed_numeric_label_as"]),
            "screen_or_render_effect_window": any(
                r["source_window"] in EFFECT_POINTER_OFFSETS for r in region_refs),
            "physical_semantics_verified": False,
        })
    phase_counts = {
        p: sum(row["phase"] == p for row in rows)
        for p in ("pre", "post", "settled")
    }
    assigned = [(r["inferred_effect_slot_index"],
                 r["inferred_effect_slot_field"]) for r in records]
    complete_slot_pairs = (
        effect_spacing and len(assigned) == 8
        and len(set(assigned)) == 8
        and set(assigned) == {
            (slot, field)
            for slot in range(4)
            for field in ("+0x078", "+0x07C")
        }
    )
    return {
        "kind": "S002-successful-shot-existing-private-cohort-audit",
        "schema_version": 1,
        "source_game": "RSPE01 Rev1",
        "observed_contact_human": "yes",
        "lead_requested_frames": lead,
        "lead_observed_at_least_requested": observed >= lead,
        "trace_dispatch_complete": True,
        "trace_frames_applied": applied,
        "snapshot_phase_counts": phase_counts,
        "all_samples_within_one_game_frame": all(
            row.get("non_atomic_frame_span") == 0 for row in rows),
        "observed_distance_human": distance,
        "observed_distance_unit_human": label.get("displayed_unit_human"),
        "observed_power_percent_human": label.get("displayed_power_percent_human"),
        "off_green_human": label.get("finished_on_green_human") == "no",
        "distance_may_be_capped_or_censored": (
            label.get("finished_on_green_human") == "no" and distance == 100),
        "candidate_count_recomputed_and_matches_saved": len(records),
        "effect_pointer_bases_spaced_0x90_in_all_phases": effect_spacing,
        "repeating_two_word_effect_pairs_observed": complete_slot_pairs,
        "repeated_effect_pair_count_if_verified": 4 if complete_slot_pairs else None,
        "effect_stride_interpretation": (
            "source-pointer spacing only; effect entry size and semantics NOT verified"),
        "candidate_temporal_classifications": records,
        "raw_input_values_printed": False,
        "shot_contact_verified_by_memory": False,
        "ball_world_xyz_verified": False,
        "ball_velocity_verified": False,
        "swing_power_verified_by_memory": False,
        "official_distance_verified_by_memory": False,
        "approved_for_training": False,
        "allowed_to_publish": False,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", required=True, help="Safe exact outcome-YYYYMMDDTHHMMSSZ-xxxxxxxx")
    p.add_argument("--data-dir", type=Path, default=DEFAULT_CAPTURES,
                   help="Existing ignored PRIVATE captures directory")
    args = p.parse_args(argv)
    if not RUN_ID.fullmatch(args.run_id):
        p.error("Invalid outcome run ID")
    try:
        folder = _inside_data(args.data_dir)
        raw = _inside_data(folder / (args.run_id + "-RAW-PRIVATE.jsonl"))
        summ = _inside_data(folder / (args.run_id + "-candidates.json"))
        result = audit(_read_raw(raw), _read_one_json(summ, MAX_SUMMARY_BYTES))
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        # Never include private paths, raw words or source JSON in errors.
        print("PRIVATE existing-shot audit failed closed: " + type(exc).__name__,
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
