"""S002 P0: source-defined RPSportsSequenceMgr 9x4 score table, not GolfConfig scores.

Read-only existing seven-pair archive. Reuses #231's complete SHA/source gates.
Never prints private score values, guest addresses, coordinates, hashes, or file paths.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR in sys.path:
    sys.path.remove(_SCRIPT_DIR)
sys.path.insert(0, _SCRIPT_DIR)

import audit_p0_seven_numbered_source_pairs_private as seven
import audit_golf_two_bank_roster_private as roster

PHASES = (1, 2, 5, 6, 7)
EDGES = ((1, 2), (5, 6), (6, 7), (5, 7))
# Source: kiwi515/ogws_info/RP/RPSports/RPSportsSequenceMgr.h (RSPE01 Rev1)
SEQUENCE_STATIC = 0x804BF708
SCORE_OFFSET = 0x14
SCORE_COUNT = 9 * 4
SEQUENCE_BYTES = 0xD0
GOLF_SPORT_ID = 2


def _sample(rd):
    base = seven._get(rd)
    u = rd.u32
    cfg = u(roster.GOLF_CONFIG_STATIC)
    field = u(roster.GOLF_FIELD_STATIC)
    pm = u(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    slot, hole = base["selected_index"], base["hole"]
    if (type(slot) is not int or not 0 <= slot < 4
            or type(hole) is not int or not 0 <= hole < 9
            or roster._bank(cfg, 0xC8) != "MEM2"
            or roster._bank(field, 0x58) != "MEM2"
            or roster._bank(pm, 0x338) != "MEM2"
            or u(cfg + 0x94) != 4 or u(cfg + 0x98) != hole):
        raise ValueError("Source Config/field/player mode and hole not qualified")
    rec = pm + 4 + slot * roster.ROSTER_STRIDE
    if roster._bank(rec, roster.ROSTER_STRIDE) != "MEM2":
        raise ValueError("Selected record bounds invalid")
    ball = u(rec + 0x88)
    if (roster._bank(ball, 0x108) != "MEM2"
            or u(ball + 0x4C) != ball + 0x30
            or u(field + 0x44) != base["pin_obj"]
            or u(field + 0x50) != base["start_obj"]):
        raise ValueError("Source ball/goal self-reference or owner invalid")

    seq = u(SEQUENCE_STATIC)
    if seq == 0:
        seq_values = None
        sport = None
        training_game = None
        sequence = None
        golf_mode = None
    else:
        if roster._bank(seq, SEQUENCE_BYTES) not in ("MEM1", "MEM2"):
            raise ValueError("Source SequenceMgr instance pointer out of bounds")
        sport = u(seq + 0x04)
        sequence = u(seq + 0x08)
        training_game = u(seq + 0x0C)
        golf_mode = u(seq + 0xAC)
        # Loose enum sanity only. Do not equate enum to active scene or game.
        if sport > 4 or training_game > 2 or golf_mode > 3:
            raise ValueError("SequenceMgr source enum sanity not met")
        seq_values = tuple(u(seq + SCORE_OFFSET + i * 4)
                           for i in range(SCORE_COUNT))

    return {
        "slot": slot,
        "hole": hole,
        "owner": (cfg, field, pm, rec, ball, base["pin_obj"], base["start_obj"]),
        "selectors": (base["cfg_bc"], base["cfg_c0"], base["cfg_c4"]),
        "pin": base["pin"],
        "tee": base["triplets"]["source_current_start"],
        "ball": base["triplets"]["ball_object_0x030"],
        "seq_pointer": seq,
        "seq_sport": sport,
        "seq_training_game": training_game,
        "seq_sequence": sequence,
        "seq_golf_mode": golf_mode,
        "seq_scores": seq_values,
    }


def _diff(a, b):
    if len(a) != len(b):
        raise ValueError("Incompatible source word field shapes")
    return sum(x != y for x, y in zip(a, b))


def summarize(states):
    if set(states) != set(PHASES):
        raise ValueError("Require D1,D2 and W5,W6,W7, no extra phases")
    for n in PHASES:
        s = states[n]
        if (type(s["slot"]) is not int or not 0 <= s["slot"] < 4
                or type(s["hole"]) is not int or not 0 <= s["hole"] < 9
                or len(s["pin"]) != 3 or len(s["tee"]) != 3
                or len(s["ball"]) != 3):
            raise ValueError("Invalid source selected geometry or context")
        seq = s["seq_scores"]
        if (seq is not None and (type(seq) not in (tuple, list)
                                 or len(seq) != SCORE_COUNT
                                 or any(type(w) is not int
                                        or not 0 <= w <= 0xFFFFFFFF for w in seq))):
            raise ValueError("Invalid source score table")
        if seq is None and s["seq_pointer"] != 0:
            raise ValueError("SequenceMgr pointer without qualified table")
        if seq is not None and (type(s["seq_pointer"]) is not int
                                or s["seq_pointer"] == 0
                                or type(s["seq_sport"]) is not int
                                or not 0 <= s["seq_sport"] <= 4):
            raise ValueError("SequenceMgr content without source-compatible pointer")
    comparisons = []
    for early, late in EDGES:
        a, b = states[early], states[late]
        if any(a[k] != b[k] for k in ("slot", "hole", "owner",
                                     "selectors", "pin", "tee")):
            raise ValueError("Changed selected owner/geometry/Config selector")
        if a["seq_pointer"] != b["seq_pointer"]:
            raise ValueError("Different SequenceMgr owner within one human shot")
        present = a["seq_scores"] is not None and b["seq_scores"] is not None
        if present:
            rows = [_diff(a["seq_scores"][i*4:(i+1)*4],
                          b["seq_scores"][i*4:(i+1)*4]) for i in range(9)]
            total = sum(rows)
            # SequenceMgr orders scores [hole][player], NOT [player][hole].
            idx = a["hole"] * 4 + a["slot"]
            selected_change = a["seq_scores"][idx] != b["seq_scores"][idx]
            sport_golf_both = (a["seq_sport"] == GOLF_SPORT_ID
                               and b["seq_sport"] == GOLF_SPORT_ID)
        else:
            rows = None
            total = None
            selected_change = None
            sport_golf_both = False
        comparisons.append({
            "transition": f"{early}_to_{late}",
            "source_selected_player_hole_pin_tee_config_stable": True,
            "selected_ball_changed_components": _diff(a["ball"], b["ball"]),
            "sequence_manager_present_both": present,
            "sequence_manager_sport_golf_both": sport_golf_both,
            "sequence_manager_sport_changed": (
                a["seq_sport"] != b["seq_sport"] if present else None
            ),
            "sequence_manager_training_game_changed": (
                a["seq_training_game"] != b["seq_training_game"]
                if present else None
            ),
            "sequence_manager_golf_mode_changed": (
                a["seq_golf_mode"] != b["seq_golf_mode"]
                if present else None
            ),
            "sequence_manager_sequence_changed": (
                a["seq_sequence"] != b["seq_sequence"] if present else None
            ),
            "sequence_manager_score_table_changed_words_of_36": total,
            "sequence_manager_score_changed_count_by_hole": rows,
            "source_selected_hole_player_cell_changed": selected_change,
            "other_score_cells_changed": (
                total - int(selected_change) if present else None
            ),
            "counts_are_only_source_table_observations": True,
        })
    return {
        "kind": "P0-SANITIZED-SEVEN-SEQUENCE-MANAGER-GOLF-SCORES",
        "native_14_bank_archive_sha_verified": True,
        "rev1_source_selected_golf_context_verified": True,
        "source_locator": "RPSportsSequenceMgr::sInstance 0x804BF708",
        "table_layout": "RPSportsSequenceMgr+0x14 [hole=9][player=4] u32",
        "mode4_training_scoring_use_verified": False,
        "comparison_edges": comparisons,
        "human_label_to_file_mapping_machine_verified": False,
        "guest_frames_or_impact_verified": False,
        "onscreen_distance_or_reward_decoded": False,
        "training_best_savedata_pointer_found": False,
        "training_best_recorded_at_each_shot_verified": False,
        "physical_xyz_or_velocity_or_power_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }


def analyze(archive: Path):
    folders = seven._check_archive(archive)
    with ExitStack() as stack:
        states = {}
        for n in PHASES:
            banks = []
            for i, size in enumerate(seven.SIZE):
                p = seven.src._file(folders[n], f"{n}.{i+1}.raw", size)
                f = stack.enter_context(p.open("rb"))
                banks.append(stack.enter_context(mmap.mmap(
                    f.fileno(), 0, access=mmap.ACCESS_READ)))
            states[n] = _sample(roster.TwoBankReader(*banks))
        result = summarize(states)
    seven._check_archive(archive)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = analyze(args.archive)
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        print("P0_SEQUENCE_SCORES_ABSTAIN: archive/source/sequence owner invalid",
              file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
