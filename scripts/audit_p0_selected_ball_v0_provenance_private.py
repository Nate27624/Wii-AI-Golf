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
        "original_source_phases_1_5_7_identical": True,
        "qualified_calls": [label for _, _, label in CALLS],
        "vector_offsets": ["+0x78", "+0x7C", "+0x80"],
        "receiver_must_definition_proven": False,
        "selected_ball_v0_verified": False,
        "runtime_execution_verified": False,
        "training_approved": False,
    }

def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    opts = parser.parse_args(argv)
    try:
        result = verify_original_calls(opts.archive)
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
