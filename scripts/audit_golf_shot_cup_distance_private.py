"""PRIVATE source-gated PRE/POST ball-to-cup geometry and UI result annotation.

Source objects: selected PlayerManager record +0x88 -> Ball +0x4C,
FieldManager +0x44 PIN / +0x54 CUP / +0x50 START, each map object's
translation at +0x4C -> its source +0x30 f32[3].
Game units, y axis, physics, game score and real ball identity unverified.
Calculates source-coordinate planar component [0,2] and 3D distances,
NOT licensed measured feet/yards. A RESULT UI number is operator-typed
and stored privately; it is not a proven distance conversion.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import math
import mmap
from pathlib import Path
import struct
import sys

import audit_golf_two_bank_roster_private as roster
import audit_selected_ball_start_link_private as selected
import audit_selected_ball_prepost_shot_private as shot
import preserve_golf_shot_distance_checkpoint_private as keeper


def _vec(words):
    v=tuple(struct.unpack(">f",struct.pack(">I",w))[0] for w in words)
    if any(not math.isfinite(x) or abs(x)>1e7 for x in v):
        raise ValueError("Source vector not finite/bounded")
    return v


def _map_vector(read, field, relative):
    obj=read(field+relative)
    if roster._bank(obj,0x50)!="MEM2" or read(obj+0x4C)!=obj+0x30:
        raise ValueError("Map object translation/selfref invalid")
    v=tuple(read(obj+0x30+j*4) for j in range(3))
    return obj,v


def snapshot(read,header):
    s=shot.snapshot_candidate(read,header)
    field=read(roster.GOLF_FIELD_STATIC)
    pin,pin_words=_map_vector(read,field,0x44)
    cup,cup_words=_map_vector(read,field,0x54)
    start,start_words=_map_vector(read,field,0x50)
    if len({pin,cup,start})!=3:
        raise ValueError("Source pin/cup/start objects not independent")
    if start_words!=s["start_words"]:
        raise ValueError("Field start and player source chain disagree")
    # No raw data included in any returned JSON. These are transient only.
    s.update({
        "pin_words":pin_words,"cup_words":cup_words,
        "map_owners":(pin,cup,start),
    })
    return s


def _distance(a,b):
    return (math.hypot(a[0]-b[0],a[2]-b[2]),
            math.sqrt(sum((x-y)**2 for x,y in zip(a,b))))


def _round(x):
    return round(float(x),6)


def summarize(pre,post,*,distinct_bank_mem1,distinct_bank_mem2,
              result_metadata=None,result_native_present=False,
              result_source_valid=None,result_source_snapshot=None):
    if any(type(x) is not bool for x in (
            distinct_bank_mem1,distinct_bank_mem2,result_native_present)):
        raise ValueError("Invalid checkpoint provenance")
    if any(s.get("source_gates") is not True for s in (pre,post)):
        raise ValueError("Source-selected PRE/POST validation absent")
    if (pre["slot"]!=post["slot"] or pre["hole"]!=post["hole"] or
            pre["owner"]!=post["owner"] or
            pre["map_owners"]!=post["map_owners"]):
        raise ValueError("PRE/POST owner, hole, source map object continuity failed")
    if pre["start_words"]!=post["start_words"] or pre["cup_words"]!=post["cup_words"] or pre["pin_words"]!=post["pin_words"]:
        raise ValueError("Start/cup/pin control moved; cannot claim same shot geometry")
    ball_before=_vec(pre["ball_words"])
    ball_after=_vec(post["ball_words"])
    record_before=_vec(pre["record_words"])
    record_after=_vec(post["record_words"])
    cup=_vec(post["cup_words"])
    pin=_vec(post["pin_words"])
    start=_vec(post["start_words"])
    motion_count=sum(a!=b for a,b in zip(pre["ball_words"],post["ball_words"]))
    record_motion=sum(a!=b for a,b in zip(pre["record_words"],post["record_words"]))
    ball_record_post=sum(a==b for a,b in zip(post["ball_words"],post["record_words"]))
    before_cup=_distance(ball_before,cup)
    after_cup=_distance(ball_after,cup)
    after_pin=_distance(ball_after,pin)
    shot_delta=_distance(ball_before,ball_after)
    start_cup=_distance(start,cup)
    meta=result_metadata or {}
    if result_source_valid not in (True,False,None):
        raise ValueError("Result scene evidence must be tri-state")
    result={
        "schema_version":1,
        "kind":"local-private-shot-ball-to-hole-candidate-distance",
        "game_id":"RSPE01","revision":1,"source_mode":4,
        "pre_post_golf_source_identity_and_selected_slot_stable":True,
        "pre_post_owner_and_hole_stable":True,
        "source_start_pin_and_cup_vectors_stable":True,
        "source_pin_and_cup_are_separate_objects":True,
        "complete_MEM1_bank_changed":distinct_bank_mem1,
        "complete_MEM2_bank_changed":distinct_bank_mem2,
        "selected_nested_ball_changed_components":motion_count,
        "selected_record_position_changed_components":record_motion,
        "selected_record_equals_nested_ball_components_post":ball_record_post,
        "candidate_ball_moved_between_pre_and_post":motion_count>0,
        "coordinate_distance_projection":"source_components_0_and_2",
        "candidate_ball_to_cup_planar_before_game_units":_round(before_cup[0]),
        "candidate_ball_to_cup_planar_after_game_units":_round(after_cup[0]),
        "candidate_ball_to_cup_3d_after_game_units":_round(after_cup[1]),
        "candidate_ball_to_pin_planar_after_game_units":_round(after_pin[0]),
        "candidate_ball_to_pin_3d_after_game_units":_round(after_pin[1]),
        "candidate_pre_to_post_displacement_planar_game_units":_round(shot_delta[0]),
        "candidate_pre_to_post_displacement_3d_game_units":_round(shot_delta[1]),
        "candidate_start_to_cup_planar_game_units":_round(start_cup[0]),
        "result_memory_pair_preserved":result_native_present,
        "result_golf_source_chain_still_valid":result_source_valid,
        "operator_typed_result_ui_distance":meta.get("ui_displayed_distance_value"),
        "operator_typed_result_ui_unit":meta.get("ui_displayed_distance_unit"),
        "ui_distance_same_quantity_as_computed_ball_to_cup_verified":False,
        "game_unit_scale_verified":False,
        "coordinate_axis_semantics_verified":False,
        "pin_cup_world_physics_verified":False,
        "ball_world_xyz_verified":False,
        "observed_gameplay_hit_independently_verified":False,
        "shot_contact_frame_verified":False,
        "ball_velocity_verified":False,
        "club_pose_and_swing_power_verified":False,
        "training_allowed":False,
        "allowed_to_publish":False,
        "warning":(
          "Numbers are candidate source-coordinate distances, not proven feet "
          "or yards. Planar components 0 and 2 are suggested by Rev1 source "
          "goal comparisons, not independently confirmed course axes. "
          "Result UI is operator-entered and may report a DIFFERENT metric "
          "or round differently. If the ball reset before POST, the study "
          "cannot determine the landing distance."
        ),
    }
    # If the RESULT UI still retains a source-valid golfer/ball object,
    # inspect it without interpreting it as flight or as necessarily
    # representing the landed point: game may reset the ball here.
    if result_source_valid is True and result_source_snapshot is not None:
        res=result_source_snapshot
        linked=(res["slot"]==post["slot"] and res["hole"]==post["hole"]
                and res["owner"]==post["owner"]
                and res["map_owners"]==post["map_owners"]
                and res["cup_words"]==post["cup_words"])
        result["result_selected_owner_hole_and_cup_same_as_post"]=linked
        if linked:
            rball=_vec(res["ball_words"])
            rcup=_vec(res["cup_words"])
            result["result_candidate_ball_to_cup_planar_game_units"]=_round(
                _distance(rball,rcup)[0])
            result["result_candidate_ball_to_cup_3d_game_units"]=_round(
                _distance(rball,rcup)[1])
            result["result_candidate_ball_same_as_post"]=(
                res["ball_words"]==post["ball_words"])
            result["result_candidate_ball_equal_to_original_start"]=(
                res["ball_words"]==pre["start_words"])
    else:
        result["result_selected_owner_hole_and_cup_same_as_post"]=False

    if (meta.get("ui_displayed_distance_value") is not None and
            result["candidate_ball_to_cup_planar_after_game_units"]>0):
        result["exploratory_display_units_per_game_unit_ratio"]=_round(
            meta["ui_displayed_distance_value"]/after_cup[0])
        result["ratio_validated_as_calibration"]=False
    return result


def run_local(folder):
    folder=Path(folder)
    root=selected.DATA_ROOT.resolve(strict=True)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Missing private shot folder")
    private=folder.resolve(strict=True)
    if private==root or not private.is_relative_to(root):
        raise ValueError("Private folder outside ignored Data root")
    compat=shot._manifest(private)
    study=keeper._read_manifest(private/keeper.NAME)
    if not isinstance(study,dict):
        raise ValueError("Missing study manifest")
    if not all(k in study["checkpoints"] for k in ("PRE","POST")):
        raise ValueError("Missing observed shot PRE/POST")
    reports=[]
    hashes=[]
    with ExitStack() as stack:
        for phase in ("PRE","POST"):
            paths=[shot._approved_bank(private,f"{phase}-{b}.bin",size)
                   for b,size in (("MEM1",roster.MEM1_SIZE),
                                  ("MEM2",roster.MEM2_SIZE))]
            saved={b:shot._sha256(p) for b,p in zip(("MEM1","MEM2"),paths)}
            if saved!=compat[phase]["sha256"] or saved!=study["checkpoints"][phase]["sha256"]:
                raise ValueError("Shot checkpoint hash mismatch")
            images=[]
            for p in paths:
                f=stack.enter_context(p.open("rb"))
                images.append(stack.enter_context(mmap.mmap(
                    f.fileno(),0,access=mmap.ACCESS_READ)))
            rd=roster.TwoBankReader(*images)
            reports.append(snapshot(rd.u32,rd.header()))
            hashes.append(saved)
        has_result="RESULT" in study["checkpoints"]
        result_valid=None
        result_snapshot=None
        result_meta=study["checkpoints"].get("RESULT",{})
        if has_result:
            paths=[shot._approved_bank(private,f"RESULT-{b}.bin",size)
                   for b,size in (("MEM1",roster.MEM1_SIZE),
                                  ("MEM2",roster.MEM2_SIZE))]
            hashes_result={b:shot._sha256(p) for b,p in zip(("MEM1","MEM2"),paths)}
            if hashes_result!=result_meta["sha256"]:
                raise ValueError("RESULT dump modified after preservation")
            images=[]
            for p in paths:
                f=stack.enter_context(p.open("rb"))
                images.append(stack.enter_context(mmap.mmap(
                    f.fileno(),0,access=mmap.ACCESS_READ)))
            rd=roster.TwoBankReader(*images)
            try:
                result_snapshot=snapshot(rd.u32,rd.header())
            except (ValueError,KeyError,TypeError):
                result_valid=False
            else:
                result_valid=True
        return summarize(reports[0],reports[1],
                         distinct_bank_mem1=hashes[0]["MEM1"]!=hashes[1]["MEM1"],
                         distinct_bank_mem2=hashes[0]["MEM2"]!=hashes[1]["MEM2"],
                         result_metadata=result_meta,
                         result_native_present=has_result,
                         result_source_valid=result_valid,
                         result_source_snapshot=result_snapshot)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root",type=Path,required=True)
    a=p.parse_args(argv)
    try:
        report=run_local(a.private_root)
    except (OSError,ValueError,KeyError,TypeError,OverflowError,struct.error):
        print("Private shot distance audit FAILED CLOSED: check PRE/POST "
              "source/selected owner, native pair integrity and observed shot. "
              "No raw pointers or memory displayed.",file=sys.stderr)
        return 1
    print(json.dumps(report,indent=2,sort_keys=True,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
