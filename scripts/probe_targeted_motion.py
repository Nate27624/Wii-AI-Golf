"""Higher-rate, read-only targeted golf motion probe; unverified effect state."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from session_bootstrap import add_boot_options, ensure_intro
from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.targeted_motion import preflight, capture_one, analyze
from wii_ai_golf.golf_collection import make_run_id, publish_sanitized


def main():
    p=argparse.ArgumentParser(description=__doc__)
    add_boot_options(p)
    p.add_argument("--port",type=int,default=55355)
    p.add_argument("--seconds",type=float,default=25)
    p.add_argument("--interval",type=float,default=0.2)
    p.add_argument("--offset",type=lambda x:int(x,0),default=0x30)
    p.add_argument("--length",type=int,default=64)
    p.add_argument("--no-upload",action="store_true")
    p.add_argument("--data-dir",type=Path,default=ROOT.parent/"Wii-AI-Golf-Data"/"captures")
    args=p.parse_args()
    if not 5<=args.seconds<=180 or not .05<=args.interval<=10:
        p.error("seconds 5..180 and interval .05..10 required")
    if args.offset<0 or args.offset%4 or args.length<4 or args.length>128 or args.length%4:
        p.error("offset aligned nonnegative; length aligned 4..128")
    ensure_intro(args)
    args.data_dir.mkdir(parents=True,exist_ok=True)
    run=make_run_id()
    path=args.data_dir/f"targeted-motion-{run}.jsonl"
    captures=[]
    errors=[]
    start=time.monotonic()
    print("Read-only narrow motion probe; NO confirmed ball object or score yet.")
    print(f"Local raw data: {path}")
    try:
        with FelkRPC(port=args.port,timeout_s=15) as rpc:
            state=preflight(rpc)
            print("Verified US Rev1 training mode; unverified effect pointers:",
                  ", ".join(state["sources"]))
            with path.open("x",encoding="utf-8") as output:
                try:
                    while time.monotonic()-start<args.seconds:
                        tick=time.monotonic()
                        try:
                            row=capture_one(rpc,state["sources"],offset=args.offset,length=args.length)
                            row["elapsed_s"]=round(tick-start,3)
                            output.write(json.dumps(row,sort_keys=True)+"\n")
                            output.flush()
                            captures.append(row)
                            if len(captures)%5==0:
                                print(f"Captured {len(captures)} | RPC frame span {row['frame_span']}")
                        except (OSError,RuntimeError,ValueError) as exc:
                            print(f"Capture error: {type(exc).__name__}: {exc}")
                            errors.append(type(exc).__name__)
                            if len(errors)>=3:break
                        pause=args.interval-(time.monotonic()-tick)
                        if pause>0:time.sleep(pause)
                except KeyboardInterrupt:
                    print("Stopped: preserving captured evidence.")
    except (OSError,RuntimeError,ValueError) as exc:
        print(f"Probe preflight failed: {type(exc).__name__}: {exc}",file=sys.stderr)
        return 1
    result=analyze(captures)
    report={"run_id":run,"study_id":"S002-HG-TARGETED-MOTION",
            "captured_utc":datetime.now(timezone.utc).isoformat(),
            "samples":len(captures),"errors":errors[:10],
            "frame_span_min":min((r["frame_span"] for r in captures),default=None),
            "frame_span_max":max((r["frame_span"] for r in captures),default=None),
            "read_offset":args.offset,"read_length":args.length,
            "numeric_hypotheses":result,
            "warning":"Source-gated minimap render effects only, not validated ball physics or score; raw RAM local"}
    summary=args.data_dir/f"targeted-motion-{run}-summary.json"
    with summary.open("x",encoding="utf-8") as f:
        json.dump(report,f,indent=2)
    print(f"Saved {len(captures)} samples: {summary}")
    if captures and not args.no_upload:
        try:
            url=publish_sanitized(report,ROOT)
            print("Numerical report:",url)
        except (OSError,RuntimeError,ValueError) as exc:
            print(f"Upload failed ({type(exc).__name__}); report saved locally.")
    return 0 if captures else 1

if __name__=="__main__":
    raise SystemExit(main())
