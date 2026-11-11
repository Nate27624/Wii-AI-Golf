"""Read-only, source-gated Rev1 golf object graph across private MEM1 and MEM2.

Uses only documented static source addresses and field offsets. Runtime
pointers and source memory words are NEVER exported. No live emulator access.
"""
from __future__ import annotations
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import struct

MEM1_SIZE = 0x1800000
MEM2_SIZE = 0x4000000
BASE_MEM1 = 0x80000000
BASE_MEM2 = 0x90000000
STATIC_SCENE_SLOTS = (0x804BF4D8, 0x804BF4DC)
STATIC_CONFIG = 0x804BF8C4
STATIC_FIELD = 0x804BF868
STATIC_PLAYER_MANAGER = 0x804BF8D0
MAIN_REV1_DATA = (0x803C7798, 0x803C77C0)
PLAYER_MANAGER_REV1_DATA = (0x803C7DD0, 0x803C7DE0)


class _Banks:
    def __init__(self, mem1, mem2):
        self.banks = (
            (BASE_MEM1, memoryview(mem1)), (BASE_MEM2, memoryview(mem2)))

    def region(self, address, n):
        if type(address) is not int or address % 4 or n <= 0:
            return None
        for name, (base, contents) in zip(("MEM1", "MEM2"), self.banks):
            if base <= address and address + n <= base + len(contents):
                return name
        return None

    def read(self, address, n):
        if self.region(address, n) is None:
            raise ValueError("Source-gated pointer missing or out of bounds")
        for base, bank in self.banks:
            if base <= address and address + n <= base + len(bank):
                return bank[address - base:address - base + n]
        raise ValueError("Missing memory bank")

    def u32(self, address):
        return struct.unpack(">I", self.read(address, 4))[0]


def audit_pair(mem1, mem2, *, strict_size=True):
    """Deterministic sanitized source checks; no runtime address escapes."""
    if strict_size and (len(mem1) != MEM1_SIZE or len(mem2) != MEM2_SIZE):
        raise ValueError("Expected exact native MEM1 and MEM2 sizes")
    if len(mem1) < 0x4BF8C8 or len(mem2) < 0x1000:
        raise ValueError("Incomplete source-linked bank")
    if bytes(memoryview(mem1)[:8]) != b"RSPE01\x00\x01":
        raise ValueError("Incorrect Wii Sports disc or revision")
    m = _Banks(mem1, mem2)
    managers = list({m.u32(o) for o in STATIC_SCENE_SLOTS
                     if m.region(m.u32(o), 0x20)})
    if len(managers) != 1:
        raise ValueError("No unique source-gated scene manager")
    manager = managers[0]
    if m.u32(manager + 0x18) != 5:
        raise ValueError("Not current Golf scene")
    scene = m.u32(manager + 0x0C)
    scene_region = m.region(scene, 0xA0)
    if (not scene_region or m.u32(scene + 0x1C) != 5
            or m.u32(scene + 0x20) != manager
            or m.u32(scene + 0x54) != 2):
        raise ValueError("Scene/backlink/sport identity gate failed")
    main = m.u32(scene + 0x9C)
    main_region = m.region(main, 0x100)
    if not main_region:
        raise ValueError("Golf-main candidate object missing")
    config = m.u32(STATIC_CONFIG)
    if not m.region(config, 0xA0) or m.u32(config + 0x94) != 4:
        raise ValueError("Wrong source-gated golf game mode")
    field = m.u32(STATIC_FIELD)
    if not m.region(field, 0xA8):
        raise ValueError("Golf field manager missing")
    player_manager = m.u32(STATIC_PLAYER_MANAGER)
    named_offsets = {
        "map_data": 0x18, "current_pin": 0x44, "current_start": 0x50,
        "cup": 0x54, "wind": 0x68, "course": 0x70}
    named_regions = {
        key: m.region(m.u32(field + off), 0x10)
        for key, off in named_offsets.items()}
    pin_count = m.u32(field + 0x3C)
    start_count = m.u32(field + 0x48)
    if pin_count > 256 or start_count > 256:
        raise ValueError("Invalid source-defined course object census")
    ptr_candidates = {"MEM1": 0, "MEM2": 0}
    for off in range(0, 0x100, 4):
        region = m.region(m.u32(main + off), 0x80)
        if region:
            ptr_candidates[region] += 1
    return {
        "schema_version": 1,
        "kind": "local-private-cross-bank-golf-source-audit",
        "memory": {
            "MEM1": {"size_bytes": len(mem1),
                     "wii_disc_id_verified": True, "revision_verified": True},
            "MEM2": {"size_bytes": len(mem2),
                     "flat_memory_length_verified": strict_size,
                     "no_disc_header_expected": True}},
        "conditions": {
            "game": "RSPE01", "revision": 1, "golf_scene_id": 5,
            "sport_id": 2, "game_mode": 4,
            "raw_current_hole_index": m.u32(config + 0x98)},
        "source_chain": {
            "scene_manager_static_slots_checked": 2,
            "plausible_scene_managers": 1,
            "scene_manager_region": m.region(manager, 0x20),
            "current_golf_scene_region": scene_region,
            "manager_scene_id_matches_golf": True,
            "scene_id_matches_golf": True,
            "scene_backlink_matches_manager": True,
            "scene_sport_id_matches_golf": True,
            "gol_main_region": main_region,
            "scene_member_main_at_offset": "+0x09C",
            "main_first_word_within_rev1_gol_main_data_range":
                MAIN_REV1_DATA[0] <= m.u32(main) < MAIN_REV1_DATA[1],
            "main_member_0x004_backlinks_scene": m.u32(main + 4) == scene},
        "other_managers": {
            "golf_config_region": m.region(config, 0xA0),
            "golf_field_manager_region": m.region(field, 0xA8),
            "player_manager_candidate_region": m.region(player_manager, 0x80),
            "player_manager_first_word_within_rev1_module_data_range":
                m.region(player_manager, 0x80) is not None
                and PLAYER_MANAGER_REV1_DATA[0] <= m.u32(player_manager)
                < PLAYER_MANAGER_REV1_DATA[1]},
        "field_manager": {
            "pin_object_count": pin_count,
            "start_object_count": start_count,
            "source_named_current_object_refs_valid_mem2": {
                name: region == "MEM2" for name, region in named_regions.items()},
            "positions_decoded": False, "ball_physics_decoded": False},
        "main_object": {
            "candidate_pointer_shaped_words_with_0x80_valid_target_by_bank":
                ptr_candidates,
            "candidate_only": True, "rpgol_main_structure_verified": False,
            "power_verified": False, "club_rotation_verified": False},
        "provenance": {
            "both_files_available": True, "same_game_frame_proven": False,
            "same_boot_proven": False, "cross_bank_scene_backlink_verified": True,
            "private_runtime_pointers_exported": False,
            "raw_memory_exported": False, "no_training_or_power_claim": True},
        "warning": (
            "Source data-range hits are not verified C++ vtables. Sequential "
            "GUI dumps are not proven frame-synchronous. Pointer-shaped "
            "words are not verified golfer, club or power fields.")}


def audit_local_pair(mem1_path, mem2_path, *, private_root, output):
    """Only approved user-local raw files; create private JSON, never overwrite."""
    root = Path(private_root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Private root is not a directory")
    resolved = []
    for p, size in zip((Path(mem1_path), Path(mem2_path)),
                       (MEM1_SIZE, MEM2_SIZE)):
        if p.is_symlink() or not p.is_file() or p.suffix.lower() not in (
                ".raw", ".bin", ".mem"):
            raise ValueError("Incorrect private memory file")
        candidate = p.resolve(strict=True)
        if not candidate.is_relative_to(root) or p.stat().st_size != size:
            raise ValueError("Private bank location or length invalid")
        resolved.append(candidate)
    if len(set(resolved)) != 2:
        raise ValueError("Duplicate bank files")
    out = Path(output)
    if (out.is_symlink() or out.exists() or out.suffix.lower() != ".json"
            or out.parent.resolve(strict=True) != root):
        raise ValueError("Private output must be new JSON at the private root")
    with ExitStack() as stack:
        files = [stack.enter_context(open(path, "rb")) for path in resolved]
        buffers = [stack.enter_context(
            mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ))
            for file in files]
        result = audit_pair(*buffers, strict_size=True)
    with out.open("x", encoding="utf-8") as fp:
        json.dump(result, fp, indent=2, sort_keys=True, allow_nan=False)
        fp.write("\n")
    return result
