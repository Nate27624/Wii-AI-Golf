#!/usr/bin/env python3
"""PRIVATE-only re-interpretation of existing S002 #178 Golf source-object JSON.

Reads the *already captured* four-phase object-window report, not Dolphin, RAM,
or a new memory atlas. Counts source-linked changes in current ball vectors,
position caches, tee controls, and player records, without publishing values.
This tool DOES NOT prove moving ball, vertical velocity, frame timing, or XYZ.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

PHASES = ("B0", "B1", "B2", "B3")
VECTOR_KEYS = ("selected_ball", "selected_start", "selected_record_plus_054",
               "selected_record_plus_060", "selected_pin")
BALL_TRIPLETS = {"current_translation_030": 0x030,
                 "initialization_or_history_cc": 0x0CC,
                 "conditional_cache_f0": 0x0F0,
                 "conditional_cache_fc": 0x0FC}
WORD = re.compile(r"^0x[0-9A-Fa-f]{8}$")
GAME_KIND = "PRIVATE-golf-source-object-windows-four-phase"


class InvalidStudy(ValueError):
    pass


def _words(words: object, expected: int | None = None) -> list[str]:
    if not isinstance(words, list) or (expected is not None and len(words) != expected):
        raise InvalidStudy("unexpected word-list shape")
    if not all(isinstance(w, str) and WORD.fullmatch(w) for w in words):
        raise InvalidStudy("invalid 32-bit game word")
    return [x.upper() for x in words]


def counts(phase_words: list[list[str]]) -> list[int]:
    if len(phase_words) != 4 or len({len(x) for x in phase_words}) != 1:
        raise InvalidStudy("expected four equally sized phases")
    return [sum(x != y for x, y in zip(a, b))
            for a, b in zip(phase_words, phase_words[1:])]


def safe_object_summary(report: dict) -> dict:
    """No raw values, guest pointers, filenames or session-local identifiers."""
    if not isinstance(report, dict) or report.get("kind") != GAME_KIND:
        raise InvalidStudy("not an S002 source-object-window four-phase JSON")
    if (report.get("schema_version") != 1 or report.get("game_id") != "RSPE01"
            or report.get("revision") != 1 or report.get("phase_names") != list(PHASES)):
        raise InvalidStudy("unexpected game revision or phase provenance")
    window_data = report.get("windows")
    phase_vectors = report.get("vec3_by_phase")
    if not isinstance(window_data, dict) or not isinstance(phase_vectors, list) or len(phase_vectors) != 4:
        raise InvalidStudy("missing source-window or source-vec3 evidence")

    vectors = {}
    for key in VECTOR_KEYS:
        rows = []
        for phase in phase_vectors:
            if not isinstance(phase, dict):
                raise InvalidStudy("invalid source vector phase")
            val = phase.get(key)
            if key == "selected_pin" and val is None:
                continue
            if not isinstance(val, dict):
                raise InvalidStudy("missing required source vector " + key)
            rows.append(_words(val.get("word_u32_hex"), 3))
        if len(rows) == 4:
            vectors[key] = counts(rows)
        elif key != "selected_pin" or len(rows) != 0:
            raise InvalidStudy("partial source vector across phases")

    controls = {}
    ball_objects = {}
    player_records = {}
    names = [f"ball_object_{i}" for i in range(4)] + [
        f"player_record_{i}" for i in range(4)] + ["selected_start", "selected_pin"]
    for name in names:
        if name == "selected_pin" and name not in window_data:
            continue
        obj = window_data.get(name)
        if not isinstance(obj, dict) or obj.get("guest_base_stable") is not True:
            raise InvalidStudy("source object missing or relocated: " + name)
        size = obj.get("size_bytes")
        if type(size) is not int or size <= 0 or size % 4 or size > 0x1AC:
            raise InvalidStudy("object size invalid: " + name)
        words = obj.get("all_words_by_phase_hex")
        if not isinstance(words, list) or len(words) != 4:
            raise InvalidStudy("expected four per-object word vectors")
        rows = [_words(w, size // 4) for w in words]
        changes = counts(rows)
        if name.startswith("ball_object_"):
            if size < 0x108:
                raise InvalidStudy("ball cache window too short")
            cache = {}
            for label, off in BALL_TRIPLETS.items():
                trip = [w[off // 4:off // 4 + 3] for w in rows]
                if any(len(x) != 3 for x in trip):
                    raise InvalidStudy("incomplete source ball cache")
                cache[label] = counts(trip)
            ball_objects[name] = {"total_changed_words_by_transition": changes,
                                  "triplet_component_changes_by_transition": cache}
        elif name.startswith("player_record_"):
            player_records[name] = {"total_changed_words_by_transition": changes}
        else:
            controls[name] = changes

    # Existing S002 report does not persist source-selected slot index: do NOT
    # automatically treat ball_object_0 as the active ball.
    return {
        "kind": "PRIVATE-sanitized-existing-source-object-phase-triage",
        "phase_labels": list(PHASES),
        "source_game_revision_checked": True,
        "all_bank_pairs_distinct_reported": report.get("all_bank_pairs_distinct") is True,
        "selected_slot_and_hole_stable_reported": report.get("selected_slot_and_hole_stable") is True,
        "source_selected_vector_component_changes": vectors,
        "source_start_pin_window_word_changes": controls,
        "ball_object_window_changes_and_cache_components": ball_objects,
        "player_record_window_word_changes": player_records,
        "selected_ball_vs_start_same_words_in_all_phases": all(
            phase["selected_ball"]["word_u32_hex"] == phase["selected_start"]["word_u32_hex"]
            for phase in phase_vectors),
        "does_not_identify_selected_ball_object_slot": True,
        "capture_labels_independently_verified": False,
        "guest_frame_atomicity_verified": False,
        "physical_ball_movement_verified": False,
        "vertical_velocity_verified": False,
        "training_allowed": False,
        "publication_allowed": False,
        "note": "Only source-relative change counts and equality controls; no vectors or heap addresses. B0-B3 were labeled no-shot/aim controls, not independently matched to a moving-ball JSON."
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-json", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        path = args.private_json
        # Read only known local PRIVATE study record; never ingest repo files.
        if (path.name != "golf-object-windows-PRIVATE.json"
                or path.parent.name != "ball-study-20261027-212633"
                or path.parent.parent.name != "Wii-AI-Golf-Data"
                or path.is_symlink() or path.stat().st_size > 8 * 1024 * 1024):
            raise InvalidStudy("not the expected local private study JSON or file over size limit")
        report = json.loads(path.read_text(encoding="utf-8-sig"))
        result = safe_object_summary(report)
    except (OSError, InvalidStudy, TypeError, ValueError, KeyError) as exc:
        print("ABORT: invalid private source-object study or incomplete phase evidence", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
