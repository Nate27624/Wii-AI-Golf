"""PRIVATE targeted PPC instruction context for source golfer aim/pose offsets.

Print existing B0 source-code neighborhoods at selected clustered *candidate*
Rev1 RPGolPlayer.cpp read/write sites and 0x802A3894 RPGolMath helper,
not a new full-bank scan.
Source scene/selected-record and B0 bank SHA checks reuse the S002 scanner.

Warning: exact literal offsets DO NOT demonstrate that a register contains the
source-selected PlayerManager inline record. This tool shows static code only.
No Dolphin, controller, RAM writes, network calls, snapshots or publication.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import mmap
from pathlib import Path
import sys

_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR in sys.path:
    sys.path.remove(_SCRIPT_DIR)
sys.path.insert(0, _SCRIPT_DIR)

import audit_golf_aim_ppc_offsets_private as source
import audit_golf_two_bank_roster_private as roster
import audit_selected_ball_start_link_private as selected
import audit_selected_ball_four_phase_private as four


# Tight PC spans, preselected from actual operator source-hit table. Every span
# lies inside Rev1 RPGolPlayer.cpp source text and under 128 native code bytes.
SPANS = (
    ("angle_matrix_first", 0x8029ED84, 0x8029EDC8),
    ("angle_matrix_second", 0x8029EE18, 0x8029EE50),
    ("rotation_update_r30_A", 0x802A0410, 0x802A043C),
    ("rotation_update_r30_B", 0x802A0544, 0x802A0578),
    ("rotation_update_r31", 0x802A07BC, 0x802A07F0),
    ("rotation_update_r30_C", 0x802A09A0, 0x802A09C8),
    ("position_like_triple", 0x8029FAE4, 0x8029FB30),
    ("integer_copy_candidates", 0x802A0D48, 0x802A0D94),
)
# Narrow additional receiver-provenance snippets. These are static PC ranges,
# NOT inferred function boundaries and never expand into arbitrary RAM reads.
PROVENANCE_SPANS = (
    ("r29_predecessor_A", 0x8029ECF0, 0x8029ED60),
    ("r29_predecessor_B", 0x8029EDC8, 0x8029EE18),
    ("r30_predecessor_A", 0x802A03C0, 0x802A0410),
    ("r30_predecessor_B", 0x802A04F0, 0x802A0544),
    ("r31_predecessor", 0x802A0770, 0x802A07BC),
)
# The Rev1 linker split in doldecomp/ogws assigns this region to
# Pack/RPSports/RPGolScene/RPGolMath.cpp, 0x802A3560..0x802A3A6C.
# The prior observed Player code called 0x802A3894, 0x802A3864,
# and 0x802A37C8. Inspect *actual* helper bytes, not a guessed name.
MATH_START = 0x802A3560
MATH_END = 0x802A3A6C
MATH_HELPER_SPANS = (
    ("math_helper_37C8", 0x802A37C8, 0x802A3810),
    ("math_helper_3864", 0x802A3864, 0x802A3890),
    ("math_helper_3894_A", 0x802A3890, 0x802A38D0),
    ("math_helper_3894_B", 0x802A38D0, 0x802A3910),
)
ALL_SPANS = SPANS + PROVENANCE_SPANS + MATH_HELPER_SPANS


def _i16(word: int) -> int:
    return (word & 0x7FFF) - (word & 0x8000)


def decode(word: int, pc: int) -> str:
    """Only limited fields. 'other' is NEVER an unambiguous disassembly."""
    op = word >> 26
    ra = (word >> 16) & 31
    rs = (word >> 21) & 31
    rb = (word >> 11) & 31
    imm = _i16(word)
    if op in source.OPS:
        name, _ = source.OPS[op]
        target = f"f{rs}" if op in (48, 50, 52, 54) else f"r{rs}"
        return f"{name} {target}, {imm:+#x}(r{ra})"
    if op == 37:
        return f"stwu r{rs},{imm:+#x}(r{ra})"
    if op == 7:
        return f"mulli r{rs},r{ra},{imm}"
    if op == 14:
        return (f"li r{rs}, {imm}" if ra == 0
                else f"addi r{rs},r{ra},{imm:+#x}")
    if op == 15:
        return f"addis r{rs},r{ra},{imm:+#x}"
    if op == 24:
        return f"ori r{ra},r{rs},0x{word & 0xFFFF:04x}"
    if op == 31 and (word >> 1) & 0x3FF == 444 and rs == rb:
        return f"mr r{ra},r{rs}"
    if op == 18:
        val = word & 0x03FFFFFC
        if val & 0x02000000:
            val -= 0x04000000
        absolute = bool(word & 2)
        target = (val if absolute else pc + val) & 0xFFFFFFFF
        return f"{'bl' if word & 1 else 'b'} 0x{target:08X}"
    if op in (59, 63):
        ext = (word >> 1) & 0x3FF
        fops = {20:"fsub",21:"fadd",25:"fmul",40:"fneg",12:"frsp"}
        label = fops.get(ext, "floating-op")
        return f"{label} [fpu opcode {op} ext {ext}]"
    return f"other [opcode={op}]"


def describe(read_word):
    output = []
    for name, start, end in ALL_SPANS:
        in_player = source.PLAYER_CODE_START <= start < end <= source.PLAYER_CODE_END
        in_math = MATH_START <= start < end <= MATH_END
        if not (in_player or in_math) or end - start > 128:
            raise ValueError("PC span outside bounded Rev1 Player/Math source")
        if (start | end) & 3:
            raise ValueError("Unaligned source PC span")
        lines = []
        for pc in range(start, end, 4):
            word = read_word(pc)
            if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
                raise ValueError("Invalid source instruction word")
            hit = source.decode_dform(word, pc)
            marker = "  * " if hit and hit["access_kind"] == "write" else "    "
            lines.append(f"{marker}0x{pc:08X} 0x{word:08X} {decode(word, pc)}")
        output.append({
            "name": name, "from": f"0x{start:08X}", "to_exclusive": f"0x{end:08X}",
            "text": "\n".join(lines),
        })
    return output


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        folder = args.private_root
        # Reuse canonical real B0 MEM1/MEM2 source+manifest+selector audit before
        # reading the same preserved code image for a target-only static view.
        prior = source.run_local(folder)
        if prior.get("source_selected_record_snapshot_gated") is not True:
            raise ValueError("Missing source-selected record gate")
        root = selected.DATA_ROOT.resolve(strict=True)
        if folder.is_symlink() or not folder.is_dir():
            raise ValueError("Missing source memory directory")
        folder = folder.resolve(strict=True)
        if folder == root or not folder.is_relative_to(root):
            raise ValueError("Source memory folder outside private Data root")
        manifest = four._validate_manifest(folder)
        files = {k: four._approved_bank(
                    folder, f"B0-{k}.bin",
                    roster.MEM1_SIZE if k == "MEM1" else roster.MEM2_SIZE
                 ) for k in ("MEM1", "MEM2")}
        if any(four._hash(files[k]) != manifest["B0"]["sha256"][k]
               for k in files):
            raise ValueError("Source code image changed during inspection")
        with ExitStack() as stack:
            images = []
            for file in files.values():
                stream = stack.enter_context(file.open("rb"))
                images.append(stack.enter_context(
                    mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ)))
            reader = roster.TwoBankReader(*images)
            contexts = describe(reader.u32)
        print("S002 Rev1 RPGolPlayer.cpp code-site contexts. * marks target-offset writes.")
        print("CAUTION: base register ownership is NOT established by these offsets.")
        for entry in contexts:
            print(f"\n[{entry['name']}] {entry['from']} to {entry['to_exclusive']}")
            print(entry["text"])
        return 0
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        print("Private source instruction context failed closed: " + str(exc),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
