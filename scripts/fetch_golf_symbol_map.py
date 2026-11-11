"""Optional fetch of upstream public Wii Sports symbol maps into local data cache.

Do not vendor whole third-party maps in this repository: upstream project
has no explicit redistribution license. This downloads unchanged files for
local research, and never accesses Dolphin or game RAM.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from urllib.request import urlopen

UPSTREAM_COMMIT = "bcf62e22f9e7fc1d75acbb24bd8368b03cba1c81"
BASE_URL = f"https://raw.githubusercontent.com/kiwi515/ogws_info/{UPSTREAM_COMMIT}/"
FILES = {"csv": "RSPE_r1.map.csv", "map": "RSPE_r1.map",
         "dmap": "RSPE_r1.dmap"}
MAX_BYTES = 2_000_000
DEFAULT_CACHE = Path(__file__).resolve().parents[1].parent / "Wii-AI-Golf-Data" / "symbols"


def upstream_url(fmt: str) -> str:
    if fmt not in FILES:
        raise ValueError("unknown symbol map format")
    return BASE_URL + FILES[fmt]


def fetch(fmt: str, directory: Path) -> Path:
    url = upstream_url(fmt)
    target = directory / FILES[fmt]
    if target.exists():
        raise FileExistsError("local symbol map already exists (will not overwrite)")
    with urlopen(url, timeout=30) as response:
        payload = response.read(MAX_BYTES + 1)
    if not 0 < len(payload) <= MAX_BYTES:
        raise ValueError("download empty or exceeds 2 MB bound")
    directory.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(payload)
    return target


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=(*FILES, "all"), default="csv")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args(argv)
    try:
        for fmt in (FILES if args.format == "all" else (args.format,)):
            target = fetch(fmt, args.out_dir)
            print(f"Cached upstream {fmt} symbol map at: {target}")
        return 0
    except (OSError, ValueError) as exc:
        print(f"Symbol map fetch failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
