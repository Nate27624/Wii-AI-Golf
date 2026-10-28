"""Local-only phase-negative-control triage of candidate RPGolPlayer windows.

Consumes 4 paired native MRAM/ExRAM checkpoints from one operator-described
session. Re-resolves source-gated object graph and module .data/.text witnesses
at every checkpoint, compares only first 0x80 player candidate bytes. No raw
memory, live Dolphin input, shot, physical coordinates, or power inference.
"""
from __future__ import annotations

from contextlib import ExitStack
import json
import mmap
from pathlib import Path

from wii_ai_golf.audit.golf_cross_bank_state import (
    _Banks, audit_pair, MEM1_SIZE, MEM2_SIZE, STATIC_SCENE_SLOTS)
from wii_ai_golf.audit.golf_player_owner_evidence import (
    PLAYER_DATA, PLAYER_TEXT, _table_evidence)

WINDOW = 0x80
TOP_LIMIT = 24


def player_window(mem1, mem2, *, strict_size=True):
    audit_pair(mem1, mem2, strict_size=strict_size)
    b = _Banks(mem1, mem2)
    scene_manager = next(
        b.u32(slot) for slot in STATIC_SCENE_SLOTS
        if b.region(b.u32(slot), 0x20))
    scene = b.u32(scene_manager+0x0C)
    main = b.u32(scene+0x9C)
    candidate = b.u32(main+0x030)
    if _table_evidence(b, candidate, PLAYER_DATA, PLAYER_TEXT) is None:
        raise ValueError("GolfMain+0x030 no longer source-player-like")
    return bytes(b.read(candidate, WINDOW))


def compare_player_control_pairs(pairs, *, strict_size=True):
    """Four B0/B1/B2/B3 pairs of (MEM1, MEM2) binary memory banks."""
    if len(pairs) != 4 or any(len(pair) != 2 for pair in pairs):
        raise ValueError("Expected four paired checkpoints")
    samples = [player_window(a,b,strict_size=strict_size) for a,b in pairs]
    changed = []
    counters = {
        "idle_B0_B1_changed_words": 0,
        "aim_B1_B2_changed_words": 0,
        "return_B2_B3_changed_words": 0,
        "stable_idle_changed_aim_words": 0,
        "aim_only_reverted_to_B1_words": 0,
        "aim_only_persisted_at_B3_words": 0,
    }
    for off in range(0,WINDOW,4):
        v0,v1,v2,v3 = [s[off:off+4] for s in samples]
        idle,aim,release = (v0 != v1), (v1 != v2), (v2 != v3)
        stable_aim = (not idle and aim)
        reverted = stable_aim and v3 == v1
        persisted = stable_aim and v3 == v2
        counters["idle_B0_B1_changed_words"] += idle
        counters["aim_B1_B2_changed_words"] += aim
        counters["return_B2_B3_changed_words"] += release
        counters["stable_idle_changed_aim_words"] += stable_aim
        counters["aim_only_reverted_to_B1_words"] += reverted
        counters["aim_only_persisted_at_B3_words"] += persisted
        if idle or aim or release:
            changed.append({
                "candidate_player_relative_offset": f"+0x{off:03X}",
                "idle_changed": idle,
                "aim_transition_changed": aim,
                "return_transition_changed": release,
                "stable_idle_then_changed_aim": stable_aim,
                "returned_to_B1_value": reverted,
                "persisted_into_B3": persisted,
                "source_field_name": "UNKNOWN",
                "physical_semantics_verified": False,
            })
    # Discovery sort: distinguish timed idle/control from any candidate aim-only.
    changed.sort(key=lambda x: (
        not x["stable_idle_then_changed_aim"],
        not x["returned_to_B1_value"],
        x["idle_changed"],
        x["candidate_player_relative_offset"]))
    return {
        "schema_version": 1,
        "kind": "local-private-player-candidate-four-phase-null-control",
        "game_id": "RSPE01", "revision": 1, "game_mode": 4,
        "source_chain_and_player_like_code_evidence_checked_each_checkpoint": True,
        "main_to_player_candidate_relative_offset": "+0x030",
        "player_candidate_window_bytes": WINDOW,
        "aligned_words_checked": WINDOW // 4,
        "counters": counters,
        "candidates": changed[:TOP_LIMIT],
        "candidates_omitted": max(0,len(changed)-TOP_LIMIT),
        "only_one_B0_B1_idle_comparison": True,
        "same_boot_and_input_phase_labels_independently_proven": False,
        "clock_controls_complete": False,
        "real_swing_recorded": False,
        "club_angle_verified": False,
        "power_verified": False,
        "ball_world_position_verified": False,
        "actual_cpp_type_verified": False,
        "raw_memory_or_runtime_pointers_exported": False,
        "allowed_to_publish": False,
        "next_action": "Investigate only stable-idle/changed-aim candidates in "
                       "RPGolPlayer source write-PC disassembly, then repeat "
                       "across fresh boots and input-control levels. "
                       "No training labels from this negative-control test.",
    }


def compare_player_control_files(pairs, *, private_root, output):
    root = Path(private_root).resolve(strict=True)
    out = Path(output)
    if (not root.is_dir() or out.exists() or out.is_symlink()
            or out.parent.resolve(strict=True) != root
            or out.suffix.lower() != ".json"
            or len(pairs) != 4):
        raise ValueError("Invalid paired private memory paths or output")
    paths = []
    for a,b in pairs:
        for p,size in ((Path(a),MEM1_SIZE),(Path(b),MEM2_SIZE)):
            if (not p.is_file() or p.is_symlink()
                    or p.resolve(strict=True).is_relative_to(root) is False
                    or p.stat().st_size != size):
                raise ValueError("Missing/invalid private native bank")
            paths.append(p.resolve(strict=True))
    if len(set(paths)) != 8:
        raise ValueError("Paired files must be eight independent paths")
    with ExitStack() as stack:
        files = [stack.enter_context(open(p,"rb")) for p in paths]
        mapped = [stack.enter_context(mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ))
                  for f in files]
        report = compare_player_control_pairs(
            [(mapped[i],mapped[i+1]) for i in range(0,8,2)],strict_size=True)
    with out.open("x",encoding="utf-8") as fp:
        json.dump(report,fp,indent=2,sort_keys=True,allow_nan=False)
        fp.write("\n")
    return report
