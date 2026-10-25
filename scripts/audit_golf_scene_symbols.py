"""Offline symbol-map triage for Wii Sports US Rev1 golf scene access.

Symbol addresses are code/data symbol locations, NOT runtime object pointers.
Never dereferences game memory, operates Dolphin, or prints raw data.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

MAX_MAP_BYTES = 32 * 1024 * 1024
TOKENS = ("RPGolScene", "RPGolMain", "RPSysSceneMgr",
          "RPSysSceneCreator", "RPSysScene", "RPSportsBaseScene")
# Match the *exact* qualified class name. Simple substring checks conflate
# RPSysScene, RPSysSceneMgr, and RPSysSceneCreator in the upstream symbol map.
CLASS_PATTERNS = {name: re.compile(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"::")
                  for name in TOKENS}
DEFAULT_MAP = Path(__file__).resolve().parents[1] / "research" / "reference" / "golf_scene_rev1_symbols.csv"
ADDRESS = re.compile(r"(?<![0-9A-Fa-f])(?:0x)?[89][0-9A-Fa-f]{7}(?![0-9A-Fa-f])")

def summarize(lines):
    entries = {}
    for line in lines:
        if not any(pattern.search(line) for pattern in CLASS_PATTERNS.values()):
            continue
        # Addresses in map/csv/dmap are source-level symbols, not heap objects.
        addresses = [int(s,16) for s in ADDRESS.findall(line)]
        if not addresses:
            continue
        symbol = next((t for t in TOKENS if CLASS_PATTERNS[t].search(line)), None)
        if symbol is None:
            continue
        # Exact member-name hints only: createInstance() is a function,
        # NOT evidence of static singleton storage.
        possible_static = re.search(
            r"(?<![A-Za-z0-9_])(?:sInstance|spInstance|gInstance|singleton)(?![A-Za-z0-9_])",
            line)
        category = "candidate_static_data_symbol" if possible_static else "symbol_location_only"
        key = (symbol, category)
        info = entries.setdefault(key, {"symbol_group":symbol, "classification":category,
                                         "matching_map_lines":0, "code_or_data_locations":0})
        info["matching_map_lines"] += 1
        info["code_or_data_locations"] += len(addresses)
    return {"schema_version":1, "kind":"golf_scene_static_symbol_audit",
            "matched_groups":sorted(entries.values(), key=lambda e:(e["symbol_group"],e["classification"])),
            "scene_object_pointer":None, "golf_main_object_pointer":None,
            "confirmed_member_offset":"RPGolScene +0x9C",
            "source":"kiwi515/ogws_info RP/RPSports/RPGolScene/RPGolScene.h",
            "warning":"Map symbol addresses are not live RPGolScene/RPGolMain object pointers. Never dereference without independently verified scene instance and mode/revision gates."}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map",type=Path,default=DEFAULT_MAP,
                        help="Local map/CSV; defaults to bundled cited scene symbols")
    parser.add_argument("--out",type=Path)
    args=parser.parse_args(argv)
    try:
        if not args.map.is_file() or not 0 < args.map.stat().st_size <= MAX_MAP_BYTES:
            raise ValueError("missing or oversized local symbol map")
        if args.out and args.out.resolve() == args.map.resolve():
            raise ValueError("cannot overwrite source symbol map")
        with args.map.open(encoding="utf-8",errors="replace") as handle:
            result=summarize(handle)
        payload=json.dumps(result,indent=2,sort_keys=True)+"\n"
        if args.out:
            args.out.parent.mkdir(parents=True,exist_ok=True)
            with args.out.open("x",encoding="utf-8") as handle:
                handle.write(payload)
        print(payload,end="")
        return 0
    except (OSError,ValueError) as exc:
        print(f"Symbol map audit failed: {exc}",file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
