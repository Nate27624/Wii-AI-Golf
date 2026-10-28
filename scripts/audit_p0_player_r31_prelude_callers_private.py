"""Original B0 SHA-qualified, read-only PPC preceding-return and direct BL candidate map.

A BL to a PC immediately following blr is a FUNCTION-ENTRY HYPOTHESIS,
not proof of typed receiver, dynamic execution or real object ownership.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import sys
import audit_ball_xyz_source_callers_private as src
import audit_p0_r31_qualified_local_paths_private as prior

BACK=0xC0
MAX_ENTRIES=8
MAX_ROWS=16
COPY=prior.COPY
END=prior.STORE
START=prior.START


def candidate_after_blr(chunk:bytes,start:int):
    if type(chunk) is not bytes or type(start) is not int or start!=COPY-BACK or len(chunk)!=BACK+4:
        raise ValueError("invalid source prelude")
    sites=[start+i+4 for i in range(0,len(chunk)-4,4)
           if struct.unpack_from(">I",chunk,i)[0]==0x4E800020]
    return tuple(sorted(sites,reverse=True)[:MAX_ENTRIES])


def bl_target(pc:int,word:int):
    if type(pc) is not int or type(word) is not int or pc%4 or not 0<=word<=0xffffffff:
        raise ValueError("invalid PPC word")
    if word>>26!=18 or word&1!=1:
        return None
    disp=word&0x03fffffc
    if disp&0x02000000:disp-=0x04000000
    return (disp if word&2 else pc+disp)&0xffffffff


def scan(units,reader,targets):
    if type(units) is not tuple or type(targets) is not tuple or not targets or len(set(targets))!=len(targets):
        raise ValueError("unqualified source code units")
    matched={t:[] for t in targets}
    counts={t:0 for t in targets}
    scanned=0
    for lo,hi,name in units:
        if not name.startswith("Pack/RPSports/RPGolScene/"):
            continue
        block=reader(lo,hi)
        if type(block) is not bytes or len(block)!=hi-lo or len(block)%4:
            raise ValueError("bad source unit")
        scanned+=1
        for i in range(0,len(block),4):
            dest=bl_target(lo+i,struct.unpack_from(">I",block,i)[0])
            if dest in matched:
                counts[dest]+=1
                if len(matched[dest])<MAX_ROWS:
                    matched[dest].append({"source_file":name,
                                          "relative_BL_site":f"+0x{i:05X}"})
    return scanned,[{"candidate_post_return_pc_relative":f"+0x{t-START:04X}",
                     "direct_Golf_BL_count":counts[t],
                     "bounded_source_calls":matched[t],
                     "omitted_calls":max(0,counts[t]-MAX_ROWS),
                     "entry_function_boundary_proven":False,
                     "incoming_r3_selected_player_record_verified":False}
                    for t in targets]


def audit(session:Path,data_root:Path):
    prior.audit(session,data_root)
    bank=src.checked_private_b0(session,data_root)
    units=src.load_public_text_units()
    matches=[n for lo,hi,n in units if lo<=COPY-BACK and END+4<=hi]
    if len(matches)!=1 or matches[0]!="Pack/RPSports/RPGolScene/RPGolPlayer.cpp":
        raise ValueError("public source owner drift")
    with bank.open("rb") as fh:
        fh.seek(COPY-BACK-src.MEM1_START)
        buf=fh.read(BACK+4)
        candidates=candidate_after_blr(buf,COPY-BACK)
        if not candidates:
            raise ValueError("no bounded exact plain-blr candidate")
        def reader(lo,hi):
            if lo<src.MEM1_START or hi>src.MEM1_START+src.MEM1_LEN:
                raise ValueError("source interval out of MEM1")
            fh.seek(lo-src.MEM1_START)
            return fh.read(hi-lo)
        count,rows=scan(units,reader,candidates)
    if src.checked_private_b0(session,data_root)!=bank:
        raise ValueError("B0 modified")
    return {"kind":"S002-P0-R31-POSTRETURN-DIRECT-GOLF-BL-CANDIDATES",
            "source_game":"RSPE01","revision":1,
            "copy_site":"+0x1BE8","store_site":"+0x1C18",
            "source_lookback_bytes":BACK,
            "original_B0_SHA_verified_before_after":True,
            "public_832_split_index_verified":len(units)==832,
            "Golf_public_source_units_scanned":count,
            "entry_hypotheses":rows,
            "caller_prologue_or_full_cfg_verified":False,
            "indirect_virtual_callers_complete":False,
            "r3_is_selected_player_record_verified":False,
            "r31_store_executed_in_shot_verified":False,
            "physical_xyz_velocity_power_verified":False,
            "approved_for_training":False,"allowed_to_publish":False}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    d=Path(__file__).resolve().parents[2]/"Wii-AI-Golf-Data"
    p.add_argument("--data-root",type=Path,default=d)
    p.add_argument("--private-session",type=Path)
    x=p.parse_args(argv)
    try:
        report=audit(x.private_session or x.data_root/"ball-study-20261027-212633",x.data_root)
    except (OSError,ValueError,TypeError,KeyError,AttributeError,OverflowError,struct.error,src.UntrustedInput):
        print("P0 r31 entry-xref ABSTAIN: canonical B0/PPC/public owner gate failed. No private source disclosed.",file=sys.stderr)
        return 2
    print(json.dumps(report,sort_keys=True,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
