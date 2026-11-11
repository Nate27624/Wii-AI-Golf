"""Read-only source-bound RSPE01 Rev1 swing-magnitude WRITER micro-audit.

Requires the EXISTING exact-SHA seven numbered MEM1/MEM2 archive. Inspects ONLY
original PPC code, does not launch Dolphin or require ROM/game-file arguments.
Outputs only sanitized SOURCE PC / register / field / branch classifications.
No raw native words, original memory dumps, private hashes, heap pointers,
physical power claims, or native-value vectors are printed.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_p0_seven_numbered_source_pairs_private as private
import audit_golf_two_bank_roster_private as roster
import audit_p0_inflight_vs_b0_private as source

DATA = HERE.parents[1] / "Wii-AI-Golf-Data"
PUBLIC_OWNER = "Pack/RPSports/RPGolScene/RPGolScene_unsplit.o"
OWNER_START, OWNER_END = 0x802A79F8, 0x802C7924
MEM1_BASE = roster.MEM1_BASE

# The original operator's exact PPC proof on the preserved Rev1 cohort.
# These are two distinct stages: current/peak writer and later state-3 latch.
STFS_GATES = {
    0x802B4914: (30, 24, 0x08),
    0x802B4924: (1, 24, 0x0C),
    0x802B31C4: (0, 27, 0x10),
}
LFS_GATES = {
    0x802B31B0: (0, 27, 0x0C),
}
STW_GATES = {
    0x802B31C0: (0, 27, 0x1A4),
}
CALL_GATES = {
    0x802B4938: 0x802B3BA0,
    0x802B3D04: 0x802B2F90,
}
# PPC "mr" is OR rA,rS,rS (primary31, XO444). Earlier original
# operator source trace showed a calc receiver preserved through two calls.
# This proves register copies only; branches/guest invocation still matter.
MR_GATES = {
    0x802B4928: (3, 24),
    0x802B3BD0: (29, 3),
    0x802B3CFC: (3, 29),
    0x802B2FB8: (27, 3),
}
# EXACT bounded source ranges within the compiled GolfScene_unsplit.o;
# the broad target names are annotations, not evidence of execution.
PEAK_WINDOW = (0x802B4794, 0x802B493C)
STATED_LATCH_WINDOW = (0x802B31A8, 0x802B31C8)
SOURCE_CALL_WINDOWS = ((0x802B3BC0, 0x802B3D08),)
COHORT_PPC_WINDOWS = (PEAK_WINDOW, STATED_LATCH_WINDOW, *SOURCE_CALL_WINDOWS)
EXCERPT = (0x802B4820, 0x802B4938)

class Abstain(ValueError):
    """Sanitized failure. Never embed private file path or native values."""


def _pc_check(pc: int) -> None:
    if type(pc) is not int or pc % 4 or not OWNER_START <= pc < OWNER_END:
        raise Abstain("source_window_outside_verified_golf_unit")


def _word(mm, pc: int) -> int:
    _pc_check(pc)
    off = pc - MEM1_BASE
    if not 0 <= off <= len(mm) - 4:
        raise Abstain("source_word_unmapped")
    return int.from_bytes(mm[off:off + 4], "big")


def _dform(word: int):
    return ((word >> 26), (word >> 21) & 31,
            (word >> 16) & 31, (word & 0xFFFF))


def _signed(x: int, bits: int) -> int:
    return x - (1 << bits) if x & (1 << (bits - 1)) else x


def _branch(pc: int, word: int):
    op = word >> 26
    if op == 18:
        li = word & 0x03FFFFFC
        val = _signed(li, 26)
    elif op == 16:
        li = word & 0xFFFC
        val = _signed(li, 16)
    else:
        return None
    addr = val if word & 2 else (pc + val)
    return {"dest": addr & 0xFFFFFFFF,
            "link": bool(word & 1), "absolute": bool(word & 2)}


def _dform_match(read, pc: int, op: int, fr: int,
                 base: int, offset: int) -> bool:
    return _dform(read(pc)) == (op, fr, base, offset & 0xFFFF)


def _mr_matches(word: int, target: int, source_reg: int) -> bool:
    return bool((word >> 26) == 31
                and (word >> 1) & 1023 == 444
                and (word >> 16) & 31 == target
                and (word >> 21) & 31 == source_reg
                and (word >> 11) & 31 == source_reg)


def verify_static_gates(read) -> dict:
    for pc in (*STFS_GATES, *LFS_GATES, *STW_GATES, *CALL_GATES, *MR_GATES):
        _pc_check(pc)
    for pc, (fr, base, disp) in STFS_GATES.items():
        if not _dform_match(read, pc, 52, fr, base, disp):
            raise Abstain("calc_writer_instruction_gate_failed")
    for pc, (fr, base, disp) in LFS_GATES.items():
        if not _dform_match(read, pc, 48, fr, base, disp):
            raise Abstain("calc_latch_reader_instruction_gate_failed")
    for pc, (reg, base, disp) in STW_GATES.items():
        if not _dform_match(read, pc, 36, reg, base, disp):
            raise Abstain("calc_state_gate_failed")
    for pc, target in CALL_GATES.items():
        b = _branch(pc, read(pc))
        if (read(pc) >> 26 != 18 or b is None or not b["link"]
                or b["absolute"] or b["dest"] != target):
            raise Abstain("calc_call_chain_gate_failed")
    for pc, (dest, src) in MR_GATES.items():
        if not _mr_matches(read(pc), dest, src):
            raise Abstain("calc_receiver_identity_chain_gate_failed")
    # Source owner: both writer and latch lie in same unsplit Golf text unit.
    if any(not OWNER_START <= pc < OWNER_END for pc in (*STFS_GATES, *CALL_GATES)):
        raise Abstain("source_owner_invalid")
    return {
        "calc_current_writer_at": "0x802B4914",
        "calc_peak_writer_at": "0x802B4924",
        "calc_peak_reader_at": "0x802B31B0",
        "calc_state3_latch_writer_at": "0x802B31C4",
        "calc_state3_writer_at": "0x802B31C0",
        "two_direct_bl_edges_exact": True,
        "four_explicit_mr_receiver_copies_exact": True,
        "writer_instruction_gates_exact": True,
    }


def symbolize(pc: int, word: int) -> dict:
    """No 4-byte private source word in output; public PC and operands only."""
    _pc_check(pc)
    op = word >> 26
    line = {"pc": f"0x{pc:08X}", "opcode": op}
    if op in (14, 15, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 57, 60, 61):
        o, rt, ra, u = _dform(word)
        names = {
            14:"addi", 15:"addis", 32:"lwz", 34:"lbz", 36:"stw", 38:"stb",
            40:"lhz", 42:"lha", 44:"sth", 46:"lmw", 48:"lfs", 50:"lfd",
            52:"stfs", 54:"stfd", 56:"psq_l", 57:"psq_lu",
            60:"psq_st", 61:"psq_stu",
        }
        line.update({"class": names.get(op, "dform"), "reg": rt,
                     "base": ra, "disp": _signed(u, 16)})
    elif op in (16, 18):
        b = _branch(pc, word)
        line.update({"class": "bc" if op == 16 else ("bl" if b["link"] else "b"),
                     "target": f"0x{b['dest']:08X}",
                     "link": b["link"], "absolute": b["absolute"]})
        if op == 16:
            line.update({"bo":(word >> 21) & 31,
                         "bi":(word >> 16) & 31})
    elif op in (59, 63):
        line.update({
            "class": "fp_opcode59" if op == 59 else "fp_opcode63",
            "fd": (word >> 21) & 31, "fa":(word >> 16) & 31,
            "fb":(word >> 11) & 31, "fc":(word >> 6) & 31,
            "xo5":(word >> 1) & 31, "xo10":(word >> 1) & 1023})
    elif op == 31:
        line.update({"class":"int_xform", "rd":(word >> 21) & 31,
                     "ra":(word >> 16) & 31,"rb":(word >> 11) & 31,
                     "xo10":(word >> 1) & 1023})
    elif op == 19:
        xo = (word >> 1) & 1023
        line.update({"class": ("bclr" if xo==16 else
                               "bcctr" if xo==528 else "op19"),
                     "xo10":xo, "link":bool(word & 1)})
    else:
        line.update({"class":"unclassified"})
    return line


def source_slice(read) -> dict:
    gates = verify_static_gates(read)
    words = [symbolize(pc, read(pc)) for pc in range(*EXCERPT, 4)]
    # Candidate upstream scratch fields on the same r24 CALC base.
    store_sites = [
        {"pc":line["pc"], "field":f"+0x{line['disp']:X}",
         "source_freg":line["reg"]}
        for line in words if line.get("class") == "stfs"
        and line.get("base") == 24 and 0 <= line.get("disp", -1) <= 0x40
    ]
    producer_window = [line for line in words if
                       0x802B4860 <= int(line["pc"], 16) <= 0x802B4924]
    # Three return/callback-candidate sites are NOT automatically game inputs.
    bl_sites = [line for line in words if line["class"] == "bl"]
    return {
        "status":"REV1_CALC_UPSTREAM_STATIC_SOURCE_PASS",
        "public_unit": PUBLIC_OWNER,
        "source_callee":"fn_802B4794",
        "source_code_only":True,
        "game_input_consumption_verified":False,
        "calc_0x0C_accepted_power_verified":False,
        "native_club_angular_velocity_verified":False,
        "guest_execution_verified":False,
        "training_approved":False,
        "latch":gates,
        "current_and_peak_register_writer_annotations":{
            "+0x08":"f30 through calc r24",
            "+0x0C":"f1 through calc r24 (comparison-before-store to be proved by control flow)",
        },
        "r24_candidate_calculation_stores":store_sites,
        "potential_upstream_direct_calls":bl_sites,
        "fp_reaching_definitions_source_excerpt":producer_window,
        "full_bounded_excerpt": words,
        "next_step":"Manually verify registers feeding f30/f1, candidate callback recipients, and exact branches before assigning acceleration/peak/accepted-power semantics.",
    }


def _default_archive(data_root: Path) -> Path:
    if data_root.name != "Wii-AI-Golf-Data" or data_root.is_symlink():
        raise Abstain("private_data_root_unqualified")
    captures = data_root / "captures"
    if not captures.is_dir() or captures.is_symlink():
        raise Abstain("private_capture_root_missing")
    candidates = []
    for path in captures.iterdir():
        if not path.is_dir() or path.is_symlink():
            continue
        manifest = path / "manifest-PRIVATE.json"
        if not manifest.is_file() or manifest.is_symlink():
            continue
        if manifest.stat().st_size > 65536:
            continue
        try:
            header = json.loads(manifest.read_text(encoding="utf-8-sig"))
        except (ValueError, OSError, UnicodeError):
            continue
        if (type(header) is dict
                and header.get("kind") == "p0-private-numbered-capture-inventory"
                and header.get("capture_count") == 7):
            candidates.append(path)
    if len(candidates) != 1:
        raise Abstain("expected_one_existing_qualified_original_archive")
    return candidates[0]


def run(archive: Path, *, detailed: bool = False) -> dict:
    # _check_archive cryptographically validates all original 14 banks,
    # and confirms the private archived inventory manifest's provenance.
    try:
        folders = private._check_archive(archive)
    except (ValueError, OSError, KeyError, TypeError):
        raise Abstain("original_archive_sha_or_manifest_gate_failed") from None

    with ExitStack() as stack:
        phase_windows = []
        readers = []
        for n in (1, 5, 7):
            path = source._file(folders[n], f"{n}.1.raw", roster.MEM1_SIZE)
            fh = stack.enter_context(path.open("rb"))
            mm = stack.enter_context(mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ))
            readers.append(mm)
        for lo,hi in COHORT_PPC_WINDOWS:
            phase_windows.append([
                bytes(mm[lo-MEM1_BASE:hi-MEM1_BASE])
                for mm in readers
            ])
        if any(windows[0] != windows[1] or windows[0] != windows[2]
               for windows in phase_windows):
            raise Abstain("native_code_differs_between_original_1_5_7")
        result = source_slice(lambda pc:_word(readers[0], pc))
    # Verify originals again after reading, fail closed on races/altered hashes.
    try:
        private._check_archive(archive)
    except (ValueError, OSError, KeyError, TypeError):
        raise Abstain("original_archive_post_sha_gate_failed") from None
    result.update({
        "original_14_bank_sha_pre_and_post_verified":True,
        "native_mem1_code_phases_1_5_7_identical":True,
        "disassembly_excerpt_includes_private_raw_bytes":False,
    })
    if not detailed:
        # Keep small default result; detailed output consists only of public
        # source PCs, register indices, and instruction class/operands.
        result.pop("full_bounded_excerpt")
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path,
                        help="existing private archive; default auto-discovers unique cohort")
    parser.add_argument("--detailed", action="store_true",
                        help="include bounded PC/operator instruction table (never raw bytes)")
    args = parser.parse_args(argv)
    try:
        archive = args.archive if args.archive else _default_archive(DATA)
        report = run(archive, detailed=args.detailed)
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (Abstain, ValueError, OSError, TypeError, KeyError, OverflowError):
        # Never expose native paths, original-bank byte content or private
        # addresses in an exception string.
        print(json.dumps({"status":"ABSTAIN",
                          "reason":"source_or_original_archive_qualification_failed",
                          "training_approved":False}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
