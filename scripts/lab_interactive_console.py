"""Console-only visibility wrapper for one already-reviewed Lab command.

Does NOT launch Dolphin by itself or change the experiment command. It keeps
the new terminal open on a failure so argparse/traceback errors stay readable.
The same typed lab runner still controls fresh boot and live permissions.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
GOLF = ROOT / "scripts" / "golf.py"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] != "--":
        print("Expected -- before a reviewed Golf Lab command.", file=sys.stderr)
        return 2
    command = args[1:]
    if (len(command) < 4 or command[0] != sys.executable
            or Path(command[1]).resolve() != GOLF.resolve()
            or command[2:4] != ["lab", "run"]):
        print("Refusing non-Lab command; only the reviewed Lab runner is allowed.",
              file=sys.stderr)
        return 2
    try:
        status = subprocess.run(command, cwd=ROOT, check=False).returncode
    except OSError as exc:
        print(f"Lab command failed to start: {exc}", file=sys.stderr)
        status = 2
    if status != 0:
        print(f"\\nLAB PROCESS FAILED (exit {status}). This is NOT a golf result.",
              flush=True)
        print("The error is above. This console stays open until you close it.",
              flush=True)
        try:
            input("Press ENTER to close this error window: ")
        except EOFError:
            pass
    return status


if __name__ == "__main__":
    raise SystemExit(main())
