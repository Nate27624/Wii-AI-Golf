"""P0 source-backed golf target-emitter flag: seven preserved snapshot study.

Source: RPGolFieldManager::mKillTargetEffEmitter bool at field +0xA4.
Related: mMapTargetEff pointer at +0xA0; mShowMiniMap at +0x88.
This is a DISPLAY/EFFECT candidate, not collision, impact, or score.

All fourteen native bank SHA values are verified against canonical #231
private manifest before AND after read-only source-selected sampling.
Never print private game words, heap addresses, bank SHA, paths, or floats.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

_SCRIPTS = str(Path(__file__).resolve().parent)
if _SCRIPTS in sys.path:
    sys.path.remove(_SCRIPTS)
sys.path.insert(0, _SCRIPTS)

import audit_p0_seven_numbered_source_pairs_private as seven
import audit_golf_two_bank_roster_private as roster

PHASES = tuple(range(1, 8))
EDGES = ((1, 2), (5, 6), (6, 7), (5, 7))


def _flag_from_first_be_byte(word: int) -> bool:
    """C++ bool at aligned offset: byte at offset, not low byte of BE-u32."""
    if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
        raise ValueError("invalid source memory word")
    first_byte = word >> 24
    if first_byte not in (0, 1):
        raise ValueError("source bool byte not 0/1")
    # Do not interpret remaining three bytes: they are adjacent/padding data.
    return first_byte == 1


def _triplet(value) -> tuple[int, int, int]:
    if (type(value) is not tuple or len(value) != 3
            or any(type(x) is not int or not 0 <= x <= 0xFFFFFFFF
                   for x in value)):
        raise ValueError("invalid three-source-word reference")
    return value


def _sample(reader) -> dict:
    """Add only two source UI flags and one effect handle to the #231 gate."""
    s = seven._get(reader)
    u = reader.u32
    field = s["field"]
    if roster._bank(field, 0xA8) != "MEM2":
        raise ValueError("FieldManager incomplete or outside captured MEM2")
    cfg = u(roster.GOLF_CONFIG_STATIC)
    pm = u(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    selected = s["selected_index"]
    if (type(selected) is not int or not 0 <= selected < roster.ROSTER_SLOTS
            or roster._bank(cfg, 0xC8) != "MEM2"
            or roster._bank(pm, 4 + roster.ROSTER_SLOTS * roster.ROSTER_STRIDE) != "MEM2"):
        raise ValueError("selected golf source owner/config invalid")
    rec = pm + 4 + selected * roster.ROSTER_STRIDE
    ball = u(rec + 0x88)
    if (roster._bank(ball, 0x108) != "MEM2"
            or u(ball + 0x4C) != ball + 0x30):
        raise ValueError("source-selected player ball link invalid")
    target_effect = u(field + 0xA0)  # pointer presence only; never dereference.
    return {
        "slot": selected,
        "hole": s["hole"],
        "_private_owners": (field, cfg, pm, rec, ball,
                            s["pin_obj"], s["start_obj"]),
        "_private_selectors": (s["cfg_bc"], s["cfg_c0"], s["cfg_c4"]),
        "_private_pin": _triplet(s["pin"]),
        "_private_start": _triplet(s["triplets"]["source_current_start"]),
        "_private_ball": _triplet(s["triplets"]["ball_object_0x030"]),
        "_private_target_effect_ref": target_effect,
        "target_emitter_kill_requested": _flag_from_first_be_byte(
            u(field + 0xA4)),
        "minimap_visibility_requested": _flag_from_first_be_byte(
            u(field + 0x88)),
    }


def summarize(states: dict[int, dict]) -> dict:
    if type(states) is not dict or set(states) != set(PHASES):
        raise ValueError("all seven canonical numbered phases required")
    for n in PHASES:
        s = states[n]
        if (type(s["slot"]) is not int or not 0 <= s["slot"] < 4
                or type(s["hole"]) is not int or not 0 <= s["hole"] < 9
                or type(s["target_emitter_kill_requested"]) is not bool
                or type(s["minimap_visibility_requested"]) is not bool
                or type(s["_private_owners"]) is not tuple
                or len(s["_private_owners"]) != 7
                or type(s["_private_selectors"]) is not tuple
                or len(s["_private_selectors"]) != 3
                or any(type(x) is not int for x in
                       s["_private_owners"] + s["_private_selectors"])
                or type(s["_private_target_effect_ref"]) is not int
                or not 0 <= s["_private_target_effect_ref"] <= 0xFFFFFFFF):
            raise ValueError("source target UI state or private owner malformed")
        for key in ("_private_pin", "_private_start", "_private_ball"):
            _triplet(s[key])

    edges = []
    for early, late in EDGES:
        a, b = states[early], states[late]
        if (a["slot"] != b["slot"] or a["hole"] != b["hole"]
                or a["_private_owners"] != b["_private_owners"]
                or a["_private_selectors"] != b["_private_selectors"]
                or a["_private_pin"] != b["_private_pin"]
                or a["_private_start"] != b["_private_start"]):
            raise ValueError("within-shot source reference/owner/config confounded")
        edges.append({
            "pair": f"{early}_to_{late}",
            "target_emitter_kill_flag_changed": (
                a["target_emitter_kill_requested"]
                != b["target_emitter_kill_requested"]),
            "minimap_visibility_flag_changed": (
                a["minimap_visibility_requested"]
                != b["minimap_visibility_requested"]),
            "target_effect_reference_changed": (
                a["_private_target_effect_ref"]
                != b["_private_target_effect_ref"]),
            "source_selected_ball_triplet_changed_components": sum(
                x != y for x, y in zip(a["_private_ball"], b["_private_ball"])),
            "stable_source_owner_pin_start_and_config": True,
        })
    return {
        "kind": "P0-SANITIZED-SEVEN-TARGET-EMITTER-UI-FLAG",
        "source_declared_field": "RPGolFieldManager.mKillTargetEffEmitter",
        "source_relative_byte_offset": "+0xA4",
        "source_ui_control_type_bool": True,
        "source_target_effect_ref_offset": "+0xA0",
        "all_14_original_native_bank_sha_verified_before_after": True,
        "source_gated_rev1_selected_field_and_ball": True,
        "per_snapshot": [{
            "phase": n,
            "target_emitter_kill_requested":
                states[n]["target_emitter_kill_requested"],
            "minimap_visibility_requested":
                states[n]["minimap_visibility_requested"],
            "target_effect_reference_nonnull":
                states[n]["_private_target_effect_ref"] != 0,
        } for n in PHASES],
        "provisional_within_shot_comparisons": edges,
        "human_phase_labels_and_order_machine_verified": False,
        "target_effect_blinking_observed_on_screen": False,
        "active_target_emitter_identity_verified": False,
        "ball_contact_or_impact_verified": False,
        "green_landing_or_score_verified": False,
        "rendered_ball_world_xyz_or_velocity_verified": False,
        "shot_power_verified": False,
        "same_game_frame_banks_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }


def analyze(archive: Path) -> dict:
    folders = seven._check_archive(archive)  # 14 archived SHA checks FIRST
    with ExitStack() as stack:
        states = {}
        for n in PHASES:
            maps = []
            for i, size in enumerate(seven.SIZE):
                path = seven.src._file(folders[n], f"{n}.{i + 1}.raw", size)
                fh = stack.enter_context(path.open("rb"))
                maps.append(stack.enter_context(mmap.mmap(
                    fh.fileno(), 0, access=mmap.ACCESS_READ)))
            states[n] = _sample(roster.TwoBankReader(*maps))
        report = summarize(states)
    seven._check_archive(archive)  # AFTER file/mmap handles close
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = analyze(args.archive)
    except (OSError, ValueError, KeyError, TypeError, OverflowError,
            AttributeError):
        print("P0_TARGET_EMITTER_ABSTAIN: original archive, Rev1 source, "
              "UI bool byte or same-owner geometry gate failed; no evidence promoted.",
              file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
