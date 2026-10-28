"""Read-only phase/handle lifetime study for an EXISTING human-observed V1 hit.

S002: derive only source-relative RPSysEffect HandleBase ID/pointer flags from
the original private 3 PRE / 2 POST / 3 SETTLED narrow-memory captures.
The four handles are plausible effect lifecycle state, NOT ball physics.
No Dolphin, input, RAM writes, or network calls. No raw values in stdout.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT.parent / "Wii-AI-Golf-Data" / "captures"
RUN_ID = re.compile(r"outcome-\d{8}T\d{6}Z-[0-9a-f]{8}\Z")
ADDRESS = re.compile(r"0x[0-9a-fA-F]{8}\Z")
SOURCE = "Felk-read-only-US-Rev1-unverified-golf-windows"
WINDOWS = ("minimap_player_effect", "minimap_shot_line_effect", "minimap_ball_effect")
PHASES = ("pre", "post", "settled")
SLOTS = tuple((0x078 + 0x90 * n, 0x07C + 0x90 * n) for n in range(4))
MAX_BYTES = 8 * 1024 * 1024


def _ram_range(address: int, size: int = 4) -> bool:
    return (0x80000000 <= address <= 0x81800000 - size or
            0x90000000 <= address <= 0x94000000 - size)


def _address(value: object) -> int:
    if not isinstance(value, str) or ADDRESS.fullmatch(value) is None:
        raise ValueError("Invalid address format")
    address = int(value, 16)
    if address % 4 or not _ram_range(address):
        raise ValueError("Invalid Wii RAM address")
    return address


def _private_path(path: Path) -> Path:
    if path.is_symlink():
        raise ValueError("Symlinked input not allowed")
    p = path.resolve(strict=True)
    root = (ROOT.parent / "Wii-AI-Golf-Data").resolve(strict=True)
    if not p.is_relative_to(root) or p == root:
        raise ValueError("Input outside ignored private Data directory")
    return p


def _load_json(path: Path) -> dict:
    path = _private_path(path)
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("Missing or oversized private file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Expected JSON object")
    return value


def _load_rows(path: Path) -> list[dict]:
    path = _private_path(path)
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("Missing or oversized private JSONL")
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if len(rows) >= 60 or len(line) > 150000:
                raise ValueError("Oversized private snapshot")
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError("Invalid private snapshot")
            rows.append(item)
    return rows


def _windows(row: dict) -> tuple[int, dict[str, tuple[int, bytes]]]:
    if not isinstance(row, dict) or row.get("source") != SOURCE:
        raise ValueError("Invalid source of private capture")
    if (row.get("game_id"), row.get("disc_revision"), row.get("game_mode_raw")) != ("RSPE01", 1, 4):
        raise ValueError("Wrong game/revision/mode")
    lo, hi = row.get("frame_start"), row.get("frame_end")
    if type(lo) is not int or type(hi) is not int or not 0 <= lo <= hi:
        raise ValueError("Invalid frame bracket")
    raw_windows = row.get("windows")
    if not isinstance(raw_windows, dict) or any(w not in raw_windows for w in WINDOWS):
        raise ValueError("Missing source effect windows")
    out = {}
    for name in WINDOWS:
        raw = raw_windows[name]
        if not isinstance(raw, dict):
            raise ValueError("Malformed source effect window")
        base = _address(raw.get("address"))
        h = raw.get("bytes_hex")
        if not isinstance(h, str) or len(h) != 0x400 or not _ram_range(base, 0x200):
            raise ValueError("Wrong source window length")
        try:
            data = bytes.fromhex(h)
        except ValueError as ex:
            raise ValueError("Malformed private bytes") from ex
        if len(data) != 0x200:
            raise ValueError("Truncated source window")
        out[name] = (base, data)
    bases = [out[n][0] for n in WINDOWS]
    if bases[1] - bases[0] != 0x90 or bases[2] - bases[1] != 0x90:
        raise ValueError("Invalid repeated effect window alignment")
    return bases[0], out


def _word(windows: dict[str, tuple[int, bytes]], address: int) -> int:
    observed = []
    for base, buf in windows.values():
        offset = address - base
        if 0 <= offset <= len(buf) - 4:
            observed.append(struct.unpack_from(">I", buf, offset)[0])
    if not observed or len(set(observed)) != 1:
        raise ValueError("Missing/contradictory overlapping effect words")
    return observed[0]


def _all_changed(samples: list[int], reference: int) -> bool:
    return bool(samples) and all(x != reference for x in samples)


def _same(samples: list[int]) -> bool:
    return len(set(samples)) == 1


def audit(rows: list[dict], summary: dict) -> dict:
    """Return a safe source-relative lifecycle sketch; never return private words."""
    if not isinstance(rows, list) or not isinstance(summary, dict) or len(rows) != 8:
        raise ValueError("Expected exactly eight original private phase snapshots")
    if [r.get("phase") for r in rows] != ["pre"]*3 + ["post"]*2 + ["settled"]*3:
        raise ValueError("Expected ordered 3/2/3 contact cohort")
    if summary.get("study_id") != "S002-HG-OUTCOME-TRANSITION-EXPLORATORY" or summary.get("raw_data_created") is not True:
        raise ValueError("Unknown source study")
    human = summary.get("human_observation")
    if not isinstance(human, dict) or human.get("contact_human") != "yes":
        raise ValueError("No human-confirmed contact")
    if human.get("game_distance_verified_by_memory") is not False or human.get("displayed_power_verified_by_memory", False) is not False:
        raise ValueError("Unexpected physics-label verification")
    lead = summary.get("known_good_swing_request")
    swing = summary.get("swing_dispatch")
    if (not isinstance(lead, dict) or lead.get("a_lead_requested_frames") != 45
        or type(lead.get("a_lead_observed_frame_delta")) is not int
        or lead["a_lead_observed_frame_delta"] < 45
        or not isinstance(swing, dict) or swing.get("state") != "complete"
        or swing.get("applied_frames") != 89 or swing.get("total_frames") != 89):
        raise ValueError("Unexpected frozen 45-lead/89-trace evidence")
    ranking = summary.get("candidate_ranking")
    if not isinstance(ranking, dict) or ranking.get("candidates_truncated") is not False:
        raise ValueError("Missing complete candidate ranking")
    if ranking.get("all_phase_stable_change_count") != 8 or not isinstance(ranking.get("candidates"), list) or len(ranking["candidates"]) != 8:
        raise ValueError("Not the expected eight candidate words")

    readings = []
    bases = []
    spans = []
    for row in rows:
        base, windows = _windows(row)
        bases.append(base)
        spans.append(row["frame_end"] - row["frame_start"])
        readings.append(tuple((_word(windows, base + id_off),
                               _word(windows, base + ptr_off)) for id_off, ptr_off in SLOTS))
    # Accept exactly the original eight persisted candidate locations, no extras.
    expected = {bases[0] + offset for pair in SLOTS for offset in pair}
    if len(set(bases)) != 1:
        raise ValueError("Effect source objects relocated between phases")
    candidates = ranking["candidates"]
    try:
        observed = [_address(c["address"]) for c in candidates]
    except (TypeError, KeyError) as ex:
        raise ValueError("Malformed candidate addresses") from ex
    if len(set(observed)) != 8 or set(observed) != expected:
        raise ValueError("Saved candidates are not the four source handle pairs")

    # Candidate summary addresses alone do not establish a persistent change.
    # Independently require stable PRE and SETTLED words, with a different
    # SETTLED value, for EVERY ID and pointer member of each alleged pair.
    for slot in range(4):
        for component in (0, 1):
            observed_words = [snapshot[slot][component] for snapshot in readings]
            if (not _same(observed_words[:3])
                    or not _same(observed_words[5:])
                    or observed_words[0] == observed_words[5]):
                raise ValueError("Saved candidate is not a persistent phase change")

    result = []
    for slot, (id_off, ptr_off) in enumerate(SLOTS):
        ids = [record[slot][0] for record in readings]
        ptrs = [record[slot][1] for record in readings]
        ip, it, iset = ids[:3], ids[3:5], ids[5:]
        pp, pt, pset = ptrs[:3], ptrs[3:5], ptrs[5:]
        before_stable = _same(ip) and _same(pp)
        id_after = before_stable and _all_changed(it, ip[0])
        ptr_after = before_stable and _all_changed(pt, pp[0])
        result.append({
            "slot_index_hypothesis": slot,
            "source_object_id_offset": f"+0x{id_off:03X}",
            "source_object_pointer_offset": f"+0x{ptr_off:03X}",
            "candidate_member_type": "RPSysEffect.mHandle: u32 ID + LinkedObject*",
            "pre_pair_stable": before_stable,
            "post_pair_stable": _same(it) and _same(pt),
            "settled_pair_stable": _same(iset) and _same(pset),
            "id_changed_in_each_post_vs_pre": bool(id_after),
            "pointer_changed_in_each_post_vs_pre": bool(ptr_after),
            "both_changed_in_each_post": bool(id_after and ptr_after),
            "id_change_present_by_settled": bool(before_stable and _all_changed(iset, ip[0])),
            "pointer_change_present_by_settled": bool(before_stable and _all_changed(pset, pp[0])),
            "ptr_null_in_all_pre": all(x == 0 for x in pp),
            "ptr_null_in_all_post": all(x == 0 for x in pt),
            "ptr_null_in_all_settled": all(x == 0 for x in pset),
            "handle_layout_plausible_each_sample": all(
                not _ram_range(i) and (p == 0 or _ram_range(p))
                for i, p in zip(ids, ptrs)),
            "pointer_target_identity_verified": False,
            "effect_lifecycle_cause_verified": False,
        })

    return {
        "kind": "S002-existing-hit-effect-handle-lifecycle-offline",
        "schema_version": 1,
        "game_revision": "RSPE01 Rev1",
        "observed_contact": "human_only",
        "phase_counts": {"pre": 3, "post": 2, "settled": 3},
        "source_windows_spaced_0x90_in_all_phases": True,
        "four_handle_pairs_match_saved_candidate_locations": True,
        "frame_reads_non_atomic": any(span != 0 for span in spans),
        "all_records_share_effect_base": True,
        "source_RPSysEffect_handle_layout_hypothesis": True,
        "pair_patterns": result,
        "ball_xyz_verified": False,
        "ball_velocity_verified": False,
        "club_power_verified": False,
        "official_distance_verified": False,
        "pointer_target_identity_verified": False,
        "approved_for_training": False,
        "allowed_to_publish": False,
        "private_values_emitted": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--data-dir", type=Path, default=PRIVATE)
    args = parser.parse_args(argv)
    if not RUN_ID.fullmatch(args.run_id):
        parser.error("Invalid run ID")
    try:
        folder = _private_path(args.data_dir)
        rows = _load_rows(folder / (args.run_id + "-RAW-PRIVATE.jsonl"))
        summary = _load_json(folder / (args.run_id + "-candidates.json"))
        print(json.dumps(audit(rows, summary), indent=2, sort_keys=True, allow_nan=False))
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as ex:
        print("PRIVATE effect-handle lifecycle audit FAILED CLOSED: " + type(ex).__name__, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
