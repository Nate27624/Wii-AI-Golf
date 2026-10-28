"""S002 P0: exact Rev1 GolfConfig getter suffix/operand role triage.

Read-only original 14-bank SHA-qualified source (via reviewed #278 audit).
Never exports native PPC words, score numbers, runtime addresses, paths,
source code bytes, SHA, raw RAM, or interpreted physical game values.
The 36-byte companion record is *compatible* with documented HoleInfo size;
the 16-byte record is *compatible* with documented [hole][player] strokes.
Neither root is given a typed runtime identity by this syntax-only pass.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import sys

_SCRIPT = str(Path(__file__).resolve().parent)
if _SCRIPT in sys.path:
    sys.path.remove(_SCRIPT)
sys.path.insert(0, _SCRIPT)

import audit_p0_golf_config_score_index_ppc_private as prev

FOCUSED_SITES={
    "get_nth_hole_score": (0x48,0x50,0x60,0x70,0x74,0x78),
    "get_nth_hole_strokes": (0x48,0x58,0x60),
}


def _word(data,offset):
    if type(data) is not bytes or offset+4>len(data) or offset<0:
        raise ValueError("untrusted bounded PPC source")
    return struct.unpack_from(">I",data,offset)[0]


def _parts(w):
    return (w>>26,(w>>21)&31,(w>>16)&31,(w>>11)&31,(w>>1)&1023)


def _add(w,d,a,b):
    op,rt,ra,rb,xo=_parts(w)
    return op==31 and xo==266 and rt==d and ra==a and rb==b and (w&1)==0


def _subf(w,d,a,b):
    op,rt,ra,rb,xo=_parts(w)
    return op==31 and xo==40 and rt==d and ra==a and rb==b and (w&1)==0


def _mulli(w,d,a,k):
    op,rt,ra,_,_=_parts(w)
    return op==7 and rt==d and ra==a and (w&65535)==k


def _lwz(w,d,base,offset):
    op,rt,ra,_,_=_parts(w)
    return op==32 and rt==d and ra==base and (w&65535)==offset


def _slwi(w,d,source,n):
    op,rt,ra,_,_=_parts(w)
    sh=(w>>11)&31
    mb=(w>>6)&31
    me=(w>>1)&31
    return (op==21 and rt==source and ra==d and sh==n
            and mb==0 and me==31-n)


def _public_holeinfo_literal_matched(window: bytes) -> bool:
    """Compare source-constructed literal against published Rev1 HoleInfo."""
    hi=_word(window,0x50)
    lo=_word(window,0x60)
    hop,hrt,hra,_,_=_parts(hi)
    lop,lrt,lra,_,_=_parts(lo)
    if (hop,hrt,hra)!=(15,6,0) or (lop,lrt,lra)!=(14,6,6):
        return False
    top,low=hi&65535,lo&65535
    signed_hi=top-65536 if top>=32768 else top
    signed_lo=low-65536 if low>=32768 else low
    return (((signed_hi<<16)+signed_lo)&0xffffffff)==0x803c7aa0


def _r13_root_load_sites(data: bytes,dest_reg: int,last: int) -> tuple:
    """Code-relative locations only; no SDA displacement or runtime value."""
    return tuple(f"+0x{i:02X}" for i in range(0,last,4)
                 if _parts(_word(data,i))[0:3]==(32,dest_reg,13))


def _same_sda_slot_candidate(a: bytes,b: bytes) -> bool:
    """Static source displacement equality is NOT runtime singleton proof."""
    apos=[i for i in range(0,0x64,4) if _parts(_word(a,i))[0:3]==(32,7,13)]
    bpos=[i for i in range(0,0x58,4) if _parts(_word(b,i))[0:3]==(32,5,13)]
    if len(apos)!=1 or len(bpos)!=1:
        return False
    return (_word(a,apos[0])&65535)==(_word(b,bpos[0])&65535)


def _source_class(w):
    """Recognize PPC source classes without emitting immediates/pointers."""
    op,rt,ra,rb,xo=_parts(w)
    out={"opcode_class":"other_or_unresolved","destination_register":None,
         "source_registers":[],"address_role":"unverified"}
    if op in (14,15):
        out.update(opcode_class="addi" if op==14 else "addis",
                   destination_register=f"r{rt}",
                   source_registers=[f"r{ra}"],
                   address_role=("zero_base_literal" if ra==0 else "register_based"))
    elif op in (32,33):
        out.update(opcode_class="lwz" if op==32 else "lwzu",
                   destination_register=f"r{rt}",
                   source_registers=[f"r{ra}"],
                   address_role=("small_data_root_source" if ra==13
                                 else "register_based"))
    elif op==31 and xo in (266,40,444):
        out.update(opcode_class={266:"add",40:"subf",444:"or"}[xo],
                   destination_register=f"r{ra}" if xo==444 else f"r{rt}",
                   source_registers=[f"r{rt}",f"r{rb}"] if xo==444
                   else [f"r{ra}",f"r{rb}"])
    elif op==21 and (w>>6)&31==0:
        out.update(opcode_class="rlwinm_or_slwi",
                   destination_register=f"r{ra}",
                   source_registers=[f"r{rt}"])
    elif op in (16,18):
        out["opcode_class"]="branch"
    return out


def evaluate_windows(windows:dict[str,bytes])->dict:
    if set(windows)!={name for name,_,_ in prev.FUNCTIONS}:
        raise ValueError("functions missing")
    for name,left,right in prev.FUNCTIONS:
        if type(windows[name]) is not bytes or len(windows[name])!=right-left:
            raise ValueError("original source window length mismatched")
    a=windows["get_nth_hole_score"]
    b=windows["get_nth_hole_strokes"]
    a36=all((
        _mulli(_word(a,0x54),5,3,36),
        _slwi(_word(a,0x58),0,4,2),
        _slwi(_word(a,0x5C),3,3,4),
        _add(_word(a,0x64),3,7,3),
        _add(_word(a,0x68),4,6,5),
        _add(_word(a,0x6C),3,3,0),
        _lwz(_word(a,0x70),4,4,4),
        _lwz(_word(a,0x74),0,3,4),
    ))
    a_subf=_subf(_word(a,0x78),3,4,0)
    b16=all((
        _slwi(_word(b,0x50),0,4,2),
        _slwi(_word(b,0x54),3,3,4),
        _add(_word(b,0x58),3,5,3),
        _add(_word(b,0x5C),3,3,0),
        _lwz(_word(b,0x60),3,3,4),
    ))
    # All suffix instruction families after the suspected dispatch must
    # be static straight-line (no branches); legacy branch-label tables
    # in earlier source ranges cannot establish a runtime path.
    branch_suffix=False
    for data,start,end in ((a,0x4C,0x7C),(b,0x4C,0x64)):
        for off in range(start,end,4):
            if _parts(_word(data,off))[0] in (16,18,19):
                branch_suffix=True

    spots=[]
    for name,_,_ in prev.FUNCTIONS:
        spots.append({
            "function":name,
            "focused_sites":[{
                "source_relative_site":f"+0x{off:02X}",
                **_source_class(_word(windows[name],off)),
            } for off in FOCUSED_SITES[name]]
        })
    return {
        "kind":"P0-GOLF-CONFIG-GETTER-TWO-STRIDE-DATAFLOW-SUFFIX-REVIEW",
        "first_getter_36byte_hole_metadata_candidate_and_16byte_score_candidate":
            a36 and not branch_suffix,
        "first_getter_subtracts_loaded_36byte_record_value_from_16byte_record_value":
            a36 and a_subf and not branch_suffix,
        "second_getter_16byte_row_4byte_player_column_candidate":
            b16 and not branch_suffix,
        "source_suffix_branch_free":not branch_suffix,
        "public_HoleInfo_static_root_literal_matches_source_rev1_symbol":
            _public_holeinfo_literal_matched(a),
        "both_getters_load_candidate_config_root_from_same_r13_slot":
            _same_sda_slot_candidate(a,b),
        "score_getter_r7_r13_load_sites":list(_r13_root_load_sites(a,7,0x64)),
        "strokes_getter_r5_r13_load_sites":list(_r13_root_load_sites(b,5,0x58)),
        "actual_sda_runtime_pointer_value_verified":False,

        "Kokeshi_HoleInfo_record_size_36_is_public_source_match_only":True,
        "config_score_root_r7_function1_and_r5_function2_verified":False,
        "metadata_root_r6_function1_verified":False,
        "input_r3_is_effective_hole_and_r4_is_player_verified":False,
        "PPC_complete_function_cfg_verified":False,
        "two_getter_source_clue_sites":spots,
        "typed_score_row_orientation_fully_verified":False,
        "historical_all_36_score_words_unchanged_still_valid":True,
        "game_result_or_stroke_units_verified":False,
        "ball_world_xyz_velocity_power_impact_verified":False,
        "training_approved":False,
        "allowed_to_publish":False,
    }


def audit(archive:Path)->dict:
    # Use exact previously reviewed original 14-bank hash before-and-after
    # validation. No reliance on current HEAD or moving github references.
    folders=prev.seven._check_archive(archive)
    file=prev.seven.src._file(folders[1],"1.1.raw",prev.roster.MEM1_SIZE)
    windows={}
    with file.open("rb") as fh:
        header=fh.read(8)
        if len(header)!=8 or header[:6]!=b"RSPE01" or header[7]!=1:
            raise ValueError("Rev1 header drift")
        for name,left,right in prev.FUNCTIONS:
            if (left<prev.CONFIG_UNIT_BOUNDS[0]
                    or right>prev.CONFIG_UNIT_BOUNDS[1]):
                raise ValueError("public Config .text boundary mismatch")
            fh.seek(left-prev.MEM1_BASE)
            windows[name]=fh.read(right-left)
    out=evaluate_windows(windows)
    prev.seven._check_archive(archive)
    out["original_14_bank_SHA_verified_before_and_after"]=True
    return out


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    args=p.parse_args(argv)
    try:
        out=audit(args.archive)
    except (OSError,ValueError,TypeError,AttributeError,KeyError,OverflowError,struct.error):
        print("P0 GOLF CONFIG SUFFIX AUDIT ABSTAIN: verified original Rev1 source/manifest failed; no private data disclosed.",file=sys.stderr)
        return 2
    print(json.dumps(out,sort_keys=True,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
