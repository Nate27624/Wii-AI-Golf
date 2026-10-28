"""S002 full-state baseline: conservative OFFLINE comparison of four MEM1 dumps.

Input: operator's *private*, native Dolphin/Felk raw MEM1 dumps B0/B1/B2/B3.
No emulation, controller input, network, Git publication, file modification,
or raw value/pointer/address/path output. See PR #148 for field study design.

Source layout gates constrain comparisons to a stable Wii Sports RSPE01 Rev1
Hitting-the-Green scene; matching known offsets is not proof that individual
changed bytes are power, club pose, physics, or score.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import struct
import sys

MEM1_BASE = 0x80000000
MEM1_BYTES = 24 * 1024 * 1024
ALLOWED_DUMP_SIZES = (MEM1_BYTES, 32 * 1024 * 1024)
PAGE_BYTES = 4096
MAX_PUBLIC_PAGES = 24
SOURCE_MODE_GLOBAL = 0x804BF8C4
SOURCE_MANAGER_GLOBAL = 0x804BF4D8
RSPE01_REV1 = b"RSPE01\x00\x01"


def _u32(mem: mmap.mmap, addr: int) -> int:
    offset = addr - MEM1_BASE
    if type(addr) is not int or addr % 4 or offset < 0 or offset + 4 > MEM1_BYTES:
        raise ValueError("required source object cannot be checked inside MEM1")
    return struct.unpack_from(">I", mem, offset)[0]


def _mem1_ptr(value: int, width: int) -> bool:
    return (type(value) is int and value % 4 == 0 and
            MEM1_BASE <= value and value + width <= MEM1_BASE + MEM1_BYTES)


def validate_snapshot(mem: mmap.mmap) -> tuple[int, int, int, int]:
    if mem[:8] != RSPE01_REV1:
        raise ValueError("unexpected game ID or disc revision in MEM1")
    cfg = _u32(mem, SOURCE_MODE_GLOBAL)
    if not _mem1_ptr(cfg, 0x98) or _u32(mem, cfg + 0x94) != 4:
        raise ValueError("Hitting the Green mode 4 is not validated")
    mgr = _u32(mem, SOURCE_MANAGER_GLOBAL)
    if not _mem1_ptr(mgr, 0x1C):
        raise ValueError("scene manager pointer cannot be validated in MEM1")
    if _u32(mem, mgr + 0x18) != 5:
        raise ValueError("active manager scene is not Golf ID 5")
    scene = _u32(mem, mgr + 0x0C)
    if not _mem1_ptr(scene, 0xA0):
        raise ValueError("active scene pointer cannot be validated in MEM1")
    if (_u32(mem, scene + 0x1C) != 5 or _u32(mem, scene + 0x20) != mgr
            or _u32(mem, scene + 0x54) != 2):
        raise ValueError("scene ID, manager backlink or sport gate failed")
    candidate_main = _u32(mem, scene + 0x9C)
    if not _mem1_ptr(candidate_main, 4):
        # Main pointer type is still unverified; do not dereference.
        raise ValueError("scene member +0x9C does not name an in-MEM1 candidate")
    return cfg, mgr, scene, candidate_main


def compare_mem1(mems: tuple[mmap.mmap, mmap.mmap, mmap.mmap, mmap.mmap],
                 *, max_pages: int = MAX_PUBLIC_PAGES) -> dict:
    if len(mems) != 4:
        raise ValueError("exactly four checkpoints are required")
    if type(max_pages) is not int or not 1 <= max_pages <= MAX_PUBLIC_PAGES:
        raise ValueError("public page cap must be between 1 and 24")
    sizes = [len(m) for m in mems]
    if len(set(sizes)) != 1 or sizes[0] not in ALLOWED_DUMP_SIZES:
        raise ValueError("MEM1 dump sizes differ or are not recognized")
    identities = [validate_snapshot(m) for m in mems]
    if len(set(identities)) != 1:
        raise ValueError("golf source scene / object identity changed between checkpoints")
    totals = Counter()
    changed_pages = []
    for offset in range(0, MEM1_BYTES, PAGE_BYTES):
        a, b, c, d = (m[offset:offset + PAGE_BYTES] for m in mems)
        if a == b == c == d:
            continue
        counts = Counter()
        # Wii PPC words are big-endian; compare 32-bit units, not floats or
        # decoded power. Content is processed in memory and NEVER returned.
        for wa, wb, wc, wd in zip(
                struct.iter_unpack(">I", a), struct.iter_unpack(">I", b),
                struct.iter_unpack(">I", c), struct.iter_unpack(">I", d)):
            wa, wb, wc, wd = wa[0], wb[0], wc[0], wd[0]
            if wa != wb:
                counts["idle_changed_words"] += 1
            if wb != wc:
                counts["pointer_stage_changed_words"] += 1
            if wc != wd:
                counts["return_stage_changed_words"] += 1
            if wa != wd:
                counts["baseline_to_final_changed_words"] += 1
            if wa == wb and wc != wb and wd == wa:
                counts["b2_only_stable_idle_words"] += 1
            if wa == wb and wc != wb and wd == wc:
                counts["post_pointer_persistent_words"] += 1
        if not counts:
            continue
        counts["page_relative_index"] = offset // PAGE_BYTES
        counts["page_has_idle_drift"] = counts["idle_changed_words"] > 0
        changed_pages.append(dict(counts))
        for k, v in counts.items():
            if k not in ("page_relative_index", "page_has_idle_drift"):
                totals[k] += v
    # A single B0/B1/B2/B3 sequence is NOT independent or necessarily
    # action-causal. Prioritize candidate pages with idle-stable changes.
    changed_pages.sort(key=lambda p: (
        -p.get("b2_only_stable_idle_words", 0),
        -p.get("post_pointer_persistent_words", 0),
        p["page_has_idle_drift"],
        -p.get("pointer_stage_changed_words", 0),
        p["page_relative_index"],
    ))
    safe_keys = (
        "idle_changed_words", "pointer_stage_changed_words",
        "return_stage_changed_words", "baseline_to_final_changed_words",
        "b2_only_stable_idle_words", "post_pointer_persistent_words",
    )
    return {
        "schema_version": 1,
        "kind": "local_mem1_four_checkpoint_source_gated_diff",
        "study_id": "S002-FULL-STATE-BASELINE-01",
        "game_id": "RSPE01",
        "revision": 1,
        "training_mode": 4,
        "golf_scene_id": 5,
        "scene_identity_stable_in_four_copies": True,
        "raw_gameplay_type_verified": False,
        "golf_main_type_verified": False,
        "club_pose_verified": False,
        "game_power_verified": False,
        "ball_position_verified": False,
        "score_verified": False,
        "checkpoints": ["B0_idle", "B1_timed_idle", "B2_pointer_only", "B3_return_idle"],
        "mem1_compared_bytes": MEM1_BYTES,
        "trailing_export_bytes_not_analyzed": sizes[0] - MEM1_BYTES,
        "u32_words_per_page": PAGE_BYTES // 4,
        "changed_pages": len(changed_pages),
        "changed_word_comparisons": {key: totals[key] for key in safe_keys},
        "candidate_page_count_reported": min(len(changed_pages), max_pages),
        "candidate_pages_truncated": len(changed_pages) > max_pages,
        "top_relative_pages": [
            {"page_relative_index": p["page_relative_index"],
             **{key: p.get(key, 0) for key in safe_keys},
             "page_has_idle_drift": p["page_has_idle_drift"],
             "source_object_verified": False,
             "swing_power_verified": False}
            for p in changed_pages[:max_pages]
        ],
        "human_pointer_action_verified_by_sensor": False,
        "independent_boots_verified": False,
        "capture_consistency_verified_by_simultaneous_freeze": False,
        "warning": (
            "Four *sequential* private GUI snapshots are not atomically "
            "time-aligned, randomized, or independent boots. Values and "
            "heap pointers never leave this analysis. A B2-specific page "
            "may be timer/UI/scene noise, not proven aim or club state. "
            "Only source-confirmed objects and repeated intervention/clock "
            "controls can upgrade a field's verification tier."
        ),
    }


def analyze_files(paths: list[Path], *, max_pages: int = MAX_PUBLIC_PAGES) -> dict:
    if len(paths) != 4:
        raise ValueError("exactly four checkpoints are required")
    resolved = []
    for p in paths:
        if not p.is_file() or p.is_symlink():
            raise ValueError("missing or symlinked private checkpoint")
        if p.suffix.lower() not in (".raw", ".bin"):
            raise ValueError("checkpoint extension is not raw or bin")
        if p.stat().st_size not in ALLOWED_DUMP_SIZES:
            raise ValueError("MEM1 checkpoint is not 24 MiB or 32 MiB")
        resolved.append(p.resolve())
    if len(set(resolved)) != 4:
        raise ValueError("checkpoint paths are not all distinct")
    with ExitStack() as stack:
        handles = [stack.enter_context(p.open("rb")) for p in paths]
        mmaps = [stack.enter_context(mmap.mmap(h.fileno(), 0, access=mmap.ACCESS_READ))
                 for h in handles]
        return compare_mem1(tuple(mmaps), max_pages=max_pages)


# Only fixed authored errors are emitted; never format private exceptions.
SAFE_ERRORS = frozenset({
    "exactly four checkpoints are required",
    "public page cap must be between 1 and 24",
    "MEM1 dump sizes differ or are not recognized",
    "unexpected game ID or disc revision in MEM1",
    "Hitting the Green mode 4 is not validated",
    "scene manager pointer cannot be validated in MEM1",
    "active manager scene is not Golf ID 5",
    "active scene pointer cannot be validated in MEM1",
    "scene ID, manager backlink or sport gate failed",
    "scene member +0x9C does not name an in-MEM1 candidate",
    "golf source scene / object identity changed between checkpoints",
    "missing or symlinked private checkpoint",
    "checkpoint extension is not raw or bin",
    "MEM1 checkpoint is not 24 MiB or 32 MiB",
    "checkpoint paths are not all distinct",
    "required source object cannot be checked inside MEM1",
})


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for stage in ("b0", "b1", "b2", "b3"):
        parser.add_argument("--" + stage, required=True, type=Path)
    parser.add_argument("--top-pages", type=int, default=MAX_PUBLIC_PAGES)
    args = parser.parse_args(argv)
    try:
        result = analyze_files([args.b0, args.b1, args.b2, args.b3],
                               max_pages=args.top_pages)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (ValueError, OSError, BufferError) as exc:
        message = str(exc)
        if message not in SAFE_ERRORS:
            message = "private checkpoint cannot be validated"
        print("Offline MEM1 audit stopped: " + message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
