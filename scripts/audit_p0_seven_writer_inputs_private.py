"""Offline comparison of source-selected *writer INPUT* and observed ball/cache contents.

This is narrower than S002 #219's static PPC callgraph and #230's pairwise
trajectory analysis: it tests whether the Player-record +0x60 triple, known
to be copied into ball+0x30 by the static code path fn_802A0320, ACTUALLY
equals the source-selected ball triplet at each of seven existing snapshots,
and whether the cache +0xCC was already equal to the W7 endpoint.

Import #230's Rev1 source-validated reader; do not construct a second memory
scanner or make calls to Dolphin. No user RAM/addresses/f32/hash/path stdout.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

SCRIPT_DIR = str(Path(__file__).resolve().parent)
if SCRIPT_DIR in sys.path:
    sys.path.remove(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)
import audit_p0_seven_source_trajectory_private as upstream

REQUIRED = tuple(range(1, 8))
WITHIN_SHOT = ((1, 2), (5, 6), (6, 7), (5, 7))
CURRENT = "ball_nested_plus_0x4c"
INPUT = "record_0x060"
MIRROR = "record_0x054"
CACHES = ("ball_cache_0x0cc", "ball_cache_0x0f0", "ball_cache_0x0fc")
REFERENCES = ("source_current_start", "source_selected_pin")


def _equal(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    if (type(a) is not tuple or type(b) is not tuple or len(a) != 3 or len(b) != 3
            or any(type(x) is not int or not 0 <= x <= 0xFFFFFFFF for x in a + b)):
        raise ValueError("selected source triplets must contain three u32 values")
    return sum(x == y for x, y in zip(a, b))


def summarize(samples: dict[int, dict]) -> dict:
    """Operates on trusted source samples. Returns relationships, not memory."""
    if set(samples) != set(REQUIRED):
        raise ValueError("require exactly seven source-gated numbered samples")
    for phase, sample in samples.items():
        if (type(sample.get("selected_index")) is not int
                or type(sample.get("hole")) is not int
                or sample.get("ball_alias_validated") is not True
                or sample.get("pin_selfref_validated") is not True
                or sample.get("start_selfref_validated") is not True):
            raise ValueError("source object/constructor identity gate failed")
        if set(sample.get("refs", {})) != {"scene_field", "ball", "pin", "start"}:
            raise ValueError("source identity references incomplete")
        vectors = sample.get("triplets", {})
        expected = {CURRENT, INPUT, MIRROR, *CACHES, *REFERENCES, "ball_object_0x030"}
        if not expected.issubset(vectors):
            raise ValueError("missing source-selected writer input/cache/negative control")
        if _equal(vectors[CURRENT], vectors["ball_object_0x030"]) != 3:
            raise ValueError("ball nested +0x4c must alias ball object +0x30")
        for name in expected:
            _equal(vectors[name], vectors[name])
    for a, b in WITHIN_SHOT:
        x, y = samples[a], samples[b]
        if x["selected_index"] != y["selected_index"] or x["hole"] != y["hole"]:
            raise ValueError("within-shot owner/hole identity changed")
        if any(x["refs"][name] != y["refs"][name] for name in ("scene_field","ball","pin","start")):
            raise ValueError("within-shot source pointer identity changed")
    per_snapshot = []
    for phase in REQUIRED:
        x = samples[phase]["triplets"]
        live = x[CURRENT]
        per_snapshot.append({
            "phase": phase,
            "source_live_equals_player_record_0x060_components": _equal(live, x[INPUT]),
            "source_live_equals_player_record_0x054_components": _equal(live, x[MIRROR]),
            "record_0x054_equals_0x060_components": _equal(x[MIRROR], x[INPUT]),
            "source_live_equals_cache_CC_components": _equal(live, x[CACHES[0]]),
            "source_live_equals_cache_F0_components": _equal(live, x[CACHES[1]]),
            "source_live_equals_cache_FC_components": _equal(live, x[CACHES[2]]),
            "source_live_equals_start_components": _equal(live, x[REFERENCES[0]]),
            "source_live_equals_pin_components": _equal(live, x[REFERENCES[1]]),
        })
    per_pair = []
    for a, b in WITHIN_SHOT:
        x, y = samples[a]["triplets"], samples[b]["triplets"]
        per_pair.append({
            "pair": f"{a}_to_{b}",
            "live_changed_components": 3 - _equal(x[CURRENT], y[CURRENT]),
            "record_0x060_changed_components": 3 - _equal(x[INPUT], y[INPUT]),
            "record_0x054_changed_components": 3 - _equal(x[MIRROR], y[MIRROR]),
            "cache_CC_changed_components": 3 - _equal(x[CACHES[0]], y[CACHES[0]]),
            "cache_F0_changed_components": 3 - _equal(x[CACHES[1]], y[CACHES[1]]),
            "cache_FC_changed_components": 3 - _equal(x[CACHES[2]], y[CACHES[2]]),
            "source_start_changed_components": 3 - _equal(x[REFERENCES[0]], y[REFERENCES[0]]),
            "source_pin_changed_components": 3 - _equal(x[REFERENCES[1]], y[REFERENCES[1]]),
        })
    w = {phase: samples[phase]["triplets"] for phase in (5, 6, 7)}
    const_record_input = len({w[p][INPUT] for p in w}) == 1
    distinct_live = len({w[p][CURRENT] for p in w})
    cache_cc_static = len({w[p][CACHES[0]] for p in w}) == 1
    result = {
        "kind": "P0-PRIVATE-SEVEN-SOURCE-SELECTED-WRITER-INPUT-RELATIONSHIPS",
        "schema_version": 1,
        "sample_count_source_gated": 7,
        "all_required_source_alias_and_owner_gates": True,
        "per_snapshot_equal_components": per_snapshot,
        "within_shot_component_differences": per_pair,
        "wedge_record_0x060_bitwise_constant": const_record_input,
        "wedge_current_ball_distinct_triplet_count": distinct_live,
        "wedge_cache_CC_bitwise_constant": cache_cc_static,
        "wedge_static_cache_CC_equal_final_W7_live": (
            cache_cc_static and _equal(w[5][CACHES[0]], w[7][CURRENT]) == 3
        ),
        "wedge_static_cache_CC_differs_from_live_W5": (
            cache_cc_static and _equal(w[5][CACHES[0]], w[5][CURRENT]) != 3
        ),
        "wedge_static_cache_CC_differs_from_live_W6": (
            cache_cc_static and _equal(w[6][CACHES[0]], w[6][CURRENT]) != 3
        ),
        "wedge_constant_record_input_not_sufficient_as_sole_snapshot_state_source":
            const_record_input and distinct_live > 1,
        "player_record_static_writer_path_source_documented": True,
        "player_record_writer_executed_between_snapshots_verified": False,
        "cache_refresh_code_known_but_runtime_receiver_identity_verified": False,
        "global_ball_pointer_runtime_identity_verified": False,
        "cache_CC_is_predicted_landing_endpoint_verified": False,
        "native_mem1_mem2_same_guest_frame_verified": False,
        "independent_frame_delta_verified": False,
        "actual_ball_world_xyz_axes_units_verified": False,
        "physical_velocity_verified": False,
        "approved_for_training": False,
        "allowed_to_publish": False,
        "interpretation": (
            "Per-phase source-selected u32 relationships only. A stable player "
            "record with changing ball object cannot alone explain all "
            "snapshot states via a simple immediate copy, but writes could "
            "occur between snapshots and reset. Cache equal to final ball "
            "does not establish precomputation, execution timing or receiver."
        ),
    }
    return result


def run_local(folder: Path) -> dict:
    folder = upstream._private_directory(folder)
    pairs = {i: upstream._phase_banks(folder, i) for i in REQUIRED}
    if any(value is None for value in pairs.values()):
        raise ValueError("seven complete numbered 24MiB/64MiB source pairs required")
    samples = {}
    for phase in REQUIRED:
        paths = pairs[phase]
        digests = {name: upstream._hash(path) for name, path in paths.items()}
        with ExitStack() as stack:
            maps = {}
            for bank, path in paths.items():
                f = stack.enter_context(path.open("rb"))
                maps[bank] = stack.enter_context(mmap.mmap(
                    f.fileno(), 0, access=mmap.ACCESS_READ))
            samples[phase] = upstream._source_sample(maps["MEM1"], maps["MEM2"])
        for name, path in paths.items():
            if upstream._hash(path) != digests[name]:
                raise ValueError("source bank changed during read-only inspection")
    return summarize(samples)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump-directory", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = run_local(args.dump_directory)
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        print("P0 SEVEN WRITER INPUTS ABSTAIN: source-gated native owner, pin/ball alias, "
              "bank length/hash or required phase failed; no private bytes printed.", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
