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
MAX_SNAPSHOT_FRAMES = 12


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
            "Unlabeled transitions and per-frame counters may confound."
        ),
    }


def read_private_capture(path: Path, *, private_dir: Path = PRIVATE_CAPTURES) -> list[dict]:
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
    paths.add_argument("--input", type=Path,
                       help="Canonical private S002 golfer JSONL in sibling Data/captures")
    args = parser.parse_args(argv)
    try:
        path = find_latest_private(PRIVATE_CAPTURES) if args.latest else args.input
        print(json.dumps(analyze_records(read_private_capture(path)),
                         indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError):
        # Never include exception text: may contain private file path/contents.
        print("Offline null-control audit failed; check local private capture format.",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
