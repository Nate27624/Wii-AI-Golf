"""PRIVATE read-only Rev1 PPC offset-access reconnaissance for aiming record fields.

Use *existing* B0 MEM1/MEM2 checkpoint, source-gated by canonical #160/#163,
and exact B0 manifest bank hashes. Decode only bounded RPGolPlayer.cpp .text;
report literal D-form offset hits with instruction address and base register.

IMPORTANT: Numeric displacement matches are NOT evidence that the base
register addresses the source-selected record, and indirect stores may be missed.
No emulator, game actions, DOL upload, network calls, model or data publication.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

import audit_golf_two_bank_roster_private as roster
import audit_selected_ball_start_link_private as selected
import audit_selected_ball_four_phase_private as four

PLAYER_CODE_START = 0x8029E62C
PLAYER_CODE_END = 0x802A2210
# U32/f32 offsets surfaced by operator's real selected record B0-B3 differential.
TARGETS = (
    0x3C, 0x40, 0x44, 0x48, 0x4C,
    0x90, 0x94, 0x98, 0x9C,
    0xA0, 0xA4, 0xA8, 0xAC, 0xB0, 0xB4, 0xB8, 0xBC, 0xC0,
)
OPS = {
    32: ("lwz", "read"), 34: ("lbz", "read"),
    36: ("stw", "write"), 38: ("stb", "write"),
    40: ("lhz", "read"), 42: ("lha", "read"),
    44: ("sth", "write"), 48: ("lfs", "read"),
    50: ("lfd", "read"), 52: ("stfs", "write"),
    54: ("stfd", "write"),
}
MAX_HITS = 1024


def decode_dform(word: int, pc: int, targets=TARGETS):
    """Decode real PPC D-form operand fields, without inferring C++ ownership."""
    if type(word) is not int or word < 0 or word > 0xFFFFFFFF:
        raise ValueError("Invalid PPC word")
    if type(pc) is not int or pc & 3:
        raise ValueError("Invalid aligned instruction address")
    opcode = word >> 26
    if opcode not in OPS:
        return None
    displacement = word & 0xFFFF
    if displacement & 0x8000:
        displacement -= 0x10000
    if displacement not in targets:
        return None
    name, direction = OPS[opcode]
    return {
        "instruction_address_hex": f"0x{pc:08X}",
        "relative_displacement_hex": f"+0x{displacement:03X}",
        "mnemonic": name,
        "access_kind": direction,
        "base_reg": f"r{(word >> 16) & 31}",
        "source_or_destination_reg": f"r{(word >> 21) & 31}" if opcode < 48
                                     else f"f{(word >> 21) & 31}",
        "raw_ppc_u32_hex": f"0x{word:08X}",
        "selected_player_record_receiver_proven": False,
    }


def scan(get_word, *, start=PLAYER_CODE_START, end=PLAYER_CODE_END):
    """Source-bounded literal offset scan, not arbitrary code/address searching."""
    if (type(start) is not int or type(end) is not int or
            start % 4 or end % 4 or not start < end or
            not PLAYER_CODE_START <= start or end > PLAYER_CODE_END):
        raise ValueError("Source scan must stay in Rev1 RPGolPlayer.cpp text")
    hits = []
    for pc in range(start, end, 4):
        match = decode_dform(get_word(pc), pc)
        if match:
            hits.append(match)
            if len(hits) > MAX_HITS:
                raise ValueError("Unexpectedly many PPC target-offset instructions")
    grouped = {}
    for offset in TARGETS:
        subset = [h for h in hits
                  if int(h["relative_displacement_hex"][1:], 16) == offset]
        grouped[f"+0x{offset:03X}"] = {
            "reads": sum(h["access_kind"] == "read" for h in subset),
            "writes": sum(h["access_kind"] == "write" for h in subset),
            "candidate_write_instruction_addresses": [
                h["instruction_address_hex"] for h in subset
                if h["access_kind"] == "write"
            ],
        }
    return {
        "kind": "PRIVATE-Rev1-RPGolPlayer-literal-offset-access-sites",
        "schema_version": 1,
        "game_id": "RSPE01",
        "revision": 1,
        "code_unit": "RPGolPlayer.cpp",
        "source_text_range": [
            f"0x{PLAYER_CODE_START:08X}", f"0x{PLAYER_CODE_END:08X}"],
        "instruction_count_examined": (end - start)//4,
        "target_offset_reads_writes": grouped,
        "matched_dform_instructions": hits,
        "known_golf_player_receiver_proven": False,
        "direct_literal_offsets_are_exhaustive": False,
        "gameplay_aim_angle_verified": False,
        "ball_motion_verified": False,
        "swing_power_verified": False,
        "model_training_approved": False,
        "allowed_to_publish": False,
        "note": (
            "Literal PPC load/store displacements, not proven this-pointer "
            "accesses. Indirect indexed stores, memory copies, pointer "
            "arithmetic and other source code units can be missed. "
            "Near PC hits alone do not identify runtime field ownership."),
    }


def run_local(folder: Path):
    data_root = selected.DATA_ROOT.resolve(strict=True)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Missing private B0-B3 session")
    resolved = folder.resolve(strict=True)
    if resolved == data_root or not resolved.is_relative_to(data_root):
        raise ValueError("Session not inside ignored data root")
    manifest = four._validate_manifest(resolved)
    files = {
        key: four._approved_bank(
            resolved, f"B0-{key}.bin",
            roster.MEM1_SIZE if key == "MEM1" else roster.MEM2_SIZE)
        for key in ("MEM1", "MEM2")
    }
    for key, file in files.items():
        if four._hash(file) != manifest["B0"]["sha256"][key]:
            raise ValueError("B0 memory image differs from private checkpoint manifest")
    with ExitStack() as stack:
        images = []
        for file in files.values():
            handle = stack.enter_context(file.open("rb"))
            images.append(stack.enter_context(mmap.mmap(
                handle.fileno(), 0, access=mmap.ACCESS_READ)))
        reader = roster.TwoBankReader(*images)
        safe, _private = selected.analyze_one(reader.u32, reader.header())
        if safe.get("selected_record_pointer_matches_code_defined_stride") is not True:
            raise ValueError("Selected player source gate failed")
        report = scan(reader.u32)
        report["source_selected_record_snapshot_gated"] = True
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        result = run_local(args.private_root)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        print("Source-gated PPC aim-offset scan FAILED CLOSED. "
              "Preserve private B0-B3 files.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
