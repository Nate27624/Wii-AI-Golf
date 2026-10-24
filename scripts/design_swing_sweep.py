"""Produce offline study manifest/trace preview; never controls Dolphin."""
import argparse
import json
from pathlib import Path
from wii_ai_golf.modeling.sweep import make_sweep
from wii_ai_golf.modeling.swing import SwingProfile, swing_trace

def main():
    p=argparse.ArgumentParser(description="Plan S003 swing calibration WITHOUT gameplay")
    p.add_argument("--stage",choices=("recognition","calibration"),required=True)
    p.add_argument("--scenario",action="append",required=True)
    p.add_argument("--confirmed-axis",choices=("x+","x-","y+","y-","z+","z-"))
    p.add_argument("--seed",type=int,default=42)
    p.add_argument("--out",type=Path)
    p.add_argument("--show-trace",type=int)
    a=p.parse_args()
    plan=make_sweep(stage=a.stage,scenarios=a.scenario,confirmed_axis=a.confirmed_axis,seed=a.seed)
    if a.show_trace is not None:
        if not 1<=a.show_trace<=len(plan["trials"]):
            p.error("invalid trial index")
        trial=plan["trials"][a.show_trace-1]
        print(json.dumps({"trial":trial,"trace":swing_trace(SwingProfile(**trial["profile"]))},indent=2))
    elif a.out is None:
        print(json.dumps(plan,indent=2))
    else:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open("x",encoding="utf-8") as f:
            json.dump(plan,f,indent=2)
            f.write("\n")
        print(f"Wrote {plan['trial_count']} proposed, unexecuted trials: {a.out}")

if __name__=="__main__":
    main()
