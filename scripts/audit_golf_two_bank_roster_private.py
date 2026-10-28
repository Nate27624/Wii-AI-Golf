"""Read-only, PRIVATE, two-bank Wii Sports Rev1 golf roster candidate triage.

Requires a native 24MiB MEM1 and 64MiB MEM2. Follows ONLY pre-registered
source offsets (static singleton, scene, mode and candidate member slots).
No Dolphin/RPC/controller, write access, networking, upload, byte scans,
arbitrary pointer graph traversal, full RAM dumps or runtime addresses printed.

WARNING: The four repeated player/ball first-word interval matches are
STRUCTURAL HINTS, NOT proved C++ class types, active players or physics balls.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import struct
import sys

MEM1_BASE, MEM1_SIZE = 0x80000000, 24 * 1024 * 1024
MEM2_BASE, MEM2_SIZE = 0x90000000, 64 * 1024 * 1024

# Public RSPE01_01 decomp source / ogws_info.
SCENE_MANAGER_STATIC = 0x804BF4D8
GOLF_CONFIG_STATIC = 0x804BF8C4
GOLF_FIELD_STATIC = 0x804BF868
PLAYER_MANAGER_STATIC_CANDIDATE = 0x804BF8D0
SCENE_DATA = (0x803C7718, 0x803C7798)
MAIN_DATA = (0x803C7798, 0x803C77C0)
BALL_DATA = (0x803C7918, 0x803C7A50)
PLAYER_DATA = (0x803C7CC8, 0x803C7DD0)
PLAYER_MANAGER_DATA = (0x803C7DD0, 0x803C7DE0)
# Hypotheses from ONE private still snapshot. NOT public source class layout.
ROSTER_SLOTS = 4
ROSTER_STRIDE = 0xCC
BALL_CANDIDATE_MEMBER = 0x8C
PLAYER_CANDIDATE_MEMBER = 0xC8
MAIN_DIRECT_PLAYERLIKE_MEMBER = 0x30


def _bank(address: int, size: int = 4) -> str | None:
    if type(address) is not int or address % 4 or size <= 0:
        return None
    if MEM1_BASE <= address and address + size <= MEM1_BASE + MEM1_SIZE:
        return "MEM1"
    if MEM2_BASE <= address and address + size <= MEM2_BASE + MEM2_SIZE:
        return "MEM2"
    return None


def _in_data(address: int, interval: tuple[int, int]) -> bool:
    return type(address) is int and address % 4 == 0 and interval[0] <= address < interval[1]


# Public Rev1 PlayerManager.cpp compilation-unit .text, NOT a function list.
PLAYER_MANAGER_CODE = (0x802A2210, 0x802A3560)


def _code_stride_instruction_counts(read_u32) -> dict:
    """Only count PPC mulli/addi immediate 0xCC within bounded code unit.

    Source-side correlation is NOT proof that base+0x8C/+0xC8 are typed C++
    members. No instruction words or source binary bytes are returned.
    """
    mulli = addi = 0
    for address in range(*PLAYER_MANAGER_CODE, 4):
        word = read_u32(address)
        if word & 0xFFFF != ROSTER_STRIDE:
            continue
        if (word >> 26) == 7:  # mulli
            mulli += 1
        elif (word >> 26) == 14:  # addi
            addi += 1
    return {
        "ppc_manager_code_instructions_checked":
            (PLAYER_MANAGER_CODE[1] - PLAYER_MANAGER_CODE[0]) // 4,
        "ppc_mulli_immediate_matching_stride": mulli,
        "ppc_addi_immediate_matching_stride": addi,
        "ppc_member_register_dataflow_proven": False,
    }


class TwoBankReader:
    def __init__(self, mem1, mem2):
        if len(mem1) != MEM1_SIZE or len(mem2) != MEM2_SIZE:
            raise ValueError("native bank size mismatch")
        self.mem1, self.mem2 = mem1, mem2

    def u32(self, address: int) -> int:
        bank = _bank(address)
        if not bank:
            raise ValueError("source-directed address outside known RAM")
        base = MEM1_BASE if bank == "MEM1" else MEM2_BASE
        data = self.mem1 if bank == "MEM1" else self.mem2
        return struct.unpack_from(">I", data, address - base)[0]

    def header(self) -> bytes:
        return bytes(self.mem1[:8])


def triage(read_u32, header: bytes) -> dict:
    """Deterministic source-gated small-object hypothesis; zero raw-value output."""
    if type(header) is not bytes or len(header) != 8 or header[:6] != b"RSPE01" or header[7] != 1:
        raise ValueError("requires RSPE01 Rev1 plain MEM1 header")
    manager = read_u32(SCENE_MANAGER_STATIC)
    if _bank(manager) != "MEM1" or read_u32(SCENE_MANAGER_STATIC + 4) != 0:
        raise ValueError("source manager static storage mismatch")
    if read_u32(manager + 0x18) != 5:
        raise ValueError("not the active golf scene")
    scene = read_u32(manager + 0xC)
    if _bank(scene, 0xA0) != "MEM2":
        raise ValueError("active scene not in captured MEM2")
    scene_checks = {
        "scene_own_id": read_u32(scene + 0x1C) == 5,
        "manager_backlink": read_u32(scene + 0x20) == manager,
        "sport_id": read_u32(scene + 0x54) == 2,
        "scene_vtable_region": _in_data(read_u32(scene), SCENE_DATA),
    }
    if not all(scene_checks.values()):
        raise ValueError("active scene structural identity failed")

    config = read_u32(GOLF_CONFIG_STATIC)
    if _bank(config, 0x9C) != "MEM2" or read_u32(config + 0x94) != 4:
        raise ValueError("golf config training-mode source gate failed")
    field = read_u32(GOLF_FIELD_STATIC)
    if _bank(field, 0xA8) != "MEM2":
        raise ValueError("source golf field not mapped to MEM2")

    main = read_u32(scene + 0x9C)
    main_firstword_hint = (
        _bank(main, 0x34) == "MEM2"
        and _in_data(read_u32(main), MAIN_DATA)
    )
    pm = read_u32(PLAYER_MANAGER_STATIC_CANDIDATE)
    pm_firstword_hint = (
        _bank(pm, PLAYER_CANDIDATE_MEMBER + ROSTER_STRIDE * (ROSTER_SLOTS - 1) + 4) == "MEM2"
        and _in_data(read_u32(pm), PLAYER_MANAGER_DATA)
    )
    if not main_firstword_hint or not pm_firstword_hint:
        raise ValueError("source unit interval candidate identity failed")

    main_direct = read_u32(main + MAIN_DIRECT_PLAYERLIKE_MEMBER)
    main_direct_playerlike = (
        _bank(main_direct) == "MEM2"
        and _in_data(read_u32(main_direct), PLAYER_DATA)
    ) if _bank(main_direct) == "MEM2" else False

    paired = []
    balls, players = [], []
    for index in range(ROSTER_SLOTS):
        ball = read_u32(pm + BALL_CANDIDATE_MEMBER + index * ROSTER_STRIDE)
        player = read_u32(pm + PLAYER_CANDIDATE_MEMBER + index * ROSTER_STRIDE)
        ball_match = (_bank(ball) == "MEM2" and
                      _in_data(read_u32(ball), BALL_DATA)) if _bank(ball) == "MEM2" else False
        player_match = (_bank(player) == "MEM2" and
                        _in_data(read_u32(player), PLAYER_DATA)) if _bank(player) == "MEM2" else False
        paired.append(bool(ball_match and player_match))
        if ball_match:
            balls.append(ball)
        if player_match:
            players.append(player)

    all_pairs = all(paired)
    source_code_stride = _code_stride_instruction_counts(read_u32)
    return {
        "kind": "local_golf_source_gated_two_bank_roster_hypothesis",
        "schema_version": 1,
        "disc_id": "RSPE01",
        "disc_revision": 1,
        "mode4_source_gate_passed": True,
        "scene_source_identity_gates_passed": all(scene_checks.values()),
        "scene_main_candidate_firstword_in_main_data": main_firstword_hint,
        "player_manager_candidate_firstword_in_manager_data": pm_firstword_hint,
        "main_direct_child_firstword_in_player_data": main_direct_playerlike,
        "candidate_slot_count_examined": ROSTER_SLOTS,
        "candidate_stride_has_bounded_source_code_corroboration": (
            source_code_stride["ppc_mulli_immediate_matching_stride"] > 0
            and source_code_stride["ppc_addi_immediate_matching_stride"] > 0),
        "player_manager_source_code_stride_checks": source_code_stride,
        "ball_data_region_firstword_match_count": len(balls),
        "player_data_region_firstword_match_count": len(players),
        "slots_with_both_data_region_hints": sum(paired),
        "all_candidate_slots_pairwise_distinct": (
            all_pairs and len(set(balls)) == ROSTER_SLOTS
            and len(set(players)) == ROSTER_SLOTS),
        "sample_count": 1,
        "same_boot_or_same_frame_pair_independently_verified": False,
        "runtime_type_or_vtable_start_verified": False,
        "roster_member_offsets_source_verified": False,
        "actual_player_or_ball_identity_verified": False,
        "club_pose_power_ball_xyz_verified": False,
        "allowed_to_publish": False,
        "warning": (
            "One cross-bank pair of non-atomic private snapshots. A first "
            "word in a decomp compilation-unit data interval is only a "
            "plausible vtable hint; 0xCC code immediates do not prove "
            "register receiver or C++ member layout; candidate slots are not source-"
            "verified class members, active golfer, physics ball or power."
        ),
    }


def _private_file(path: Path, root: Path, length: int) -> Path:
    if path.is_symlink() or not path.is_file():
        raise ValueError("private native bank missing")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root) or resolved.stat().st_size != length:
        raise ValueError("private native bank wrong size or location")
    return resolved


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mem1", type=Path, required=True)
    parser.add_argument("--mem2", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        # Never read dumps from a Git checkout; Data is a known ignored sibling.
        root = (Path(__file__).resolve().parents[2] /
                "Wii-AI-Golf-Data").resolve(strict=True)
        if not root.is_dir():
            raise ValueError("private Data root missing")
        p1 = _private_file(args.mem1, root, MEM1_SIZE)
        p2 = _private_file(args.mem2, root, MEM2_SIZE)
        if p1 == p2:
            raise ValueError("duplicate native banks")
        with ExitStack() as stack:
            f1 = stack.enter_context(p1.open("rb"))
            f2 = stack.enter_context(p2.open("rb"))
            mem1 = stack.enter_context(mmap.mmap(f1.fileno(), 0, access=mmap.ACCESS_READ))
            mem2 = stack.enter_context(mmap.mmap(f2.fileno(), 0, access=mmap.ACCESS_READ))
            reader = TwoBankReader(mem1, mem2)
            report = triage(reader.u32, reader.header())
        print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, struct.error):
        print("Private two-bank golf triage stopped: invalid raw banks or "
              "source/scene/class gate. No raw values disclosed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
