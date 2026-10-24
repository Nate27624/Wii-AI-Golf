"""Read-only candidate object pointer scan; no known ball-physics pointer yet."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from session_bootstrap import add_boot_options,ensure_intro
from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.physics_pointer_census import discover_roots,find_pointer_candidates,capture,analyze
from wii_ai_golf.golf_collection import make_run_id,publish_sanitized

def main():
    p=argparse.ArgumentParser(description=__doc__)
    add_boot_options(p)
    p.add_argument("--port",type=int,default=55355)
    p.add_argument("--seconds",type=float,default=25)
    p.add_argument("--interval",type=float,default=.2)
    p.add_argument("--max-pointers",type=int,default=16)
    p.add_argument("--data-dir",type=Path,default=ROOT.parent/"Wii-AI-Golf-Data"/"captures")
    p.add_argument("--no-upload",action="store_true")
    args=p.parse_args()
    if not 5<=args.seconds<=180 or not .05<=args.interval<=10:
        p.error("seconds 5..180 and interval .05..10")
    if not 1<=args.max_pointers<=16:
        p.error("max-pointers 1..16")
    ensure_intro(args)
    args.data_dir.mkdir(parents=True,exist_ok=True)
    run=make_run_id()
    rawfile=args.data_dir/f"pointer-census-{run}.jsonl"
    recorded=[]
    errors=[]
    try:
        with FelkRPC(port=args.port,timeout_s=15) as rpc:
            roots=discover_roots(rpc)
            candidates=find_pointer_candidates(rpc,roots,max_pointers=args.max_pointers)
            if not candidates:
                raise RuntimeError("no safe candidate pointers found in root structs")
            print(f"Read-only one-hop census: {len(candidates)} hypothetical objects")
            print("Swing manually while recording; none is verified ball data.")
            print("Raw RAM stays local:",rawfile)
            start=time.monotonic()
            with rawfile.open("x",encoding="utf-8") as output:
                try:
                    while time.monotonic()-start<args.seconds:
                        tick=time.monotonic()
                        try:
                            row=capture(rpc,candidates)
                            row["elapsed_s"]=round(tick-start,3)
                            output.write(json.dumps(row,sort_keys=True)+"\n")
                            output.flush()
                            recorded.append(row)
                            if len(recorded)%10==0:
                                print(f"Collected {len(recorded)} snapshots; frame span {row['frame_span']}")
                        except (OSError,ValueError,RuntimeError) as e:
                            errors.append(type(e).__name__)
                            print(f"Read-only error: {type(e).__name__}: {e}")
                            if len(errors)>=3:break
                        delay=args.interval-(time.monotonic()-tick)
                        if delay>0:time.sleep(delay)
                except KeyboardInterrupt:
                    print("Ctrl+C: preserving collected data.")
    except (OSError,RuntimeError,ValueError) as exc:
        print(f"Pointer census failed: {exc}",file=sys.stderr)
        return 1
    report={"schema_version":1,"run_id":run,"study_id":"S002-GOLF-ONE-HOP-POINTER-CENSUS",
            "captured_utc":datetime.now(timezone.utc).isoformat(),
            "samples":len(recorded),"errors":errors,
            "pointer_provenance":candidates,
            "frame_span_min":min((r["frame_span"] for r in recorded),default=None),
            "frame_span_max":max((r["frame_span"] for r in recorded),default=None),
            "hypotheses":analyze(recorded),
            "warning":"Unverified one-hop objects; not confirmed ball position, velocity or scoring"}
    summary=args.data_dir/f"pointer-census-{run}-summary.json"
    with summary.open("x",encoding="utf-8") as out:json.dump(report,out,indent=2)
    print(f"Saved {len(recorded)} scans: {summary}")
    if recorded and not args.no_upload:
        try:print("Numerical report:",publish_sanitized(report,ROOT))
        except (RuntimeError,OSError,ValueError) as exc:print("Upload failed; report remains local:",exc)
    return 0 if recorded else 1

if __name__=="__main__":
    raise SystemExit(main())
