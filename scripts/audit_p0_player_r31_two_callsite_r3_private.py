"""Original B0 source-qualified r3 argument syntax before TWO direct Player calls.

This is bounded source syntax, not call-flow dominance, typed receiver,
runtime execution or physical golfing state. Print only source-relative
instruction sites/register categories; never private bytes or pointers.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import sys

import audit_ball_xyz_source_callers_private as source
import audit_p0_player_r31_prelude_callers_private as prior
import audit_p0_r31_local_cfg_private as branch

UNIT="RPGolPlayer"
UNIT_START=prior.START
ENTRY_REL=0x1BD4
ENTRY=UNIT_START+ENTRY_REL
BL_RELS=(0x2024,0x2520)
WINDOW=0xA0
MAX_EVENTS=14

KNOWN_NO_GPR_WRITE=frozenset((4,10,11,16,17,18,19,36,38,44,47,48,50,52,54,59,63))
RT_WRITE=frozenset((7,8,12,13,14,15,32,34,40,42))
RA_WRITE=frozenset((20,21,22,23,24,25,26,27,28,29))
UPDATE=frozenset((33,35,37,39,41,43,45,49,51,53,55))


def _site(pc:int)->str:
    return f"+0x{pc-UNIT_START:04X}"


def r3_event(word:int)->dict|None:
    """Conservatively recognize explicit source r3 writes and unknown touches."""
    if type(word) is not int or not 0<=word<=0xffffffff:
        raise ValueError("bad PPC instruction")
    op=word>>26
    rs=(word>>21)&31
    ra=(word>>16)&31
    rb=(word>>11)&31
    xo=(word>>1)&1023
    if op in (14,15) and rs==3:
        return {"class":("addi" if op==14 else "addis"),
                "source":("literal_zero_base" if ra==0 else f"r{ra}"),
                "definite_r3_write":True}
    if op in (32,34,40,42) and rs==3:
        return {"class":"gpr_memory_load","source":f"r{ra}",
                "definite_r3_write":True}
    if op in RA_WRITE and ra==3:
        return {"class":"logical_or_rotate_to_r3","source":f"r{rs}",
                "definite_r3_write":True}
    if op==31:
        if xo==444 and ra==3 and rs==rb:
            return {"class":"mr_register_copy","source":f"r{rs}",
                    "definite_r3_write":True}
        if xo==444 and ra==3:
            return {"class":"logical_or_two_sources","source":"multiple",
                    "definite_r3_write":True}
        if rs==3 or ra==3:
            return {"class":"extended_gpr_touch_uncertain",
                    "source":"unknown","definite_r3_write":False}
        return None
    if op==46 and rs<=3:
        return {"class":"lmw_overwrites_r3","source":"memory",
                "definite_r3_write":True}
    if op in UPDATE and (rs==3 or ra==3):
        return {"class":"update_form_r3_effect","source":"unknown",
                "definite_r3_write":False}
    if op in RT_WRITE and rs==3:
        return {"class":"integer_destination_r3","source":"unknown",
                "definite_r3_write":True}
    if op in KNOWN_NO_GPR_WRITE:
        return None
    if rs==3 or ra==3:
        return {"class":"unclassified_r3_touch","source":"unknown",
                "definite_r3_write":False}
    return None


def inspect_call(blob:bytes,start_pc:int,call_pc:int)->dict:
    if (type(blob) is not bytes or len(blob)!=WINDOW+4 or
        type(start_pc) is not int or type(call_pc) is not int or
        call_pc-start_pc!=WINDOW or call_pc%4 or
        call_pc-UNIT_START not in BL_RELS):
        raise ValueError("bad bounded source call window")
    words=[struct.unpack_from(">I",blob,i)[0] for i in range(0,len(blob),4)]
    if prior.bl_target(call_pc,words[-1])!=ENTRY:
        raise ValueError("source site no longer directly calls candidate entry")
    barriers=[]
    events=[]
    for i,word in enumerate(words[:-1]):
        pc=start_pc+i*4
        flow=branch._branch(pc,word)
        if flow is not None:
            barriers.append({"site":_site(pc),"kind":flow[0],
                             "target_in_bounded_window":bool(
                                 flow[1] is not None and start_pc<=flow[1]<=call_pc)})
            continue
        ev=r3_event(word)
        if ev is not None:
            events.append({"site":_site(pc),**ev})
    cutoff=barriers[-1]["site"] if barriers else None
    start_suffix=(int(cutoff[3:],16)+4) if cutoff else (start_pc-UNIT_START)
    suffix=[e for e in events if int(e["site"][3:],16)>=start_suffix]
    nearest=suffix[-1] if suffix else None
    return {
        "source_call_site":_site(call_pc),
        "source_target_entry_candidate":f"+0x{ENTRY_REL:04X}",
        "exact_direct_PPC_BL_source_verified":True,
        "previous_bytes_inspected":WINDOW,
        "control_transfer_count_in_window":len(barriers),
        "last_control_transfer_before_call":barriers[-1] if barriers else None,
        "r3_definition_or_uncertain_touch_count":len(events),
        "post_last_barrier_r3_events":len(suffix),
        "nearest_post_barrier_r3_hint":nearest,
        "r3_events_nearest_first":list(reversed(events[-MAX_EVENTS:])),
        "additional_r3_events_omitted":max(0,len(events)-MAX_EVENTS),
        "last_straightline_origin_proves_runtime_argument":False,
        "incoming_r3_is_selected_player_record_verified":False,
    }


def audit(session:Path,data_root:Path)->dict:
    # Qualify known player entry BL xref and original B0 SHA before source read.
    base=prior.audit(session,data_root)
    rows=base["entry_hypotheses"]
    correct=[x for x in rows
             if x["candidate_post_return_pc_relative"]==f"+0x{ENTRY_REL:04X}"]
    if len(correct)!=1 or correct[0]["direct_Golf_BL_count"]!=2:
        raise ValueError("original two-callsite candidate drift")
    target_sites={(x["source_file"],x["relative_BL_site"])
                  for x in correct[0]["bounded_source_calls"]}
    expected={("Pack/RPSports/RPGolScene/RPGolPlayer.cpp",f"+0x{n:05X}")
              for n in BL_RELS}
    if target_sites!=expected:
        raise ValueError("two source callsites changed")
    bank=source.checked_private_b0(session,data_root)
    intervals=source.load_public_text_units()
    player=[(lo,hi) for lo,hi,name in intervals
            if name=="Pack/RPSports/RPGolScene/RPGolPlayer.cpp"
            and lo<=UNIT_START and UNIT_START+max(BL_RELS)+4<=hi]
    if len(player)!=1 or player[0][0]!=UNIT_START:
        raise ValueError("public player source owner changed")
    calls=[]
    with bank.open("rb") as fh:
        for rel in BL_RELS:
            pc=UNIT_START+rel
            fh.seek(pc-WINDOW-source.MEM1_START)
            data=fh.read(WINDOW+4)
            calls.append(inspect_call(data,pc-WINDOW,pc))
    if source.checked_private_b0(session,data_root)!=bank:
        raise ValueError("original B0 SHA changed")
    return {
        "kind":"S002-P0-PLAYER-R31-TWO-CALLSITE-R3-ARGUMENT-HINTS",
        "source_game":"RSPE01","revision":1,
        "entry_source_relative":f"+0x{ENTRY_REL:04X}",
        "candidate_entry_after_exact_blr_verified":True,
        "exact_source_two_direct_calls_verified":True,
        "original_private_B0_SHA_verified_before_after":True,
        "public_832_source_split_gate_verified":len(intervals)==832,
        "source_calls":calls,
        "complete_reaching_definitions_proven":False,
        "function_entry_prologue_verified":False,
        "incoming_r3_is_selected_player_record_verified":False,
        "dynamic_source_store_during_shot_verified":False,
        "actual_ball_world_xyz_velocity_power_score_verified":False,
        "approved_for_training":False,
        "allowed_to_publish":False,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    default=Path(__file__).resolve().parents[2]/"Wii-AI-Golf-Data"
    p.add_argument("--data-root",type=Path,default=default)
    p.add_argument("--private-session",type=Path)
    opts=p.parse_args(argv)
    try:
        report=audit(opts.private_session or opts.data_root/"ball-study-20261027-212633",
                     opts.data_root)
    except (OSError,ValueError,TypeError,KeyError,AttributeError,OverflowError,
            source.UntrustedInput,struct.error):
        print("P0 two-callsite r3 source ABSTAIN: source SHA, PPC or public unit gate failed. No private words, values or paths emitted.",file=sys.stderr)
        return 2
    print(json.dumps(report,sort_keys=True,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
