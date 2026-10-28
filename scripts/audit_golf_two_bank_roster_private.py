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



def _dform_matches(read_u32, pc: int, opcode: int, value_reg: int,
                   base_reg: int, disp: int) -> bool:
    word = read_u32(pc)
    return (word >> 26 == opcode
            and (word >> 21) & 31 == value_reg
            and (word >> 16) & 31 == base_reg
            and (word & 0xFFFF) == (disp & 0xFFFF))


def _mr_matches(read_u32, pc: int, target_reg: int, source_reg: int) -> bool:
    word = read_u32(pc)
    return (word >> 26 == 31 and (word >> 1) & 1023 == 444
            and (word >> 16) & 31 == target_reg
            and (word >> 21) & 31 == source_reg
            and (word >> 11) & 31 == source_reg)


def _add_matches(read_u32, pc: int, dest: int, lhs: int, rhs: int) -> bool:
    word = read_u32(pc)
    return (word >> 26 == 31 and (word >> 1) & 1023 == 266
            and (word >> 21) & 31 == dest
            and (word >> 16) & 31 == lhs
            and (word >> 11) & 31 == rhs)


def _relative_branch_target(pc: int, word: int, opcode: int) -> int | None:
    if word >> 26 != opcode or word & 2:  # exclude absolute branch forms
        return None
    if opcode == 18:
        disp = word & 0x03FFFFFC
        if disp & 0x02000000:
            disp -= 0x04000000
    elif opcode == 16:
        disp = word & 0xFFFC
        if disp & 0x8000:
            disp -= 0x10000
    else:
        return None
    return (pc + disp) & 0xFFFFFFFF


def _bl_matches(read_u32, pc: int, target: int) -> bool:
    word = read_u32(pc)
    return bool(word & 1 and _relative_branch_target(pc, word, 18) == target)


def source_member_flow_evidence(read_u32) -> dict:
    """Bounded instruction-pattern corroboration with explicit provenance limits.

    These exact PC ranges are publicly documented Rev1 code units.
    Checks verify register movement along specified basic blocks, not a full
    interprocedural dataflow analysis. No raw instruction words are returned.
    """
    manager_record_loop = all((
        _mr_matches(read_u32, 0x802A3194, 29, 3),
        _dform_matches(read_u32, 0x802A3200, 14, 31, 29, 4),
        _mr_matches(read_u32, 0x802A3214, 3, 31),
        _mr_matches(read_u32, 0x802A3218, 4, 30),
        _bl_matches(read_u32, 0x802A321C, 0x802A08A0),
        _dform_matches(read_u32, 0x802A3224, 14, 31, 31, 0xCC),
        _dform_matches(read_u32, 0x802A3228, 11, 0, 30, 4),
        _relative_branch_target(0x802A322C, read_u32(0x802A322C), 16)
            == 0x802A3214,
    ))
    ball_member_access = all((
        _mr_matches(read_u32, 0x802A08B4, 30, 3),
        _dform_matches(read_u32, 0x802A08F0, 36, 0, 30, 0x88),
        _dform_matches(read_u32, 0x8029F0E4, 32, 3, 3, 0x88),
        _bl_matches(read_u32, 0x8029F0E8, 0x80297124),
    ))
    nested_three_float_writer = all((
        _dform_matches(read_u32, 0x802A03A0, 32, 4, 3, 0x88),
        _dform_matches(read_u32, 0x802A03B4, 32, 4, 4, 0x4C),
        _dform_matches(read_u32, 0x802A03B8, 52, 2, 4, 0),
        _dform_matches(read_u32, 0x802A03C0, 52, 0, 4, 4),
        _dform_matches(read_u32, 0x802A03C8, 52, 0, 4, 8),
    ))
    player_subobject_constructor = all((
        _dform_matches(read_u32, 0x802A0D74, 15, 3, 0, -32708),
        _dform_matches(read_u32, 0x802A0D7C, 14, 3, 3, 32040),
        _dform_matches(read_u32, 0x802A0D88, 36, 3, 31, 0),
        _dform_matches(read_u32, 0x802A0D94, 36, 31, 30, 0xC4),
    ))
    selector_calculation = all((
        _dform_matches(read_u32, 0x802A31E8, 32, 0, 29, 0x34C),
        _dform_matches(read_u32, 0x802A31EC, 7, 0, 0, 0xCC),
        _add_matches(read_u32, 0x802A31F0, 3, 29, 0),
        _dform_matches(read_u32, 0x802A31F4, 14, 0, 3, 4),
        _dform_matches(read_u32, 0x802A31F8, 36, 0, 29, 0x334),
    ))
    return {
        "four_inline_0xcc_record_loop_source_supported": manager_record_loop,
        "manager_selected_record_pointer_offset_source_supported":
            selector_calculation,
        "record_plus_0x88_ball_code_path_source_supported": ball_member_access,
        "ball_child_plus_0x4c_three_float_writer_source_supported":
            nested_three_float_writer,
        "record_plus_0xc4_allocated_subobject_source_supported":
            player_subobject_constructor,
        "full_interprocedural_register_dataflow_proven": False,
        "world_space_ball_xyz_or_units_verified": False,
        "actual_player_selection_verified": False,
    }


def _start_ball_vec3_code_evidence(read_u32) -> dict:
    """Strict, bounded PPC source paths; no code bytes or runtime values emitted.

    These checks establish translation *copy* logic, not units, world-space
    coordinates, ball physics, shot activity, or same-frame capture.
    """
    start_getter = all((
        _dform_matches(read_u32, 0x802922EC, 32, 3, 3, 0x50),
        _dform_matches(read_u32, 0x802922F0, 32, 3, 3, 0x4C),
        _dform_matches(read_u32, 0x8029F244, 32, 3, 13, -23320),
        _bl_matches(read_u32, 0x8029F248, 0x802922EC),
    ))
    start_to_record = all(
        _dform_matches(read_u32, load_pc, 48, 0, 3, j * 4)
        and _dform_matches(read_u32, store_pc, 52, 0, 29, 0x60 + j * 4)
        for j, (load_pc, store_pc) in enumerate((
            (0x8029F24C, 0x8029F254),
            (0x8029F258, 0x8029F25C),
            (0x8029F260, 0x8029F264),
        ))
    )
    ball_to_record = all((
        _dform_matches(read_u32, 0x8029F300, 32, 3, 29, 0x88),
        _dform_matches(read_u32, 0x8029F304, 32, 4, 3, 0x4C),
    )) and all(
        _dform_matches(read_u32, 0x8029F308 + j * 8, 48, 0, 4, j * 4)
        and _dform_matches(read_u32, 0x8029F30C + j * 8, 52, 0, 29,
                           0x60 + j * 4)
        for j in range(3)
    )
    record_to_ball = all((
        _dform_matches(read_u32, 0x802A038C, 48, 2, 3, 0x60),
        _dform_matches(read_u32, 0x802A0390, 48, 1, 3, 0x64),
        _dform_matches(read_u32, 0x802A0394, 48, 0, 3, 0x68),
        _dform_matches(read_u32, 0x802A03A4, 52, 2, 3, 0x54),
        _dform_matches(read_u32, 0x802A03A8, 52, 1, 3, 0x58),
        _dform_matches(read_u32, 0x802A03AC, 52, 0, 3, 0x5C),
        _dform_matches(read_u32, 0x802A03A0, 32, 4, 3, 0x88),
        _dform_matches(read_u32, 0x802A03B4, 32, 4, 4, 0x4C),
        _dform_matches(read_u32, 0x802A03B8, 52, 2, 4, 0),
        _dform_matches(read_u32, 0x802A03BC, 48, 0, 3, 0x58),
        _dform_matches(read_u32, 0x802A03C0, 52, 0, 4, 4),
        _dform_matches(read_u32, 0x802A03C4, 48, 0, 3, 0x5C),
        _dform_matches(read_u32, 0x802A03C8, 52, 0, 4, 8),
    ))
    return {
        "start_object_translation_getter_source_supported": start_getter,
        "start_translation_to_record_plus_0x60_source_supported": start_to_record,
        "ball_translation_to_record_plus_0x60_source_supported": ball_to_record,
        "record_plus_0x60_through_0x54_to_ball_translation_source_supported":
            record_to_ball,
        "actual_world_space_ball_xyz_verified": False,
        "dynamic_movement_verified": False,
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

    # This dereference is source-controlled: the separately validated PPC
    # player code reads record+0x88 then follows child+0x4C before storing a
    # three-word vector. Compare equality only; no f32/XYZ decoding here.
    source_flow = source_member_flow_evidence(read_u32)
    nested_pointer_count = 0
    local_triplet_equal_count = 0
    if source_flow["ball_child_plus_0x4c_three_float_writer_source_supported"]:
        for index in range(ROSTER_SLOTS):
            ball = read_u32(pm + BALL_CANDIDATE_MEMBER + index * ROSTER_STRIDE)
            if (_bank(ball, 0x50) != "MEM2"
                    or not _in_data(read_u32(ball), BALL_DATA)):
                continue
            vec = read_u32(ball + 0x4C)
            if _bank(vec, 12) != "MEM2":
                continue
            nested_pointer_count += 1
            record = pm + 4 + index * ROSTER_STRIDE
            local_triplet_equal_count += all(
                read_u32(record + 0x54 + j * 4) == read_u32(vec + j * 4)
                for j in range(3)
            )
    all_pairs = all(paired)
    selector = read_u32(pm + 0x334)
    selected_indices = [
        idx for idx in range(ROSTER_SLOTS)
        if selector == pm + 4 + idx * ROSTER_STRIDE
    ]
    selected_index = (
        selected_indices[0]
        if source_flow["manager_selected_record_pointer_offset_source_supported"]
        and len(selected_indices) == 1 else None
    )
    source_code_stride = _code_stride_instruction_counts(read_u32)
    start_vector_code = _start_ball_vec3_code_evidence(read_u32)
    start_matches = {
        "selected_record_054": 0,
        "selected_record_060": 0,
        "selected_ball_nested": 0,
        "unselected_ball_nested_full_match_count": 0,
        "current_start_translation_selfref": False,
        "current_start_pointer_mapped": False,
    }
    # A content equality comparison only, not a position decoder. Gate on
    # source-proven getter & copy sites and one source-derived selected slot.
    if (selected_index is not None
            and all(start_vector_code[k] for k in (
                "start_object_translation_getter_source_supported",
                "start_translation_to_record_plus_0x60_source_supported",
                "ball_translation_to_record_plus_0x60_source_supported",
                "record_plus_0x60_through_0x54_to_ball_translation_source_supported"))):
        start_obj = read_u32(field + 0x50)
        if _bank(start_obj, 0x50) == "MEM2":
            start_vec = read_u32(start_obj + 0x4C)
            if _bank(start_vec, 12) == "MEM2":
                start_matches["current_start_pointer_mapped"] = True
                start_matches["current_start_translation_selfref"] = (
                    start_vec == start_obj + 0x30
                )
                selected_rec = pm + 4 + selected_index * ROSTER_STRIDE
                selected_ball = read_u32(selected_rec + 0x88)
                if (_bank(selected_ball, 0x50) == "MEM2"
                        and _in_data(read_u32(selected_ball), BALL_DATA)):
                    selected_vec = read_u32(selected_ball + 0x4C)
                    if _bank(selected_vec, 12) == "MEM2":
                        for component in range(3):
                            original = read_u32(start_vec + 4 * component)
                            for label, address in (
                                ("selected_record_054", selected_rec + 0x54),
                                ("selected_record_060", selected_rec + 0x60),
                                ("selected_ball_nested", selected_vec),
                            ):
                                start_matches[label] += (
                                    read_u32(address + 4 * component) == original
                                )
                for idx in range(ROSTER_SLOTS):
                    if idx == selected_index:
                        continue
                    rec = pm + 4 + idx * ROSTER_STRIDE
                    ball = read_u32(rec + 0x88)
                    if (_bank(ball, 0x50) != "MEM2"
                            or not _in_data(read_u32(ball), BALL_DATA)):
                        continue
                    vec = read_u32(ball + 0x4C)
                    if _bank(vec, 12) != "MEM2":
                        continue
                    start_matches["unselected_ball_nested_full_match_count"] += all(
                        read_u32(vec + 4 * comp) == read_u32(start_vec + 4 * comp)
                        for comp in range(3)
                    )
    exact_subobject_vtable_matches = sum(
        _bank(p) == "MEM2" and read_u32(p) == 0x803C7D28
        for p in players
    ) if source_flow["record_plus_0xc4_allocated_subobject_source_supported"] else 0
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
        "bounded_source_register_flow_evidence": source_flow,
        "exact_constructor_firstword_matches_for_plus_0xc4_subobjects":
            exact_subobject_vtable_matches,
        "ball_related_child_plus_0x4c_mapped_triplet_count": nested_pointer_count,
        "nested_triplets_equal_record_triplet_count": local_triplet_equal_count,
        "nested_three_word_destination_is_world_ball_xyz_verified": False,
        "start_to_selected_ball_source_code_evidence": start_vector_code,
        "selected_start_three_word_equality_component_counts": start_matches,
        "start_vector_physically_ball_xyz_verified": False,
        "source_gated_selected_record_index_hypothesis": selected_index,
        "source_selected_record_identity_confirmed": False,
        "source_supported_record_layout_not_gameplay_semantics":
            bool(source_flow["four_inline_0xcc_record_loop_source_supported"]
                 and source_flow["record_plus_0x88_ball_code_path_source_supported"]),
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
