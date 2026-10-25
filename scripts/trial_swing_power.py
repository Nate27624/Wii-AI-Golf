"""One-variable swing-power system-identification trial, post canonical intro.

Usage: py scripts/run_golf_experiment.py --send-live --script trial_swing_power.py -- --live --variant baseline
Only one explicit shot; human observes contact and the displayed power.
"""
from __future__ import annotations
import argparse,hashlib,json,math,sys
from dataclasses import replace
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]
from probe_swing import build_probe
from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.integration.swing_client import SwingTraceClient

VARIANTS={"baseline":("none",1.0),"shorter":("distance",0.75),
          "slower":("speed",0.75),"faster":("speed",1.15),
          "longer-backswing":("backswing",1.25)}
CAPTURES=ROOT.parent/"Wii-AI-Golf-Data"/"captures"

def waveform(variant):
    if variant not in VARIANTS:raise ValueError("Unknown registered variant")
    param,scale=VARIANTS[variant]
    base=build_probe("forward",follow_through_frames=30)
    # A-only setup, forward duration, follow-through and release are unchanged.
    output=[]
    for i,s in enumerate(base):
        if param=="distance" and 27<=i<47:
            s=replace(s,distance_m=s.distance_m*scale)
        elif param=="speed" and 27<=i<47:
            s=replace(s,speed_m_s=s.speed_m_s*scale)
        elif param=="backswing" and 12<=i<27:
            s=replace(s,distance_m=s.distance_m*scale)
        output.append(s)
    return output

def public_record(variant,trace,dispatch,contact,power,start_pose="unknown"):
    payload=[[s.hold_a,*s.direction,s.distance_m,s.speed_m_s,s.return_speed_m_s,s.angle_rad] for s in trace]
    return {"schema_version":1,"kind":"swing-power-calibration","study_id":"S002-POWER-INPUT-OUTPUT",
            "id":datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")+"-"+variant,
            "utc":datetime.now(timezone.utc).isoformat(),"variant":variant,
            "changed_parameter":VARIANTS[variant][0],"parameter_multiplier":VARIANTS[variant][1],
            "trace_sha256":hashlib.sha256(json.dumps(payload,separators=(",",":")).encode()).hexdigest(),
            "trace_frames":len(trace),"dispatch_acknowledged":isinstance(dispatch,dict),
            "contact_human":contact,"power_percent_human":power,
            "initial_club_pose_human":start_pose,
            "initial_club_pose_verified_by_memory":False,
            "power_verified_by_memory":False,"contact_verified_by_memory":False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--variant",choices=tuple(VARIANTS),required=True)
    p.add_argument("--live",action="store_true",help="Opt in to one controller swing")
    p.add_argument("--port",type=int,default=55355)
    p.add_argument("--no-upload",action="store_true")
    a=p.parse_args()
    trace=waveform(a.variant)
    print("VARIANT",a.variant,"changed parameter",VARIANTS[a.variant],
          "frames",len(trace),flush=True)
    if not a.live:
        print("Dry run: no controller inputs sent");return 0
    with FelkRPC(port=a.port,timeout_s=15) as rpc:
        while True:
            start_pose=input("Starting club position [back/center/forward/unknown]: ").strip().lower()
            if start_pose in ("back","center","forward","unknown"):break
        input("Check ready-to-swing tee, then press ENTER (Ctrl+C cancels): ")
        dispatched=SwingTraceClient(rpc,port=0).run(trace)
    print("Controller trace dispatched; observe game to decide hit and power.")
    while True:
        contact=input("Visible ball contact? [yes/no/unknown]: ").strip().lower()
        if contact in ("yes","no","unknown"):break
    while True:
        value=input("Displayed swing power percent [0..100, blank if unavailable]: ").strip()
        if not value:power=None;break
        try:
            power=float(value.rstrip("%"))
            if math.isfinite(power) and 0<=power<=100:break
        except ValueError:pass
        print("Enter a percent between 0 and 100, or leave blank.")
    record=public_record(a.variant,trace,dispatched,contact,power,start_pose)
    CAPTURES.mkdir(parents=True,exist_ok=True)
    path=CAPTURES/(record["id"]+"-power-summary.json")
    path.write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    print("Saved summary:",path)
    if not a.no_upload:
        try:
            from research_cli import publish_summary
            print("GitHub:",publish_summary(record),flush=True)
        except (OSError,RuntimeError,ValueError) as e:
            print("GitHub upload unsuccessful, summary retained:",e,file=sys.stderr)
    return 0
if __name__=="__main__":
    try:raise SystemExit(main())
    except (OSError,RuntimeError,ValueError,KeyboardInterrupt) as e:
        print("Trial aborted:",e,file=sys.stderr);raise SystemExit(1)
