"""PRIVATE full MEM1+MEM2 B0–B3 differential atlas with source-linked overlays.

Unlike 128-byte candidate scans, this compares every aligned 32-bit word in
both native banks across four locally preserved checkpoints, then overlays
selected source-validated Golf scene, Config, FieldManager, PlayerManager,
four player records, selected ball-like object, and map objects. Results are
PRIORITIZATION of input-vs-idle changes, NOT semantic type identification.
No Dolphin, controller, RPC, external dependency or network access.
No game bytes, decoded arbitrary values or absolute runtime pointers emitted.
"""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
import argparse
import json
import mmap
from pathlib import Path
import struct
import sys

import audit_golf_two_bank_roster_private as roster
import audit_selected_ball_start_link_private as selected
import audit_selected_ball_four_phase_private as phases

PAGE = 4096
BLOCK = 256
MEM1_BASE, MEM2_BASE = roster.MEM1_BASE, roster.MEM2_BASE
SIZES = {"MEM1": roster.MEM1_SIZE, "MEM2": roster.MEM2_SIZE}
BANK_BASE = {"MEM1": MEM1_BASE, "MEM2": MEM2_BASE}
MAX_TOP = 10000
MAX_OBJECT_OFFSETS = 4096


def _shape(a,b,c,d):
    idle,aim,release=(a != b,b != c,c != d)
    return idle,aim,release, (not idle and aim and c == d), (
        not idle and aim and d == b)


def _scan_bank(four, bank, *, top_blocks):
    """Complete aligned 32-bit comparison; <=256B rank resolution."""
    if len(four) != 4 or any(len(m) != SIZES[bank] for m in four):
        raise ValueError("All four native bank images required")
    view = [memoryview(m).cast("I") for m in four]
    try:
        changes=Counter()
        blocks=[]
        page_changes=[0,0,0]
        pages_changed_any=0
        words_total=SIZES[bank]//4
        for page_start in range(0,SIZES[bank],PAGE):
            page_end=page_start+PAGE
            page_bytes=[m[page_start:page_end] for m in four]
            flags=[page_bytes[i]!=page_bytes[i+1] for i in range(3)]
            for i,b in enumerate(flags):
                page_changes[i]+=int(b)
            if not any(flags):
                continue
            pages_changed_any+=1
            start_word=page_start//4
            for bi in range(PAGE//BLOCK):
                baseword=start_word+(bi*BLOCK//4)
                bucket=Counter()
                for wi in range(baseword,baseword+BLOCK//4):
                    a,b,c,d=(v[wi] for v in view)
                    idle,aim,release,aim_persist,aim_revert=_shape(a,b,c,d)
                    if idle or aim or release:
                        bucket["changed_any"]+=1
                    if idle: bucket["idle"]+=1
                    if aim: bucket["aim"]+=1
                    if release: bucket["release"]+=1
                    if aim and not idle: bucket["aim_with_quiet_prior_idle"]+=1
                    if aim_persist: bucket["aim_persistent"]+=1
                    if aim_revert: bucket["aim_reverted"]+=1
                    if idle and aim and release: bucket["all_three_changed"]+=1
                if bucket["changed_any"]:
                    changes.update(bucket)
                    blocks.append({
                        "bank":bank,
                        "bank_relative_block_index":(page_start+bi*BLOCK)//BLOCK,
                        "block_bytes":BLOCK,
                        **dict(bucket),
                    })
        # Rank changes that appeared with WASD but not the idle control,
        # then persistent or reverted signatures. Never call them "aim".
        blocks.sort(key=lambda x:(
            -x.get("aim_with_quiet_prior_idle",0),
            -x.get("aim_persistent",0),
            -x.get("aim_reverted",0),
            x.get("idle",0),
            -x.get("aim",0),
            x["bank_relative_block_index"]))
        return {
            "bank":bank,
            "all_aligned_words_examined":words_total,
            "total_4k_pages":SIZES[bank]//PAGE,
            "pages_different_by_transition":page_changes,
            "pages_different_in_any_transition":pages_changed_any,
            "word_change_counts":dict(changes),
            "changed_256byte_blocks_total":len(blocks),
            "top_changed_256byte_blocks":blocks[:top_blocks],
            "omitted_changed_blocks":max(0,len(blocks)-top_blocks),
        }
    finally:
        for v in view:
            v.release()


def _address_bytes(bank_pair, ptr, length):
    kind=roster._bank(ptr,length)
    if kind is None:
        raise ValueError("Object region outside source-resolved banks")
    base=BANK_BASE[kind]
    mm=bank_pair[0 if kind=="MEM1" else 1]
    return kind,bytes(mm[ptr-base:ptr-base+length])


def _resolve_objects(rd):
    """Re-evaluate source-backed owner chain separately in EACH snapshot."""
    s,_=selected.analyze_one(rd.u32,rd.header())
    if not s["selected_record_pointer_matches_code_defined_stride"]:
        raise ValueError("Selected record not source-stride verified")
    u=rd.u32
    manager=u(roster.SCENE_MANAGER_STATIC)
    scene=u(manager+0xC)
    main=u(scene+0x9C)
    config=u(roster.GOLF_CONFIG_STATIC)
    field=u(roster.GOLF_FIELD_STATIC)
    pm=u(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    selected_record=u(pm+0x334)
    record_idx=(selected_record-pm-4)//roster.ROSTER_STRIDE
    if record_idx not in range(roster.ROSTER_SLOTS):
        raise ValueError("Selected player index out of range")
    ball=u(selected_record+0x88)
    ball_vector=u(ball+0x4C)
    start=u(field+0x50)
    pin=u(field+0x44)
    cup=u(field+0x54)
    course=u(field+0x70)
    tee=u(field+0x2C)
    regions={
        "scene":(scene,0x100),
        "golf_main":(main,0x200),
        "golf_config":(config,0xA0),
        "field_manager":(field,0x90),
        "player_manager":(pm,0x360),
        "selected_player_record":(selected_record,roster.ROSTER_STRIDE),
        "selected_ball_related_object":(ball,0x1AC),
        "selected_ball_translation":(ball_vector,0x0C),
        "current_start_map_object":(start,0x80),
        "current_pin_map_object":(pin,0x80),
        "current_cup_map_object":(cup,0x80),
        "course_map_object":(course,0x80),
        "tee_map_object":(tee,0x80),
        "candidate_player_from_golf_main":(u(main+0x30),0x100),
        "source_wind_direction_BSS_9x_u32":(0x804A8B54,9*4),
        "source_wind_speed_BSS_9x_u32":(0x804A8B78,9*4),
    }
    for i in range(roster.ROSTER_SLOTS):
        rec=pm+4+i*roster.ROSTER_STRIDE
        regions[f"player_record_slot_{i}"]=(rec,roster.ROSTER_STRIDE)
        child=u(rec+0x88)
        regions[f"ball_related_slot_{i}"]=(child,0x1AC)
    return record_idx, u(config+0x98), regions


def _region_analysis(four_pairs, *, max_object_offsets):
    all_regions=[]
    indices=[]
    holes=[]
    for p in four_pairs:
        reader=roster.TwoBankReader(*p)
        idx,hole,regions=_resolve_objects(reader)
        all_regions.append(regions)
        indices.append(idx)
        holes.append(hole)
    if len(set(indices))!=1 or len(set(holes))!=1:
        raise ValueError("Selected index or hole changed across no-shot session")
    out={}
    for name in all_regions[0]:
        ptrs=[d[name][0] for d in all_regions]
        sizes=[d[name][1] for d in all_regions]
        if len(set(sizes))!=1 or sizes[0]%4:
            raise ValueError("Source object layout size changed unexpectedly")
        vectors=[_address_bytes(pair,p,sizes[0]) for pair,p in zip(four_pairs,ptrs)]
        if len(set(kind for kind,_ in vectors))!=1:
            raise ValueError("Source object migrated between MEM1/MEM2")
        mem=[x[1] for x in vectors]
        diffs=[]
        totals=Counter()
        for off in range(0,sizes[0],4):
            a,b,c,d=[v[off:off+4] for v in mem]
            idle,aim,release,aim_persist,aim_revert=_shape(a,b,c,d)
            if not (idle or aim or release):
                continue
            totals["changed_words"]+=1
            totals["idle_words"]+=int(idle)
            totals["aim_words"]+=int(aim)
            totals["release_words"]+=int(release)
            totals["aim_no_idle_words"]+=int(aim and not idle)
            totals["aim_persist_words"]+=int(aim_persist)
            totals["aim_revert_words"]+=int(aim_revert)
            diffs.append({
                "source_object_relative_word_offset":f"+0x{off:03X}",
                "changed_idle":idle,
                "changed_while_aim_changed":aim,
                "changed_after_aim_release":release,
                "changed_on_aim_and_stable_after":aim_persist,
                "aim_change_reverted_to_B1":aim_revert,
                "field_semantics_verified":False,
            })
        diffs.sort(key=lambda x:(
            not x["changed_on_aim_and_stable_after"],
            not x["aim_change_reverted_to_B1"],
            x["changed_idle"],
            x["source_object_relative_word_offset"]))
        out[name]={
            "length_bytes":sizes[0],
            "bank":vectors[0][0],
            "source_object_address_constant_all_phases":len(set(ptrs))==1,
            "counts":dict(totals),
            "changed_word_details":diffs[:max_object_offsets],
            "changed_word_details_omitted":max(0,len(diffs)-max_object_offsets),
        }
    return {"selected_record_index":indices[0],
            "source_raw_hole_index_stable":True,
            "source_resolved_regions":out}


def analyze_four_pairs(pairs, *,top_blocks=250,max_object_offsets=1024):
    if (len(pairs)!=4 or type(top_blocks) is not int or
            not 1<=top_blocks<=MAX_TOP or
            type(max_object_offsets) is not int or
            not 1<=max_object_offsets<=MAX_OBJECT_OFFSETS):
        raise ValueError("Invalid source-pair count or bounded reporting options")
    return {
        "schema_version":1,
        "kind":"local-private-fullbank-fourphase-golf-source-overlay",
        "game_id":"RSPE01", "revision":1,"mode":4,
        "all_native_bytes_scanned_in_each_phase":roster.MEM1_SIZE+roster.MEM2_SIZE,
        "total_aligned_words_scanned_across_banks_each_phase":
            (roster.MEM1_SIZE+roster.MEM2_SIZE)//4,
        "bank_diff_results":{
            bank:_scan_bank([pairs[i][0 if bank=="MEM1" else 1] for i in range(4)],
                            bank,top_blocks=top_blocks)
            for bank in ("MEM1","MEM2")
        },
        "source_overlay":_region_analysis(pairs,max_object_offsets=max_object_offsets),
        "B0_B1_idle_B1_B2_visible_aim_B2_B3_idle_operator_labels_only":True,
        "aim_sensitive_words_are_unverified_candidate_offsets":True,
        "independently_verified_guest_frames":False,
        "physical_ball_xyz_verified":False,
        "club_pose_verified":False,
        "swing_power_verified":False,
        "ball_motion_observed":False,
        "approved_for_training":False,
        "allowed_to_publish":False,
        "next_action":"Rank source-linked aim-specific changes against full-bank "
                      "block controls; inspect high-scoring local offsets "
                      "with PPC write sites and repeated independent boots. "
                      "No unverified aim/physics/shot label."
    }


def run_local(folder,output,*,top_blocks=250,max_object_offsets=1024):
    folder=Path(folder)
    output=Path(output)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Missing private session")
    trusted=selected.DATA_ROOT.resolve(strict=True)
    session=folder.resolve(strict=True)
    if session==trusted or not session.is_relative_to(trusted):
        raise ValueError("Private inputs outside ignored data root")
    if (output.exists() or output.is_symlink()
            or output.parent.resolve(strict=True)!=session
            or output.suffix.lower()!=".json"):
        raise ValueError("Output must be a new JSON in same private session")
    meta=phases._validate_manifest(session)
    with ExitStack() as stack:
        images=[]
        for phase in phases.PHASES:
            pair=[]
            for bank in ("MEM1","MEM2"):
                p=phases._approved_bank(
                    session,f"{phase}-{bank}.bin",SIZES[bank])
                if phases._hash(p)!=meta[phase]["sha256"][bank]:
                    raise ValueError("Native dump does not match checkpoint manifest")
                fh=stack.enter_context(p.open("rb"))
                pair.append(stack.enter_context(mmap.mmap(
                    fh.fileno(),0,access=mmap.ACCESS_READ)))
            images.append(tuple(pair))
        report=analyze_four_pairs(
            images,top_blocks=top_blocks,max_object_offsets=max_object_offsets)
    with output.open("x",encoding="utf-8") as dest:
        json.dump(report,dest,indent=2,sort_keys=True,allow_nan=False)
        dest.write("\n")
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--top-blocks",type=int,default=250)
    p.add_argument("--max-object-offsets",type=int,default=1024)
    args=p.parse_args(argv)
    try:
        report=run_local(args.private_root,args.output,
                         top_blocks=args.top_blocks,
                         max_object_offsets=args.max_object_offsets)
    except (OSError,ValueError,TypeError,KeyError,OverflowError):
        print("Private full-bank study refused missing/unsafe paired input "
              "or source mismatch; no raw memory/path printed.",file=sys.stderr)
        return 1
    safe={
        "kind":report["kind"],
        "all_native_bytes_scanned_in_each_phase":
            report["all_native_bytes_scanned_in_each_phase"],
        "bank_summary":{
            name:{
                "all_aligned_words_examined":info["all_aligned_words_examined"],
                "pages_different_by_transition":info["pages_different_by_transition"],
                "pages_different_in_any_transition":
                    info["pages_different_in_any_transition"],
                "word_change_counts":info["word_change_counts"]
            } for name,info in report["bank_diff_results"].items()
        },
        "source_object_change_counts":{
            key:info["counts"]
            for key,info in report["source_overlay"][
                "source_resolved_regions"].items()
        },
        "approved_for_training":False,
        "allowed_to_publish":False,
        "note":"Full detailed bank-relative hotspot ranking and every source-object "
               "word offset are saved in the private local JSON output.",
    }
    print(json.dumps(safe,indent=2,sort_keys=True,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
