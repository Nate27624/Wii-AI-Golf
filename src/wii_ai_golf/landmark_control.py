"""Source-gated pin/start/cup map-object world-position control. No ball claims."""
from __future__ import annotations
import math
import struct
from .focused_object_xyz import preflight
from .physics_pointer_census import valid_mem, read_bytes
from .symbol_probe import STATIC

OFFSETS={"pin":0x44,"start":0x50,"cup":0x54}
TRANSLATION=0x30

def observe_landmarks(rpc):
    preflight(rpc)  # verify RSPE01 rev1 and Hitting the Green mode
    first=rpc.call("frame.get_count")
    root=rpc.call("memory.read_u32",[STATIC["golf_field"][0]])
    if not valid_mem(root,0xA8):
        raise RuntimeError("invalid live golf-field manager")
    result={}
    for name,offset in OFFSETS.items():
        ptr=rpc.call("memory.read_u32",[root+offset])
        if not valid_mem(ptr,TRANSLATION+12):
            result[name]=None
            continue
        xyz=struct.unpack(">fff",read_bytes(rpc,ptr+TRANSLATION,12))
        result[name]=[round(x,6) for x in xyz] if all(math.isfinite(x) and abs(x)<100000 for x in xyz) else None
    last=rpc.call("frame.get_count")
    if type(first) is not int or type(last) is not int or last<first:
        raise ValueError("invalid frame bracket")
    return {"frame_start":first,"frame_end":last,"frame_span":last-first,"landmarks":result}

def summarize_landmarks(samples,threshold=0.1):
    if threshold<=0:raise ValueError("threshold must be positive")
    stats={}
    for name in OFFSETS:
        count=0;moves=0;maximum=0.;previous=None
        for row in samples:
            xyz=row["landmarks"].get(name)
            if xyz is None:
                previous=None;continue
            count+=1
            if previous is not None:
                delta=math.dist(previous,xyz)
                maximum=max(maximum,delta)
                moves+=delta>=threshold
            previous=xyz
        stats[name]={"present":count,"moving_steps":moves,"max_adjacent_step_units":round(maximum,5)}
    return {"samples":len(samples),"landmarks":stats,
            "claim":"SOURCE_DOCUMENTED_MAP_OBJECT_TRANSLATIONS_NOT_BALL_COORDINATES"}
