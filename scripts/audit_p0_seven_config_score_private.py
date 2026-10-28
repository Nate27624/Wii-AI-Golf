"""P0: source-gated Config score-table transitions in existing seven-pair golf captures.

Read-only private analysis. Reports only bounded change COUNTS and booleans.
A source-typed score table is NOT evidence of on-screen or physical shot outcome.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

# In isolated Python (-I), rely only on reviewed sibling S002 modules.
_SCRIPTS = str(Path(__file__).resolve().parent)
if _SCRIPTS in sys.path:
    sys.path.remove(_SCRIPTS)
sys.path.insert(0, _SCRIPTS)
import audit_p0_seven_numbered_source_pairs_private as seven
import audit_golf_two_bank_roster_private as roster

PHASES = (1, 2, 5, 6, 7)
EDGES = ((1, 2), (5, 6), (6, 7), (5, 7))
# Independent exact-target public class header, Kokeshi immutable commit
# dfbdda61aadad423911d5345f67f8793aa92cd5f:
# RPGolConfig::mStrokeTotal[HOLE_MAX=9][PLAYER_MAX=4] at +0x04.
# All 36 raw words and total change counts are unchanged by the indexing fix;
# source-selected hole/player position and row-level interpretation are not.
SCORE_COUNT = 36
SCORE_ROWS = 9  # Rev1 Kokeshi RPGolConfig::mStrokeTotal[hole][player]
SCORE_COLS = 4


def _sample(rd):
    """Reuse authoritative Rev1/source-selected reader, add only known config fields."""
    s = seven._get(rd)
    u = rd.u32
    cfg = u(roster.GOLF_CONFIG_STATIC)
    field = u(roster.GOLF_FIELD_STATIC)
    pm = u(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    slot = s["selected_index"]
    hole = s["hole"]
    if (type(slot) is not int or not 0 <= slot < SCORE_COLS
            or type(hole) is not int or not 0 <= hole < SCORE_ROWS
            or roster._bank(cfg, 0x9C) != "MEM2"
            or roster._bank(field, 0x58) != "MEM2"
            or roster._bank(pm, 0x334 + 4) != "MEM2"
            or u(cfg + 0x94) != 4
            or u(cfg + 0x98) != hole):
        raise ValueError("Source score table context or mode/hole invalid")
    rec = pm + 4 + slot * roster.ROSTER_STRIDE
    if roster._bank(rec, roster.ROSTER_STRIDE) != "MEM2":
        raise ValueError("Selected record bounds invalid")
    ball = u(rec + 0x88)
    if (roster._bank(ball, 0x108) != "MEM2"
            or u(ball + 0x4C) != ball + 0x30
            or u(field + 0x44) != s["pin_obj"]
            or u(field + 0x50) != s["start_obj"]):
        raise ValueError("Source-selected ball/pin/start failed")
    scores = tuple(u(cfg + 4 + i * 4) for i in range(SCORE_COUNT))
    field_counts = (u(field + 0x30), u(field + 0x3C), u(field + 0x48))
    tree_timer = u(field + 0x10)
    return {
        "slot": slot,
        "hole": hole,
        "owner": (cfg, field, pm, rec, ball, s["pin_obj"], s["start_obj"]),
        "selectors": (s["cfg_bc"], s["cfg_c0"], s["cfg_c4"]),
        "pin": s["pin"],
        "tee": s["triplets"]["source_current_start"],
        "ball": s["triplets"]["ball_object_0x030"],
        "scores": scores,
        "field_counts": field_counts,
        "tree_timer": tree_timer,
    }


def _changed(a, b):
    if len(a) != len(b):
        raise ValueError("Incompatible source field lengths")
    return sum(x != y for x, y in zip(a, b))


def summarize(states):
    if set(states) != set(PHASES):
        raise ValueError("Require exact original D1,D2 and W5,W6,W7 states")
    for phase in PHASES:
        s = states[phase]
        if (type(s["slot"]) is not int or not 0 <= s["slot"] < SCORE_COLS
                or type(s["hole"]) is not int or not 0 <= s["hole"] < SCORE_ROWS
                or len(s["scores"]) != SCORE_COUNT
                or len(s["field_counts"]) != 3
                or len(s["ball"]) != 3 or len(s["pin"]) != 3
                or len(s["tee"]) != 3):
            raise ValueError("Malformed source state or score-table shape")
        for value in s["scores"] + s["field_counts"] + (s["tree_timer"],):
            if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
                raise ValueError("Malformed word in source table or control")

    comparisons = []
    for early, late in EDGES:
        a, b = states[early], states[late]
        stable = (a["slot"] == b["slot"] and a["hole"] == b["hole"]
                  and a["owner"] == b["owner"]
                  and a["selectors"] == b["selectors"]
                  and a["pin"] == b["pin"] and a["tee"] == b["tee"])
        if not stable:
            raise ValueError("Same-human-shot source owner or target confounded")
        row_changes = [
            _changed(a["scores"][k * SCORE_COLS:(k + 1) * SCORE_COLS],
                     b["scores"][k * SCORE_COLS:(k + 1) * SCORE_COLS])
            for k in range(SCORE_ROWS)
        ]
        score_changed = sum(row_changes)
        active_cell_index = a["hole"] * SCORE_COLS + a["slot"]
        comparisons.append({
            "transition": f"{early}_to_{late}",
            "same_selected_source_owner_hole_pin_tee_config": True,
            "current_ball_changed_components": _changed(a["ball"], b["ball"]),
            "player_score_table_changed_words_of_36": score_changed,
            "score_changed_cells_per_hole_row": row_changes,
            "selected_player_source_hole_score_cell_changed": (
                a["scores"][active_cell_index] != b["scores"][active_cell_index]
            ),
            "other_score_cells_changed": score_changed - int(
                a["scores"][active_cell_index] != b["scores"][active_cell_index]
            ),
            "field_source_count_words_changed_of_3": _changed(
                a["field_counts"], b["field_counts"]
            ),
            "field_tree_shadow_timer_changed": a["tree_timer"] != b["tree_timer"],
        })
    return {
        "kind": "P0-SANITIZED-SEVEN-CONFIG-SCORE-TRANSITION-CONTROL",
        "native_14_bank_archive_sha_verified": True,
        "rev1_source_selected_context_verified": True,
        "compared_human_same_shot_edges_only": True,
        "human_phase_file_mapping_machine_verified": False,
        "score_table_source_layout": "GolfConfig+0x04 u32[9][4] hole-major",
        "comparisons": comparisons,
        "no_changed_score_words_if_all_zero_is_mode4_only_negative": True,
        "golf_training_mode_score_table_is_verified_outcome": False,
        "game_reported_15p2ft_decoded_from_memory": False,
        "score_units_or_game_reward_verified": False,
        "actual_frame_or_impact_verified": False,
        "physical_ball_xyz_or_velocity_verified": False,
        "game_power_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }


def analyze(archive: Path):
    folders = seven._check_archive(archive)  # All 14 SHA256 and native sizes.
    with ExitStack() as stack:
        states = {}
        for n in PHASES:
            maps = []
            for i, size in enumerate(seven.SIZE):
                path = seven.src._file(folders[n], f"{n}.{i+1}.raw", size)
                fh = stack.enter_context(path.open("rb"))
                maps.append(stack.enter_context(mmap.mmap(
                    fh.fileno(), 0, access=mmap.ACCESS_READ)))
            states[n] = _sample(roster.TwoBankReader(*maps))
        report = summarize(states)
    seven._check_archive(archive)  # Rehash after all readers close.
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = analyze(args.archive)
    except (OSError, ValueError, KeyError, TypeError, OverflowError):
        print("P0_CONFIG_SCORE_ABSTAIN: native/source/geometry/score guard failed.", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
