"""Bounded minimap-ball EFFECT differential, not ball physics or score."""
from __future__ import annotations
from .landmark_control import observe_landmarks
from .physics_pointer_census import valid_mem,read_bytes
from .symbol_probe import STATIC

EFFECT_OFFSET=0x9C
EFFECT_BYTES=0x80

def observe_effect(rpc):
    anchors=observe_landmarks(rpc)  # validates rev1 game mode and landmarks
    root=rpc.call("memory.read_u32",[STATIC["golf_field"][0]])
    if not valid_mem(root,0xA8):raise RuntimeError("invalid field root")
    ptr=rpc.call("memory.read_u32",[root+EFFECT_OFFSET])
    raw=read_bytes(rpc,ptr,EFFECT_BYTES) if valid_mem(ptr,EFFECT_BYTES) else None
    return {"elapsed_s":None,"frame_start":anchors["frame_start"],
            "frame_end":anchors["frame_end"],"landmarks":anchors["landmarks"],
            "effect_present":raw is not None,"effect_pointer":ptr if raw else None,
            "effect_hex":raw.hex() if raw else None}

def summarize_effect(samples):
    previous=None;changed=0;present=0;nulls=0;pointer_transitions=0
    changed_offsets=set();seen=0
    for row in samples:
        raw=row.get("effect_hex")
        if raw is None:
            nulls+=1;previous=None;continue
        data=bytes.fromhex(raw)
        if len(data)!=EFFECT_BYTES:raise ValueError("unexpected effect size")
        present+=1
        if previous is not None:
            if row.get("effect_pointer")!=previous[0]:
                pointer_transitions+=1
            else:
                offsets=[i for i,(a,b) in enumerate(zip(previous[1],data)) if a!=b]
                if offsets:
                    changed+=1
                    changed_offsets.update(offsets)
        previous=(row.get("effect_pointer"),data);seen+=1
    return {"samples":len(samples),"effect_present":present,"effect_absent":nulls,
            "adjacent_changes":changed,"pointer_changes":pointer_transitions,
            "changed_byte_offsets":sorted(changed_offsets),
            "claim":"MINIMAP_VISUAL_EFFECT_NOT_VERIFIED_PHYSICS_BALL"}
