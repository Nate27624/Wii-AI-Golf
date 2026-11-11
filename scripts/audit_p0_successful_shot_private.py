"""Offline P0 successful-shot RAM triage; prints only sanitized source-relative evidence.

The raw 8-sample JSONL and the unsanitized saved candidates JSON NEVER leave
the user's ignored sibling Wii-AI-Golf-Data/captures directory. No emulator,
input, network, memory writes, or automatic GitHub publication.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOT = ROOT.parent / "Wii-AI-Golf-Data" / "captures"
ALLOWED = {
    "golf_config": (0x1C74, "configuration_or_game_state"),
    "golf_field": (0xA8, "environment_reference_or_state"),
    "sports_sequence": (0xD0, "sequence_or_timing_confound"),
    "minimap_ball_effect": (0x200, "visual_effect_confound"),
    "minimap_player_effect": (0x200, "visual_effect_confound"),
    "minimap_shot_line_effect": (0x200, "visual_effect_confound"),
}
KNOWN = {
    ("golf_config", 0x94): "game_mode_raw_not_power",
    ("golf_config", 0x98): "hole_index_raw_not_shot_power",
    ("golf_field", 0x44): "selected_pin_reference_not_xyz",
    ("golf_field", 0x50): "selected_start_reference_not_ball_xyz",
    ("golf_field", 0x54): "cup_reference_not_distance",
    ("golf_field", 0x68): "wind_object_reference_not_wind_speed",
    ("golf_field", 0x70): "course_object_reference_not_terrain",
    ("golf_field", 0x18): "map_data_reference_not_height",
}
_HEXADDR = re.compile(r"0x[0-9A-Fa-f]{8}$")
_MAX_BYTES = 6 * 1024 * 1024
_MAX_ROWS = 60


def _addr(value: object) -> int:
    if not isinstance(value, str) or not _HEXADDR.fullmatch(value):
        raise ValueError("Invalid guest address encoding")
    address = int(value, 16)
    if not (0x80000000 <= address < 0x81800000 or
            0x90000000 <= address < 0x94000000):
        raise ValueError("Unsupported guest memory region")
    return address


def _pointer_like(bits: object) -> bool:
    return type(bits) is int and (
        0x80000000 <= bits < 0x81800000 or 0x90000000 <= bits < 0x94000000
    )


def audit(summary: dict, rows: list[dict]) -> dict:
    """Validate private phase samples against saved candidate ranking; redact output."""
    if not isinstance(summary, dict) or not isinstance(rows, list) or not 1 <= len(rows) <= _MAX_ROWS:
        raise ValueError("Invalid private capture")
    ranking = summary.get("candidate_ranking")
    if not isinstance(ranking, dict) or not isinstance(ranking.get("candidates"), list):
        raise ValueError("Missing candidate ranking")
    if ranking.get("candidates_truncated") is True:
        raise ValueError("Truncated candidate ranking")
    candidates = ranking["candidates"]
    if not (len(candidates) <= 80 and ranking.get("all_phase_stable_change_count") == len(candidates)):
        raise ValueError("Ranking count mismatch")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("Malformed raw phase sample")
    phases = [row.get("phase") for row in rows]
    order = {"pre": 0, "post": 1, "settled": 2}
    if any(phase not in order for phase in phases):
        raise ValueError("Unknown snapshot phase")
    if phases != sorted(phases, key=order.get):
        raise ValueError("Non-chronological snapshot phases")
    counts = {phase: phases.count(phase) for phase in order}
    if any(count < 2 for count in counts.values()):
        raise ValueError("Insufficient PRE or SETTLED controls")
    if any(ranking.get(phase + "_samples") != counts[phase] for phase in order):
        raise ValueError("Summary/raw phase counts mismatch")
    if ranking.get("sample_count") != len(rows):
        raise ValueError("Sample count mismatch")

    spans = []
    decoded = []
    for row in rows:
        if row.get("game_id") != "RSPE01" or row.get("disc_revision") != 1 or row.get("game_mode_raw") != 4:
            raise ValueError("Wrong disc revision/game mode")
        start, end = row.get("frame_start"), row.get("frame_end")
        if type(start) is not int or type(end) is not int or not 0 <= start <= end:
            raise ValueError("Malformed frame bracket")
        spans.append(end - start)
        windows = row.get("windows")
        if not isinstance(windows, dict) or not windows or not set(windows).issubset(ALLOWED):
            raise ValueError("Unrecognized private window")
        word_windows = {}
        for name, item in windows.items():
            if not isinstance(item, dict) or not isinstance(item.get("bytes_hex"), str):
                raise ValueError("Malformed raw window")
            base = _addr(item.get("address"))
            expected_size, _ = ALLOWED[name]
            if base % 4 or len(item["bytes_hex"]) != 2 * expected_size:
                raise ValueError("Source window bounds/size mismatch")
            raw = bytes.fromhex(item["bytes_hex"])
            word_windows[name] = (base, raw)
        if sum(len(raw) for _, raw in word_windows.values()) > 12 * 1024:
            raise ValueError("Capture too large")
        decoded.append(word_windows)

    result = []
    for i, item in enumerate(candidates, 1):
        if not isinstance(item, dict):
            raise ValueError("Malformed candidate")
        absolute_address = _addr(item.get("address"))
        names = item.get("windows")
        if not isinstance(names, list) or not names or not set(names).issubset(ALLOWED):
            raise ValueError("Unknown candidate window")
        relative_locations = []
        for name in sorted(set(names)):
            positions = []
            for row in rows:
                item_window = row["windows"].get(name)
                if item_window is None:
                    continue
                base = _addr(item_window.get("address"))
                size, family = ALLOWED[name]
                if base <= absolute_address < base + size and (absolute_address - base) % 4 == 0:
                    positions.append(absolute_address - base)
            if len(positions) != len(rows) or len(set(positions)) != 1:
                raise ValueError("Candidate source window moved or vanished")
            offset = positions[0]
            relative_locations.append({
                "window": name,
                "relative_word_offset": f"+0x{offset:03X}",
                "triage_family": ALLOWED[name][1],
                "source_field_hint": KNOWN.get((name, offset), "untyped_change"),
            })
        before, after = item.get("before"), item.get("settled")
        if not isinstance(before, dict) or not isinstance(after, dict):
            raise ValueError("Missing candidate before/settled data")
        observed = []
        for window_data in decoded:
            values = []
            for base, raw in window_data.values():
                if base <= absolute_address <= base + len(raw) - 4 and (absolute_address - base) % 4 == 0:
                    values.append(struct.unpack_from(">I", raw, absolute_address - base)[0])
            if not values or len(set(values)) != 1:
                raise ValueError("Candidate word missing/conflicting")
            observed.append(values[0])
        pre = [word for word, phase in zip(observed, phases) if phase == "pre"]
        post = [word for word, phase in zip(observed, phases) if phase == "post"]
        settled = [word for word, phase in zip(observed, phases) if phase == "settled"]
        if (len(set(pre)) != 1 or len(set(settled)) != 1
                or pre[0] == settled[0]
                or pre[0] != before.get("u32") or settled[0] != after.get("u32")
                or sum(word != pre[0] for word in post) != item.get("post_samples_differing_from_pre")
                or len(set(post)) != item.get("post_distinct_values")):
            raise ValueError("Saved ranking disagrees with private sample values")
        matches = item.get("matches_displayed_numeric_label_as", [])
        if not isinstance(matches, list) or not set(matches).issubset({"f32", "s32", "u32"}):
            raise ValueError("Malformed UI numeric coincidence classification")
        result.append({
            "candidate_id": f"C{i:02d}",
            "source_relative_locations": relative_locations,
            "post_samples_differing_from_pre": item.get("post_samples_differing_from_pre"),
            "post_distinct_values": item.get("post_distinct_values"),
            "before_or_after_pointer_shaped": _pointer_like(before.get("u32")) or _pointer_like(after.get("u32")),
            "ui_number_raw_coincidence_types": sorted(set(matches)),
            "gameplay_semantics_verified": False,
            "training_eligible": False,
        })
    human = summary.get("human_observation", {})
    if not isinstance(human, dict):
        raise ValueError("Missing human observation")
    return {
        "kind": "P0_PRIVATE_OUTCOME_SOURCE_RELATIVE_TRIAGE",
        "source": "offline_private_saved_S002_prepostsettled",
        "phase_samples": counts,
        "non_atomic_snapshot_span_max_frames": max(spans),
        "human_contact_yes": human.get("contact_human") == "yes",
        "human_green_yes": human.get("finished_on_green_human") == "yes",
        "stored_persistent_candidate_count": len(result),
        "candidates": result,
        "not_covered_by_this_snapshot": [
            "source_selected_player_record_51_words",
            "player_record_plus_0x024_lifecycle",
            "selected_ball_object_translation_and_cache",
            "frame_aligned_club_motion_or_power",
            "contact_frame_and_initial_ball_velocity",
        ],
        "verified_ball_xyz": False,
        "verified_power": False,
        "verified_distance_score": False,
        "model_training_allowed": False,
    }


def _private_path(value: str) -> Path:
    requested = Path(value)
    if requested.is_symlink():
        raise ValueError("Linked evidence path refused")
    path = requested.resolve(strict=True)
    root = PRIVATE_ROOT.resolve(strict=True)
    if path.parent != root or not path.is_file() or path.stat().st_size > _MAX_BYTES:
        raise ValueError("Evidence must be a bounded local ignored private capture")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--raw", required=True)
    args = parser.parse_args(argv)
    try:
        summary_path, raw_path = _private_path(args.summary), _private_path(args.raw)
        if not raw_path.name.endswith("-RAW-PRIVATE.jsonl") or not summary_path.name.endswith("-candidates.json"):
            raise ValueError("Unexpected capture filenames")
        prefix = summary_path.name[:-len("-candidates.json")]
        if raw_path.name != prefix + "-RAW-PRIVATE.jsonl":
            raise ValueError("Capture names mismatch")
        with summary_path.open("r", encoding="utf-8") as stream:
            summary = json.load(stream)
        with raw_path.open("r", encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream if line.strip()]
        print(json.dumps(audit(summary, rows), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        # No exception message: could otherwise expose guest pointers or paths.
        print(f"P0 private audit refused ({type(exc).__name__}). No files modified.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
