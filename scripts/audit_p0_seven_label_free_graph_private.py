"""P0: label-agnostic seven-capture source-context/equality graph (offline only).

Operates on seven ORIGINAL SHA-verified source-selected Golf RAM pairs, but
DOES NOT trust operator labels, ordering, shot membership, club or render state.
All 21 unordered comparisons are purely snapshot relationships, not trajectories.
No raw memory words, float values, runtime addresses, hashes or paths on stdout.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

_HERE = str(Path(__file__).resolve().parent)
if _HERE in sys.path:
    sys.path.remove(_HERE)
sys.path.insert(0, _HERE)
import audit_p0_seven_numbered_source_pairs_private as seven
import audit_golf_two_bank_roster_private as roster

CAPTURES = tuple(range(1, 8))
VECTOR_KEYS = ("ball_object_0x030", "ball_cache_0x0cc",
               "ball_cache_0x0f0", "ball_cache_0x0fc",
               "source_current_start")


def _words_equal(a, b):
    if len(a) != 3 or len(b) != 3:
        raise ValueError("invalid three-word source vector")
    return sum(x == y for x, y in zip(a, b))


def _count_changed(a, b):
    return 3 - _words_equal(a, b)


def source_state(reader):
    """Extend #231's source-gated sample only with proven owner references.

    Private object identities and raw triples stay inside this process; never
    serialize the result of this function.
    """
    s = seven._get(reader)
    u = reader.u32
    slot, hole = s["selected_index"], s["hole"]
    if (type(slot) is not int or slot not in range(4)
            or type(hole) is not int or hole not in range(9)):
        raise ValueError("invalid source-selected slot/hole")
    pm = u(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    cfg = u(roster.GOLF_CONFIG_STATIC)
    field = u(roster.GOLF_FIELD_STATIC)
    rec = pm + 4 + slot * roster.ROSTER_STRIDE
    if (roster._bank(rec, roster.ROSTER_STRIDE) != "MEM2"
            or roster._bank(cfg, 0xC8) != "MEM2"
            or roster._bank(field, 0x54) != "MEM2"
            or u(pm + 0x334) != rec):
        raise ValueError("source owner chain drift")
    ball = u(rec + 0x88)
    if (roster._bank(ball, 0x108) != "MEM2"
            or u(ball + 0x4C) != ball + 0x30
            or u(field + 0x44) != s["pin_obj"]
            or u(field + 0x50) != s["start_obj"]):
        raise ValueError("source selected ball or target identity drift")
    vectors = {key: s["triplets"][key] for key in VECTOR_KEYS}
    vectors["source_pin"] = s["pin"]
    # A context match is NOT same-shot/boot/frame proof. These are strict
    # source-selection and scene geometry comparability keys only.
    context = (slot, hole, pm, cfg, field, rec, ball,
               s["pin_obj"], s["start_obj"],
               s["cfg_bc"], s["cfg_c0"], s["cfg_c4"],
               tuple(vectors["source_current_start"]), tuple(s["pin"]))
    return {"context": context, "vectors": vectors}


def _validated_state(value):
    if type(value) is not dict or set(value) != {"context", "vectors"}:
        raise ValueError("unexpected source graph sample")
    context = value["context"]
    vec = value["vectors"]
    if type(context) is not tuple or len(context) != 14:
        raise ValueError("invalid private context length")
    if any(type(item) is not int or not 0 <= item <= 0xFFFFFFFF
           for item in context[:12]):
        raise ValueError("invalid source context word")
    if (type(context[12]) is not tuple or type(context[13]) is not tuple
            or len(context[12]) != 3 or len(context[13]) != 3):
        raise ValueError("invalid source geometry")
    if type(vec) is not dict or set(vec) != set(VECTOR_KEYS) | {"source_pin"}:
        raise ValueError("invalid vector key set")
    for words in list(vec.values()) + [context[12], context[13]]:
        if type(words) not in (tuple, list) or len(words) != 3:
            raise ValueError("invalid source triplet shape")
        if any(type(w) is not int or not 0 <= w <= 0xFFFFFFFF for w in words):
            raise ValueError("invalid source triplet word")
    if tuple(vec["source_current_start"]) != context[12] or tuple(vec["source_pin"]) != context[13]:
        raise ValueError("source geometry context disagrees")


def summarize(states):
    """All 21 unordered capture pairs, invariant to human phase descriptions.

    Capture NUMBER is used only as an immutable filename identifier, not a
    temporal index or a claimed actual swing/shot sequence.
    """
    if type(states) is not dict or set(states) != set(CAPTURES):
        raise ValueError("exact seven capture identifiers required")
    for n in CAPTURES:
        _validated_state(states[n])

    # Assign stable group IDs in first-capture encounter order, never output
    # the private group key (which includes dynamic pointers and raw words).
    context_to_group = {}
    groups = {}
    for n in CAPTURES:
        key = states[n]["context"]
        if key not in context_to_group:
            context_to_group[key] = len(context_to_group) + 1
        groups[n] = context_to_group[key]

    nodes = []
    for n in CAPTURES:
        vec = states[n]["vectors"]
        nodes.append({
            "capture_number_not_elapsed_time": n,
            "source_context_equivalence_group": groups[n],
            "current_equals_own_start_components": _words_equal(
                vec["ball_object_0x030"], vec["source_current_start"]),
            "current_equals_own_cache_CC_components": _words_equal(
                vec["ball_object_0x030"], vec["ball_cache_0x0cc"]),
            "cache_CC_equals_own_start_components": _words_equal(
                vec["ball_cache_0x0cc"], vec["source_current_start"]),
        })
    pairs = []
    for a in CAPTURES:
        for b in CAPTURES:
            if b <= a:
                continue
            same_context = groups[a] == groups[b]
            x = states[a]["vectors"]
            y = states[b]["vectors"]
            # Incomparable contexts ABSTAIN instead of printing misleading
            # deltas that may just be scene/owner/target changes.
            pair = {
                "capture_pair_unordered": [a, b],
                "same_source_owner_hole_pin_tee_and_config": same_context,
                "same_physical_shot_verified": False,
                "number_order_proves_time_order": False,
                "current_changed_components": None,
                "cache_CC_changed_components": None,
                "cache_F0_changed_components": None,
                "cache_FC_changed_components": None,
                "both_current_triplets_equal": None,
                "both_cache_CC_triplets_equal": None,
            }
            if same_context:
                pair.update({
                    "current_changed_components": _count_changed(
                        x["ball_object_0x030"], y["ball_object_0x030"]),
                    "cache_CC_changed_components": _count_changed(
                        x["ball_cache_0x0cc"], y["ball_cache_0x0cc"]),
                    "cache_F0_changed_components": _count_changed(
                        x["ball_cache_0x0f0"], y["ball_cache_0x0f0"]),
                    "cache_FC_changed_components": _count_changed(
                        x["ball_cache_0x0fc"], y["ball_cache_0x0fc"]),
                    "both_current_triplets_equal":
                        x["ball_object_0x030"] == y["ball_object_0x030"],
                    "both_cache_CC_triplets_equal":
                        x["ball_cache_0x0cc"] == y["ball_cache_0x0cc"],
                })
            pairs.append(pair)
    assert len(pairs) == 21
    return {
        "kind": "P0-SANITIZED-SEVEN-LABEL-AGNOSTIC-SOURCE-CONTEXT-GRAPH",
        "capture_count": len(CAPTURES),
        "unordered_pairs_exhaustively_compared": len(pairs),
        "source_context_group_count": len(context_to_group),
        "original_archive_SHA_checked_before_and_after": True,
        "operator_reported_phase_labels_used_as_ground_truth": False,
        "capture_number_is_not_frame_or_time_order": True,
        "source_context_match_is_not_proof_of_same_shot": True,
        "human_phase_to_file_mapping_machine_verified": False,
        "physical_ball_xyz_verified": False,
        "velocity_or_impact_verified": False,
        "power_or_score_verified": False,
        "landing_endpoint_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
        "nodes": nodes,
        "pairs": pairs,
    }


def analyze(archive: Path):
    folders = seven._check_archive(archive)  # SHA-check original 14 banks.
    states = {}
    with ExitStack() as stack:
        for n in CAPTURES:
            mem = []
            for bank_index, size in enumerate(seven.SIZE):
                path = seven.src._file(folders[n], f"{n}.{bank_index+1}.raw", size)
                handle = stack.enter_context(path.open("rb"))
                mem.append(stack.enter_context(mmap.mmap(
                    handle.fileno(), 0, access=mmap.ACCESS_READ)))
            states[n] = source_state(roster.TwoBankReader(*mem))
        report = summarize(states)
    seven._check_archive(archive)  # No hash drift while analysis performed.
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = analyze(args.archive)
    except (OSError, ValueError, KeyError, TypeError,
            OverflowError, AttributeError, json.JSONDecodeError):
        print("P0 LABEL-FREE GRAPH ABSTAIN: private archive, Rev1 source"
              " identity, context or hash check failed.", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
