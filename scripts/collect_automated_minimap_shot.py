"""One approved automated S002 shot with bounded minimap-effect snapshots.

Invoked ONLY as a post-boot action via scripts/run_golf_experiment.py.
No Dolphin launch, controller setup, or savestate mutation in this module.
"""
from __future__ import annotations
import argparse,hashlib,json,sys,time
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from wii_ai_golf.audit.outcome_transition import _ram,_u32,_bytes,STATIC_STRUCTS
from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.integration.swing_client import SwingTraceClient
from probe_swing import build_probe

def snapshot(rpc):
    start=rpc.call("frame.get_count",[])
    header=_bytes(rpc,0x80000000,8)
    if header[:6]!=b"RSPE01" or header[7]!=1:
        raise RuntimeError("Requires Wii Sports USA Rev1")
    config=_u32(rpc,STATIC_STRUCTS["golf_config"][0])
    field=_u32(rpc,STATIC_STRUCTS["golf_field"][0])
    if not _ram(config,0x98) or not _ram(field,0xA8) or _u32(rpc,config+0x94)!=4:
        raise RuntimeError("Hitting the Green mode not ready")
    ptr=_u32(rpc,field+0x9C)
    if not _ram(ptr,128):raise RuntimeError("Minimap visual effect unavailable")
    data=_bytes(rpc,ptr,128)
    end=rpc.call("frame.get_count",[])
    if type(start)!=int or type(end)!=int or end<start:raise RuntimeError("Invalid frame bracket")
    return {"frames":[start,end],"pointer":ptr,"hex":data.hex()}

def summary(rows,dispatch):
    phases={}
    for row in rows: phases.setdefault(row["phase"],[]).append(row)
    offsets=set();changes=0;previous=None
    for row in rows:
        if previous is not None and row["pointer"]==previous["pointer"]:
            delta=[i for i,(a,b) in enumerate(zip(bytes.fromhex(previous["hex"]),bytes.fromhex(row["hex"]))) if a!=b]
            if delta:changes+=1;offsets.update(delta)
        previous=row
    return {"schema_version":1,"study_id":"S002-AUTOMATED-MINIMAP-SHOT",
            "utc":datetime.now(timezone.utc).isoformat(),
            "samples":len(rows),"phase_counts":{k:len(v) for k,v in phases.items()},
            "changed_byte_offsets":sorted(offsets),"adjacent_changes":changes,
            "swing_dispatch_received":isinstance(dispatch,dict),
            "claim":"AUTOMATED_SWING_COMMAND_NOT_VERIFIED_BALL_CONTACT",
            "warning":"Minimap visual effect is not verified physics ball or score"}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--send-live-swing",action="store_true")
    p.add_argument("--no-upload",action="store_true",help="Keep sanitized report local")
    p.add_argument("--port",type=int,default=55355)
    p.add_argument("--before",type=int,default=5)
    p.add_argument("--after",type=int,default=20)
    p.add_argument("--interval",type=float,default=.25)
    args=p.parse_args()
    if not args.send_live_swing:p.error("Explicit --send-live-swing required")
    if not 2<=args.before<=30 or not 2<=args.after<=100 or not .05<=args.interval<=3:
        p.error("invalid bounded collection controls")
    folder=ROOT.parent/"Wii-AI-Golf-Data"/"captures"
    folder.mkdir(parents=True,exist_ok=True)
    run=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw=folder/("automated-effect-"+run+"-RAW-PRIVATE.jsonl")
    report=folder/("automated-effect-"+run+"-summary.json")
    samples=build_probe("forward",follow_through_frames=30)
    rows=[]
    print("Post-boot S002 capture: one automatic swing, private RAM stays local.",flush=True)
    with FelkRPC(port=args.port,timeout_s=15) as rpc,raw.open("x",encoding="utf-8") as out:
        def collect(phase,count):
            for i in range(count):
                entry={"phase":phase,"elapsed_s":time.monotonic()-begin,**snapshot(rpc)}
                rows.append(entry);out.write(json.dumps(entry)+"\n");out.flush()
                print(phase,i+1,"/",count,flush=True)
                time.sleep(args.interval)
        begin=time.monotonic()
        collect("pre",args.before)
        stroke=SwingTraceClient(rpc,port=0).run(samples)
        print("Swing dispatched; ball contact UNVERIFIED.",flush=True)
        collect("post",args.after)
    result=summary(rows,stroke)
    report.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
    print("Private raw:",raw,"Sanitized local summary:",report)
    if not args.no_upload:
        # Explicit allowlist. Never forward raw rows, RAM hex, pointers or local paths.
        public={key:result[key] for key in (
            "schema_version","study_id","utc","samples","phase_counts",
            "changed_byte_offsets","adjacent_changes","swing_dispatch_received",
            "claim","warning")}
        public["id"]=run+"-automated-minimap"
        public["kind"]="automated-minimap-effect"
        try:
            from research_cli import publish_summary
            url=publish_summary(public)
            print("Sanitized GitHub observation:",url,flush=True)
        except (OSError,RuntimeError,ValueError) as exc:
            print("GitHub publication failed; sanitized local summary retained:",exc,file=sys.stderr)
    return 0
if __name__=="__main__":
    try:raise SystemExit(main())
    except (OSError,ValueError,RuntimeError) as exc:
        print("Automated effect study failed:",exc,file=sys.stderr);raise SystemExit(1)
