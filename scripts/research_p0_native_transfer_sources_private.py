#!/usr/bin/env python3
"""Read-only original Rev1 PPC wind/contact source candidate audit.

Requires original seven-pair SHA gates and the reviewed source preflight
module from PR #454 in the SAME Git checkout. Does not start Dolphin, read
guest-time execution, write files, or publish native code/private paths.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import audit_p0_localops_rev1_study as source

WINDOWS = {
    "wind": (
        (0x8029128C, 0x80291394),
        (0x802B8728, 0x802B8864),
        (0x80298FF0, 0x80299098),
    ),
    "contact": (
        (0x802974B0, 0x8029792C),
        (0x8029F3A8, 0x8029F400),
    ),
}
CALL_TARGETS = {
    "wind": (0x802B8728, 0x802A3894, 0x80298E70),
    "contact": (0x802A39BC, 0x802A38E0, 0x802A39E0, 0x802A3DE4),
}
MAX_OUTPUT = 1900

def direct_bl(pc: int, word: int) -> int | None:
    """Decode PPC direct branch-with-link only, not indirect calls."""
    if (word >> 26) != 18 or not (word & 1):
        return None
    disp = word & 0x03FFFFFC
    if disp & 0x02000000:
        disp -= 0x04000000
    return (disp if word & 2 else pc + disp) & 0xffffffff

def signed16(word: int) -> int:
    off = word & 0xffff
    return off - 0x10000 if off & 0x8000 else off

def analyze_source(stage: str, windows: dict[tuple[int, int], bytes]) -> dict:
    """Bounded PPC lexical signals, NOT an object/receiver or CFG proof."""
    if stage not in WINDOWS:
        raise source.Abstain("UNSUPPORTED_STUDY")
    calls, fields = [], []
    for lo, hi in WINDOWS[stage]:
        block = windows[lo, hi]
        if len(block) != hi - lo or len(block) % 4:
            raise source.Abstain("SOURCE_WINDOW_LENGTH")
        for offset in range(0, len(block), 4):
            pc = lo + offset
            word = struct.unpack_from(">I", block, offset)[0]
            target = direct_bl(pc, word)
            if target in CALL_TARGETS[stage]:
                calls.append((f"0x{pc:08X}", f"0x{target:08X}"))
            opcode = word >> 26
            if opcode in (48, 52):
                displacement = signed16(word)
                wanted = ({-20, -16, 0x30, 0x60, 0x84, 0x88, 0x8C}
                          if stage == "wind"
                          else {0x30, 0x4C, 0x60, 0x78, 0x7C, 0x80, 0x84, 0x88, 0x8C})
                if displacement in wanted:
                    fields.append((f"0x{pc:08X}",
                                   "lfs" if opcode == 48 else "stfs",
                                   (word >> 16) & 31, displacement))
    if len(calls) > 28 or len(fields) > 120:
        raise source.Abstain("RESULT_COUNT_CAP")
    observed = {int(target, 16) for _, target in calls}
    out = {
        "status": "NATIVE_SOURCE_CANDIDATES_ONLY",
        "stage": stage,
        "native_calls": calls[:16],
        "native_call_count": len(calls),
        "target_presence": {f"0x{t:08X}": t in observed for t in CALL_TARGETS[stage]},
        "field_counts": {"lfs": sum(x[1] == "lfs" for x in fields),
                         "stfs": sum(x[1] == "stfs" for x in fields)},
        "field_samples": fields[:14],
        "source_register_receiver_proven": False,
        "same_selected_ball_execution_proven": False,
        "guest_tick_verified": False,
        "native_kcol_collision_parity": False,
        "training_approved": False,
    }
    if stage == "wind":
        out["wind_reaches_selected_ball_velocity"] = "UNKNOWN"
    else:
        out["contact_response_order"] = "UNKNOWN"
        out["query_radius_is_ball_radius"] = "UNPROVEN"
    return out

def qualified_study(stage: str, checkout: Path) -> dict:
    """Full source qualification before and after bounded source reads."""
    if stage not in WINDOWS:
        raise source.Abstain("UNSUPPORTED_STUDY")
    if not source._source_owners():
        raise source.Abstain("PUBLIC_UNIT_MAP")
    ((archive, topology),) = source._find_candidates(checkout)
    before = source._validate_banks(archive)
    if len(before) != 14:
        raise source.Abstain("ORIGINAL_ARCHIVE_INCOMPLETE")
    mem1 = {phase: path for phase, size, path, _ in before
            if size == source.MEM1_SIZE}
    source_windows = source.SOURCE_WINDOWS + WINDOWS[stage]
    snapshots = [source._read_windows(mem1[p], source_windows)
                 for p in (1, 5, 7)]
    if not (snapshots[0] == snapshots[1] == snapshots[2]):
        raise source.Abstain("SOURCE_CODE_PHASE_MISMATCH")
    source._source_gates(lambda pc: source._word(snapshots[0], pc))
    out = analyze_source(stage, snapshots[0])
    after = source._validate_banks(archive)
    if len(after) != 14 or tuple(x[3] for x in after) != tuple(x[3] for x in before):
        raise source.Abstain("ORIGINAL_POST_READ_SHA_MISMATCH")
    out.update({
        "original_sha_14_banks_pre_post": True,
        "source_phases_1_5_7_equal": True,
        "qualified_native_nonlinear_call_gates": True,
        "archive_topology": topology,
        "allowed_to_publish": False,
    })
    if len(json.dumps(out, separators=(",", ":"))) > MAX_OUTPUT:
        raise source.Abstain("OUTPUT_BUDGET")
    return out

def main(stage: str) -> int:
    try:
        result = qualified_study(stage, Path(__file__).resolve().parents[1])
    except (source.Abstain, OSError, ValueError, KeyError, TypeError,
            UnicodeError, struct.error) as exc:
        code = exc.code if type(exc) is source.Abstain else "SOURCE_PRECONDITION"
        result = {"status": "DIAGNOSTIC_ABSTAIN", "stage": stage, "reason": code,
                  "allowed_to_publish": False, "training_approved": False}
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 2 if result["status"] == "DIAGNOSTIC_ABSTAIN" else 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", choices=tuple(WINDOWS), required=True)
    args = parser.parse_args()
    raise SystemExit(main(args.study))
