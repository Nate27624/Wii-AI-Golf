"""Compare local candidate-motion traces without treating movements as ball shots."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from wii_ai_golf.focused_trace import analyze_trace

def compare(paths):
    if len(paths)<2: raise ValueError("at least two control/experiment traces are needed")
    results=[]
    for name,path in paths:
        d=analyze_trace(path)
        results.append({"label":name,"samples":d["samples_parsed"],
                        "absent":d["null_or_invalid_pointer_samples"],
                        "movement_steps":d["moving_steps_below_reset"],
                        "movement_periods":len(d["motion_episodes"]),
                        "discontinuities":len(d["discontinuities"]),
                        "duration_s":d["duration_s"]})
    return {"schema_version":1,"claim":"COMPARISON_NOT_VERIFIED_BALL_IDENTITY",
            "experiments":results,
            "interpretation":"Aim-only movement would weaken ball-coordinate identity; lack of movement supports but does not prove it"}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--idle",type=Path,required=True)
    p.add_argument("--aim",type=Path,required=True)
    p.add_argument("--swing",type=Path,required=True)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    result=compare([("idle",a.idle),("aim_only_no_swing",a.aim),("swing",a.swing)])
    text=json.dumps(result,indent=2)
    print(text)
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(text+"\n",encoding="utf-8")
    return 0
if __name__=="__main__":raise SystemExit(main())
