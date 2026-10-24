"""Trace one promising golf object XYZ, NOT a verified ball."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from session_bootstrap import add_boot_options, ensure_intro
from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.focused_object_xyz import preflight, observe, summarize
from wii_ai_golf.golf_collection import make_run_id, publish_sanitized

def main():
    p=argparse.ArgumentParser(description=__doc__)
    add_boot_options(p)
    p.add_argument("--port",type=int,default=55355)
    p.add_argument("--seconds",type=float,default=25)
    p.add_argument("--interval",type=float,default=0.05,
                   help="target delay; actual RPC frame time can exceed it")
    p.add_argument("--ready-timeout",type=float,default=180,
                   help="seconds for manual navigation before recording")
    p.add_argument("--phase",choices=("idle","swing","landing","unknown"),
                   default="unknown",help="user-observed phase label, never inferred")
    p.add_argument("--data-dir",type=Path,default=ROOT.parent/"Wii-AI-Golf-Data"/"captures")
    p.add_argument("--no-upload",action="store_true")
    args=p.parse_args()
    if not 5 <= args.seconds <= 180 or not .02 <= args.interval <= 10 or not 0 <= args.ready_timeout <= 600:
        p.error("--seconds 5..180 and --interval .02..10 required")
    ensure_intro(args)
    args.data_dir.mkdir(parents=True,exist_ok=True)
    run=make_run_id()
    rawfile=args.data_dir/f"focused-object-xyz-{run}.jsonl"
    samples=[]
    errors=[]
    try:
        with FelkRPC(port=args.port,timeout_s=15) as rpc:
            deadline=time.monotonic()+args.ready_timeout
            print("Waiting for Hitting the Green. Navigate with the physical Wii Remote.")
            print("Capture timer starts only AFTER the game is ready.")
            while True:
                try:
                    root=preflight(rpc)
                    break
                except (RuntimeError,KeyError,ValueError) as exc:
                    if time.monotonic() >= deadline:
                        raise RuntimeError("Golf mode not ready: "+str(exc)) from exc
                    time.sleep(1)
            print("Training golf mode verified; starting capture.")
            print("Source-gated Hitting the Green. Unverified dynamic object XYZ.")
            print("Raw local:",rawfile)
            start=time.monotonic()
            with rawfile.open("x",encoding="utf-8") as handle:
                try:
                    while time.monotonic()-start < args.seconds:
                        tick=time.monotonic()
                        try:
                            row=observe(rpc,root)
                            row["elapsed_s"]=round(tick-start,3)
                            row["observed_phase"]=args.phase
                            samples.append(row)
                            handle.write(json.dumps(row,sort_keys=True)+"\n")
                            handle.flush()
                            if len(samples)%30==0:
                                print(len(samples),"samples; xyz",row["xyz"],
                                      "span",row["frame_span"])
                        except (OSError,RuntimeError,ValueError) as exc:
                            errors.append(type(exc).__name__)
                            print("Read-only sample error:",type(exc).__name__,str(exc))
                            if len(errors)>=3:break
                        pause=args.interval-(time.monotonic()-tick)
                        if pause>0:time.sleep(pause)
                except KeyboardInterrupt:
                    print("Interrupted: local raw captures preserved.")
    except (OSError,RuntimeError,ValueError) as exc:
        print("Focused probe failure:",exc,file=sys.stderr)
        return 1
    report={"schema_version":1,"run_id":run,
            "study_id":"S002-FOCUSED-GOLF-OBJECT-XYZ",
            "captured_utc":datetime.now(timezone.utc).isoformat(),
            "observed_phase":args.phase,
            "samples":len(samples),"errors":errors,
            "frame_span_min":min((x["frame_span"] for x in samples),default=None),
            "frame_span_max":max((x["frame_span"] for x in samples),default=None),
            "hypotheses":summarize(samples),
            "warning":"This pointer +0x50 is NOT verified as the actual ball"}
    summary=args.data_dir/f"focused-object-xyz-{run}-summary.json"
    with summary.open("x",encoding="utf-8") as f:json.dump(report,f,indent=2)
    print("Completed:",len(samples),"samples. Summary:",summary)
    if samples and not args.no_upload:
        try:print("GitHub:",publish_sanitized(report,ROOT))
        except (OSError,RuntimeError,ValueError) as exc:
            print("Upload failed; local report retained:",exc)
    return 0 if samples else 1

if __name__=="__main__":
    raise SystemExit(main())
