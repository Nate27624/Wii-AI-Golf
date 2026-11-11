"""S002-GOLFER-NULL-01: offline falsification of candidate main+0x74.

Only reads previously captured private S002 #129 golfer JSONL. No Dolphin,
controller, network, repository publishing, memory RPC, or file mutation.
Public stdout contains counts/relative offsets, NEVER memory bytes, pointer
values, file names/paths, or per-capture IDs.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_CAPTURES = ROOT.parent / "Wii-AI-Golf-Data" / "captures"
NAME_PATTERN = re.compile(r"golfer-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}-RAW-PRIVATE[.]jsonl\Z")
PRIVATE_POINTER = re.compile(r"0x[89][0-9A-Fa-f]{7}\Z")
WORD_OFFSET = 0x74
MAIN_BYTES = 0x100
MAX_ROWS = 60
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_SNAPSHOT_FRAMES = 240  # source #129 and peer #135 capture contract
HIGH_RES_MAX_FRAMES = 12    # values above this require caution about timing
# Explicit fixed error vocabulary; never publish private filenames, RAM values,
# usernames, runtime heap pointers or third-party error strings.
SAFE_ERROR_REASONS = frozenset({
    "missing or symbolic-link private capture",
    "capture must be canonical private S002 golfer JSONL",
    "capture file outside bounded input size",
    "invalid private JSONL content",
    "too many private capture snapshots",
    "private capture directory missing",
    "no private S002 golfer capture found",
    "need between 4 and 60 captured snapshots",
    "raw capture row must be a JSON object",
    "invalid capture stage",
    "unsupported control phase (no live-swing inference)",
    "invalid or excessive non-atomic frame span",
    "unexpected candidate main window size",
    "invalid private snapshot bytes",
    "invalid main word count",
    "missing source-capture object identity",
    "scene or candidate object changed during capture",
    "control stage must start at zero",
    "non-contiguous or out-of-order stages",
    "frame rollback or overlapping observations",
    "expected idle -> aim_only -> optional idle sequence",
    "missing repeated or correctly labeled control stages",
    "non-increasing within-stage frame count",
    "missing required candidate child windows",
    "invalid child window provenance",
    "invalid candidate child bytes",
    "candidate child identity changed during capture",
    "no compatible private four-child capture found",
})


def _row(item: object) -> dict:
    if not isinstance(item, dict):
        raise ValueError("raw capture row must be a JSON object")
    stage, phase = item.get("stage"), item.get("phase")
    a, b = item.get("frame_start"), item.get("frame_end")
    if type(stage) is not int or not 0 <= stage <= 2:
        raise ValueError("invalid capture stage")
    if phase not in ("idle", "aim_only"):
        raise ValueError("unsupported control phase (no live-swing inference)")
    if (type(a) is not int or type(b) is not int
            or not 0 <= a <= b <= 2_000_000_000 or b - a > MAX_SNAPSHOT_FRAMES):
        raise ValueError("invalid or excessive non-atomic frame span")
    raw = item.get("bytes_hex")
    if type(raw) is not str or len(raw) != MAIN_BYTES * 2:
        raise ValueError("unexpected candidate main window size")
    try:
        main = bytes.fromhex(raw)
    except ValueError:
        raise ValueError("invalid private snapshot bytes") from None
    if len(main) != MAIN_BYTES:
        raise ValueError("invalid main word count")
    pointers = (item.get("runtime_scene_address"),
                item.get("runtime_golf_main_address"))
    if not all(isinstance(x, str) and PRIVATE_POINTER.fullmatch(x) for x in pointers):
        raise ValueError("missing source-capture object identity")
    return {
        "stage": stage,
        "phase": phase,
        "start": a,
        "end": b,
        "candidate_word": struct.unpack_from(">I", main, WORD_OFFSET)[0],
        "private_identity": pointers,
    }


def analyze_records(records: list[object]) -> dict:
    if not isinstance(records, list) or not 4 <= len(records) <= MAX_ROWS:
        raise ValueError("need between 4 and 60 captured snapshots")
    observations = [_row(x) for x in records]
    stages = defaultdict(list)
    identity = observations[0]["private_identity"]
    previous = None
    for item in observations:
        if item["private_identity"] != identity:
            raise ValueError("scene or candidate object changed during capture")
        stage = item["stage"]
        if previous is None and stage != 0:
            raise ValueError("control stage must start at zero")
        if previous is not None:
            if stage < previous["stage"] or stage > previous["stage"] + 1:
                raise ValueError("non-contiguous or out-of-order stages")
            if item["start"] < previous["end"]:
                raise ValueError("frame rollback or overlapping observations")
        stages[stage].append(item)
        previous = item
    expected = {0: "idle", 1: "aim_only", 2: "idle"}
    if 0 not in stages or 1 not in stages or set(stages) not in ({0, 1}, {0, 1, 2}):
        raise ValueError("expected idle -> aim_only -> optional idle sequence")
    if any(len(rows) < 2 or any(x["phase"] != expected[k] for x in rows)
           for k, rows in stages.items()):
        raise ValueError("missing repeated or correctly labeled control stages")

    groups = {}
    total = 0
    idle_changes = 0
    aim_changes = 0
    exact_frame_steps = 0
    for stage in sorted(stages):
        rows = stages[stage]
        changes = 0
        same_delta_as_frames = 0
        nonzero_step = 0
        for earlier, later in zip(rows, rows[1:]):
            # Use frame_start spacing, NOT sample count as assumed time.
            frames = later["start"] - earlier["start"]
            if frames <= 0:
                raise ValueError("non-increasing within-stage frame count")
            delta = (later["candidate_word"] - earlier["candidate_word"]) & 0xFFFFFFFF
            if delta:
                changes += 1
            if delta == frames:
                same_delta_as_frames += 1
            if 0 < delta <= frames * 4:
                nonzero_step += 1
        opportunities = len(rows) - 1
        groups[str(stage)] = {
            "phase": expected[stage],
            "observations": len(rows),
            "within_stage_comparison_opportunities": opportunities,
            "changed_pairs_at_main_plus_0x74": changes,
            "u32_step_equal_to_elapsed_frame_delta_pairs": same_delta_as_frames,
            "positive_step_at_most_4_per_frame_pairs": nonzero_step,
            "snapshot_frame_span_max": max(x["end"] - x["start"] for x in rows),
        }
        total += opportunities
        exact_frame_steps += same_delta_as_frames
        if expected[stage] == "idle":
            idle_changes += changes
        else:
            aim_changes += changes

    if idle_changes:
        conclusion = "changes_during_idle_refutes_exclusive_swing_event_indicator"
    elif aim_changes:
        conclusion = "changes_only_during_pointer_control_not_verified_power"
    else:
        conclusion = "no_observed_control_change_inconclusive"

    return {
        "schema_version": 1,
        "kind": "offline_golfer_main_0x74_null_control",
        "study_id": "S002-GOLFER-NULL-01",
        "candidate_region": "main",
        "candidate_relative_offset": "+0x074",
        "raw_input_kept_private": True,
        "sample_count": len(observations),
        "independent_sessions_verified": False,
        "human_pointer_action_verified_by_sensor": False,
        "wii_revision_reverified_from_saved_rows": False,
        "snapshots_bracketed_by_emulator_frames": True,
        "max_non_atomic_frame_span": max(x["end"] - x["start"] for x in observations),
        "timing_limited": any(x["end"] - x["start"] > HIGH_RES_MAX_FRAMES
                              for x in observations),
        "frame_delta_relation_is_exploratory": True,
        "stage_results": groups,
        "within_stage_total_opportunities": total,
        "within_idle_changed_pairs": idle_changes,
        "within_pointer_only_changed_pairs": aim_changes,
        "frame_step_equal_pairs": exact_frame_steps,
        "candidate_exclusive_swing_event_indicator_supported": False,
        "game_power_field_verified": False,
        "club_pose_verified": False,
        "null_control_conclusion": conclusion,
        "warning": (
            "One source-gated candidate object, repeated snapshots within one "
            "capture; not independent swing trials. Changes while idle falsify "
            "exclusive swing-event specificity, not every possible power "
            "encoding. Pointer-only is an operator label, not sensor proof. "
            "Unlabeled transitions and per-frame counters may confound. "
            "Non-atomic windows over 12 frames are timing-limited; a "
            "matching u32 frame delta is never a verified game clock."
        ),
    }



# Four PREDECLARED words identified independently by the public #135/#137
# control study. Parent-child addresses come only from private raw captures.
# These keys are structure-relative labels; NOT absolute runtime pointers.
FOUR_WORDS = (
    ("main", None, 0x74),
    ("child_at_main+0x008", "+0x008", 0x50),
    ("child_at_main+0x020", "+0x020", 0x38),
    ("child_at_main+0x044", "+0x044", 0x60),
)


def _four_word_row(raw: object) -> dict:
    base = _row(raw)
    assert isinstance(raw, dict)  # _row has already validated
    windows = raw.get("child_windows")
    pointers = raw.get("watched_child_addresses")
    if not isinstance(windows, dict) or not isinstance(pointers, dict):
        raise ValueError("missing required candidate child windows")
    if len(windows) > 16 or len(pointers) > 16 or set(windows) != set(pointers):
        raise ValueError("invalid child window provenance")
    words = {"main": base["candidate_word"]}
    identities = {}
    for label, key, offset in FOUR_WORDS[1:]:
        encoded = windows.get(key)
        pointer = pointers.get(key)
        if not isinstance(encoded, str) or len(encoded) != 0x80 * 2:
            raise ValueError("missing required candidate child windows")
        if not isinstance(pointer, str) or PRIVATE_POINTER.fullmatch(pointer) is None:
            raise ValueError("invalid child window provenance")
        try:
            window = bytes.fromhex(encoded)
        except ValueError:
            raise ValueError("invalid candidate child bytes") from None
        if len(window) != 0x80:
            raise ValueError("invalid candidate child bytes")
        words[label] = struct.unpack_from(">I", window, offset)[0]
        identities[label] = pointer
    base["words"] = words
    base["child_identity"] = identities
    return base


def analyze_four_word_clock(records: list[object]) -> dict:
    """Compare exact predeclared child/main u32 deltas with observed frame gaps.

    Pair comparisons NEVER cross human-labelled stage boundaries.
    A matching value/frame difference is exploratory, not source proof
    of time or power; sampling-cadence lag control guards false certainty.
    """
    parent = analyze_records(records)  # independent privacy/sequence gates
    values = [_four_word_row(row) for row in records]
    identity = values[0]["child_identity"]
    if any(row["child_identity"] != identity for row in values):
        raise ValueError("candidate child identity changed during capture")

    by_stage = defaultdict(list)
    for v in values:
        by_stage[v["stage"]].append(v)

    # Private intermediate arithmetic is never returned or logged.
    all_gaps = []
    stage_results = {}
    totals = {name: {"changed_pairs": 0, "matches_elapsed_frames": 0,
                     "matches_main_delta": 0, "matches_shifted_frame_gaps": 0,
                     "shifted_control_opportunities": 0}
              for name, _, _ in FOUR_WORDS}
    all_four_changed = 0
    all_four_followed_frames = 0
    for stage, rows in sorted(by_stage.items()):
        comparisons = []
        for early, late in zip(rows, rows[1:]):
            gap = late["start"] - early["start"]
            if gap <= 0:
                raise ValueError("non-increasing within-stage frame count")
            deltas = {
                name: (late["words"][name] - early["words"][name]) & 0xFFFFFFFF
                for name, _, _ in FOUR_WORDS
            }
            comparisons.append((gap, deltas))
            all_gaps.append(gap)
            if all(x != 0 for x in deltas.values()):
                all_four_changed += 1
            if all(delta == gap for delta in deltas.values()):
                all_four_followed_frames += 1
        stage_fields = {}
        for name, _, _ in FOUR_WORDS:
            changed = sum(d[name] != 0 for _, d in comparisons)
            exact_frame = sum(d[name] == gap for gap, d in comparisons)
            main_equal = sum(d[name] == d["main"] for _, d in comparisons)
            # Adjacent-next interval is a NEGATIVE alignment control. When
            # every frame gap is identical, it matches as well (uninformative).
            shifted = sum(d[name] == next_gap for (_, d), (next_gap, _) in
                          zip(comparisons, comparisons[1:]))
            shifted_n = max(0, len(comparisons) - 1)
            stage_fields[name] = {
                "changed_pairs": changed,
                "matches_elapsed_frames": exact_frame,
                "matches_main_delta": main_equal if name != "main" else None,
                "matches_shifted_frame_gaps": shifted,
                "shifted_control_opportunities": shifted_n,
            }
            acc = totals[name]
            acc["changed_pairs"] += changed
            acc["matches_elapsed_frames"] += exact_frame
            acc["matches_main_delta"] += main_equal if name != "main" else 0
            acc["matches_shifted_frame_gaps"] += shifted
            acc["shifted_control_opportunities"] += shifted_n
        stage_results[str(stage)] = {
            "phase": rows[0]["phase"],
            "samples": len(rows),
            "within_stage_comparisons": len(comparisons),
            "distinct_frame_step_values": len({gap for gap, _ in comparisons}),
            "fields": stage_fields,
        }
    gaps_vary = len(set(all_gaps)) >= 2
    total_pairs = parent["within_stage_total_opportunities"]
    return {
        "schema_version": 1,
        "kind": "offline_four_golfer_words_vs_emulated_frames",
        "study_id": "S002-GOLFER-FOUR-CLOCK-02",
        "sample_count": len(values),
        "within_stage_comparison_opportunities": total_pairs,
        "distinct_observed_frame_step_values": len(set(all_gaps)),
        "varied_frame_cadence_observed": gaps_vary,
        "all_four_fields_changed_pairs": all_four_changed,
        "all_four_fields_match_elapsed_frames_pairs": all_four_followed_frames,
        "max_non_atomic_frame_span": parent["max_non_atomic_frame_span"],
        "timing_limited": parent["timing_limited"],
        "fields": [{
            "region": name,
            "relative_offset": f"+0x{offset:03X}",
            "within_stage_opportunities": total_pairs,
            "changed_pairs": totals[name]["changed_pairs"],
            "matches_elapsed_frames": totals[name]["matches_elapsed_frames"],
            "matches_main_delta": (
                totals[name]["matches_main_delta"] if name != "main" else None),
            "matches_shifted_frame_gaps": totals[name]["matches_shifted_frame_gaps"],
            "shifted_control_opportunities": totals[name]["shifted_control_opportunities"],
            "field_identity_verified": False,
            "power_verified": False,
        } for name, _, offset in FOUR_WORDS],
        "stage_results": stage_results,
        "raw_input_kept_private": True,
        "independent_sessions_verified": False,
        "runtime_scene_and_child_identity_stable_in_saved_rows": True,
        "wii_revision_reverified_from_saved_rows": False,
        "club_pose_verified": False,
        "game_power_field_verified": False,
        "ball_state_verified": False,
        "warning": (
            "Offline comparisons of one candidate capture; NOT independent "
            "swings or confirmed counters. Identical fixed sampling cadence "
            "can make both correct and shifted-frame matches high; varying "
            "frame gaps and negative alignment controls are essential. "
            "Child windows are non-atomic; sensor labels and class meanings "
            "are not independently verified. No private RAM is published."
        ),
    }


def find_latest_four_private(private_dir: Path) -> Path:
    """Select latest existing canonical file containing all three child windows.

    Bounded private inspection of first line only. File names and contents
    are never printed; full capture gates still apply once selected.
    """
    if not private_dir.is_dir():
        raise ValueError("private capture directory missing")
    files = sorted((p for p in private_dir.glob("golfer-*-RAW-PRIVATE.jsonl")
                    if p.is_file() and not p.is_symlink()
                    and NAME_PATTERN.fullmatch(p.name)), reverse=True)
    for path in files[:100]:
        if not 0 < path.stat().st_size <= MAX_FILE_BYTES:
            continue
        try:
            with path.open("r", encoding="utf-8") as stream:
                line = stream.readline(32769)
            if len(line) > 32768:
                continue
            row = json.loads(line)
            windows = row.get("child_windows") if isinstance(row, dict) else None
            if isinstance(windows, dict) and all(
                    key in windows for _, key, _ in FOUR_WORDS[1:]):
                return path
        except (UnicodeError, ValueError, OSError):
            continue
    raise ValueError("no compatible private four-child capture found")



def read_private_capture(path: Path, *, private_dir: Path | None = None) -> list[dict]:
    private_dir = PRIVATE_CAPTURES if private_dir is None else private_dir
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing or symbolic-link private capture")
    if path.parent.resolve() != private_dir.resolve() or not NAME_PATTERN.fullmatch(path.name):
        raise ValueError("capture must be canonical private S002 golfer JSONL")
    if not 0 < path.stat().st_size <= MAX_FILE_BYTES:
        raise ValueError("capture file outside bounded input size")
    try:
        with path.open("r", encoding="utf-8") as stream:
            records = [json.loads(line) for line in stream]
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError("invalid private JSONL content") from None
    if len(records) > MAX_ROWS:
        raise ValueError("too many private capture snapshots")
    return records


def find_latest_private(private_dir: Path) -> Path:
    if not private_dir.is_dir():
        raise ValueError("private capture directory missing")
    files = sorted((p for p in private_dir.glob("golfer-*-RAW-PRIVATE.jsonl")
                    if p.is_file() and not p.is_symlink()
                    and NAME_PATTERN.fullmatch(p.name)))
    if not files:
        raise ValueError("no private S002 golfer capture found")
    return files[-1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    paths = parser.add_mutually_exclusive_group(required=True)
    paths.add_argument("--latest", action="store_true",
                       help="Use newest private S002 golfer capture (offline, no game)")
    paths.add_argument("--latest-four", action="store_true",
                       help="Use newest private capture with all three pinned child windows")
    paths.add_argument("--input", type=Path,
                       help="Canonical private S002 golfer JSONL in sibling Data/captures")
    parser.add_argument("--four-clock", action="store_true",
                        help="Compare four predeclared words with observed frames")
    args = parser.parse_args(argv)
    try:
        if args.latest_four:
            path = find_latest_four_private(PRIVATE_CAPTURES)
        else:
            path = find_latest_private(PRIVATE_CAPTURES) if args.latest else args.input
        if args.latest_four or args.four_clock:
            report = analyze_four_word_clock(read_private_capture(path))
        else:
            report = analyze_records(read_private_capture(path))
        print(json.dumps(report,
                         indent=2, sort_keys=True, allow_nan=False))
        return 0
    except ValueError as exc:
        # All emitted diagnostics come from a fixed list of locally authored,
        # privacy-reviewed strings. Never echo exceptions from file/JSON APIs.
        reason = str(exc)
        if reason not in SAFE_ERROR_REASONS:
            reason = "private capture did not match the reviewed input schema"
        print("Offline null-control audit failed: " + reason, file=sys.stderr)
        return 1
    except OSError:
        # OS errors can contain real paths, usernames and access details.
        print("Offline null-control audit failed: private capture inaccessible",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
