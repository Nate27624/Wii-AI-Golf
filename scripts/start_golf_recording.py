"""One-command golf recording: canonical Felk launch + savestate + A/A+B/A + scan.

Startup is AUTOMATIC by default. Uses the integration agent's exact menu
timing and existing pre-start savestate, and does not automatically swing.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from session_bootstrap import (
    add_boot_options, ensure_intro, boot_command, bridge_open,
    CANONICAL as DEFAULT_CANONICAL, DEFAULT_BRIDGE, DEFAULT_DOLPHIN,
)

SCAN_SCRIPT = ROOT / "scripts" / "discover_golf_motion.py"


def scan_command(*, seconds: float, interval: float, profile: str,
                 port: int, no_upload: bool) -> list[str]:
    """Scan ONLY; bootstrap occurs once in parent and must not run twice."""
    cmd = [
        sys.executable, str(SCAN_SCRIPT), "--seconds", str(seconds),
        "--interval", str(interval), "--profile", profile,
        "--port", str(port), "--startup", "skip",
    ]
    if no_upload:
        cmd.append("--no-upload")
    return cmd


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_boot_options(parser)
    parser.add_argument("--port", type=int, default=55355)
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--interval", type=float, default=0.6)
    parser.add_argument("--scan-profile", choices=("fast", "broad"), default="fast")
    parser.add_argument("--no-upload", action="store_true")
    args = parser.parse_args(argv)
    if not 5 <= args.seconds <= 180 or not .2 <= args.interval <= 10:
        parser.error("seconds must be 5..180; interval must be 0.2..10")
    if not SCAN_SCRIPT.is_file():
        raise FileNotFoundError("Evaluation motion scanner is missing")

    ensure_intro(args)
    print("Canonical intro complete. Recording read-only variables now.")
    print("Swing manually. Press Ctrl+C to finish and upload early.")
    status = subprocess.run(
        scan_command(seconds=args.seconds, interval=args.interval,
                     profile=args.scan_profile, port=args.port,
                     no_upload=args.no_upload),
        cwd=ROOT, check=False,
    )
    return status.returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Golf capture startup failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
