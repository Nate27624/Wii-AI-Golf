"""Capture candidate RPGolMain RAM in Wii Sports USA Rev1, read-only.

Use ONLY after canonical tee startup:
 py scripts/run_golf_experiment.py --send-live --script capture_golfer_memory.py -- --read-only

Find a possible live SceneManager via bounded static-global pointer census,
validate scene ID / sport / pointer chain, then sample its candidate RPGolMain
instance during idle and aim-only stages. NOT a verified club/power decoder.
Raw RAM and absolute runtime pointers remain private. No controllers are sent.
"""
from __future__ import annotations
import argparse, json, math, struct, sys, time, uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.audit.outcome_transition import _ram,_bytes,_u32

# Source-backed neighborhood of existing US Rev1 sports singleton globals.
# This is a bounded search HYPOTHESIS, not the proven SceneMgr slot.
GLOBALS_BASE=0x804BF000
GLOBALS_SIZE=0x1000
CONFIG_STORAGE=0x804BF8C4
SCENE_ID=5
SPORT_ID=2
MAIN_BYTES=0x100
MAX_GLOBAL_POINTERS=512
CAPTURE_DIR=ROOT.parent/"Wii-AI-Golf-Data"/"captures"
STAGE_NAMES={"idle","aim_only"}
SOURCE_NOTE="EGG::SceneManager +0xC scene, +0x18 scene ID; RPSportsBaseScene +0x54 sport; RPGolScene +0x9C RPGolMain"

def _words(data):
    return struct.unpack(">"+str(len(data)//4)+"I",data)

def gate(rpc):
    disc=_bytes(rpc,0x80000000,8)
    if disc[:6]!=b"RSPE01" or disc[7]!=1:
        raise RuntimeError("Wii Sports USA RSPE01 revision 1 required")
    config=_u32(rpc,CONFIG_STORAGE)
    if not _ram(config,0xA0) or _u32(rpc,config+0x94)!=4:
        raise RuntimeError("Hitting the Green golf mode 4 required")

def find_golfer(rpc):
    """Return local candidate object pointers; do not confuse shape with proof."""
    gate(rpc)
    raw=_bytes(rpc,GLOBALS_BASE,GLOBALS_SIZE)
    slots=defaultdict(list)
    for i,value in enumerate(_words(raw)):
        if _ram(value,0x20):
            slots[value].append(i*4)
    if len(slots)>MAX_GLOBAL_POINTERS:
        raise RuntimeError("Too many global pointer candidates for bounded audit")
    checks={"static_pointer_candidates":len(slots),
            "golf_scene_id_candidates":0,
            "validated_sport_scene_candidates":0}
    matches=[]
    for manager,locations in slots.items():
        hdr=_bytes(rpc,manager,0x20)
        if struct.unpack_from(">I",hdr,0x18)[0]!=SCENE_ID:
            continue
        checks["golf_scene_id_candidates"]+=1
        scene=struct.unpack_from(">I",hdr,0x0C)[0]
        if not _ram(scene,0xA0):
            continue
        scene_data=_bytes(rpc,scene,0xA0)
        if struct.unpack_from(">I",scene_data,0x54)[0]!=SPORT_ID:
            continue
        checks["validated_sport_scene_candidates"]+=1
        gameplay=struct.unpack_from(">I",scene_data,0x9C)[0]
        if not _ram(gameplay,MAIN_BYTES):
            continue
        matches.append({"manager":manager,"scene":scene,
                        "gameplay":gameplay,"slot_offsets":locations,
                        "creator_scene_id":struct.unpack_from(">I",scene_data,0x40)[0]})
    return matches,checks

def read_instance(rpc,match):
    """Check chain identity again before every candidate gameplay read."""
    manager,scene,gameplay=(match[k] for k in ("manager","scene","gameplay"))
    if _u32(rpc,manager+0x18)!=SCENE_ID or _u32(rpc,manager+0x0C)!=scene:
        raise RuntimeError("Active scene manager identity changed; stop capture")
    if _u32(rpc,scene+0x54)!=SPORT_ID or _u32(rpc,scene+0x9C)!=gameplay:
        raise RuntimeError("Golfer pointer changed or golf scene replaced; stop capture")
    frame_start=rpc.call("frame.get_count",[])
    if type(frame_start) is not int or frame_start<0:
        raise RuntimeError("Invalid frame count")
    raw=_bytes(rpc,gameplay,MAIN_BYTES)
    frame_end=rpc.call("frame.get_count",[])
    if type(frame_end) is not int or frame_end<frame_start:
        raise RuntimeError("Frame count reversed")
    return {"frame_start":frame_start,"frame_end":frame_end,
            "bytes_hex":raw.hex()}

def summarize(rows,phase_labels,checks,match,run_id):
    stats=defaultdict(lambda:{"within_stage_changes":0,"between_stage_changes":0,
                               "plausible_float_changes":0})
    prior=None
    for row in rows:
        data=bytes.fromhex(row["bytes_hex"])
        if len(data)!=MAIN_BYTES:raise ValueError("Invalid golfer window bytes")
        words=_words(data)
        if prior:
            stage,old=prior
            for idx,(a,b) in enumerate(zip(old,words)):
                if a==b:continue
                entry=stats[idx*4]
                key="within_stage_changes" if row["stage"]==stage else "between_stage_changes"
                entry[key]+=1
                try:
                    va,vb=struct.unpack(">f",struct.pack(">I",a))[0],struct.unpack(">f",struct.pack(">I",b))[0]
                    entry["plausible_float_changes"]+=int(
                        all(math.isfinite(x) and 1e-6<abs(x)<10000 for x in (va,vb)))
                except (OverflowError,struct.error):
                    pass
        prior=(row["stage"],words)
    changed=[{"offset":f"+0x{off:03X}",**values} for off,values in stats.items()]
    changed.sort(key=lambda x:(-x["within_stage_changes"],-x["between_stage_changes"],x["offset"]))
    return {
        "schema_version":1,"kind":"local-golfer-memory-audit","id":run_id,
        "candidate_only":True,"source_claim":SOURCE_NOTE,
        "game_id":"RSPE01","revision":1,"game_mode":4,
        "source_global_search_range":"804BF000+1000",
        "global_pointer_candidates":checks["static_pointer_candidates"],
        "matched_scene_chains":1,
        "manager_slot_relative_offsets":[f"+0x{x:03X}" for x in match["slot_offsets"]],
        "observed_creator_scene_id_matches_golf":match["creator_scene_id"]==SCENE_ID,
        "phase_sample_counts":phase_labels,
        "samples":len(rows),"max_non_atomic_frame_span":max(
            row["frame_end"]-row["frame_start"] for row in rows),
        "changed_candidate_words":len(changed),
        "top_relative_changes":changed[:64],
        "power_verified":False,"club_rotation_verified":False,
        "warning":"Read-only RPGolMain* structural candidate, not verified club or power semantics; actual bytes and addresses are PRIVATE."
    }

def capture(rpc,stages,interval,frame_limit,private):
    matches,checks=find_golfer(rpc)
    print("Pointer-census result:",json.dumps({
        **checks,"matching_golf_main_chains":len(matches)},indent=2),flush=True)
    if len(matches)!=1:
        return {"diagnostic":"no_unique_golfer_pointer_chain",
                "candidate_chains":len(matches),**checks,
                "note":"No gameplay bytes dereferenced unless exactly one source-gated pointer chain matches."}
    match=matches[0]
    count={};rows=[]
    with private.open("x",encoding="utf-8") as stream:
        for stage,(name,n) in enumerate(stages):
            print(f"Phase {stage+1}: {name}, {n} samples.",flush=True)
            if name=="idle":print("Keep club, camera and controls STILL.",flush=True)
            else:print("When capturing, move WASD aim/camera only. NO swing.",flush=True)
            if input("Press ENTER to begin this phase, q to cancel: ").strip().lower():
                raise RuntimeError("Operator canceled; partial private data retained")
            count[name]=count.get(name,0)+n
            for i in range(n):
                t0=time.monotonic()
                row=read_instance(rpc,match)
                if row["frame_end"]-row["frame_start"]>frame_limit:
                    raise RuntimeError("Non-atomic capture too long; partial private evidence retained")
                row["stage"]=stage;row["phase"]=name
                private_row={**row,"runtime_scene_address":f"0x{match['scene']:08X}",
                             "runtime_golf_main_address":f"0x{match['gameplay']:08X}"}
                stream.write(json.dumps(private_row,separators=(",",":"))+"\n")
                stream.flush()
                rows.append(row)
                time.sleep(max(0,interval-(time.monotonic()-t0)))
                print(f"{name}: {i+1}/{n} game frames {row['frame_start']}..{row['frame_end']}",flush=True)
    return summarize(rows,count,checks,match,private.stem)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--read-only",action="store_true",help="Explicitly opt in to read-only live RAM sampling")
    p.add_argument("--port",type=int,default=55355)
    p.add_argument("--phase",action="append",help="idle:6 or aim_only:8, repeated; default idle:6,aim_only:8")
    p.add_argument("--interval",type=float,default=.18)
    p.add_argument("--max-frame-span",type=int,default=80)
    a=p.parse_args(argv)
    if not a.read_only:p.error("Must pass --read-only. This program never controls Dolphin.")
    if not 1<=a.port<=65535 or not .05<=a.interval<=2.0 or not 1<=a.max_frame_span<=240:
        p.error("Invalid port, interval or frame budget")
    stages=[]
    for stage in a.phase or ["idle:6","aim_only:8","idle:6"]:
        label,sep,n=stage.partition(":")
        if not sep or label not in STAGE_NAMES or not n.isdigit() or not 2<=int(n)<=24:
            p.error("Phase must be idle:N or aim_only:N, with N 2..24")
        stages.append((label,int(n)))
    if len(stages)>4 or sum(n for _,n in stages)>60:
        p.error("At most 4 stages and 60 snapshots")
    CAPTURE_DIR.mkdir(parents=True,exist_ok=True)
    id=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")+uuid.uuid4().hex[:8]
    private=CAPTURE_DIR/("golfer-"+id+"-RAW-PRIVATE.jsonl")
    summary_file=CAPTURE_DIR/("golfer-"+id+"-summary.json")
    print("READ ONLY. Captures candidate golfer object; zero controller writes.",flush=True)
    print("Dolphin must already be on ready-to-swing Hitting the Green tee.",flush=True)
    try:
        with FelkRPC(port=a.port,timeout_s=15) as rpc:
            result=capture(rpc,stages,a.interval,a.max_frame_span,private)
        with summary_file.open("x",encoding="utf-8") as fp:
            json.dump(result,fp,indent=2,sort_keys=True,allow_nan=False)
            fp.write("\n")
        print("Local sanitized report:",summary_file,flush=True)
        print(json.dumps(result,indent=2),flush=True)
        print("No RAM uploaded. Paste the printed summary for research.",flush=True)
        return 0
    except (OSError,ValueError,RuntimeError,EOFError,KeyboardInterrupt) as exc:
        print("Scene/golfer read-only capture stopped:",exc,file=sys.stderr)
        return 1

if __name__=="__main__":raise SystemExit(main())
