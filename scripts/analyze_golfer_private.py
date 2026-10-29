"""Offline characterization of PRIVATE golfer-object RAM already captured.

No Dolphin connection, no game input, no network or GitHub upload.
Outputs bounded region-relative offsets, phase-change counts, and counter
patterns. Never outputs raw 32-bit memory words or runtime pointers.
"""
from __future__ import annotations
import argparse,json,math,statistics,struct,sys,uuid
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from wii_ai_golf.audit.outcome_transition import _ram

MAX_FILE_BYTES=8_000_000
MAX_SAMPLES=240
MAX_CHILDREN=16
MAX_OUTPUT_WORDS=1024
_ALLOWED_PHASES={"idle","aim_only","a_hold","club_motion","settled"}

def words(data):
    return struct.unpack(">"+str(len(data)//4)+"I",data)

def load(path):
    if not path.is_file() or not 0<path.stat().st_size<=MAX_FILE_BYTES:
        raise ValueError("Missing or oversized PRIVATE golfer capture")
    result=[]
    with path.open(encoding="utf-8") as fp:
        for line in fp:
            if not line.strip():continue
            if len(result)>=MAX_SAMPLES:raise ValueError("Too many RAM snapshots")
            rec=json.loads(line)
            if not isinstance(rec,dict):
                raise ValueError("Invalid snapshot")
            for name in ("frame_start","frame_end","stage"):
                if type(rec.get(name)) is not int or rec[name]<0:
                    raise ValueError("Invalid frame or stage")
            if rec["frame_end"]<rec["frame_start"]:
                raise ValueError("Reversed frame bracket")
            if rec.get("phase") not in _ALLOWED_PHASES:
                raise ValueError("Unrecognized phase label")
            raw=bytes.fromhex(rec["bytes_hex"])
            if len(raw)!=0x100:raise ValueError("Wrong main window length")
            child=rec.get("child_windows",{})
            if not isinstance(child,dict) or len(child)>MAX_CHILDREN:
                raise ValueError("Invalid child inventory")
            windows={"main":raw}
            for parent_off,hex_bytes in child.items():
                if (not isinstance(parent_off,str) or not parent_off.startswith("+0x")
                    or not 0<=int(parent_off[3:],16)<0x100
                    or int(parent_off[3:],16)%4):
                    raise ValueError("Invalid child parent offset")
                data=bytes.fromhex(hex_bytes)
                if len(data)!=0x80:raise ValueError("Wrong child window length")
                windows["child_at_main"+parent_off]=data
            result.append((rec,windows))
    if len(result)<2:raise ValueError("Need at least two snapshots")
    return result

def classify(stats):
    idle_n=stats["idle_pair_count"]
    aim_n=stats["aim_pair_count"]
    idle=stats["idle_changes"]/idle_n if idle_n else 0
    aim=stats["aim_changes"]/aim_n if aim_n else 0
    if idle_n>=2 and aim_n>=2 and idle>=.75 and aim>=.75:
        return "continuous_during_idle_and_aim"
    if idle_n>=2 and aim_n>=2 and idle<=.1 and aim>=.6:
        return "aim_phase_correlated_candidate"
    if stats["changed_pairs"]==1:
        return "single_transition_only"
    return "unclassified_change"

def summarize(samples):
    phases=Counter()
    previous=None
    pointer_inventory=set()
    child_keys=None
    stats=defaultdict(lambda:{"idle_pair_count":0,"aim_pair_count":0,
                              "idle_changes":0,"aim_changes":0,"changed_pairs":0,
                              "within_stage_changes":0,"between_stage_changes":0,
                              "positive_steps":0,"negative_steps":0,
                              "zero_signed_steps":0,"plausible_float_pairs":0,
                              "_nonzero_steps":[],"_change_pattern":[]})
    minspan=1_000_000;maxspan=0;stage_boundary=0;total_pairs=0
    last_end=None
    main_address=None
    scene_address=None
    for rec,windows in samples:
        span=rec["frame_end"]-rec["frame_start"]
        minspan=min(minspan,span);maxspan=max(maxspan,span)
        if last_end is not None and rec["frame_start"]<last_end:
            raise ValueError("Non-monotonic frame counter across snapshots")
        last_end=rec["frame_end"]
        phases[rec["phase"]]+=1
        keys=set(windows)-{"main"}
        if child_keys is None:child_keys=keys
        elif keys!=child_keys:raise ValueError("Inconsistent child-pointer inventory; cannot compare")
        this_main=rec.get("runtime_golf_main_address")
        this_scene=rec.get("runtime_scene_address")
        if not isinstance(this_main,str) or not isinstance(this_scene,str):
            raise ValueError("Missing source provenance")
        if main_address is None:main_address,scene_address=this_main,this_scene
        if this_main!=main_address or this_scene!=scene_address:
            raise ValueError("Live scene/main pointer moved between samples")
        if previous is None:
            raw=windows["main"]
            for off,value in enumerate(words(raw)):
                if _ram(value,0x80) and value not in (int(main_address,16),int(scene_address,16)):
                    pointer_inventory.add(off*4)
        else:
            prev,prevwindows=previous
            same_stage=prev["stage"]==rec["stage"]
            stage_boundary+=int(not same_stage)
            total_pairs+=1
            within_phase=rec["phase"] if same_stage else None
            for region,data in windows.items():
                before=words(prevwindows[region])
                after=words(data)
                for index,(a,b) in enumerate(zip(before,after)):
                    key=(region,index*4)
                    e=stats[key]
                    if within_phase=="idle":e["idle_pair_count"]+=1
                    if within_phase=="aim_only":e["aim_pair_count"]+=1
                    changed=a!=b
                    e["_change_pattern"].append(changed)
                    if not changed:continue
                    e["changed_pairs"]+=1
                    e["within_stage_changes" if same_stage else "between_stage_changes"]+=1
                    if within_phase=="idle":e["idle_changes"]+=1
                    if within_phase=="aim_only":e["aim_changes"]+=1
                    step=((b-a+(1<<31))%(1<<32))-(1<<31)
                    e["positive_steps"]+=int(step>0)
                    e["negative_steps"]+=int(step<0)
                    e["zero_signed_steps"]+=int(step==0)
                    e["_nonzero_steps"].append(step)
                    fa=struct.unpack(">f",struct.pack(">I",a))[0]
                    fb=struct.unpack(">f",struct.pack(">I",b))[0]
                    e["plausible_float_pairs"]+=int(
                        all(math.isfinite(x) and 1e-6<abs(x)<=360 for x in (fa,fb)))
        previous=(rec,windows)
    ranking=[]
    groups={}
    for (region,offset),e in stats.items():
        if not e["changed_pairs"]:continue
        pattern=tuple(e["_change_pattern"])
        if pattern not in groups:groups[pattern]="pattern_"+str(len(groups)+1)
        counts=Counter(e["_nonzero_steps"])
        most_common=counts.most_common(1)[0][1]
        ranking.append({
            "region":region,"relative_offset":f"+0x{offset:03X}",
            "changed_pairs":e["changed_pairs"],"within_stage_changes":e["within_stage_changes"],
            "between_stage_changes":e["between_stage_changes"],
            "idle_changed_pairs":e["idle_changes"],"idle_comparable_pairs":e["idle_pair_count"],
            "aim_changed_pairs":e["aim_changes"],"aim_comparable_pairs":e["aim_pair_count"],
            "positive_integer_steps":e["positive_steps"],"negative_integer_steps":e["negative_steps"],
            "plausible_float_pairs":e["plausible_float_pairs"],
            "most_common_integer_step_repetitions":most_common,
            "change_timing_group":groups[pattern],"interpretation":classify(e)
        })
    ranking.sort(key=lambda e:(e["interpretation"]!="aim_phase_correlated_candidate",
                               -e["aim_changed_pairs"],-e["changed_pairs"],
                               e["region"],e["relative_offset"]))
    if len(ranking)>MAX_OUTPUT_WORDS:raise ValueError("More changed words than report allows")
    watched=set(int(x.removeprefix("child_at_main+0x"),16) for x in child_keys)
    unobserved=sorted(pointer_inventory-watched)
    return {
        "schema_version":1,"kind":"local-private-golfer-pattern-analysis",
        "sample_count":len(samples),"phase_sample_counts":dict(sorted(phases.items())),
        "comparisons":total_pairs,"stage_boundary_pairs":stage_boundary,
        "minimum_frame_span":minspan,"maximum_frame_span":maxspan,
        "watched_first_level_children":len(child_keys),
        "main_ram_pointer_shape_count":len(pointer_inventory),
        "unwatched_main_pointer_offsets":[f"+0x{x:03X}" for x in unobserved],
        "changed_word_count":len(ranking),"candidate_words":ranking,
        "confirmed_club_rotation":False,"confirmed_power":False,
        "warning":"Counter and phase classifications are statistical hints only; no game-physics fields identified. Read-only private data analysis."
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True,
                   help="LOCAL golfer-*-RAW-PRIVATE.jsonl; never uploaded")
    p.add_argument("--output",type=Path,
                   help="Optional sanitized report JSON; auto-choose adjacent new path if omitted")
    a=p.parse_args(argv)
    try:
        rows=load(a.input)
        report=summarize(rows)
        if a.output and a.output.resolve()==a.input.resolve():
            raise ValueError("Never overwrite PRIVATE capture")
        dest=a.output or a.input.with_name(
            "golfer-pattern-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")
            +uuid.uuid4().hex[:8]+"-summary.json")
        if dest.exists():raise ValueError("Report exists; refuse overwrite")
        with dest.open("x",encoding="utf-8") as fp:
            json.dump(report,fp,indent=2,sort_keys=True,allow_nan=False)
            fp.write("\n")
        print("Local sanitized pattern analysis:",dest,flush=True)
        print(json.dumps(report,indent=2,sort_keys=True,allow_nan=False),flush=True)
        return 0
    except (OSError,ValueError,TypeError,KeyError,struct.error) as exc:
        print("Offline golfer analysis stopped:",exc,file=sys.stderr)
        return 1

if __name__=="__main__":raise SystemExit(main())
