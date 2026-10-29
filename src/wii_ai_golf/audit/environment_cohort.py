"""Aggregate sanitized S002 environment-candidate reports; never inspect RAM here."""
from __future__ import annotations

from collections import Counter

MIN_FILES = 2
MAX_FILES = 64
PTR_KEYS = ("course", "cup", "map_data", "pin", "start", "wind_object")
FLAG_KEYS = ("green_slope_visible", "minimap_visible", "wind_arrow_visible")


def _plain_int(x: object, lo: int, hi: int) -> bool:
    return type(x) is int and lo <= x <= hi


def summarize_environment_cohort(reports: list[dict]) -> dict:
    """Compare *capture files*, not independent sessions or memory addresses.

    An individual report comes ONLY from audit_environment_snapshots() with
    full source/revision/mode/size checks. This aggregate is not a decoder.
    """
    if type(reports) is not list or not MIN_FILES <= len(reports) <= MAX_FILES:
        raise ValueError("Expected 2..64 bounded environment capture reports")
    hole_counts: Counter[int] = Counter()
    ref_present = Counter()
    ref_changed = Counter()
    flag_all_true = Counter()
    flag_changed = Counter()
    current_hole_transitions = 0
    unstable_counts = Counter()
    pin_counts: list[int] = []
    start_counts: list[int] = []
    max_span = 0
    total_samples = 0
    for report in reports:
        if (type(report) is not dict
            or type(report.get("schema_version")) is not int
            or report.get("schema_version") != 1
            or report.get("kind") != "local-golf-environment-source-candidates"
            or type(report.get("source_candidate_game_mode")) is not int
            or report.get("source_candidate_game_mode") != 4):
            raise ValueError("Unsupported candidate report")
        sample_count = report.get("sample_count")
        frame_span = report.get("max_non_atomic_frame_span")
        if not _plain_int(sample_count, 1, 100) or not _plain_int(frame_span, 0, 240):
            raise ValueError("Invalid capture observations")
        if (report.get("pin_xyz_verified") is not False
            or report.get("ball_xyz_verified") is not False
            or report.get("wind_speed_direction_verified") is not False):
            raise ValueError("Prohibited verified physical-value claim")
        hole = report.get("source_candidate_current_hole_raw")
        changed = report.get("hole_value_changed_in_capture")
        if (type(changed) is not bool
            or (hole is None and not changed)
            or (hole is not None and (not _plain_int(hole, 0, 31) or changed))):
            raise ValueError("Inconsistent source candidate hole report")
        if hole is not None:
            hole_counts[hole] += 1
        if changed:
            current_hole_transitions += 1
        object_counts = report.get("map_object_counts")
        if type(object_counts) is not dict or set(object_counts) != {"pin_count", "start_count"}:
            raise ValueError("Incomplete source object counts")
        for name, dest in (("pin_count", pin_counts), ("start_count", start_counts)):
            count = object_counts[name]
            if (type(count) is not dict or set(count) != {"distinct_values", "first_observed"}
                or not _plain_int(count["distinct_values"], 1, sample_count)
                or not _plain_int(count["first_observed"], 0, 256)):
                raise ValueError("Inconsistent map object count")
            dest.append(count["first_observed"])
            unstable_counts[name] += int(count["distinct_values"] > 1)
        object_refs = report.get("object_refs")
        if type(object_refs) is not dict or set(object_refs) != set(PTR_KEYS):
            raise ValueError("Incomplete source object-reference set")
        for name in PTR_KEYS:
            entry = object_refs[name]
            if (type(entry) is not dict
                or set(entry) != {"present_every_snapshot", "changed_during_capture"}
                or type(entry["present_every_snapshot"]) is not bool
                or type(entry["changed_during_capture"]) is not bool):
                raise ValueError("Invalid pointer stability classification")
            ref_present[name] += int(entry["present_every_snapshot"])
            ref_changed[name] += int(entry["changed_during_capture"])
        flags = report.get("visual_flags")
        if type(flags) is not dict or set(flags) != set(FLAG_KEYS):
            raise ValueError("Incomplete visual source flags")
        for name in FLAG_KEYS:
            entry = flags[name]
            if (type(entry) is not dict
                or set(entry) != {"true_in_all_samples", "changed_during_capture"}
                or type(entry["true_in_all_samples"]) is not bool
                or type(entry["changed_during_capture"]) is not bool):
                raise ValueError("Invalid visual flag classification")
            flag_all_true[name] += int(entry["true_in_all_samples"])
            flag_changed[name] += int(entry["changed_during_capture"])
        total_samples += sample_count
        max_span = max(max_span, frame_span)
    return {
        "kind": "local-golf-environment-candidate-cohort", "schema_version": 1,
        "capture_file_count": len(reports), "independent_sessions_verified": False,
        "total_snapshot_count": total_samples, "max_non_atomic_frame_span": max_span,
        "candidate_hole_file_counts": {str(x): hole_counts[x] for x in sorted(hole_counts)},
        "hole_changed_within_capture_file_count": current_hole_transitions,
        "pin_object_count_first_observed": {"min": min(pin_counts), "max": max(pin_counts),
                                             "distinct_file_values": len(set(pin_counts))},
        "start_object_count_first_observed": {"min": min(start_counts), "max": max(start_counts),
                                               "distinct_file_values": len(set(start_counts))},
        "map_count_changed_within_capture_file_count": {
            k: unstable_counts[k] for k in ("pin_count", "start_count")},
        "reference_present_all_samples_file_count": {k: ref_present[k] for k in PTR_KEYS},
        "reference_changed_within_capture_file_count": {k: ref_changed[k] for k in PTR_KEYS},
        "visual_true_all_samples_file_count": {k: flag_all_true[k] for k in FLAG_KEYS},
        "visual_changed_within_capture_file_count": {k: flag_changed[k] for k in FLAG_KEYS},
        "pin_xyz_verified": False, "ball_xyz_verified": False,
        "wind_speed_direction_verified": False, "course_terrain_verified": False,
        "game_phase_verified": False,
        "warning": ("Files are not proven independent boots; cross-file object addresses are not "
                    "compared. Existing source-layout candidates are not independently validated "
                    "pin/ball positions, wind values or trajectory."),
    }
