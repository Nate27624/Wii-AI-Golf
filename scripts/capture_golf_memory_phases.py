"""Read-only, phase-labeled golf memory recorder for ALREADY RUNNING Dolphin.

This tool never launches Dolphin, loads a savestate, sends Wii Remote inputs,
or writes game memory. Raw snapshots stay under the private sibling Data tree.
Only a bounded, allowlisted differential summary is published to GitHub.
"""
from __future__ import annotations
import argparse,json,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.audit.outcome_transition import _ram,_u32,_bytes,STATIC_STRUCTS
from wii_ai_golf.audit.memory_phases import (
    ALLOWED_PHASES,ALLOWED_OBSERVATIONS,WINDOW_LENGTHS,
    summarize_phase_memory
)

CAPTURES=ROOT.parent/"Wii-AI-Golf-Data"/"captures"
DEFAULT_PHASES=("idle:6","aim_only:6")
EFFECT_OFFSETS={
    "minimap_ball_effect":0x9C,
    "minimap_player_effect":0x94,
    "minimap_shot_line_effect":0x98
}
CUES={
    "idle":"Hands off controls; keep scene and camera still.",
    "aim_only":"Move the camera/aim ONLY. Do not swing.",
    "a_hold":"Hold A without performing a swing; if control is unavailable, abort.",
    "club_motion":"Move the club without intentionally hitting the ball.",
    "shot_attempt":"Perform at most ONE intentional shot; record if it actually hits.",
    "settled":"Hands off after ball or club motion has ended."
}

def parse_phases(tokens):
    stages=[]
    if not 1<=len(tokens)<=6:raise ValueError("choose 1..6 phase stages")
    total=0
    for token in tokens:
        phase,sep,num=token.partition(":")
        if not sep or phase not in ALLOWED_PHASES or not num.isdigit():
            raise ValueError(f"invalid phase specification: {token}")
        n=int(num)
        if not 2<=n<=40:raise ValueError("samples per stage must be 2..40")
        stages.append((phase,n));total+=n
    if total>240:raise ValueError("at most 240 samples per capture")
    return stages

def snapshot(rpc,scope,phase,stage):
    start=rpc.call("frame.get_count",[])
    if type(start) is not int or start<0:raise RuntimeError("invalid emulator frame counter")
    header=_bytes(rpc,0x80000000,8)
    if header[:6]!=b"RSPE01" or header[7]!=1:
        raise RuntimeError("Game must be Wii Sports USA revision 1 (RSPE01)")
    ptrs={}
    for name,(address,required_size) in STATIC_STRUCTS.items():
        ptrs[name]=_u32(rpc,address)
        if not _ram(ptrs[name],required_size):
            raise RuntimeError("Invalid "+name+" instance; expected active golf scene")
    config,field=ptrs["golf_config"],ptrs["golf_field"]
    mode=_u32(rpc,config+0x94)
    if mode!=4:raise RuntimeError("Not in Hitting the Green (golf mode 4)")
    regions={name:(ptr,WINDOW_LENGTHS[scope][name])
             for name,ptr in ptrs.items()}
    if scope=="broad":
        for name,offset in EFFECT_OFFSETS.items():
            ptr=_u32(rpc,field+offset)
            if _ram(ptr,0x200):regions[name]=(ptr,0x200)
    windows={}
    for name,(ptr,size) in regions.items():
        windows[name]={"address":f"0x{ptr:08X}","bytes_hex":_bytes(rpc,ptr,size).hex()}
    end=rpc.call("frame.get_count",[])
    if type(end) is not int or end<start:
        raise RuntimeError("invalid ending emulator frame")
    return {"schema_version":1,"phase":phase,"stage":stage,
            "game_id":"RSPE01","disc_revision":1,"game_mode_raw":mode,
            "frame_start":start,"frame_end":end,
            "utc":datetime.now(timezone.utc).isoformat(),
            "windows":windows,
            "warning":"Private non-atomic Wii memory sample; no identified club or power fields"}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--attach-running",action="store_true",help="Explicit permission for read-only local RPC; does not boot emulator")
    p.add_argument("--port",type=int,default=55355)
    p.add_argument("--scope",choices=tuple(WINDOW_LENGTHS),default="focused")
    p.add_argument("--phase",action="append",default=None,
                   help="Repeat phase:sample_count, e.g. --phase idle:6 --phase aim_only:6")
    p.add_argument("--interval",type=float,default=0.10,
                   help="Minimum wall-clock pause between non-atomic snapshots (0.05..2 seconds)")
    p.add_argument("--max-frame-span",type=int,default=180,
                   help="Abort/report partial raw if a snapshot spans >N emulator frames")
    p.add_argument("--no-upload",action="store_true")
    a=p.parse_args(argv)
    if not a.attach_running:p.error("Requires --attach-running. Only use with existing Dolphin game/bridge.")
    if not 1<=a.port<=65535 or not .05<=a.interval<=2.0 or not 1<=a.max_frame_span<=1000:
        p.error("invalid port/interval/frame-span")
    try:stages=parse_phases(a.phase or DEFAULT_PHASES)
    except ValueError as e:p.error(str(e))
    CAPTURES.mkdir(parents=True,exist_ok=True)
    run=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")+uuid.uuid4().hex[:8]
    path=CAPTURES/("golf-memory-phases-"+run+"-RAW-PRIVATE.jsonl")
    report_path=CAPTURES/("golf-memory-phases-"+run+"-summary.json")
    print("Read-only recorder; NO automated button or swing commands.",flush=True)
    print("Ensure Hitting the Green is ready and Dolphin's Felk RPC is active.",flush=True)
    print("Private raw capture:",path,flush=True)
    rows=[];observations=[];last_frame=None
    with FelkRPC(port=a.port,timeout_s=15) as rpc:
        with path.open("x",encoding="utf-8") as raw:
            for stage,(phase,n) in enumerate(stages):
                print(f"Phase {stage+1}/{len(stages)}: {phase} — {CUES[phase]}",flush=True)
                answer=input("When ready, press ENTER to record; type q to cancel: ").strip().lower()
                if answer!="":raise RuntimeError("Capture canceled; any raw rows remain private")
                for i in range(n):
                    tick=time.monotonic()
                    row=snapshot(rpc,a.scope,phase,stage)
                    span=row["frame_end"]-row["frame_start"]
                    if span>a.max_frame_span:
                        raise RuntimeError(f"Non-atomic read spanned {span} frames; inspect partial private capture")
                    if last_frame is not None and row["frame_start"]<last_frame:
                        raise RuntimeError("Emulation frame counter moved backwards; experiment invalid")
                    last_frame=row["frame_end"]
                    rows.append(row)
                    raw.write(json.dumps(row,separators=(",",":"))+"\n");raw.flush()
                    print(f"{phase}: {i+1}/{n}, frames {row['frame_start']}..{row['frame_end']}",flush=True)
                    time.sleep(max(0,a.interval-(time.monotonic()-tick)))
                while True:
                    label=input("Observed [unchanged/camera_moved/club_moved/ball_hit/no_contact/unknown]: ").strip().lower()
                    if label in ALLOWED_OBSERVATIONS:break
                    print("Please enter one of the listed observation labels.")
                observations.append({"stage":stage,"phase":phase,"observation":label})
    result=summarize_phase_memory(rows,observations,scope=a.scope,run_id=run)
    report_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("Sanitized summary:",report_path,flush=True)
    print(json.dumps({"run_id":run,"scope":a.scope,"samples":len(rows),
                      "changed_word_count":result["changed_word_count"],
                      "max_frame_span":result["max_non_atomic_frame_span"]},indent=2))
    if not a.no_upload:
        try:
            from research_cli import publish_summary
            print("Published GitHub observation:",publish_summary(result),flush=True)
            print("Observation record ID:",run,flush=True)
        except (OSError,RuntimeError,ValueError) as exc:
            print("Could not publish; sanitized summary safely retained locally:",exc,file=sys.stderr)
    return 0

if __name__=="__main__":
    try:raise SystemExit(main())
    except (OSError,ValueError,RuntimeError,EOFError,KeyboardInterrupt) as exc:
        print("Read-only phase capture stopped:",exc,file=sys.stderr)
        raise SystemExit(1)
