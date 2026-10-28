"""Connect #219 authenticated ORIGINAL B0 Rev1 source bytes to #254 pure CFG.

SOURCE-ONLY. No emulator, controller, new shot, or native data upload.
Proves no more than a source-level conservative must-definition candidate.
The #254 helper is imported ONLY from an exact clean reviewed Git worktree.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_ball_xyz_source_callers_private as source

CFG_SHA = "abd875dc83f3cf8e773c1790272ffb4759f37ef7"
CFG_RELATIVE = Path("scripts/review_p0_cache_receiver_cfg_mustdef.py")
EXPECTED_SOURCE_OWNER = "Pack/RPSports/RPGolScene/RPGolMapObjBall.cpp"
EXPECTED_CALLERS = (
    ("fn_80299ACC", 0x80299ACC, 0x80299B64),
    ("fn_80299C20", 0x80299C20, 0x80299C58),
)
ALLOWED_STATUS = {
    "STATIC_ENTRY_R3_MUST_FLOW",
    "NOT_PROVEN_FOR_ALL_REACHING_PATHS",
    "ABSTAIN_TARGET_UNREACHABLE",
    "ABSTAIN_SOURCE_UNRESOLVED",
}
# Mirror the reviewed #254 public categorical contract, not native error text.
ALLOWED_REASONS = {
    "INVALID_WINDOW", "INVALID_SOURCE_WORD", "TARGET_CALL_MISMATCH",
    "STATE_BUDGET", "OUT_OF_WINDOW_PATH", "ZERO_INSTRUCTION",
    "OUT_OF_WINDOW_BRANCH", "UNSUPPORTED_XFORM", "UNSUPPORTED_OPCODE",
    "INTERVENING_CALL", "INDIRECT_OR_UNSUPPORTED_BRANCH",
    "SYSTEM_CALL", "CALLSITE_NOT_VERIFIED", "NO_REACHABLE_TARGET_PATH",
    "UNCLASSIFIED_SOURCE_FAILURE", "SOURCE_ACCESS_FAILURE",
}


class QualificationError(Exception):
    """Redacted failure that never embeds a private path or instruction."""


def _git(root: Path, *args: str) -> str:
    try:
        p = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True,
            text=True, timeout=12, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise QualificationError from None
    if p.returncode != 0:
        raise QualificationError
    return p.stdout.strip()


def qualified_helper_root(root: Path):
    """Verify exact repo commit, worktree cleanliness and helper location."""
    if not root.is_dir() or root.is_symlink():
        raise QualificationError
    root = root.resolve()
    if _git(root, "rev-parse", "HEAD") != CFG_SHA:
        raise QualificationError
    if _git(root, "status", "--porcelain", "--untracked-files=all") != "":
        raise QualificationError
    helper = root / CFG_RELATIVE
    if (not helper.is_file() or helper.is_symlink()
            or helper.resolve() != root / CFG_RELATIVE):
        raise QualificationError
    # Reject a checked-out file that differs from the pinned commit,
    # even if a different worktree-level config hides status changes.
    blob = _git(root, "rev-parse", CFG_SHA + ":" + CFG_RELATIVE.as_posix())
    if _git(root, "hash-object", "--", str(helper)) != blob:
        raise QualificationError
    return helper


def load_helper(helper_root: Path):
    path = qualified_helper_root(helper_root)
    spec = importlib.util.spec_from_file_location("p0_reviewed_cfg_helper", path)
    if spec is None or spec.loader is None:
        raise QualificationError
    module = importlib.util.module_from_spec(spec)
    # The helper worktree must remain pristine after import.
    old = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    except Exception:
        raise QualificationError from None
    finally:
        sys.dont_write_bytecode = old
    if (getattr(module, "CALLERS", None) != EXPECTED_CALLERS
            or getattr(module, "CACHE_TARGET", None) != 0x80299C70
            or not callable(getattr(module, "inspect_known_callers", None))):
        raise QualificationError
    return module


def _validate_source_ownership(public_units):
    if not isinstance(public_units, (list, tuple)) or not public_units:
        raise QualificationError
    for _, entry, call in EXPECTED_CALLERS:
        # Exactly ONE published Rev1 code unit must contain this entire
        # source slice, and it MUST be the expected MapObjBall.cpp unit.
        # Another Golf file with broader fabricated bounds is not enough.
        containing = [(a, b, name) for a, b, name in public_units
                      if a <= entry and call + 4 <= b]
        if not (source.UNITS[2][1] <= entry < call
                and call + 4 <= source.UNITS[2][2]
                and len(containing) == 1
                and containing[0][2] == EXPECTED_SOURCE_OWNER):
            raise QualificationError


def report_from_bytes(bank: Path, module, *, public_units):
    """Inspect exactly two reviewed code windows from independently gated B0.

    Caller must verify original bank SHA before and AFTER this function.
    """
    _validate_source_ownership(public_units)
    with bank.open("rb") as f:
        if f.read(6) != source.GAME_ID:
            raise QualificationError
        f.seek(7)
        if f.read(1) != b"\x01":
            raise QualificationError
        if bank.stat().st_size != source.MEM1_LEN:
            raise QualificationError

        def native_u32(pc):
            if type(pc) is not int or pc % 4:
                raise QualificationError
            if not any(entry <= pc <= call for _, entry, call in EXPECTED_CALLERS):
                raise QualificationError
            f.seek(pc - source.MEM1_START)
            word = f.read(4)
            if len(word) != 4:
                raise QualificationError
            return struct.unpack(">I", word)[0]

        findings = module.inspect_known_callers(native_u32)

    if (type(findings) is not dict
            or findings.get("kind") != "P0-STATIC-TWO-CALLER-R31-MUSTDEF-REVIEW"
            or type(findings.get("sources")) is not list
            or len(findings["sources"]) != 2
            or findings.get("runtime_receiver_verified") is not False
            or findings.get("training_approved") is not False):
        raise QualificationError
    rows = []
    for row, expected in zip(findings["sources"], EXPECTED_CALLERS):
        if (row.get("published_source_function") != expected[0]
                or row.get("kind") != "P0-STATIC-PPC-R31-CALLSITE-MUSTDEF"
                or row.get("status") not in ALLOWED_STATUS
                or type(row.get("all_reaching_paths_pass_entry_r3_through_r31_to_call_r3")) is not bool
                or row.get("runtime_receiver_object_verified") is not False
                or row.get("executed_cache_write_verified") is not False
                or row.get("training_approved") is not False):
            raise QualificationError
        reason = row.get("abstain_reason_category")
        relative = row.get("first_encountered_unresolved_source_relative_offset")
        if (reason is not None and reason not in ALLOWED_REASONS):
            raise QualificationError
        if (relative is not None and
                (type(relative) is not str
                 or re.fullmatch(r"\\+0x[0-9A-F]{4}", relative) is None
                 or int(relative[3:], 16) > expected[2] - expected[1])):
            raise QualificationError
        if row["status"] == "ABSTAIN_SOURCE_UNRESOLVED" and reason is None:
            raise QualificationError
        if (row["status"] != "ABSTAIN_SOURCE_UNRESOLVED"
                and relative is not None):
            raise QualificationError
        rows.append({
            "public_caller": expected[0],
            "conservative_static_cfg_status": row["status"],
            "first_abstain_reason_class": reason,
            "first_source_relative_unresolved_offset": relative,
            "diagnostic_witness_is_static_not_executed": True,
            "exact_cache_writer_callsite_reached": bool(
                row["known_exact_cache_writer_callsite_reached"]
            ),
            "all_reaching_paths_preserve_entry_receiver": row[
                "all_reaching_paths_pass_entry_r3_through_r31_to_call_r3"
            ],
        })
    return {
        "kind": "P0-SOURCE-AUTHENTICATED-ORIGINAL-B0-CACHE-CFG-ADAPTER",
        "game_id": "RSPE01",
        "revision": 1,
        "original_B0_SHA_and_manifest_verified_before_after": False,
        "public_Golf_source_window_gated": False,
        "reviewed_pure_CFG_helper_commit_verified": False,
        "source_only_two_callers": rows,
        "entry_r3_object_class_or_identity_verified": False,
        "runtime_cache_receiver_or_executed_writer_verified": False,
        "actual_guest_frames_verified": False,
        "rendered_physical_ball_XYZ_velocity_power_impact_score_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }


def audit(session: Path, data_root: Path, helper_root: Path):
    helper = load_helper(helper_root)
    original = source.checked_private_b0(session, data_root)
    public = source.load_public_text_units()
    result = report_from_bytes(original, helper, public_units=public)
    # Source ownership and original bank hash are checked again after reads.
    if source.checked_private_b0(session, data_root) != original:
        raise QualificationError
    result["original_B0_SHA_and_manifest_verified_before_after"] = True
    result["public_Golf_source_window_gated"] = True
    result["reviewed_pure_CFG_helper_commit_verified"] = True
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-session", type=Path, required=True)
    p.add_argument("--helper-root", type=Path, required=True)
    p.add_argument("--data-root", type=Path, default=(
        Path(__file__).resolve().parents[2] / "Wii-AI-Golf-Data"))
    args = p.parse_args(argv)
    try:
        result = audit(args.private_session, args.data_root, args.helper_root)
    except Exception:
        print("P0_CACHE_CFG_ADAPTER_ABSTAIN: original SHA/Rev1, source, "
              "helper revision, or conservative CFG qualification failed.",
              file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
