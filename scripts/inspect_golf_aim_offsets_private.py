"""Read existing private S002 B0-B3 object-window JSON; pinpoint aim-only words.

This is an OFFLINE inspection of a user-chosen game-memory research artifact.
It never launches Dolphin, reads live RAM, writes files, or sends data anywhere.
Values are untyped hypotheses until gameplay/source experiments corroborate them.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import struct
import sys

PHASES = ("idle_baseline", "idle_delayed", "wasd_aim_only", "idle_after_aim")
HEX_WORD = re.compile(r"0x[0-9a-fA-F]{8}\Z")
EXPECTED_KIND = "PRIVATE-golf-source-object-windows-four-phase"
SELECTED_BYTES = 0xCC

# These are *source-connected* fields, not verified game-world semantics.
SOURCE_HINTS = {
    0x24: "candidate untyped state word (no-shot zero)",
    0x54: "record translation copy component 0",
    0x58: "record translation copy component 1",
    0x5C: "record translation copy component 2",
    0x60: "record position candidate component 0",
    0x64: "record position candidate component 1",
    0x68: "record position candidate component 2",
    0x88: "source-linked ball-object pointer",
    0xC4: "source-backed allocated subobject pointer",
}


def _words(report: dict, label: str, expected_size: int | None = None) -> list[list[int]]:
    windows = report.get("windows")
    if not isinstance(windows, dict) or label not in windows:
        raise ValueError(f"Missing named game-memory window: {label}")
    window = windows[label]
    if window.get("guest_base_stable") is not True:
        raise ValueError(f"Unstable object address: refusing to compare {label}")
    rows = window.get("all_words_by_phase_hex")
    if not isinstance(rows, list) or len(rows) != 4:
        raise ValueError(f"Expected exactly four source-backed phases for {label}")
    length = window.get("size_bytes")
    if type(length) is not int or length <= 0 or length % 4:
        raise ValueError(f"Invalid named window size: {label}")
    if expected_size is not None and length != expected_size:
        raise ValueError(f"Wrong selected record length: {length}")
    for phase in rows:
        if (not isinstance(phase, list) or len(phase) != length // 4
                or any(not isinstance(w, str) or not HEX_WORD.fullmatch(w)
                       for w in phase)):
            raise ValueError(f"Invalid game words in {label}")
    return [[int(w, 16) for w in phase] for phase in rows]


def _float_guess(bits: int) -> str:
    val = struct.unpack(">f", bits.to_bytes(4, "big"))[0]
    if not math.isfinite(val):
        return "nonfinite"
    # Don't misrepresent pointers and small integer/bit flags as meaningful floats.
    if val == 0:
        return "0"
    if abs(val) < 1e-6 or abs(val) > 1e6:
        return "unlikely"
    return f"{val:.8g}"


def analyze(report: dict) -> dict:
    if (not isinstance(report, dict)
            or report.get("kind") != EXPECTED_KIND
            or report.get("game_id") != "RSPE01"
            or report.get("revision") != 1
            or report.get("phase_names") != list(PHASES)
            or report.get("selected_slot_and_hole_stable") is not True
            or report.get("model_training_allowed") is not False):
        raise ValueError("Not a verified private RSPE01 Rev1 B0-B3 object report")
    records = _words(report, "player_record_0", SELECTED_BYTES)
    main = _words(report, "main")
    rows = []
    for index, values in enumerate(zip(*records)):
        v0, v1, v2, v3 = values
        idle_before = v0 != v1
        aim = v1 != v2
        idle_after = v2 != v3
        if not (idle_before or aim or idle_after):
            continue
        classification = (
            "aim-only candidate" if aim and not idle_before and not idle_after
            else "aim+idle confound" if aim else "idle/background"
        )
        rows.append({
            "offset": index * 4,
            "offset_hex": f"+0x{index * 4:03X}",
            "b0": f"0x{v0:08X}",
            "b1": f"0x{v1:08X}",
            "b2": f"0x{v2:08X}",
            "b3": f"0x{v3:08X}",
            "idle_before_changed": idle_before,
            "aim_changed": aim,
            "idle_after_changed": idle_after,
            "class": classification,
            "b1_possible_f32": _float_guess(v1),
            "b2_possible_f32": _float_guess(v2),
            "source_hint": SOURCE_HINTS.get(index * 4, "untyped"),
        })
    main_changed = [
        f"+0x{i * 4:03X}" for i, words in enumerate(zip(*main))
        if len(set(words)) > 1
    ]
    return {
        "selected_record_changed_offsets": rows,
        "aim_changed_count": sum(x["aim_changed"] for x in rows),
        "aim_only_count": sum(x["class"] == "aim-only candidate" for x in rows),
        "main_changed_offsets": main_changed,
        "training_allowed": False,
        "ball_motion_verified": False,
    }


def format_results(results: dict) -> str:
    rows = results["selected_record_changed_offsets"]
    lines = [
        "S002 B0-B3 SELECTED PLAYER RECORD +0xCC WORD DIFF",
        "Phases: B0 idle | B1 delayed idle | B2 WASD aim | B3 after aim",
        "AIM-only candidate means unchanged in both idle controls; NOT proof of aiming semantics.",
        f"Selected record: {results['aim_changed_count']} changing words during B1->B2; "
        f"{results['aim_only_count']} unique to aim-only transition",
        "RPGolMain changing offsets across four phases: " +
            (", ".join(results["main_changed_offsets"]) or "(none)"),
        "",
        "Offset  B0          B1          B2          B3          Id0 Aim Id1  Class",
    ]
    for r in rows:
        marks = ["Y" if r[k] else "-" for k in
                 ("idle_before_changed", "aim_changed", "idle_after_changed")]
        lines.append(
            f"{r['offset_hex']:7} {r['b0']:10}  {r['b1']:10}  {r['b2']:10}  "
            f"{r['b3']:10}  {marks[0]:>3} {marks[1]:>3} {marks[2]:>3}  {r['class']}"
        )
    lines.append("")
    lines.append("Possible big-endian f32 B1 -> B2 (do NOT assume every u32 is a float):")
    for r in rows:
        if r["aim_changed"]:
            lines.append(
                f"  {r['offset_hex']}: {r['b1_possible_f32']} -> "
                f"{r['b2_possible_f32']} | {r['source_hint']}"
            )
    lines.extend([
        "",
        "Interpretation: record position/rotation/aim is UNKNOWN without source "
        "callsite and an independent game-observed control.",
        "No game action, memory modification, file output or automatic publication occurred.",
    ])
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", required=True, type=Path,
                   help="Existing golf-object-windows-PRIVATE.json file")
    args = p.parse_args(argv)
    try:
        if not args.report.is_file() or args.report.is_symlink():
            raise ValueError("Missing or linked private input file")
        # Require user-selected preserved game-memory study in ignored sibling.
        root = (Path(__file__).resolve().parents[2] / "Wii-AI-Golf-Data").resolve(
            strict=True)
        source = args.report.resolve(strict=True)
        if not source.is_relative_to(root) or source.stat().st_size > 512_000:
            raise ValueError("Report outside ignored private game-memory root")
        data = json.loads(source.read_text(encoding="utf-8"))
        print(format_results(analyze(data)))
        return 0
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        print("Private aim offset inspection stopped:", str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
