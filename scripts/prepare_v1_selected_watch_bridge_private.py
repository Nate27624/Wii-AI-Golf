"""OFFLINE ONLY: prepare a distinct watched V1 bridge for owner source review.

Never launches Dolphin, calls Felk RPC, changes controller/savestate, replaces
original V1/V2, or enables live use. The source hash is the exact human-contact
bridge. Only one new file may be created under local sibling tools/.
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

from wii_ai_golf.integration.v1_ball_watch_compat import (
    KNOWN_CONTACT_V1_SHA256,
    extend_known_v1_with_selected_watch,
    V1BallWatchCompatibilityError,
)


def prepare(source: Path, output: Path) -> dict:
    if source.is_symlink() or output.is_symlink():
        raise V1BallWatchCompatibilityError("Linked bridge paths refused")
    parent = (ROOT.parent / "tools").resolve(strict=True)
    source = source.resolve(strict=True)
    output = output.resolve(strict=False)
    if source.parent != parent or source.name != "mcp_bridge_swing_legacy_eval.py":
        raise V1BallWatchCompatibilityError("Source must be original isolated known V1")
    if (output.parent != parent or output.name != "mcp_bridge_swing_legacy_watch_eval.py"
            or output == source or output.exists()):
        raise V1BallWatchCompatibilityError("Output must be one new separate known watched V1 path")
    if not source.is_file() or not 0 < source.stat().st_size <= 200_000:
        raise V1BallWatchCompatibilityError("Source bounds invalid")
    original = source.read_bytes()
    if hashlib.sha256(original).hexdigest() != KNOWN_CONTACT_V1_SHA256:
        raise V1BallWatchCompatibilityError("Actual installed V1 hash is not known-contact fingerprint")
    # Exact byte decoding; no CRLF/universal-newline changes to source hash.
    watched_text = extend_known_v1_with_selected_watch(original.decode("utf-8"))
    compile(watched_text, "<OFFLINE-V1-watched-bridge>", "exec",
            flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
    # Exclusive creation after complete validations, never overwrite.
    with output.open("x", encoding="utf-8", newline="") as stream:
        stream.write(watched_text)
    return {
        "kind": "offline-source-pinned-v1-selected-record-watch-PREPARATION",
        "generated_separate_source": True,
        "original_controller_bridge_untouched": True,
        "read_only_51_selected_record_words": True,
        "a_lead_45_OBSERVED_FRAMES_implemented_by_this_tool": False,
        "dolphin_or_rpc_launched": False,
        "live_shot_authorized": False,
        "training_allowed": False,
        "new_output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(prepare(args.source, args.output),
                         sort_keys=True, indent=2))
        return 0
    except (OSError, UnicodeError, SyntaxError, V1BallWatchCompatibilityError) as exc:
        print("V1 watch offline preparation refused: " + type(exc).__name__,
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
