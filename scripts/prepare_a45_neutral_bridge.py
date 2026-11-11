"""Prepare an isolated A45 neutral-suppressed bridge source; never touch V1.

Input is the reviewed local mcp_bridge_swing_atomic_a45.py. Output is another
name, created exclusively; script does not load or interact with Dolphin.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.integration.a45_neutral_probe_patch import patch_atomic_v1_to_neutral
from wii_ai_golf.shared.bridge_provenance import inspect_bridge_file

DEFAULT_SOURCE = ROOT.parent / "tools" / "mcp_bridge_swing_atomic_a45.py"
DEFAULT_OUTPUT = ROOT.parent / "tools" / "mcp_bridge_swing_atomic_a45_neutral.py"


def prepare(source: Path, output: Path) -> dict:
    source, output = Path(source), Path(output)
    if source.is_symlink() or not source.is_file():
        raise ValueError("Source must be an existing regular non-symlink file")
    if output.is_symlink() or (output.exists() and not output.is_file()):
        raise ValueError("Output must not be a link or a non-file")
    if source.resolve() == output.resolve() or output.suffix.lower() != ".py":
        raise ValueError("Output must be a separate .py source")
    inspected = inspect_bridge_file(source)
    if inspected.get("revision") != "V1-atomic-a45":
        raise ValueError("Expected the known V1 atomic A45 bridge source")
    patched = patch_atomic_v1_to_neutral(source.read_text(encoding="utf-8"))
    data = patched.encode("utf-8")
    if output.exists():
        if output.read_bytes() != data:
            raise FileExistsError("Different existing output: REFUSING overwrite")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            stream.write(data)
    return {"kind": "isolated-a45-neutral-button-only-source",
            "source_sha256": inspected["sha256"],
            "sha256": hashlib.sha256(data).hexdigest(),
            "output": str(output), "dolphin_launched": False,
            "runtime_capability_verified": False, "game_contact_verified": False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        receipt = prepare(args.source, args.output)
    except (ValueError, OSError, UnicodeError) as exc:
        parser.error(str(exc))
    print("Isolated neutral bridge prepared (Dolphin NOT launched).")
    print("SHA256:", receipt["sha256"])
    print("Original V1 source and game savestates unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
