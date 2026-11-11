"""Offline-only golfer player-like state comparisons, 4 paired checkpoints.

Requires 8 existing native files in ignored private folder, no live emulator.
No values, paths, addresses, ROMs, or raw RAM are printed or published.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from wii_ai_golf.audit.golf_player_four_phase import compare_player_control_files


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root",type=Path,required=True)
    for stage in ("b0","b1","b2","b3"):
        p.add_argument("--"+stage+"-mem1",type=Path,required=True)
        p.add_argument("--"+stage+"-mem2",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(argv)
    try:
        pairs=[(getattr(a,stage+"_mem1"),getattr(a,stage+"_mem2"))
               for stage in ("b0","b1","b2","b3")]
        r=compare_player_control_files(pairs,private_root=a.private_root,output=a.output)
    except (OSError,ValueError,TypeError,KeyError):
        print("Player-source private four-phase triage stopped; "
              "check bank sizes/scene/provenance offline; no upload",
              file=sys.stderr)
        return 1
    print(json.dumps(r,indent=2,sort_keys=True,allow_nan=False))
    print("LOCAL-ONLY summary, not approved for public GitHub")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
