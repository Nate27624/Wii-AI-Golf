"""Offline evaluation-only trace audit. For future shared golf CLI delegation."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from wii_ai_golf.evaluation.focused_trace import analyze_trace

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True,help="local raw focused XYZ .jsonl")
    p.add_argument("--output",type=Path,help="optional local sanitized summary .json")
    p.add_argument("--motion-threshold",type=float,default=.1)
    p.add_argument("--reset-threshold",type=float,default=25.)
    args=p.parse_args()
    result=analyze_trace(args.input,motion_threshold=args.motion_threshold,
                         reset_threshold=args.reset_threshold)
    rendered=json.dumps(result,indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(rendered+"\n",encoding="utf-8")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
