#!/usr/bin/env python3
"""Offline P0 validation matrix. No RAM access, emulator input, or training.

Optional --evidence is sanitized, claim-level metadata, NOT independently
verified gameplay. Never publish run IDs, addresses, raw vectors or paths.
"""
from __future__ import annotations
import argparse
import json
import math
import re
import sys
from pathlib import Path

# Per-variable discriminators, not a generic role-derived approval rule.
P = {
"scene.current_id": ("fresh_boot scene_change idle_no_a", "Compare fresh Golf and menu scene IDs."),
"golf.main_ptr": ("fresh_boot scene_change generation_change", "Re-resolve scene main pointer across lifecycle."),
"golf.tee_start.map_translation_xyz": ("idle_no_a aim_only hole_change visual_match units_calibrated", "Change tee/hole, independently calibrate rendered start."),
"golf.pin.map_translation_xyz": ("idle_no_a hole_change visual_match units_calibrated", "Vary pin separately from tee and check rendered pin."),
"golf.cup.map_translation_xyz": ("hole_change visual_match source_typed units_calibrated", "Verify cup inherited layout, varying pin and physical units."),
"golf.ball.world_xyz": ("idle_no_a aim_only flight settled source_global_control inactive_player generation_change frame_sync visual_match units_calibrated shot_join", "Pair same-shot guest physics steps with rendered ball and inactive/global negatives."),
"golf.player.selected_record.initial_position_candidate": ("idle_no_a aim_only flight settled source_global_control inactive_player frame_sync visual_match shot_join", "Compare selected initial +0x54 and selected-child current +0x30 during verified flight."),
"golf.player.selected_record.start_copy_candidate": ("idle_no_a aim_only flight_stable hole_change shot_join", "Show immutable START copy during flight and independent hole change."),
"golf.ball_object.current_translation_candidate": ("idle_no_a aim_only flight settled source_global_control inactive_player generation_change frame_sync visual_match shot_join", "Trace selected/global receiver against rendered projectile in one guest-framed shot."),
"golf.ball_object.initialized_cache_cc": ("idle_no_a aim_only flight source_global_control cache_branch frame_sync shot_join", "Distinguish initialized CC cache from selected current and source-global receiver."),
"golf.ball_object.conditional_cache_f0": ("idle_no_a aim_only flight cache_branch hole_change frame_sync shot_join", "Prove executed conditional F0 writer and owner during an independently timed shot."),
"golf.ball_object.conditional_cache_fc": ("idle_no_a aim_only flight cache_branch frame_sync visual_match shot_join", "Observe descending rendered flight and source FC writer on guest frames."),
"golf.player.selected_record.aim_rotation": ("idle_no_a aim_left aim_right wrong_controller disconnected_controller inactive_player preaction source_typed", "Repeat opposite precontact aim inputs; establish selected controller, sign and units."),
"golf.ball.source_global_translation_candidate": ("idle_no_a aim_only flight source_global_control generation_change frame_sync visual_match shot_join", "Determine global object generation and independently identify rendered actor."),
"golf.ball_object.cache_f0_update_tag_118": ("idle_no_a aim_only cache_branch cache_pair source_typed shot_join", "Trace selected +0x118 typed writer and F0 branch during same shot."),
"golf.ball_object.cache_fc_update_tag_11c": ("idle_no_a aim_only cache_branch cache_pair source_typed shot_join", "Trace selected +0x11C typed writer and FC branch during same shot."),
"golf.config.standard_scores_table_4x9": ("source_typed mode_change native_result censored_100ft shot_join", "Trace mode4 game-owned terminal score writer; exclude 100ft penalty."),
"golf.player.selected_record.scalar_030": ("idle_no_a aim_only flight source_typed frame_sync shot_join", "Find typed selected record +0x030 writer and exclude clock/animation confounds."),
"golf.player.selected_record.scalar_090": ("idle_no_a aim_only flight source_typed frame_sync shot_join", "Find typed selected record +0x090 writer and exclude velocity guesses."),
"golf.sequence_mgr.golf_scores_hole_major_9x4": ("source_typed mode_change native_result censored_100ft shot_join", "Separate SequenceMgr 9x4 from Config and find mode4 terminal writer."),
"golf.player.selected_record.stroke_count_source_candidate": ("source_typed idle_no_a native_result shot_join", "Prove selected stroke setter is causally linked to accepted native stroke."),
"golf.config.mode_selector_094_source_candidate": ("source_typed mode_change scene_change idle_no_a", "Cross-check source Config+0x94 and independently selected training mode."),
"golf.config.current_hole_index_098_source_candidate": ("source_typed hole_change scene_change idle_no_a", "Cross-check Config+0x98 and independent hole transition."),
"golf.wind.hole_direction_table_source_candidate": ("source_typed hole_change visual_match units_calibrated", "Trace wind direction getter and calibrate against independent UI."),
"golf.wind.hole_speed_table_source_candidate": ("source_typed hole_change visual_match units_calibrated", "Trace wind speed getter and calibrate against independent UI."),
}
NEG = {"idle_no_a","aim_only","wrong_controller","disconnected_controller",
       "inactive_player","source_global_control","scene_change","hole_change",
       "generation_change","pointer_reuse","cross_shot","airborne_start",
       "censored_100ft","frame_unsynced"}
CONTROLS = NEG | set("fresh_boot visual_match units_calibrated flight flight_stable settled frame_sync shot_join cache_branch cache_pair source_typed mode_change native_result aim_left aim_right preaction".split())
FIELDS = set("control response run_id shot_id scene_id hole_id selected_actor observed_actor rendered_actor generation observed_generation rendered_generation controller_matches_selected controller_connected frame guest_frame_verified physics_step_verified game_owned_acceptance contact_verified owner_re_resolved selected_vs_global_distinct source_typed visual_verified units_verified state visual_label phase direction signed_delta censored distance_label used_as_carry joined independent_witness different_shot_id".split())
TOKEN = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")
PENALTY = re.compile(r"(?:m\s*:\s*100\s*ft|off[\s_-]*green[\s_-]*100\s*ft)",re.I)

def yes(o,*ks):
    return all(type(o.get(k)) is bool and o[k] for k in ks)
def no(o,*ks):
    return all(type(o.get(k)) is bool and not o[k] for k in ks)
def token(x):
    return isinstance(x,str) and bool(TOKEN.fullmatch(x))
def penalty(o):
    x=o.get("distance_label","")
    return isinstance(x,str) and bool(PENALTY.search(x))
def identity(o,frame=False):
    keys=("run_id","shot_id","scene_id","hole_id","selected_actor",
          "observed_actor","rendered_actor","generation",
          "observed_generation","rendered_generation")
    if not all(token(o.get(k)) for k in keys):
        return False
    if len({o["selected_actor"],o["observed_actor"],o["rendered_actor"]})!=1:
        return False
    if len({o["generation"],o["observed_generation"],o["rendered_generation"]})!=1:
        return False
    return not frame or (type(o.get("frame")) is int and o["frame"]>=0
                         and yes(o,"guest_frame_verified","physics_step_verified"))

def judge(o):
    c,r=o["control"],o["response"]
    if c=="frame_unsynced":
        return False,"unverified_guest_physics_frame"
    if c=="cross_shot":
        return False,"cross_shot_join" if o.get("joined") is True else None
    if c=="airborne_start":
        bad=str(o.get("visual_label","")).lower()=="airborne" and str(o.get("state","")).upper()=="START"
        return False,"airborne_start_conflict" if bad else None
    if c=="censored_100ft":
        if o.get("used_as_carry") is True or (o.get("censored") is False and penalty(o)):
            return False,"censored_penalty_as_carry"
        return yes(o,"censored") and no(o,"used_as_carry") and penalty(o) and r=="rejected",None
    if c in ("generation_change","pointer_reuse"):
        if not yes(o,"owner_re_resolved"):
            return False,"object_generation_not_re_resolved"
        return r=="rejected",None
    frame=c in ("flight","flight_stable","settled","frame_sync","shot_join","native_result")
    if not identity(o,frame):
        return False,"actor_or_frame_identity_unverified"
    if c in ("idle_no_a","aim_only","wrong_controller","disconnected_controller",
             "inactive_player","source_global_control"):
        if not no(o,"game_owned_acceptance","contact_verified"):
            return False,"unverified_contact_or_input_control"
        if c=="source_global_control":
            ok=yes(o,"selected_vs_global_distinct","visual_verified") and r in ("stable","rejected")
        elif c=="wrong_controller":
            ok=no(o,"controller_matches_selected") and r=="stable"
        elif c=="disconnected_controller":
            ok=no(o,"controller_connected") and r=="stable"
        else:
            ok=r=="stable"
        return ok,None if ok else "negative_control_failed"
    if c in ("aim_left","aim_right","preaction"):
        if not (yes(o,"controller_connected","controller_matches_selected")
                and no(o,"game_owned_acceptance","contact_verified")
                and o.get("phase")=="PRE"):
            return False,"aim_not_preaction_selected_control"
        if c=="preaction":
            return r in ("stable","matched"),None
        delta=o.get("signed_delta")
        if type(delta) not in (int,float) or not math.isfinite(delta) or delta==0:
            return False,"aim_direction_unverified"
        target=-1 if c=="aim_left" else 1
        return (r=="changed" and o.get("direction")==("left" if target<0 else "right")
                and delta*target>0),None
    if c in ("scene_change","hole_change","fresh_boot","mode_change"):
        return yes(o,"owner_re_resolved") and r in ("changed","matched"),None
    if c=="visual_match":
        return yes(o,"visual_verified","independent_witness") and r=="matched",None
    if c=="units_calibrated":
        return yes(o,"units_verified","independent_witness") and r=="matched",None
    if c=="source_typed":
        return yes(o,"source_typed") and r=="matched",None
    if c in ("flight","settled","flight_stable"):
        return (yes(o,"visual_verified","independent_witness")
                and r==("stable" if c=="flight_stable" else "changed")),None
    if c=="frame_sync":
        return yes(o,"guest_frame_verified","physics_step_verified") and r=="matched",None
    if c=="shot_join":
        if not (yes(o,"independent_witness","guest_frame_verified","physics_step_verified")
                and token(o.get("different_shot_id"))
                and o["different_shot_id"]!=o["shot_id"]):
            return False,"shot_join_unverified"
        return r=="rejected",None
    if c in ("cache_branch","cache_pair"):
        return yes(o,"source_typed","independent_witness") and r=="matched",None
    if c=="native_result":
        if penalty(o) or o.get("censored") is not False:
            return False,"censored_penalty_as_carry"
        if not (yes(o,"game_owned_acceptance","contact_verified","units_verified",
                    "independent_witness") and r=="matched"):
            return False,"native_result_or_contact_unverified"
        return True,None
    return False,"unknown_control"

def check_evidence(e,ids):
    if (not isinstance(e,dict) or set(e)!={"schema_version","origin","variables"}
        or type(e["schema_version"]) is not int or e["schema_version"]!=1
        or e["origin"] not in ("synthetic","source_only","operator_reviewed")
        or not isinstance(e["variables"],dict) or set(e["variables"])-ids):
        raise ValueError("Bad evidence envelope")
    for item in e["variables"].values():
        if not isinstance(item,dict) or set(item)!={"observations"} or not isinstance(item["observations"],list) or len(item["observations"])>1000:
            raise ValueError("Bad observations")
        for o in item["observations"]:
            if (not isinstance(o,dict) or set(o)-FIELDS or
                o.get("control") not in CONTROLS or o.get("response") not in
                ("stable","changed","rejected","matched")):
                raise ValueError("Unsafe observation fields")
            if any(k.endswith("_id") and not token(v) for k,v in o.items()):
                raise ValueError("Unsafe identity")
            if ("signed_delta" in o and (type(o["signed_delta"]) not in (int,float)
                or not math.isfinite(o["signed_delta"]))):
                raise ValueError("Nonfinite delta")
            if ("distance_label" in o and (not isinstance(o["distance_label"],str)
                or len(o["distance_label"])>80)):
                raise ValueError("Unsafe label")
    return e

def cross_contradictions(observations):
    """Reject *every* unpaired flight/settled witness, not just the first pair.

    One valid shot must never launder an unrelated flight/settled observation
    from another run, shot, scene, hole, actor generation, or guest frame.
    This remains a hypothesis-only check, not game-side physics attestation.
    """
    flights = [o for o in observations if o.get("control") == "flight"]
    settled = [o for o in observations if o.get("control") == "settled"]
    if not flights or not settled:
        return set()

    def follows(flight, stop):
        keys = ("run_id", "shot_id", "scene_id", "hole_id",
                "selected_actor", "generation")
        return (all(flight.get(k) == stop.get(k) for k in keys)
                and type(flight.get("frame")) is int
                and type(stop.get("frame")) is int
                and flight["frame"] < stop["frame"]
                and yes(flight, "guest_frame_verified", "physics_step_verified")
                and yes(stop, "guest_frame_verified", "physics_step_verified")
                and identity(flight, frame=True)
                and identity(stop, frame=True))

    if (any(not any(follows(f, s) for s in settled) for f in flights)
            or any(not any(follows(f, s) for f in flights) for s in settled)):
        return {"moving_settled_shot_or_frame_mismatch"}
    return set()

def build_matrix(registry,evidence=None):
    vs=registry.get("variables")
    if not isinstance(vs,list):
        raise ValueError("Missing registry variables")
    chosen=[v for v in vs if isinstance(v,dict) and v.get("priority")=="P0"]
    ids=[v.get("id") for v in chosen]
    allowed={"unresolved","snapshot_correlated","source_candidate","rejected","runtime_verified"}
    if (len(ids)!=25 or len(set(ids))!=25 or set(ids)!=set(P) or
        any(v.get("status") not in allowed for v in chosen)):
        raise ValueError("P0 registry drift")
    if evidence is None:
        evidence={"schema_version":1,"origin":"source_only","variables":{}}
    check_evidence(evidence,set(ids))
    rows=[]
    for v in chosen:
        vid=v["id"]
        required,experiment=P[vid]
        required=required.split()
        observations=evidence["variables"].get(vid,{}).get("observations",[])
        satisfied=set()
        conflicts=set()
        for o in observations:
            good,why=judge(o)
            if why:
                conflicts.add(why)
            if good and o["control"] in required:
                satisfied.add(o["control"])
        cross=cross_contradictions(observations)
        conflicts.update(cross)
        if cross:
            satisfied.difference_update(("flight","settled"))
        missing=[c for c in required if c not in satisfied]
        status=("contradicted" if conflicts or v["status"]=="rejected" else
                "supported_hypothesis_only" if satisfied else "unresolved")
        ready=(not conflicts and not missing and
               evidence["origin"]=="operator_reviewed" and v["status"]!="rejected")
        rows.append({"variable_id":vid,"registry_status":v["status"],
            "candidate_status":status,"evidence_source":"registry_and_"+evidence["origin"],
            "controls_satisfied":sorted(satisfied),"contradictions":sorted(conflicts),
            "missing_witnesses":missing,"next_experiment":experiment,
            "ready_for_independent_live_experiment_review":ready,
            "runtime_verified":False,"training_eligible":False})
    return {"schema_version":1,"kind":"sanitized_p0_variable_validation_matrix",
        "scope":"RSPE01 Rev1; claims not experimental proof","origin":evidence["origin"],
        "p0_count":25,"runtime_verified_count":0,"training_approved":False,"rows":rows}

def markdown(report):
    out=["# P0 validation matrix (synthetic/source metadata; no training)","",
         "No runtime verification or training approval.","",
         "| Variable | Status | Evidence | Controls satisfied | Contradictions | Missing | Next experiment |",
         "|---|---|---|---|---|---|---|"]
    for r in report["rows"]:
        cells=[r["variable_id"],r["candidate_status"],r["evidence_source"],
               ", ".join(r["controls_satisfied"]) or "none",
               ", ".join(r["contradictions"]) or "none",
               ", ".join(r["missing_witnesses"]) or "none",r["next_experiment"]]
        out.append("| "+" | ".join(x.replace("|","/") for x in cells)+" |")
    return "\n".join(out)+"\n"

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry",type=Path,default=Path(__file__).resolve().parents[1]/"research/memory-variables/registry.json")
    ap.add_argument("--evidence",type=Path,help="sanitized control claims only; never raw banks")
    ap.add_argument("--format",choices=("json","markdown"),default="json")
    args=ap.parse_args(argv)
    try:
        reg=json.loads(args.registry.read_text(encoding="utf-8"))
        ev=json.loads(args.evidence.read_text(encoding="utf-8")) if args.evidence else None
        result=build_matrix(reg,ev)
    except (OSError,UnicodeError,ValueError,TypeError,KeyError):
        print("P0 validation REFUSED: invalid registry/evidence",file=sys.stderr)
        return 2
    print(markdown(result) if args.format=="markdown" else json.dumps(result,sort_keys=True,allow_nan=False),end="" if args.format=="markdown" else "\n")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
