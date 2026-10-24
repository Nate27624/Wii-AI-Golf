"""Read-only Wii Sports US Rev 1 golf struct-hint probe; never alters game."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from session_bootstrap import add_boot_options, ensure_intro

from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.observation_capture import write_snapshot
from wii_ai_golf.symbol_probe import probe_rev1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=55355)
    add_boot_options(parser)
    parser.add_argument("--out", type=Path,
                        default=Path("research/game-data.local/symbol-probe.json"))
    args = parser.parse_args()
    ensure_intro(args)
    with FelkRPC(port=args.port) as rpc:
        result = probe_rev1(rpc)
    write_snapshot(result, args.out)
    print(json.dumps({"saved": str(args.out), **result}, indent=2))


if __name__ == "__main__":
    main()
