"""Offline, private-only source-table wind shape audit (NO Dolphin RPC).

Source data in user-owned ignored sibling Wii-AI-Golf-Data only; does not
write or upload files. Output is counts/flags, never wind table entries.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.audit.golf_cross_bank_state import MEM1_SIZE, MEM2_SIZE
from wii_ai_golf.audit.golf_wind_table import audit_wind_source_tables

DEFAULT_PRIVATE_ROOT = ROOT.parent / "Wii-AI-Golf-Data"


def _private_bank(path: Path, root: Path, size: int) -> Path:
    if path.is_symlink() or not path.is_file() or path.suffix.lower() not in (
            ".raw", ".bin", ".mem"):
        raise ValueError("Missing or disallowed private native bank")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ValueError("Native bank outside ignored private root")
    if resolved.stat().st_size != size:
        raise ValueError("Native bank has unexpected size")
    return resolved


def analyze_local(mem1_path: Path, mem2_path: Path, *, private_root: Path):
    root = private_root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Invalid private root")
    p1 = _private_bank(mem1_path, root, MEM1_SIZE)
    p2 = _private_bank(mem2_path, root, MEM2_SIZE)
    if p1 == p2:
        raise ValueError("Duplicate private native bank")
    with ExitStack() as stack:
        f1 = stack.enter_context(p1.open("rb"))
        f2 = stack.enter_context(p2.open("rb"))
        b1 = stack.enter_context(mmap.mmap(f1.fileno(), 0, access=mmap.ACCESS_READ))
        b2 = stack.enter_context(mmap.mmap(f2.fileno(), 0, access=mmap.ACCESS_READ))
        return audit_wind_source_tables(b1, b2)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mem1", type=Path, required=True)
    parser.add_argument("--mem2", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, default=DEFAULT_PRIVATE_ROOT)
    args = parser.parse_args(argv)
    try:
        report = analyze_local(args.mem1, args.mem2, private_root=args.private_root)
    except (OSError, ValueError, BufferError, TypeError):
        # Do not echo arbitrary exceptions: OS and parsing errors may
        # contain user private paths, memory bytes and machine details.
        print("Private GetWind source audit stopped: local bank path/size or "
              "game source gate failed. No RAM values disclosed.",
              file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
