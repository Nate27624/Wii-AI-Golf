"""S002 US Rev1 source-gated READ-ONLY scene-manager / golfer pointer census.

Research hypothesis, NOT a confirmed global or game-power decoder:
- EGG::SceneManager.mCurrentScene +0x0C
- RPSysScene.mCreatorSceneId +0x40 (golf scene ID 5)
- RPSportsBaseScene.mSport +0x54 (golf sport ID 2)
- RPGolScene.mGolMain +0x9C

Search only one 4-KiB candidate global-pointer page near other documented
sports singleton pointers. An empty search DOES NOT disprove the chain.
No savestate, controller input, RAM writes, or full-memory scanning.
"""
from __future__ import annotations
import argparse,json,struct,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.audit.outcome_transition import _ram,_u32,_bytes

PAGE_START=0x804BF000
PAGE_SIZE=0x1000
MAX_UNIQUE_POINTERS=768
SCENE_ID_GOLF=5
SPORT_ID_GOLF=2
OUTPUT=ROOT.parent/"Wii-AI-Golf-Data"/"captures"

def _word(raw,offset):
    return struct.unpack_from(">I",raw,offset)[0]

def find_scene_chains(rpc):
    start=rpc.call("frame.get_count",[])
    if type(start) is not int or start<0:raise ValueError("invalid starting frame")
    header=_bytes(rpc,0x80000000,8)
    if header[:6]!=b"RSPE01" or header[7]!=1:
        raise RuntimeError("Wrong game ID/revision; requires RSPE01 rev 1")
    config=_u32(rpc,0x804BF8C4)
    if not _ram(config,0xA0) or _u32(rpc,config+0x94)!=4:
        raise RuntimeError("Hitting the Green mode 4 is not active")
    globals_raw=_bytes(rpc,PAGE_START,PAGE_SIZE)
    ptr_slots={}
    for off in range(0,PAGE_SIZE,4):
        ptr=_word(globals_raw,off)
        if _ram(ptr,0x20):
            ptr_slots.setdefault(ptr,[]).append(off)
    if len(ptr_slots)>MAX_UNIQUE_POINTERS:
        raise RuntimeError("Too many candidate pointers; bounded read aborted")
    manager_scene_candidates=0;validated=[]
    for possible_manager,offsets in ptr_slots.items():
        manager=_bytes(rpc,possible_manager,0x20)
        active_scene=_word(manager,0x0C)
        if not _ram(active_scene,0xA0):
            continue
        manager_scene_candidates+=1
        scene=_bytes(rpc,active_scene,0xA0)
        creator_id=_word(scene,0x40)
        sport_id=_word(scene,0x54)
        gameplay=_word(scene,0x9C)
        if creator_id!=SCENE_ID_GOLF or sport_id!=SPORT_ID_GOLF:
            continue
        if not _ram(gameplay,0x80):continue
        validated.append({
            "global_slot_offsets":[f"+0x{x:03X}" for x in offsets],
            "scene_id":creator_id,"sport_id":sport_id,
            "gameplay_pointer_plausible":True
        })
    end=rpc.call("frame.get_count",[])
    if type(end) is not int or end<start:raise ValueError("Frame counter reset")
    summary={
        "source":"source-constrained-relative-golf-scene-pointer-survey",
        "source_refs":[
            "EGG::SceneManager +0x0C",
            "RPSysScene +0x40",
            "RPSportsBaseScene +0x54",
            "RPGolScene +0x9C"
        ],
        "scan_region":"documented-singleton-neighborhood-4KiB",
        "scan_size_bytes":PAGE_SIZE,
        "pointer_candidates":len(ptr_slots),
        "pointer_to_scene_shape_candidates":manager_scene_candidates,
        "matching_scene_chains":len(validated),
        "candidate_global_slot_relative_offsets":sorted(set(
            offset for candidate in validated for offset in candidate["global_slot_offsets"])),
        "non_atomic_frame_span":end-start,
        "club_rotation_verified":False,
        "swing_power_verified":False,
        "physical_ball_state_verified":False,
        "warning":"Candidate pointer chain only. Runtime scene base, manager layout and RPGolMain identity require repeatable independent validation; zero candidates does NOT prove absence."
    }
    # Detailed addresses intentionally NOT included even in public report.
    return summary

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--attach-running",action="store_true")
    p.add_argument("--port",type=int,default=55355)
    p.add_argument("--no-upload",action="store_true")
    p.add_argument("--max-frame-span",type=int,default=300)
    a=p.parse_args(argv)
    if not a.attach_running:p.error("Explicit --attach-running is required; no emulator will be launched")
    if not 1<=a.port<=65535 or not 1<=a.max_frame_span<=1000:
        p.error("invalid RPC port or frame span")
    try:
        with FelkRPC(port=a.port,timeout_s=15) as rpc:
            result=find_scene_chains(rpc)
        if result["non_atomic_frame_span"]>a.max_frame_span:
            raise RuntimeError("Scan spans too many game frames; discarding as unstable")
        run="scene-chain-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")+uuid.uuid4().hex[:8]
        report={"schema_version":1,"kind":"golf-scene-chain-census",
                "study_id":"S002-GOLF-SCENE-CHAIN","id":run,**result}
        OUTPUT.mkdir(parents=True,exist_ok=True)
        path=OUTPUT/("golf-scene-chain-"+run+"-summary.json")
        with path.open("x",encoding="utf-8") as stream:
            json.dump(report,stream,indent=2,sort_keys=True,allow_nan=False)
            stream.write("\n")
        print("Sanitized local report:",path)
        print("Matching object chains:",report["matching_scene_chains"])
        if not a.no_upload:
            try:
                from research_cli import publish_summary
                publish_summary(report)
                print("GitHub JSON: https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/"+run+".json",flush=True)
            except (RuntimeError,OSError,ValueError) as exc:
                print("Could not upload; sanitized local report saved:",exc,file=sys.stderr)
        return 0
    except (RuntimeError,OSError,ValueError,KeyError,TypeError) as exc:
        print("Read-only golfer chain survey failed:",exc,file=sys.stderr)
        return 1

if __name__=="__main__":raise SystemExit(main())
