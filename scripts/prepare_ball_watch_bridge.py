"""Generate an isolated, opt-in Felk Swing V2 bridge with selected-ball watch.

OFFLINE ONLY. Never overwrites an existing bridge or launches Dolphin.
Input must be an already version-patched Swing V2 source. Output is separate,
outside the Git checkout, so the operator can revert by selecting old bridge.
"""
from __future__ import annotations

import argparse
import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.integration.ball_watch_patch import extend_swing_bridge_with_ball_watch


def prepare(source: Path, output: Path) -> dict:
    source = source.resolve(strict=True)
    output = output.resolve(strict=False)
    if source == output or output.exists():
        raise ValueError("Refusing to overwrite a source or existing bridge")
    if output.is_relative_to(ROOT):
        raise ValueError("Generated bridge must live outside the public repository")
    if not source.is_file() or source.stat().st_size > 200_000:
        raise ValueError("Expected locally installed small bridge .py source")
    new = extend_swing_bridge_with_ball_watch(source.read_text(encoding="utf-8"))
    compile(new, "<private-generated-bridge>", "exec",
            flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
    if not output.parent.is_dir() or output.suffix != ".py":
        raise ValueError("Output must be a separate .py under an existing private folder")
    with output.open("x", encoding="utf-8", newline="\n") as out:
        out.write(new)
    return {"kind": "offline-ball-watch-bridge-preparation",
            "created_separate_output": True,
            "modified_existing_bridge": False,
            "dolphin_launched": False,
            "swing_waveform_modified": False,
            "requires_review_before_live_use": True}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    try:
        report = prepare(args.source, args.output)
    except (OSError, UnicodeError, ValueError, SyntaxError, RuntimeError) as exc:
        print("Ball watch bridge preparation refused: " + type(exc).__name__,
              file=sys.stderr)
        return 1
    import json
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
