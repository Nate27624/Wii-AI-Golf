"""Capture candidate RPGolMain RAM in Wii Sports USA Rev1, read-only.

Use ONLY after canonical tee startup:
 py scripts/run_golf_experiment.py --send-live --script capture_golfer_memory.py -- --read-only

Find a possible live SceneManager via source-constrained two-cell static pointer census,
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

# RSPE01 Rev1 scene manager .sbss from doldecomp/ogws splits.txt:
# [0x804BF4D8,0x804BF4E0) contains TWO u32 cells, one may be spInstance.
# Source range constrains search; which cell stores the singleton remains to validate.
GLOBALS_BASE=0x804BF4D8
GLOBALS_SIZE=0x8
CONFIG_STORAGE=0x804BF8C4
SCENE_ID=5
SPORT_ID=2
MAIN_BYTES=0x100
MAX_GLOBAL_POINTERS=2
CHILD_BYTES=0x80
MAX_CHILD_POINTERS=16
CAPTURE_DIR=ROOT.parent/"Wii-AI-Golf-Data"/"captures"
STAGE_NAMES={"idle","aim_only"}
SOURCE_NOTE="RPSysSceneMgr .sbss 0x804BF4D8..0x804BF4DF; EGG::SceneManager +0xC/+0x18; EGG::Scene +0x1C/+0x20; RPSportsBaseScene +0x54; RPGolScene +0x9C"

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
    """Return source-constrained candidates, not a verified gameplay decoder."""
    start=rpc.call("frame.get_count",[])
    gate(rpc)
    raw=_bytes(rpc,GLOBALS_BASE,GLOBALS_SIZE)
    slots=defaultdict(list)
    for i,value in enumerate(_words(raw)):
        if _ram(value,0x20):
            slots[value].append(0x4D8+i*4)
    if len(slots)>MAX_GLOBAL_POINTERS:
        raise RuntimeError("Out-of-contract scene singleton storage")
    checks={"static_pointer_candidates":len(slots),
            "golf_scene_id_candidates":0,
            "validated_sport_scene_candidates":0,
            "validated_scene_identity_candidates":0,
            "source_static_slot_count":2}
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
        # EGG::Scene.mSceneID (NOT mCreatorSceneID) and mSceneMgr backlink.
        # Creator scene at +0x40 legitimately identifies a PARENT/previous scene.
        if (struct.unpack_from(">I",scene_data,0x1C)[0]!=SCENE_ID
            or struct.unpack_from(">I",scene_data,0x20)[0]!=manager):
            continue
        checks["validated_scene_identity_candidates"]+=1
        gameplay=struct.unpack_from(">I",scene_data,0x9C)[0]
        if not _ram(gameplay,MAIN_BYTES):
            continue
        matches.append({"manager":manager,"scene":scene,
                        "gameplay":gameplay,"slot_offsets":locations,
                        "creator_scene_id":struct.unpack_from(">I",scene_data,0x40)[0]})
    end=rpc.call("frame.get_count",[])
    if type(start) is not int or type(end) is not int or start<0 or end<start:
        raise RuntimeError("Invalid census frame counters")
    checks["census_frame_span"]=end-start
    return matches,checks

def child_watchlist(rpc,match,*,start_index=0,limit=MAX_CHILD_POINTERS):
    """Select stable, valid, distinct first-level pointer targets from gameplay."""
    gate(rpc)
    data=_bytes(rpc,match["gameplay"],MAIN_BYTES)
    exclude={match["manager"],match["scene"],match["gameplay"]}
    found=[]
    for i,ptr in enumerate(_words(data)):
        if ptr in exclude or not _ram(ptr,CHILD_BYTES):
            continue
        if any(existing["pointer"]==ptr for existing in found):
            continue
        found.append({"parent_offset":i*4,"pointer":ptr})
    if type(start_index) is not int or start_index<0 or type(limit) is not int or not 1<=limit<=MAX_CHILD_POINTERS:
        raise ValueError("Invalid child selection")
    if start_index>=len(found):
        raise ValueError("Requested child batch starts beyond candidate pointer inventory")
    selected=found[start_index:start_index+limit]
    overflow=(start_index+len(selected))<len(found)
    return selected,overflow

def read_instance(rpc,match,watchlist=()):
    """Recheck disc, game mode and chain before every candidate gameplay read."""
    gate(rpc)
    manager,scene,gameplay=(match[k] for k in ("manager","scene","gameplay"))
    if (_u32(rpc,manager+0x18)!=SCENE_ID or _u32(rpc,manager+0x0C)!=scene
        or _u32(rpc,scene+0x1C)!=SCENE_ID or _u32(rpc,scene+0x20)!=manager):
        raise RuntimeError("Active scene identity changed; stop capture")
    if _u32(rpc,scene+0x54)!=SPORT_ID or _u32(rpc,scene+0x9C)!=gameplay:
        raise RuntimeError("Golfer pointer changed or golf scene replaced; stop capture")
    frame_start=rpc.call("frame.get_count",[])
    if type(frame_start) is not int or frame_start<0:
        raise RuntimeError("Invalid frame count")
    raw=_bytes(rpc,gameplay,MAIN_BYTES)
    child_windows={}
    for item in watchlist:
        offset,ptr=item["parent_offset"],item["pointer"]
        if struct.unpack_from(">I",raw,offset)[0]!=ptr:
            raise RuntimeError("Gameplay child pointer changed; stop capture")
        child_windows[f"+0x{offset:03X}"]=_bytes(rpc,ptr,CHILD_BYTES).hex()
    frame_end=rpc.call("frame.get_count",[])
    if type(frame_end) is not int or frame_end<frame_start:
        raise RuntimeError("Frame count reversed")
    return {"frame_start":frame_start,"frame_end":frame_end,
            "bytes_hex":raw.hex(),"child_windows":child_windows}

def summarize(rows,phase_labels,checks,match,run_id,child_count=0,child_overflow=False):
    stats=defaultdict(lambda:{"within_stage_changes":0,"between_stage_changes":0,
                               "plausible_float_changes":0})
    prior=None
    for row in rows:
        current={"main":bytes.fromhex(row["bytes_hex"])}
        if len(current["main"])!=MAIN_BYTES:raise ValueError("Invalid golfer window bytes")
        for parent_offset,raw in row.get("child_windows",{}).items():
            key="child_at_main"+parent_offset
            data=bytes.fromhex(raw)
            if len(data)!=CHILD_BYTES:raise ValueError("Invalid child window")
            current[key]=data
        if prior:
            stage,old=prior
            for region,data in current.items():
                if region not in old:continue
                for idx,(a,b) in enumerate(zip(_words(old[region]),_words(data))):
                    if a==b:continue
                    entry=stats[(region,idx*4)]
                    key="within_stage_changes" if row["stage"]==stage else "between_stage_changes"
                    entry[key]+=1
                    try:
                        va=struct.unpack(">f",struct.pack(">I",a))[0]
                        vb=struct.unpack(">f",struct.pack(">I",b))[0]
                        entry["plausible_float_changes"]+=int(
                            all(math.isfinite(x) and 1e-6<abs(x)<10000 for x in (va,vb)))
                    except (OverflowError,struct.error):
                        pass
        prior=(row["stage"],current)
    changed=[{"region":region,"offset":f"+0x{off:03X}",**values}
             for (region,off),values in stats.items()]
    changed.sort(key=lambda x:(-x["within_stage_changes"],
                                -x["between_stage_changes"],x["region"],x["offset"]))
    return {
        "schema_version":2,"kind":"local-golfer-memory-audit","id":run_id,
        "candidate_only":True,"source_claim":SOURCE_NOTE,
        "game_id":"RSPE01","revision":1,"game_mode":4,
        "source_global_search_range":"804BF4D8+8",
        "global_pointer_candidates":checks["static_pointer_candidates"],
        "source_static_slot_count":checks["source_static_slot_count"],
        "census_frame_span":checks["census_frame_span"],
        "matched_scene_chains":1,
        "manager_slot_relative_offsets":[f"+0x{x:03X}" for x in match["slot_offsets"]],
        "creator_scene_id_role":"previous_scene_not_current_scene_id",
        "creator_scene_id_not_used_for_identity":True,
        "actual_scene_id_verified":True,"manager_backlink_verified":True,
        "phase_sample_counts":phase_labels,
        "samples":len(rows),"max_non_atomic_frame_span":max(
            row["frame_end"]-row["frame_start"] for row in rows),
        "first_level_child_watch_count":child_count,
        "first_level_child_watch_truncated":child_overflow,
        "changed_candidate_words":len(changed),
        "top_relative_changes":changed[:100],
        "power_verified":False,"club_rotation_verified":False,
        "warning":"Read-only candidate object graph, not identified club or power; bytes and runtime pointers remain PRIVATE."
    }

def capture(rpc,stages,interval,frame_limit,private,*,child_start=0,child_limit=MAX_CHILD_POINTERS):
    matches,checks=find_golfer(rpc)
    print("Pointer-census result:",json.dumps({
        **checks,"matching_golf_main_chains":len(matches)},indent=2),flush=True)
    if len(matches)!=1:
        return {"diagnostic":"no_unique_golfer_pointer_chain",
                "candidate_chains":len(matches),**checks,
                "note":"No gameplay bytes dereferenced unless exactly one source-gated pointer chain matches."}
    match=matches[0]
    watchlist,overflow=child_watchlist(rpc,match,start_index=child_start,limit=child_limit)
    print("Selected first-level objects:",len(watchlist),
          "batch starts at:",child_start,"more pointers after batch:",overflow,flush=True)
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
                row=read_instance(rpc,match,watchlist)
                if row["frame_end"]-row["frame_start"]>frame_limit:
                    raise RuntimeError("Non-atomic capture too long; partial private evidence retained")
                row["stage"]=stage;row["phase"]=name
                private_row={**row,"watched_child_addresses":{
                    f"+0x{x['parent_offset']:03X}":f"0x{x['pointer']:08X}"
                    for x in watchlist},"runtime_scene_address":f"0x{match['scene']:08X}",
                             "runtime_golf_main_address":f"0x{match['gameplay']:08X}"}
                stream.write(json.dumps(private_row,separators=(",",":"))+"\n")
                stream.flush()
                rows.append(row)
                time.sleep(max(0,interval-(time.monotonic()-t0)))
                print(f"{name}: {i+1}/{n} game frames {row['frame_start']}..{row['frame_end']}",flush=True)
    report=summarize(rows,count,checks,match,private.stem,len(watchlist),overflow)
    report["first_level_child_batch_start"]=child_start
    report["first_level_child_parent_offsets"]=[
        f"+0x{item['parent_offset']:03X}" for item in watchlist]
    return report

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--read-only",action="store_true",help="Explicitly opt in to read-only live RAM sampling")
    p.add_argument("--port",type=int,default=55355)
    p.add_argument("--phase",action="append",help="idle:6 or aim_only:8, repeated; default idle:6,aim_only:8")
    p.add_argument("--interval",type=float,default=.18)
    p.add_argument("--child-start",type=int,default=0,
                   help="Zero-based child-pointer candidate index for next batch")
    p.add_argument("--child-limit",type=int,default=MAX_CHILD_POINTERS,
                   help="Number of candidate child objects in this batch (1..16)")
    p.add_argument("--max-frame-span",type=int,default=80)
    a=p.parse_args(argv)
    if not a.read_only:p.error("Must pass --read-only. This program never controls Dolphin.")
    if (not 1<=a.port<=65535 or not .05<=a.interval<=2.0
        or not 1<=a.max_frame_span<=240 or not 0<=a.child_start<=63
        or not 1<=a.child_limit<=MAX_CHILD_POINTERS):
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
            result=capture(rpc,stages,a.interval,a.max_frame_span,private,
                           child_start=a.child_start,child_limit=a.child_limit)
        with summary_file.open("x",encoding="utf-8") as fp:
            json.dump(result,fp,indent=2,sort_keys=True,allow_nan=False)
            fp.write("\n")
        print("Private captured game memory:",private if private.exists() else "No gameplay bytes recorded",flush=True)
        print("Local sanitized report:",summary_file,flush=True)
        print(json.dumps(result,indent=2),flush=True)
        print("No RAM uploaded. Paste the printed summary for research.",flush=True)
        return 0
    except (OSError,ValueError,RuntimeError,EOFError,KeyboardInterrupt) as exc:
        print("Scene/golfer read-only capture stopped:",exc,file=sys.stderr)
        return 1

if __name__=="__main__":raise SystemExit(main())
