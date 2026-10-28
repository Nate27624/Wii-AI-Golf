"""Source-gated coordinate-component/ground-anchor hypothesis for W5,W6,W7.

This is NOT a coordinate-axis decoder. Numeric values stay private; it emits
only three per-component direction and equality/near-anchor classifications.
Requires canonical #231 seven-pair archive SHA and Rev1 source checks.
No emulator, controller, network/upload, physics-frame or training claims.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import math
import mmap
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as seven
import audit_golf_two_bank_roster_private as roster

PHASES = (5, 6, 7)
# Purely numerical and arbitrary; physical game units remain unknown.
ABS_TOL = 1e-4
REL_TOL = 1e-6
MAX_ABS = 100000.0


def _f32(word):
    if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
        raise ValueError("Invalid private source coordinate word")
    value = struct.unpack(">f", struct.pack(">I", word))[0]
    if not math.isfinite(value) or abs(value) > MAX_ABS:
        raise ValueError("Nonfinite/unbounded private coordinate")
    return value


def _vec(words):
    if type(words) not in (list, tuple) or len(words) != 3:
        raise ValueError("Expected source-validated private f32 triple")
    return tuple(_f32(w) for w in words)


def _near(x, y):
    return math.isclose(x, y, abs_tol=ABS_TOL, rel_tol=REL_TOL)


def _direction(x, y):
    if _near(x, y):
        return "within_numerical_tolerance"
    return "increase" if y > x else "decrease"


def _sample(rd):
    # Existing #231 reader checks Rev1 PPC, source scene/mode/selected actor.
    s = seven._get(rd)
    u = rd.u32
    pm = u(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    rec = pm + 4 + s["selected_index"] * roster.ROSTER_STRIDE
    ball = u(rec + 0x88)
    field = u(roster.GOLF_FIELD_STATIC)
    pin = u(field + 0x44)
    start = u(field + 0x50)
    config = u(roster.GOLF_CONFIG_STATIC)

    if (roster._bank(rec, roster.ROSTER_STRIDE) != "MEM2"
            or roster._bank(ball, 0x108) != "MEM2"
            or roster._bank(pin, 0x50) != "MEM2"
            or roster._bank(start, 0x50) != "MEM2"
            or u(ball + 0x4C) != ball + 0x30
            or u(pin + 0x48) != pin + 0x0C
            or u(pin + 0x4C) != pin + 0x30
            or u(start + 0x48) != start + 0x0C
            or u(start + 0x4C) != start + 0x30):
        raise ValueError("Selected source object self-reference failed")
    return {
        "slot": s["selected_index"],
        "hole": s["hole"],
        "owner": (pm, rec, ball, field, pin, start, config),
        "selectors": (s["cfg_bc"], s["cfg_c0"], s["cfg_c4"]),
        "ball": s["triplets"]["ball_object_0x030"],
        "pin": s["pin"],
        "tee": s["triplets"]["source_current_start"],
    }


def summarize(states):
    if set(states) != set(PHASES):
        raise ValueError("Exactly wedge captures 5,6,7 required")
    w5, w6, w7 = (states[n] for n in PHASES)
    controls = ("slot", "hole", "owner", "selectors", "pin", "tee")
    if any(w5[key] != state[key] for state in (w6, w7) for key in controls):
        raise ValueError("Confounded target/tee/owner/selector source identity")
    for state in (w5, w6, w7):
        for k in ("ball", "pin", "tee"):
            _vec(state[k])
    if w5["ball"] == w6["ball"] or w6["ball"] == w7["ball"]:
        raise ValueError("No separate candidate motion across one interval")

    a, b, c = (_vec(state["ball"]) for state in (w5, w6, w7))
    pin, tee = _vec(w5["pin"]), _vec(w5["tee"])
    rows = []
    for i in range(3):
        d1, d2 = _direction(a[i], b[i]), _direction(b[i], c[i])
        pin_near = _near(c[i], pin[i])
        tee_near = _near(c[i], tee[i])
        # Candidate only if at terminal human-labeled W7 phase and earlier
        # candidate axis values are numerically farther from pin component.
        pin_anchor_candidate = (
            pin_near and not _near(a[i], pin[i])
            and not _near(b[i], pin[i])
            and abs(b[i] - pin[i]) < abs(a[i] - pin[i])
        )
        rows.append({
            "component_index_source_order_only": i,
            "W5_to_W6_numeric_direction": d1,
            "W6_to_W7_numeric_direction": d2,
            "both_steps_same_strict_direction": d1 == d2 and d1 in ("increase", "decrease"),
            "W5_W6_on_same_side_of_W7": (a[i] - c[i]) * (b[i] - c[i]) > 0,
            "W6_between_W5_and_W7": min(a[i], c[i]) < b[i] < max(a[i], c[i]),
            "W7_bitwise_equal_pin_component": w7["ball"][i] == w7["pin"][i],
            "W7_near_pin_component_arbitrary_tolerance": pin_near,
            "W7_bitwise_equal_tee_component": w7["ball"][i] == w7["tee"][i],
            "W7_near_tee_component_arbitrary_tolerance": tee_near,
            "pin_anchor_coincidence_candidate": pin_anchor_candidate,
        })
    candidate_indices = [row["component_index_source_order_only"]
                         for row in rows if row["pin_anchor_coincidence_candidate"]]
    return {
        "kind": "P0-SANITIZED-WEDGE-AXIS-ANCHOR-HYPOTHESIS",
        "schema_version": 1,
        "wedge_source_owner_hole_pin_tee_selectors_stable": True,
        "wedge_ball_word_triples_differ_on_consecutive_phases": True,
        "operator_human_phase_order_only": [5, 6, 7],
        "per_component": rows,
        "pin_anchor_coincidence_candidate_count": len(candidate_indices),
        "pin_anchor_coincidence_candidate_indices": candidate_indices,
        "unique_pin_anchor_coincidence_candidate": len(candidate_indices) == 1,
        "pin_anchor_is_ground_height_verified": False,
        "any_component_is_physical_vertical_axis_verified": False,
        "physical_axes_or_game_distance_units_verified": False,
        "guest_frame_timestamps_machine_verified": False,
        "impact_frame_or_score_memory_verified": False,
        "ball_velocity_or_power_verified": False,
        "physical_ball_world_xyz_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
        "interpretation_limit": (
            "Coincidence with PIN coordinate of one component at human W7 "
            "is not proof of gravity axis or ground height. Elevation, green "
            "slope, target placement, visual-to-game axes and precise frame "
            "timestamps are unverified. Numerical tolerance is arbitrary."
        ),
    }


def analyze(archive: Path):
    # SHA checks for all 14 archived banks happen before source reads.
    folders = seven._check_archive(archive)
    with ExitStack() as stack:
        samples = {}
        for n in PHASES:
            banks = []
            for i, size in enumerate(seven.SIZE):
                p = seven.src._file(folders[n], f"{n}.{i+1}.raw", size)
                f = stack.enter_context(p.open("rb"))
                banks.append(stack.enter_context(
                    mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)))
            samples[n] = _sample(roster.TwoBankReader(*banks))
        return summarize(samples)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        report = analyze(a.archive)
    except (OSError, ValueError, TypeError, KeyError, OverflowError, struct.error):
        print("P0_WEDGE_AXIS_ANCHOR_ABSTAIN: private source/geometry/float guard failed.",
              file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
