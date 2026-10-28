"""OFFLINE private cache-coherence audit for preserved B0 and in-flight pair.

Source gating/manifest verification are re-used from S002 PR #223. Answer
ONLY whether candidate +0x30 and ball caches +0xCC/+0xF0/+0xFC
contain the same three 32-bit words WITHIN each snapshot. Never decode or
print numeric vectors, pointer values, native memory or hashes. These are
not four independent pieces of position evidence if they alias.
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

# Python -I does not automatically include the script directory.
SCRIPT_DIR = str(Path(__file__).resolve().parent)
if SCRIPT_DIR in sys.path:
    sys.path.remove(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)

import audit_p0_inflight_vs_b0_private as base

VECTOR_NAMES = (
    "ball_nested_plus_0x4c",
    "ball_object_0x030",
    "ball_cache_0x0cc",
    "ball_cache_0x0f0",
    "ball_cache_0x0fc",
)
PAIRS = (
    ("ball_nested_plus_0x4c", "ball_object_0x030"),
    ("ball_nested_plus_0x4c", "ball_cache_0x0cc"),
    ("ball_nested_plus_0x4c", "ball_cache_0x0f0"),
    ("ball_nested_plus_0x4c", "ball_cache_0x0fc"),
    ("ball_cache_0x0cc", "ball_cache_0x0f0"),
    ("ball_cache_0x0cc", "ball_cache_0x0fc"),
    ("ball_cache_0x0f0", "ball_cache_0x0fc"),
    ("record_0x054", "ball_nested_plus_0x4c"),
    ("record_0x060", "ball_nested_plus_0x4c"),
    ("source_current_start", "ball_nested_plus_0x4c"),
)
MEM1 = base.roster.MEM1_SIZE
MEM2 = base.roster.MEM2_SIZE


def _bounded_three_float_words(words: tuple) -> bool:
    if type(words) is not tuple or len(words) != 3:
        return False
    try:
        vals = [struct.unpack(">f", struct.pack(">I", v))[0]
                for v in words if type(v) is int and 0 <= v <= 0xFFFFFFFF]
    except (struct.error, OverflowError):
        return False
    return (len(vals) == 3 and
            all(math.isfinite(f) and abs(f) <= 100000.0 for f in vals))


def _phase(sample: dict) -> dict:
    vectors = sample["triplets"]
    if not all(name in vectors and type(vectors[name]) is tuple
               and len(vectors[name]) == 3 for name in set(VECTOR_NAMES).union(
                   name for pair in PAIRS for name in pair)):
        raise ValueError("missing source-gated vector")
    if sample.get("ball_constructor_translation_selfref") is not True:
        raise ValueError("source-selected +0x4C pointer does not self-reference +0x30")
    if vectors["ball_nested_plus_0x4c"] != vectors["ball_object_0x030"]:
        raise ValueError("source ball nested and +0x30 alias disagree")
    groups = {}
    for name in VECTOR_NAMES:
        value = vectors[name]
        groups.setdefault(value, []).append(name)
    return {
        "source_selected_ball_alias_selfref_validated": True,
        "unique_ball_related_three_word_bit_patterns": len(groups),
        "bitwise_identical_candidate_groups": list(groups.values()),
        "pairwise_equal_component_counts": {
            a + "__vs__" + b: sum(x == y for x, y in zip(vectors[a], vectors[b]))
            for a, b in PAIRS
        },
        "candidate_three_float_finite_bounded": {
            name: _bounded_three_float_words(vectors[name])
            for name in VECTOR_NAMES
        },
        "actual_ball_world_xyz_verified": False,
        "cache_role_or_semantics_verified": False,
    }


def compare(b0: dict, flight: dict) -> dict:
    if (b0.get("selected_index") != flight.get("selected_index")
            or b0.get("hole") != flight.get("hole")):
        raise ValueError("source owner slot/hole mismatch")
    first, second = _phase(b0), _phase(flight)
    cache_names = VECTOR_NAMES[2:]
    return {
        "kind": "PRIVATE-SANITIZED-INFLIGHT-BALL-CACHE-COHERENCE",
        "schema_version": 1,
        "source_selected_slot_and_hole_match": True,
        "phases": {"B0_stationary_original": first,
                   "airborne_operator": second},
        "all_three_caches_equal_current_ball_within_B0": all(
            first["pairwise_equal_component_counts"][
                "ball_nested_plus_0x4c__vs__" + name] == 3
            for name in cache_names),
        "all_three_caches_equal_current_ball_within_airborne": all(
            second["pairwise_equal_component_counts"][
                "ball_nested_plus_0x4c__vs__" + name] == 3
            for name in cache_names),
        "five_cross_phase_3_component_changes_independent_evidence": False,
        "same_boot_proven": False,
        "mem1_mem2_exports_same_guest_frame_verified": False,
        "actual_ball_world_xyz_verified": False,
        "actual_velocity_or_power_verified": False,
        "approved_for_training": False,
        "allowed_to_publish": False,
        "warning": "Equal cache contents are source-linked redundancy candidates, not distinct proofs of physical movement. Different cache contents can reflect lagged copies/scene phases. Human-airborne annotation is not guest-frame timing.",
    }


def run_local(baseline: Path, flight: Path) -> dict:
    private_root = base.selected.DATA_ROOT.resolve(strict=True)
    b0 = base._under_data(baseline, private_root)
    airborne = base._under_data(flight, private_root)
    if b0 == airborne:
        raise ValueError("identical private input directory")
    manifest = base.four._validate_manifest(b0)
    base._flight_manifest(airborne)
    for name, bank in (("B0-MEM1.bin", "MEM1"), ("B0-MEM2.bin", "MEM2")):
        expected = manifest["B0"]["sha256"][bank].lower()
        if base._hash_file(base._file(b0, name, base.roster.MEM1_SIZE
                                     if bank == "MEM1" else base.roster.MEM2_SIZE)) != expected:
            raise ValueError("original B0 manifest hash mismatched")
    with ExitStack() as stack:
        samples = []
        for folder, names in (
            (b0, ("B0-MEM1.bin", "B0-MEM2.bin")),
            (airborne, ("mem1.raw", "mem2.raw")),
        ):
            maps = []
            for name, size in zip(names, (MEM1, MEM2)):
                stream = stack.enter_context(base._file(folder, name, size).open("rb"))
                maps.append(stack.enter_context(mmap.mmap(
                    stream.fileno(), 0, access=mmap.ACCESS_READ)))
            samples.append(base._sample(base.roster.TwoBankReader(*maps)))
        return compare(*samples)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--flight", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        report = run_local(args.baseline, args.flight)
    except (OSError, ValueError, TypeError, KeyError, OverflowError, struct.error,
            json.JSONDecodeError):
        print("PRIVATE CACHE COHERENCE FAILED CLOSED: hashes, source chain, "
              "alias or relative snapshot layout not validated. No RAM printed.",
              file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
