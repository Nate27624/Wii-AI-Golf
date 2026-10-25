"""Launch the unified S000-S005 Golf Lab desktop app on Windows."""
from pathlib import Path
import sys

SRC = str(Path(__file__).resolve().parents[1] / "src")
if SRC in sys.path:
    sys.path.remove(SRC)
sys.path.insert(0, SRC)

from wii_ai_golf.lab.gui import launch

if __name__ == "__main__":
    try:
        raise SystemExit(launch())
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Golf Lab: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
