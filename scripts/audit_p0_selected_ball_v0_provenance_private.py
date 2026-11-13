"""Read-only, original-SHA-gated Rev1 Ball launch callsite audit.

Only bounded callsite qualification; receiver/guest execution remains UNKNOWN.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as original
import audit_golf_two_bank_roster_private as banks

CALLS = (
    (0x80299B38, 0x8029A0E0, "prepare_third"),
    (0x80299B48, 0x8029A5EC, "third_to_global_candidate"),
    (0x80299B64, 0x80299C70, "intermediate_process"),
    (0x80299BC4, 0x8029A5EC, "incoming_to_global_candidate"),
    (0x80299CCC, 0x80299890, "conditional_global_process_candidate"),
)
PHASES = (1, 5, 7)

def direct_bl_target(pc: int, word: int) -> int | None:
    """Return only a relative PowerPC direct BL target."""
    if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
        return None
    if (word >> 26) != 18 or (word & 3) != 1:
        return None
    displacement = word & 0x03FFFFFC
    if displacement & 0x02000000:
        displacement -= 0x04000000
    return (pc + displacement) & 0xFFFFFFFF

def symbolic_handoff(*, state3: bool | None, flag1: bool | None,
                     intermediate_returns: bool | None,
                     incoming_is_selected: bool | None) -> dict:
    """Branch-conditional source chronology: NOT an executed-shot witness."""
    if any(type(x) not in (bool, type(None)) for x in (
            state3, flag1, intermediate_returns, incoming_is_selected)):
        raise ValueError("Invalid symbolic branch predicate")
    steps = ["prepare_third", "candidate_copy_third_to_global",
             "call_intermediate_global_processing"]
    if intermediate_returns is True and state3 is True:
        steps += ["conditional_state3_scalar_0x8c",
                  "candidate_copy_incoming_to_global",
                  "incoming_state_ptr_clear_0x138"]
    elif intermediate_returns is True and state3 is False:
        steps.append("state3_late_copy_not_entered")
    else:
        steps.append("later_copy_reachability_unproven")
    scalar = ("direct_state_scalar" if state3 is True and flag1 is True
              else "unknown_optional_multiplier" if state3 is True and flag1 is False
              else "not_proven")
    return {
        "steps": steps,
        "scalar_0x8c_input": scalar,
        "selected_receiver_identity_known": incoming_is_selected is True,
        "selected_ball_v0_verified": False,
        "runtime_execution_verified": False,
        "training_approved": False,
    }



# Exact public ogws RSPE01_01 symbols.txt function intervals:
# fn_80299890 [0x80299890,0x80299ACC)
# fn_80299C70 [0x80299C70,0x8029A038)
# fn_8029B554 [0x8029B554,0x8029B57C)
# These windows stay strictly inside them, avoiding neighboring functions.
WINDOWS = {
    "integrator_receiver_prefix": (0x80299890, 0x802998D0),
    "global_processing_call": (0x80299C9C, 0x80299CDC),
    "selected_sim_entry": (0x8029B554, 0x8029B57C),
}
ALLOWED_DFORM = {14: "addi", 32: "lwz", 34: "lbz", 36: "stw",
                 40: "lhz", 48: "lfs", 52: "stfs"}

def signed16(x: int) -> int:
    return x - 65536 if x & 32768 else x

def decode_symbolic(pc: int, word: int) -> dict:
    """Compact PPC operands, no private memory values or instruction words."""
    if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
        raise ValueError("unqualified source word")
    op = word >> 26
    row = {"pc": f"0x{pc:08X}", "kind": "unresolved_opcode"}
    if op in ALLOWED_DFORM:
        row.update(kind=ALLOWED_DFORM[op], register=(word >> 21) & 31,
                   base=(word >> 16) & 31, offset=signed16(word & 65535))
    elif op == 18:
        displacement = word & 0x03FFFFFC
        if displacement & 0x02000000:
            displacement -= 0x04000000
        target = (displacement if word & 2 else pc + displacement) & 0xFFFFFFFF
        row.update(kind="bl" if word & 1 else "b", target=f"0x{target:08X}")
    elif op == 16:
        displacement = word & 0xFFFC
        if displacement & 0x8000:
            displacement -= 0x10000
        target = (displacement if word & 2 else pc + displacement) & 0xFFFFFFFF
        row.update(kind="bc", target=f"0x{target:08X}",
                   bo=(word >> 21) & 31, bi=(word >> 16) & 31,
                   lk=bool(word & 1))
    elif op == 19:
        row.update(kind="branch_register_candidate", xo=(word >> 1) & 1023)
    elif op == 31:
        row.update(kind="integer_xform_candidate", rt=(word >> 21) & 31,
                   ra=(word >> 16) & 31, rb=(word >> 11) & 31,
                   xo=(word >> 1) & 1023)
    return row

def source_window_report(archive: Path) -> dict:
    """Original-bank source windows only; cannot prove runtime receivers."""
    original._check_archive(archive)
    phases = {}
    with ExitStack() as stack:
        for phase in PHASES:
            mapped = []
            for bank_index, size in enumerate(original.SIZE):
                path = original.src._file(
                    archive, f"{phase}.{bank_index+1}.raw", size)
                fd = stack.enter_context(path.open("rb"))
                mapped.append(stack.enter_context(
                    mmap.mmap(fd.fileno(), 0, access=mmap.ACCESS_READ)))
            rd = banks.TwoBankReader(*mapped)
            phases[phase] = {
                name: tuple(rd.u32(pc) for pc in range(lo, hi, 4))
                for name, (lo, hi) in WINDOWS.items()
            }
    if not all(phases[1] == phases[phase] for phase in (5, 7)):
        raise ValueError("original source windows mismatch")
    report = {
        name: [decode_symbolic(pc, word)
               for pc, word in zip(range(*WINDOWS[name], 4), phases[1][name])]
        for name in WINDOWS
    }
    original._check_archive(archive)
    return {
        "status": "SOURCE_BOUNDED_INTEGRATOR_WINDOWS_ONLY",
        "source_windows_phases_1_5_7_equal": True,
        "original_archive_sha_pre_post": True,
        "symbolic_windows": report,
        "selected_receiver_must_definition_verified": False,
        "selected_v0_runtime_verified": False,
        "training_approved": False,
    }


# Scan only the exact published fn_80299890 body. The register is a
# candidate control/mode argument, NOT a proven semantic switch.
MODE_WINDOW = (0x80299890, 0x80299ACC)
MODE_MR_PC = 0x802998AC
MODE_CALLS = ((0x802998B4, 0x80298E70), (0x80299A18, 0x80297A00))
MAX_MODE_REFERENCES = 12

def is_mr(word: int, *, dest: int, source: int) -> bool:
    """PowerPC mr alias: or rA,rS,rS (XO=444, Rc=0)."""
    return (type(word) is int and 0 <= word <= 0xFFFFFFFF
            and word >> 26 == 31 and (word >> 1) & 1023 == 444
            and (word & 1) == 0 and (word >> 16) & 31 == dest
            and (word >> 21) & 31 == source
            and (word >> 11) & 31 == source)

def mode_reference(pc: int, word: int) -> dict | None:
    """Conservative candidate r30 operand, never complete PPC dataflow."""
    op = word >> 26
    if op in (14, 15, 32, 34, 36, 38, 40, 42, 44, 48, 50, 52, 54):
        reg = (word >> 21) & 31
        base = (word >> 16) & 31
        if base == 30 or (reg == 30 and op in (14, 15, 32, 34, 40, 42)):
            return {"pc": f"0x{pc:08X}", "op": op, "reg": reg,
                    "base": base, "offset": signed16(word & 65535),
                    "role": "possible_base_or_definition"}
    elif op == 31:
        rt, ra, rb = (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31
        if 30 in (rt, ra, rb):
            return {"pc": f"0x{pc:08X}", "op": 31,
                    "rt": rt, "ra": ra, "rb": rb,
                    "xo": (word >> 1) & 1023, "role": "possible_xform_operand"}
    elif op in (10, 11) and (word >> 16) & 31 == 30:
        return {"pc": f"0x{pc:08X}", "op": op,
                "comparison_register": 30, "role": "comparison_candidate"}
    return None

def mode_source_report(archive: Path) -> dict:
    """Minimal JSON for LocalOps; SHA gates pre/post, no output clipping."""
    original._check_archive(archive)
    snapshots = []
    with ExitStack() as stack:
        for phase in PHASES:
            mapped = []
            for bank_index, size in enumerate(original.SIZE):
                bank_path = original.src._file(
                    archive, f"{phase}.{bank_index+1}.raw", size)
                fd = stack.enter_context(bank_path.open("rb"))
                mapped.append(stack.enter_context(
                    mmap.mmap(fd.fileno(), 0, access=mmap.ACCESS_READ)))
            rd = banks.TwoBankReader(*mapped)
            snapshots.append(tuple(rd.u32(pc) for pc in range(*MODE_WINDOW, 4)))
    if snapshots[0] != snapshots[1] or snapshots[0] != snapshots[2]:
        raise ValueError("integrator source phases differ")
    words = snapshots[0]
    index = lambda pc: (pc - MODE_WINDOW[0]) // 4
    if not is_mr(words[index(MODE_MR_PC)], dest=30, source=4):
        raise ValueError("integrator entry mode save differs")
    for pc, target in MODE_CALLS:
        if direct_bl_target(pc, words[index(pc)]) != target:
            raise ValueError("integrator call target differs")
    uses = [
        mode_reference(pc, words[index(pc)])
        for pc in range(MODE_MR_PC+4, MODE_WINDOW[1], 4)
    ]
    uses = [u for u in uses if u is not None]
    if len(uses) > MAX_MODE_REFERENCES:
        raise ValueError("mode candidate use count exceeds output cap")
    original._check_archive(archive)
    report = {
        "status": "SOURCE_R4_R30_OPERANDS_ONLY",
        "original_14_bank_sha_pre_post": True,
        "phase_1_5_7_integrator_body_equal": True,
        "entry_r4_saved_to_r30": True,
        "fixed_call_targets_pass": True,
        "r30_candidate_uses": uses,
        "r30_use_count": len(uses),
        "r30_mode_semantics_verified": False,
        "selected_ball_v0_verified": False,
        "runtime_execution_verified": False,
        "training_approved": False,
    }
    if len(json.dumps(report, separators=(",", ":"))) > 2200:
        raise ValueError("research report would be clipped by LocalOps")
    return report

def discover_approved_archive() -> Path:
    """Find exactly one original seven-pair archive in the existing private root.

    Directory metadata only: no broad filesystem traversal or outside root
    fallback. The complete manifest, native source and SHA gates run later.
    """
    root = original.src.selected.DATA_ROOT
    if root.is_symlink():
        raise ValueError("private root symlink")
    captures = root / "captures"
    if captures.is_symlink() or not captures.is_dir():
        raise ValueError("private captures directory unavailable")
    candidates = []
    entries = list(captures.iterdir())
    if len(entries) > 32:
        raise ValueError("private capture inventory exceeds bound")
    for candidate in entries:
        if candidate.is_symlink() or not candidate.is_dir():
            continue
        marker = candidate / "manifest-PRIVATE.json"
        if marker.is_symlink() or not marker.is_file():
            continue
        if marker.stat().st_size > 65536:
            continue
        try:
            manifest = json.loads(marker.read_text(encoding="utf-8-sig"))
        except (ValueError, OSError, UnicodeError):
            continue
        if (type(manifest) is dict
                and manifest.get("kind") == "p0-private-numbered-capture-inventory"
                and manifest.get("capture_count") == 7
                and manifest.get("capture_numbers") == list(range(1, 8))
                and manifest.get("training_approved") is False):
            candidates.append(candidate)
    if len(candidates) != 1:
        raise ValueError("original archive not uniquely identified")
    return candidates[0]

def verify_original_calls(archive: Path) -> dict:
    # Private archive identity, source root and all 14 bank SHA gates.
    original._check_archive(archive)
    rows = []
    with ExitStack() as stack:
        for phase in PHASES:
            mapped = []
            for bank_index, size in enumerate(original.SIZE):
                path = original.src._file(
                    archive, f"{phase}.{bank_index + 1}.raw", size)
                fd = stack.enter_context(path.open("rb"))
                mapped.append(stack.enter_context(
                    mmap.mmap(fd.fileno(), 0, access=mmap.ACCESS_READ)))
            reader = banks.TwoBankReader(*mapped)
            rows.append(tuple(reader.u32(pc) for pc, _, _ in CALLS))
    if rows[0] != rows[1] or rows[1] != rows[2]:
        raise ValueError("source phases disagree")
    for (pc, target, _), word in zip(CALLS, rows[0]):
        if direct_bl_target(pc, word) != target:
            raise ValueError("source call gate failed")
    original._check_archive(archive)  # mandatory final SHA gate
    return {
        "status": "SOURCE_DIRECT_CALLS_ONLY",
        "original_archive_sha_pre_post": True,
        "audited_call_words_phases_1_5_7_identical": True,
        "qualified_calls": [label for _, _, label in CALLS],
        "vector_offsets": ["+0x78", "+0x7C", "+0x80"],
        "receiver_must_definition_proven": False,
        "selected_ball_v0_verified": False,
        "runtime_execution_verified": False,
        "training_approved": False,
    }

def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, help="Optional existing private archive; LocalOps must use no arguments")
    parser.add_argument("--study", choices=("calls", "integrator", "mode"), default="mode")
    opts = parser.parse_args(argv)
    try:
        archive = opts.archive if opts.archive is not None else discover_approved_archive()
        result = (mode_source_report(archive) if opts.study == "mode"
                  else source_window_report(archive) if opts.study == "integrator"
                  else verify_original_calls(archive))
    except (ValueError, OSError, TypeError, KeyError, OverflowError):
        # Never display exception strings (private paths/native state).
        result = {"status": "ABSTAIN",
                  "reason": "archive_or_source_call_gate_unqualified",
                  "selected_ball_v0_verified": False,
                  "training_approved": False}
        print(json.dumps(result))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
