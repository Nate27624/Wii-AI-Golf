"""Determine whether source-global ball is among four player-slot balls.

Uses source-gated seven-pair readers from #230, source-global PPC proof #240,
and public Rev1 roster stride #160. No data mining, Dolphin, dump or upload.
Also classifies bounded PPC r31 definitions in the two known writer callers.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

HERE=str(Path(__file__).resolve().parent)
if HERE in sys.path: sys.path.remove(HERE)
sys.path.insert(0,HERE)
import audit_p0_cache_global_receiver_private as prev

roster=prev.ROSTER
seven=prev.seven


def roster_global_membership(read, sample:dict, pointer:int) -> dict:
    pm=read(roster.PLAYER_MANAGER_STATIC_CANDIDATE)
    if roster._bank(pm, 4+4*roster.ROSTER_STRIDE) != "MEM2":
        raise ValueError("source player manager out of MEM2")
    slot=[]
    for index in range(roster.ROSTER_SLOTS):
        rec=pm+4+index*roster.ROSTER_STRIDE
        if roster._bank(rec,0x90)!="MEM2":
            raise ValueError("player record outside verified MEM2")
        child=read(rec+0x88)
        if roster._bank(child,0x1AC)!="MEM2":
            raise ValueError("one of four source player ball pointers missing")
        if read(child+0x4C)!=child+0x30:
            raise ValueError("player slot ball translation selfref missing")
        slot.append(child)
    if len(set(slot))!=4:
        raise ValueError("roster ball pointers are aliased")
    chosen=sample["selected_index"]
    if type(chosen) is not int or not 0<=chosen<4 or slot[chosen]!=sample["refs"]["ball"]:
        raise ValueError("source-selected roster child disagree")
    if type(pointer) is not int or roster._bank(pointer,0x50)!="MEM2":
        raise ValueError("source-global pointer untrusted")
    matches=[i for i,x in enumerate(slot) if x==pointer]
    return {
        "four_player_slot_ball_pointers_source_validated":True,
        "global_matches_any_player_slot":bool(matches),
        "global_matches_source_selected_slot":pointer==slot[chosen],
        "global_matches_an_inactive_player_slot":any(i!=chosen for i in matches),
        "global_matches_exactly_zero_player_slots":len(matches)==0,
        # Internal-only; compared across samples, NEVER included in public JSON.
        "_private_roster_ball_pointers":tuple(slot),
        # no source memory addresses or slot identities printed
    }


def _mr(word:int, destination:int, origin:int) -> bool:
    if type(word) is not int or not 0<=word<=0xffffffff:
        return False
    return (
        word>>26==31 and ((word>>1)&1023)==444
        and ((word>>16)&31)==destination
        and ((word>>21)&31)==origin
        and ((word>>11)&31)==origin
    )


def _r31_writer(word:int) -> str|None:
    d=prev.dform(word)
    if _mr(word,31,3): return "mr_r31_from_entry_r3_candidate"
    if d["op"] in (14,15,32,33,34,35,40,42,46) and d["rt"]==31:
        return "other_integer_assignment_r31"
    if d["op"]==31:
        # X-form potentially writes via RA, not all instruction forms do.
        if ((word>>16)&31)==31 and ((word>>1)&1023) in (444,266,40,28,60,316,24):
            return "other_X_form_assignment_r31"
    return None


def trace_r31_inputs(read) -> list[dict]:
    out=[]
    for name,pc,entry in prev.CALLS:
        if prev.branch_target(pc,read(pc))!=(prev.CACHE_WRITER_ENTRY,True):
            raise ValueError("PPC function call target changed")
        if entry>=pc or (pc-entry)>0x200:
            raise ValueError("source caller bounds changed")
        defs=[]
        branch_before_assignment=False
        branch_seen=False
        for address in range(entry,pc,4):
            word=read(address)
            if word>>26 in (16,18,17) or (
                word>>26==19 and ((word>>1)&1023) in (16,528)):
                branch_seen=True
            assignment=_r31_writer(word)
            if assignment is not None:
                if not defs and branch_seen:
                    branch_before_assignment=True
                defs.append((address,assignment))
        first=defs[0][1] if defs else "no_supported_r31_assignment"
        late=[x[1] for x in defs[1:]]
        out.append({
            "source_caller":name,
            "exact_callsite_to_cache_writer":True,
            "first_observed_r31_assignment_class":first,
            "first_assignment_after_branch_hazard":branch_before_assignment,
            "later_supported_r31_assignment_count":len(late),
            "r31_from_entry_r3_unambiguous_linear_candidate":(
                first=="mr_r31_from_entry_r3_candidate" and not late
                and not branch_before_assignment and not branch_seen
            ),
            "source_call_can_prove_runtime_receiver":False,
        })
    return out


def summarize(samples:dict[int,dict], code:dict[int,dict], caller:list[dict]) -> dict:
    if set(samples)!=set(range(1,8)) or set(code)!=set(range(1,8)):
        raise ValueError("exact 7 source selected samples required")
    for a,b in ((1,2),(5,6),(6,7),(5,7)):
        if samples[a]["selected_index"]!=samples[b]["selected_index"] or samples[a]["hole"]!=samples[b]["hole"]:
            raise ValueError("within shot actor/hole changed")
        if any(samples[a]["refs"][key]!=samples[b]["refs"][key] for key in ("ball","pin","start","scene_field")):
            raise ValueError("within shot source identity changed")
    # A same-numbered player slot alone does not establish the same four
    # roster actors or reference frame across any two captures.
    for i in range(1, 8):
        roster_ids=code[i].get("_private_roster_ball_pointers")
        selectors=code[i].get("_private_config_selectors")
        if (type(roster_ids) is not tuple or len(roster_ids)!=4
                or len(set(roster_ids))!=4
                or type(selectors) is not tuple or len(selectors)!=3
                or any(type(x) is not int for x in selectors)):
            raise ValueError("complete source roster/config reference required")
        if type(code[i].get("_private_global_source_slot")) is not int:
            raise ValueError("exact global small-data source slot unavailable")
        for label in ("source_selected_pin","source_current_start"):
            v=samples[i].get("triplets",{}).get(label)
            if type(v) is not tuple or len(v)!=3 or any(type(x) is not int for x in v):
                raise ValueError("source pin/start vector incomplete")
    if len({code[i]["_private_global_source_slot"] for i in range(1,8)})!=1:
        raise ValueError("PPC global source r13 displacement drift")
    for a,b in ((1,2),(5,6),(6,7),(5,7)):
        if code[a]["_private_roster_ball_pointers"] != code[b]["_private_roster_ball_pointers"]:
            raise ValueError("four player-slot child ball objects changed")
        if code[a]["_private_config_selectors"]!=code[b]["_private_config_selectors"]:
            raise ValueError("Config selector changed across provisional shot pair")
        for label in ("source_selected_pin","source_current_start"):
            if samples[a]["triplets"][label]!=samples[b]["triplets"][label]:
                raise ValueError("source pin/start vector changed across provisional shot pair")
    rows=[dict(phase=i,**{k:v for k,v in code[i].items() if not k.startswith("_private_")})
          for i in range(1,8)]
    source_is_outside_all_four=all(code[i]["global_matches_exactly_zero_player_slots"] for i in (5,6,7))
    return {
        "kind":"P0-SANITIZED-GLOBAL-BALL-VERSUS-FOUR-ROSTER-AND-R31-SOURCE",
        "source_validated_seven_snapshots":7,
        "original_fourteen_bank_manifest_verified_by_this_extension":False,
        "human_phase_order_and_same_shot_independently_verified":False,
        "crossphase_roster_pin_start_config_and_source_slot_consistent":True,
        "per_phase_global_roster_pointer_identity":rows,
        "wedge_source_global_outside_all_four_roster_balls":source_is_outside_all_four,
        "two_cache_writer_call_r31_source_classification":caller,
        "global_source_independent_of_four_player_slots_for_all_wedge_phases":source_is_outside_all_four,
        "global_source_is_simulation_endpoint_verified":False,
        "r31_runtime_receiver_verified":False,
        "cache_writer_runtime_execution_verified":False,
        "frame_atomicity_verified":False,
        "real_ball_world_xyz_verified":False,
        "velocity_power_contact_score_verified":False,
        "training_approved":False,
        "allowed_to_publish":False,
    }


def run(directory:Path) -> dict:
    directory=seven._private_directory(directory)
    pairs={p:seven._phase_banks(directory,p) for p in range(1,8)}
    if any(v is None for v in pairs.values()):
        raise ValueError("seven native pairs required")
    samples={}
    code={}
    callers=None
    for phase in range(1,8):
        pair=pairs[phase]
        before={bank:seven._hash(path) for bank,path in pair.items()}
        with ExitStack() as stack:
            mem={}
            for bank,path in pair.items():
                fp=stack.enter_context(path.open("rb"))
                mem[bank]=stack.enter_context(mmap.mmap(fp.fileno(),0,access=mmap.ACCESS_READ))
            read=roster.TwoBankReader(mem["MEM1"],mem["MEM2"]).u32
            samples[phase]=seven._source_sample(mem["MEM1"],mem["MEM2"])
            config=read(roster.GOLF_CONFIG_STATIC)
            if roster._bank(config,0xC8)!="MEM2":
                raise ValueError("source golf Config out of native MEM2")
            selectors=tuple(read(config+off) for off in (0xBC,0xC0,0xC4))
            source=prev.source_global_slot(read)
            if not source["static_source_global_slot_supported"]:
                raise ValueError("PPC global r13 load must be verified")
            glob=prev.sample_runtime(read,samples[phase],source)
            code[phase]=roster_global_membership(
                read,samples[phase],glob["_private_runtime_source_global_pointer"])
            code[phase]["_private_config_selectors"]=selectors
            code[phase]["_private_global_source_slot"]=source["slot"]
            phase_callers=trace_r31_inputs(read)
            if callers is not None and phase_callers!=callers:
                raise ValueError("PPC cache caller/r31 candidate changed between phases")
            callers=phase_callers
        for bank,path in pair.items():
            if seven._hash(path)!=before[bank]:
                raise ValueError("bank changed during offline read")
    return summarize(samples,code,callers)


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dump-directory",required=True,type=Path)
    a=p.parse_args(argv)
    try:
        report=run(a.dump_directory)
    except (OSError,ValueError,TypeError,KeyError,OverflowError,AttributeError):
        print("P0 GLOBAL BALL ROSTER RECEIVER ABSTAIN: source owner,"
              " four-player roster, PPC flow or input bank gate failed.",
              file=sys.stderr)
        return 2
    print(json.dumps(report,sort_keys=True,indent=2,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
