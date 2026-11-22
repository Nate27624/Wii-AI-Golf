#!/usr/bin/env python3
"""Source-only accepted-power boundary review; no native archive access.

This conservative evidence tool uses previously published original-source
receipts. Its path probes are SYNTHETIC falsifiers for a future separately
approved, SHA-gated receiver/CFG audit. Even a passing probe is not a native
shot proof. This module never reads private source files, invokes Dolphin,
requests LocalOps, publishes a capture, or declares a training-ready label.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
from typing import Any

KIND = "s002-accepted-power-source-boundary-v1"
RECEIPTS = (
    "https://github.com/Nate27624/Wii-AI-Golf/issues/418#issuecomment-6843895549",  # #86 GPR census
    "https://github.com/Nate27624/Wii-AI-Golf/issues/418#issuecomment-6844088017",  # #96 same-f1 stores
    "https://github.com/Nate27624/Wii-AI-Golf/issues/418#issuecomment-6844226780",  # #99 zero constant
    "https://github.com/Nate27624/Wii-AI-Golf/issues/418#issuecomment-6844637943",  # conditional case1
)
# These exact public PCs are source findings, not a guest-executed path.
NONLINEAR_WRITE_PC = 0x802B2EF4
RESET_CALL_PC = 0x802B3E80
RESET_ENTRY_PC = 0x802B499C
THIRD_PREP_AUX_PC = 0x802A7ACC


class Abstain(ValueError):
    """A bounded synthetic audit cannot justify the requested inference."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _f32(value: float) -> float:
    """One host IEEE binary32 rounding, not full Gekko FMA parity."""
    if type(value) not in (int, float) or not math.isfinite(value):
        raise Abstain("NONFINITE_OR_NONTYPED_INPUT")
    try:
        return struct.unpack(">f", struct.pack(">f", value))[0]
    except (OverflowError, struct.error):
        raise Abstain("OUTSIDE_F32_RANGE") from None


def case1_aux_f32(f28: float) -> dict[str, Any]:
    """Test source-conditional aux=f32(0.5*f28), never accepted-power status.

    A half-multiply followed by double is bit-exact for ordinary binary32
    values, but can lose bits due to underflow at the smallest exponents.
    """
    value = _f32(f28)
    aux = _f32(0.5 * value)
    recovered = _f32(2.0 * aux)
    exact = struct.pack(">f", recovered) == struct.pack(">f", value)
    return {
        "source_math": "conditional_case1_aux_only",
        "roundtrip_binary32_exact": exact,
        "underflow_or_rounding_loss": not exact,
        "f28_is_accepted_shot_power": False,
        "aux_is_selected_ball_launch_scalar": False,
    }


def classify_calc_branch(calc40: int | None, state1a4: int | None,
                         flag1a8: int | None, flag1bc: int | None,
                         context_threshold: float | None) -> dict[str, Any]:
    """Retain input branches without inventing their native acceptance logic.

    The calc +0x40 zero/nonzero branch is a *candidate* selection fork. Its
    actual relation to shot commitment is not established; state/flags and
    context require original source branch proof. None is a power label.
    """
    for name, v in (("calc40", calc40), ("state1a4", state1a4),
                    ("flag1a8", flag1a8), ("flag1bc", flag1bc)):
        if v is not None and (type(v) is not int or not 0 <= v <= 0xffffffff):
            raise Abstain("INVALID_" + name.upper())
    if context_threshold is not None:
        _f32(context_threshold)
    return {
        "calc40_source_branch": ("UNKNOWN" if calc40 is None else
                                 "ZERO" if calc40 == 0 else "NONZERO"),
        "state_flag_context_available": all(x is not None for x in
                                            (state1a4, flag1a8, flag1bc,
                                             context_threshold)),
        "native_branch_meaning_verified": False,
        "committed_power_verified": False,
    }


def _validated_events(path: object) -> list[tuple[str, str]]:
    """A path is an explicitly ordered, symbolic *synthetic* instruction path.

    Tokens: nonlinear, reset, other_write, read. Receiver IDs are opaque
    synthetic labels; equal GPR names or equal offsets never imply equality.
    """
    if type(path) is not list or not 1 <= len(path) <= 64:
        raise Abstain("PATH_LENGTH_OR_TYPE")
    events = []
    for item in path:
        if (type(item) is not dict or set(item) != {"op", "receiver"} or
                item["op"] not in ("nonlinear", "reset", "other_write", "read") or
                type(item["receiver"]) is not str or
                not 1 <= len(item["receiver"]) <= 12 or
                not item["receiver"].isascii() or
                not item["receiver"].isalnum()):
            raise Abstain("INVALID_EVENT")
        events.append((item["op"], item["receiver"]))
    if sum(op == "read" for op, _ in events) != 1:
        raise Abstain("REQUIRES_ONE_CONSUMER")
    return events


def classify_synthetic_reaching_paths(paths: object, *,
                                      complete_cfg: bool,
                                      receiver_alias_proven: bool) -> dict[str, Any]:
    """Find last write of a read across enumerated hypothetical CFG paths.

    Even when every path is LIVE and flags are true, this is a SYNTHETIC
    model: caller/receiver alias, execution, and shot commit need a real
    separately approved SHA-qualified original-source proof.
    """
    if type(complete_cfg) is not bool or type(receiver_alias_proven) is not bool:
        raise Abstain("INVALID_PROOF_FLAG")
    if type(paths) is not list or not 1 <= len(paths) <= 16:
        raise Abstain("PATH_SET_BOUNDS")
    results = []
    for path in paths:
        events = _validated_events(path)
        last: dict[str, str] = {}
        for operation, receiver in events:
            if operation in ("nonlinear", "reset", "other_write"):
                last[receiver] = operation
            elif operation == "read":
                writer = last.get(receiver)
                results.append({"nonlinear": "LIVE", "reset": "KILLED_BY_RESET",
                                "other_write": "KILLED_BY_OVERWRITE",
                                None: "NO_QUALIFIED_REACHING_DEF"}[writer])
    unique = set(results)
    # A single path alone cannot prove that it is the exhaustive native CFG.
    if not complete_cfg or not receiver_alias_proven:
        conclusion = "UNKNOWN"
    elif unique == {"LIVE"}:
        conclusion = "LIVE_ON_ALL_ENUMERATED_PATHS_SYNTHETIC"
    elif unique <= {"KILLED_BY_RESET", "KILLED_BY_OVERWRITE"}:
        conclusion = "KILLED_ON_ALL_ENUMERATED_PATHS_SYNTHETIC"
    else:
        conclusion = "MIXED_OR_MISSING_DEFINITION_SYNTHETIC"
    return {
        "path_count": len(paths),
        "per_path": results,
        "synthetic_reaching_definition": conclusion,
        "source_same_receiver_proven": False,
        "source_full_cfg_proven": False,
        "actual_shot_commit_verified": False,
        "selected_ball_launch_transfer_verified": False,
    }


def source_ledger() -> dict[str, Any]:
    """Strictly scoped synthesis of already original-SHA-qualified receipts."""
    return {
        "kind": KIND,
        "published_original_source_receipts": list(RECEIPTS),
        "edges": [
            {
                "edge": "fn_802B499C_zero_initializer",
                "status": "PASS",
                "scope": "static_original_sha_qualified",
                "pc": f"0x{RESET_ENTRY_PC:08X}",
                "result": "+0x1AC/+0x1B0/+0x1B4/+0x1B8 are set to f32 zero on this source path",
            },
            {
                "edge": "fn_802B2AB4_nonlinear_to_accepted_scalar",
                "status": "UNKNOWN",
                "scope": "receiver_cfg_and_same_shot_unproven",
                "pc": f"0x{NONLINEAR_WRITE_PC:08X}",
            },
            {
                "edge": "case1_f28_to_aux",
                "status": "PASS",
                "scope": "conditional_static_prep_math_only",
                "pc": f"0x{THIRD_PREP_AUX_PC:08X}",
            },
            {
                "edge": "third_prep_to_selected_ball_launch",
                "status": "UNKNOWN",
                "scope": "separate_S002_selected_v0_owner_issue_415",
            },
        ],
        "priority_falsifier": (
            "same_receiver_reaching_definition_of_r3_at_0x802B3E80_"
            "versus_r29_later_0x1B0_and_r31_nonlinear_0x802B2EF4_"
            "then_committed_f28_and_selected_ball_transfer"
        ),
        "actual_accepted_power_verified": False,
        "selected_launch_p0_v0_verified": False,
        "native_game_parity_verified": False,
        "training_approved": False,
        "source_private_study_executed_by_this_tool": False,
    }


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("ledger", "synthetic-controls"),
                        default="ledger")
    args = parser.parse_args()
    if args.stage == "ledger":
        result = source_ledger()
    else:
        cases = {
            "before_reset": [{"op": "nonlinear", "receiver": "calcA"},
                             {"op": "read", "receiver": "calcA"},
                             {"op": "reset", "receiver": "calcA"}],
            "reset_before_read": [{"op": "nonlinear", "receiver": "calcA"},
                                  {"op": "reset", "receiver": "calcA"},
                                  {"op": "read", "receiver": "calcA"}],
            "different_receiver": [{"op": "nonlinear", "receiver": "calcA"},
                                   {"op": "reset", "receiver": "scratch"},
                                   {"op": "read", "receiver": "calcA"}],
            "branch_bypass": [{"op": "read", "receiver": "calcA"}],
        }
        result = {"kind": KIND, "synthetic_only": True,
                  "controls": {key: classify_synthetic_reaching_paths(
                      [value], complete_cfg=True, receiver_alias_proven=True)
                      ["per_path"][0] for key, value in cases.items()},
                  "actual_accepted_power_verified": False,
                  "training_approved": False}
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
