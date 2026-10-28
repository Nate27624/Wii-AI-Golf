"""S002 Rev1 offline effect-writer source audit (NO emulation).

Input: existing B0 MEM1/MEM2 banks, immutable SHA manifest, source-selected
golfer gate. Scan exactly three public source-linked .text units for D-form
+0x78/+0x7C loads/stores and source field effect pointers +0x94/98/9C.
Do not conflate a literal displacement with ownership of minimap effect
objects. Print bounded nearest PPC instructions per match; all offsets
are relative to the instruction's REGISTER, NOT an independently proven
C++ class member. No raw RAM addresses, changed values, object pointers,
ROMs, new captures, network, controller actions, or game writes.

Public source split: doldecomp/ogws config/RSPE01_01/splits.txt.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

SCRIPTS = str(Path(__file__).resolve().parent)
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import audit_golf_aim_ppc_context_private as context
import audit_golf_aim_ppc_offsets_private as offsets
import audit_golf_two_bank_roster_private as roster
import audit_selected_ball_four_phase_private as four
import audit_selected_ball_start_link_private as selected

# RSPE01_01 exact CODE section boundaries from public split, NOT assumed functions.
TEXT_UNITS = {
    "RPGolFieldManager.cpp": (0x80290B44, 0x80294184),
    "RPGolDrawManager.cpp": (0x80294184, 0x8029528C),
    "RPGolMapObjBall.cpp": (0x80296FD8, 0x8029B240),
}
WATCH_FIELDS = (0x78, 0x7C)
FIELD_EFFECT_PTRS = (0x94, 0x98, 0x9C)
TARGETS = WATCH_FIELDS + FIELD_EFFECT_PTRS
MAX_HITS_PER_UNIT = 320
# For reviewer economy do NOT show thousands of unrelated instructions.
CONTEXT_BEFORE = 8
CONTEXT_AFTER = 5
MAX_OUTPUT_CONTEXTS_PER_UNIT = 24


def inspect_source_word(word: int, pc: int):
    """The underlying canonical decoder limits claims to 32-bit D-form ops."""
    return offsets.decode_dform(word, pc, targets=TARGETS)


def analyze(read_word) -> dict:
    units = []
    hits_count = 0
    for label, (start, end) in TEXT_UNITS.items():
        if (start | end) & 3 or start >= end or end-start > 0x5000:
            raise ValueError("Invalid bounded Rev1 golf text range")
        candidates = []
        for pc in range(start, end, 4):
            hit = inspect_source_word(read_word(pc), pc)
            if hit is None:
                continue
            hit = {
                "pc": hit["instruction_address_hex"],
                "offset": hit["relative_displacement_hex"],
                "mnemonic": hit["mnemonic"],
                "kind": hit["access_kind"],
                "base_register": hit["base_reg"],
                "value_register": hit["source_or_destination_reg"],
                "base_register_owner_proven": False,
                "runtime_effect_receiver_proven": False,
            }
            candidates.append(hit)
            if len(candidates) > MAX_HITS_PER_UNIT:
                raise ValueError("Too many target displacement hits")
        # Select stores of the paired field positions first, not broad lookups.
        ordered = sorted(candidates, key=lambda x: (
            0 if x["offset"] in ("+0x078", "+0x07C") and x["kind"] == "write" else
            1 if x["offset"] in ("+0x094", "+0x098", "+0x09C") else 2,
            int(x["pc"], 16)))
        contexts = []
        for hit in ordered[:MAX_OUTPUT_CONTEXTS_PER_UNIT]:
            pc = int(hit["pc"], 16)
            before = max(start, pc - 4*CONTEXT_BEFORE)
            after = min(end, pc + 4*(CONTEXT_AFTER+1))
            context_words = []
            for addr in range(before, after, 4):
                word = read_word(addr)
                context_words.append({
                    "pc": f"0x{addr:08X}",
                    "word": f"0x{word:08X}",
                    "approximate_disassembly": context.decode(word, addr),
                })
            contexts.append({
                "target": hit,
                "nearby_static_code_only": context_words,
            })
        units.append({
            "source_unit": label,
            "text_bounds": [f"0x{start:08X}", f"0x{end:08X}"],
            "static_instruction_count": (end-start)//4,
            "matched_dform_count": len(candidates),
            "paired_field_write_count": sum(
                x["kind"] == "write" and
                x["offset"] in ("+0x078", "+0x07C") for x in candidates),
            "paired_field_read_count": sum(
                x["kind"] == "read" and
                x["offset"] in ("+0x078", "+0x07C") for x in candidates),
            "effect_pointer_offset_hits": sum(
                x["offset"] in ("+0x094", "+0x098", "+0x09C")
                for x in candidates),
            "literal_hits": candidates,
            "selected_source_contexts": contexts,
            "displacement_is_effect_member_proven": False,
            "receiver_base_register_traced": False,
        })
        hits_count += len(candidates)
    return {
        "kind": "S002-private-Rev1-three-unit-effect-writer-static-triage",
        "source_game": "RSPE01 Rev1",
        "target_relative_offsets": ["+0x078", "+0x07C", "+0x094",
                                    "+0x098", "+0x09C"],
        "source_units": units,
        "total_dform_hits": hits_count,
        "game_field_pointer_type_proven": False,
        "effect_entry_constructor_or_stride_proven": False,
        "effect_slot_field_078_07C_ownership_proven": False,
        "indexed_or_indirect_writes_exhaustive": False,
        "ball_world_xyz_verified": False,
        "ball_velocity_verified": False,
        "swing_power_verified": False,
        "allowed_to_publish": False,
        "approved_for_model_training": False,
    }


def run_local(folder: Path) -> dict:
    # Same source and real private native bank guards as proven aim studies.
    prior = offsets.run_local(folder)
    if prior.get("source_selected_record_snapshot_gated") is not True:
        raise ValueError("Source-selected manager gate failed")
    root = selected.DATA_ROOT.resolve(strict=True)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Missing original private source folder")
    folder = folder.resolve(strict=True)
    if folder == root or not folder.is_relative_to(root):
        raise ValueError("Outside private research data")
    manifest = four._validate_manifest(folder)
    paths = {k: four._approved_bank(
        folder, f"B0-{k}.bin",
        roster.MEM1_SIZE if k == "MEM1" else roster.MEM2_SIZE
    ) for k in ("MEM1", "MEM2")}
    if any(four._hash(p) != manifest["B0"]["sha256"][k]
           for k, p in paths.items()):
        raise ValueError("Preserved B0 image hash mismatched")
    with ExitStack() as stack:
        images = []
        for path in paths.values():
            stream = stack.enter_context(path.open("rb"))
            images.append(stack.enter_context(
                mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ)))
        reader = roster.TwoBankReader(*images)
        return analyze(reader.u32)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(run_local(args.private_root), indent=2, sort_keys=True,
                         allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as e:
        print("Effect writer static source audit FAILED CLOSED: " +
              type(e).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
