"""Source-local universal CLI; works without pip install or PYTHONPATH setup."""
from __future__ import annotations

from pathlib import Path
import sys

_REPO = Path(__file__).resolve().parents[1]
_SRC = str(_REPO / "src")
if _SRC in sys.path:
    sys.path.remove(_SRC)
sys.path.insert(0, _SRC)

from wii_ai_golf.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
