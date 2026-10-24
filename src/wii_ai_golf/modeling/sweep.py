"""Predeclared offline swing calibration trial manifests; NO game actions."""
from __future__ import annotations
from dataclasses import asdict
import random
from .swing import AXES, SwingProfile, swing_trace, trace_hash

def make_sweep(*,stage:str,scenarios:list[str],seed:int=42,confirmed_axis:str|None=None)->dict:
    if stage not in ("recognition","calibration"):
        raise ValueError("unrecognized sweep stage")
    if type(seed) is not int or seed<0:
        raise ValueError("seed must be nonnegative int")
    if not scenarios or any(not isinstance(s,str) or not s.strip() for s in scenarios) or len(set(scenarios))!=len(scenarios):
        raise ValueError("nonempty distinct scenario IDs required")
    if stage=="recognition" and len(scenarios)!=1:
        raise ValueError("recognition requires one at-ball scenario")
    if stage=="calibration" and (len(scenarios)!=2 or confirmed_axis not in AXES):
        raise ValueError("calibration requires two distinct scenarios and a confirmed axis")
    rng=random.Random(seed)
    trials=[]
    def add(phase,scenario,profile,rep):
        trace=swing_trace(profile)
        trials.append({
            "trial_id":f"S003-{len(trials)+1:03d}","phase":phase,"scenario_id":scenario,
            "repetition":rep,"profile":asdict(profile),"trace_sha256":trace_hash(trace),
            "frames":len(trace),"outcome":None})
    if stage=="recognition":
        for rep in range(1,3):
            axes=list(AXES);rng.shuffle(axes)
            for axis in axes:
                add("find_ball_contact",scenarios[0],SwingProfile(axis=axis),rep)
    else:
        base=SwingProfile(axis=confirmed_axis)
        factors=[
            ("speed","speed_m_s",[1.2,2.0,2.8,3.5,4.3,5.0],3),
            ("travel","travel_m",[0.3,0.6,0.9],3),
            ("timing","downswing_frames",[12,20,28],3),
            ("angle","angle_rad",[-0.25,-0.125,0.0,0.125,0.25],3),
            ("reference",None,[None],10),
        ]
        for phase,key,values,repeats in factors:
            for rep in range(1,repeats+1):
                choices=[(scenario,v) for scenario in scenarios for v in values]
                rng.shuffle(choices)
                for scenario,v in choices:
                    p=base if key is None else base.with_changes(**{key:v})
                    add(phase,scenario,p,rep)
    return {
        "schema_version":1,"study_id":"S003-SWING-CALIBRATION",
        "source":"offline-proposed-profile-manifest; NOT real Wii Sports results",
        "stage":stage,"seed":seed,"scenarios":scenarios,
        "confirmed_axis":confirmed_axis if stage=="calibration" else None,
        "trial_count":len(trials),"requires_first_ball_savestate":True,
        "requires_per_trial_human_hit_and_score_confirmation":True,
        "execution":"manual gated one trial at a time; NEVER run blindly",
        "stop_rule":"recognition: stop after 12 with no contact; calibration: stop on nondeterministic reset or invalid outcomes",
        "trials":trials
    }
