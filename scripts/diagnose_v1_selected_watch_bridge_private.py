"""Read-only, fail-closed structural diagnosis for the approved historical V1 bridge.

Prints ONLY bounded counts and booleans. No source text, guest values,
runtime paths, controller calls, emulation, or generated files.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.integration.atomic_patch import PATCH_MARKER, BOOT_MARKER
from wii_ai_golf.integration.swing_patch import SWING_MARKER, SWING_NEUTRAL_V2_MARKER
from wii_ai_golf.integration.ball_watch_patch import BALL_WATCH_MARKER
from wii_ai_golf.integration.v1_ball_watch_compat import (
    KNOWN_CONTACT_V1_SHA256, extend_known_v1_with_selected_watch,
    V1BallWatchCompatibilityError,
)

COUNTS = {
    "handler_table": "HANDLERS = {",
    "swing_handler_registration": '    "trace.submit_swing": _wii_ai_submit_swing,',
    "frame_loop_tick": "    _wii_ai_tick()\n    _poll_sockets()",
}
MAX_READ_SIZE = 200_000


def inspect_text(text: str, *, actual_sha256: str) -> dict:
    counts = {name: min(3, text.count(anchor)) for name, anchor in COUNTS.items()}
    flags = {
        "atomic_marker_present": PATCH_MARKER in text,
        "swing_v1_marker_present": SWING_MARKER in text,
        "autoload_marker_absent": BOOT_MARKER not in text,
        "neutral_v2_marker_absent": SWING_NEUTRAL_V2_MARKER not in text,
        "watch_marker_absent": BALL_WATCH_MARKER not in text,
        "exact_historical_hit_source_sha256": actual_sha256 == KNOWN_CONTACT_V1_SHA256,
    }
    # Ordered fixed reason codes. The raw hash, bridge text and paths are
    # deliberately never returned, even on failures.
    if not flags["exact_historical_hit_source_sha256"]:
        reason = "ORIGINAL_SHA256_DIFFERENT"
    elif not all(flags.values()):
        reason = "SOURCE_MARKER_POLICY_MISMATCH"
    elif not all(n == 1 for n in counts.values()):
        reason = "SOURCE_ANCHOR_LAYOUT_MISMATCH"
    else:
        reason = "SOURCE_PREFLIGHT_PASS"
    return {
        "kind": "P0_V1_WATCH_SOURCE_DIAGNOSTIC_REDACTED",
        "read_only": True,
        "dolphin_or_rpc_contacted": False,
        "original_bridge_changed": False,
        "new_bridge_created": False,
        "full_source_sha256_printed": False,
        "marker_checks": flags,
        "source_anchor_counts_capped_at_three": counts,
        "preflight": reason,
        "live_use_approved": False,
    }


def diagnostic(source: Path) -> dict:
    report = inspect_text("", actual_sha256="")
    report["preflight"] = "SOURCE_PATH_REJECTED"
    if source.is_symlink():
        return report
    try:
        allowed_dir = (ROOT.parent / "tools").resolve(strict=True)
        source = source.resolve(strict=True)
    except (OSError, RuntimeError):
        report["preflight"] = "SOURCE_NOT_FOUND"
        return report
    if source.parent != allowed_dir or source.name != "mcp_bridge_swing_legacy_eval.py":
        return report
    if not source.is_file() or not 0 < source.stat().st_size <= MAX_READ_SIZE:
        report["preflight"] = "SOURCE_MISSING_OR_TOO_LARGE"
        return report
    data = source.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        report["preflight"] = "SOURCE_ENCODING_REJECTED"
        return report
    report = inspect_text(text, actual_sha256=hashlib.sha256(data).hexdigest())
    if report["preflight"] != "SOURCE_PREFLIGHT_PASS":
        return report
    try:
        patched = extend_known_v1_with_selected_watch(text)
    except V1BallWatchCompatibilityError:
        report["preflight"] = "SOURCE_TRANSFORM_REJECTED"
        return report
    try:
        compile(patched, "<OFFLINE-V1-TRANSFORM>", "exec",
                flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
    except SyntaxError:
        report["preflight"] = "SOURCE_COMPILE_REJECTED"
        return report
    report["in_memory_source_transform_and_compile_passed"] = True
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = diagnostic(args.source)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["preflight"] == "SOURCE_PREFLIGHT_PASS" else 2
    except (OSError, RuntimeError, ValueError):
        print('{"kind":"P0_V1_WATCH_SOURCE_DIAGNOSTIC_REDACTED","preflight":"SOURCE_READ_ERROR"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
