"""Prepare a NEW optional A45 bridge source file without launching Dolphin.

The original isolated V1 bridge is never overwritten. Requires review of the
new file identity before use. This generator does not start or swing the game.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.integration.atomic_a45_patch import patch_isolated_v1_bridge
from wii_ai_golf.shared.bridge_provenance import inspect_bridge_file

DEFAULT_SOURCE = ROOT.parent / "tools" / "mcp_bridge_swing_legacy_eval.py"
DEFAULT_OUTPUT = ROOT.parent / "tools" / "mcp_bridge_swing_atomic_a45.py"


def prepare(source: Path, output: Path) -> dict:
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output or output.suffix.lower() != ".py":
        raise ValueError("Output must be a distinct Python source file")
    inspected = inspect_bridge_file(source)
    if (inspected["revision"] != "V1-neutral-swing-calls"
            or inspected["safe_for_isolated_legacy_copy"] is not True):
        raise ValueError("Input is not a vetted isolated, no-autoload V1 swing bridge")
    patched = patch_isolated_v1_bridge(source.read_text(encoding="utf-8"))
    data = patched.encode("utf-8")
    if output.exists():
        if not output.is_file() or output.read_bytes() != data:
            raise FileExistsError("Output exists with DIFFERENT bytes: never overwrite bridge")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            stream.write(data)
    return {
        "kind": "new-isolated-atomic-a45-bridge-source",
        "output": str(output), "sha256": hashlib.sha256(data).hexdigest(),
        "source_sha256": inspected["sha256"],
        "dolphin_launched": False, "bridge_loaded_in_runtime_verified": False,
        "game_a_recognition_verified": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = p.parse_args()
    try:
        report = prepare(args.source, args.output)
    except (OSError, ValueError, UnicodeError) as exc:
        p.error(str(exc))
    print("Prepared separate A45 bridge:", report["output"])
    print("SHA256:", report["sha256"])
    print("No Dolphin launched; runtime loaded bridge/ball contact are NOT verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
