"""Source-gated PPC GPR-use classification for RPGolPlayer r31 +0x90 writer.

Read ONLY the original B0 source text, validated by #219 canonical B0 SHA.
Never emit full source instruction words, private runtime addresses, game data
or raw memory. This is a local opcode classification, not executed CFG proof.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import sys
import audit_p0_r31_local_cfg_private as parent
import audit_ball_xyz_source_callers_private as upstream

UNIT=parent.UNIT
START=parent.UNIT_START
RELATIVE_SITES=(0x1BE8,0x1BF4,0x1BFC,0x1C00,0x1C04,0x1C08,0x1C0C,0x1C10,0x1C14,0x1C18)
FIRST=START+RELATIVE_SITES[0]
LAST=START+RELATIVE_SITES[-1]
INT_LOADS=frozenset((32,34,40,42))
INT_LOADS_UPDATE=frozenset((33,35,41,43))
INT_STORE_UPDATE=frozenset((37,39,45))
FLOAT_LOAD_UPDATE=frozenset((49,51))
FLOAT_STORE_UPDATE=frozenset((53,55))
INT_REGISTER_TARGET=frozenset((7,8,12,13,14,15,32,34,40,42))
INT_RA_TARGET=frozenset((20,21,22,23,24,25,26,27,28,29))
NO_GPR_WRITE=frozenset((4,10,11,16,17,18,19,36,38,44,47,48,50,52,54,59,63))
XFORM_RA_WRITE=frozenset((28,60,124,284,316,444,476))
XFORM_RT_WRITE=frozenset((8,10,11,20,21,23,24,26,40,53,55,87,119,138,200,202,232,233,234,235,266,279,311,339,371,375,407,459,489,491,534,535,597,661,790,792,824,922,954))
XFORM_NO_GPR_WRITE=frozenset((0,4,32,54,86,144,150,210,246,278,310,342,370,438,439,470,467,512,566,598,854,918,982,1014))


def classify_gpr31(word:int)->dict:
    """A definite no-write is safe only for recognized PPC opcode families.

    Definite clobber means a GPR result is written, not its runtime value.
    Unknown means classification incomplete; never assume preserving.
    """
    if type(word) is not int or not 0<=word<=0xffffffff:
        raise ValueError("bad PPC word")
    op=word>>26
    rt=(word>>21)&31
    ra=(word>>16)&31
    rb=(word>>11)&31
    xo=(word>>1)&1023
    branch=parent._branch(0x802A0200,word)
    family=f"primary_{op}"
    writes=False
    unknown=False
    if op in NO_GPR_WRITE:
        family={10:"cmpli_compare",11:"cmpi_compare",16:"conditional_branch",
                18:"direct_branch",19:"condition_or_indirect",
                52:"stfs_float_store",59:"floating_single",
                63:"floating_double"}.get(op,"recognized_non_gpr_destination")
    elif op in INT_REGISTER_TARGET or op in INT_LOADS:
        family="gpr_rt_destination"
        writes=rt==31
    elif op in INT_RA_TARGET:
        family="gpr_ra_destination"
        writes=ra==31
    elif op in INT_LOADS_UPDATE:
        family="gpr_load_update_rt_and_ra"
        writes=rt==31 or ra==31
    elif op in INT_STORE_UPDATE or op in FLOAT_LOAD_UPDATE or op in FLOAT_STORE_UPDATE:
        family="update_form_ra_destination"
        writes=ra==31
    elif op==46:
        family="lmw_multi_register_load"
        writes=rt<=31  # lmw overwrites rT through r31
    elif op==31:
        if xo in XFORM_RA_WRITE:
            family="extended_ra_destination"
            writes=ra==31
        elif xo in XFORM_RT_WRITE:
            family="extended_rt_destination"
            writes=rt==31
        elif xo in XFORM_NO_GPR_WRITE:
            family="extended_no_gpr_destination"
        else:
            family="extended_unknown_gpr_effect"
            unknown=True
    else:
        family="unclassified_possible_gpr_effect"
        unknown=True
    # Link-register effects are not GPR r31 effects; calls can be followed
    # under the Wii PowerPC EABI nonvolatile convention only as an ASSUMPTION.
    return {
        "opcode_family":family,
        "primary_opcode":op,
        "extended_opcode_if_any":xo if op==31 else None,
        "r31_direct_instruction_write_confirmed":writes,
        "r31_gpr_write_possible_unknown":unknown,
        "branch_kind_if_recognized":branch[0] if branch else None,
        "callee_nonvolatile_r31_abi_assumption_needed":bool(branch and "call" in branch[0]),
    }


def analyze_window(data:bytes, start:int=FIRST)->dict:
    if type(data) is not bytes or type(start) is not int or start!=FIRST or len(data)!=(LAST-FIRST+4):
        raise ValueError("unexpected bounded original source code slice")
    if parent.analyze_window(data):
        pass  # Parent exact r3->r31 and +0x90 source site / CFG gates.
    sites=[]
    for off in RELATIVE_SITES:
        w=struct.unpack_from(">I",data,off-RELATIVE_SITES[0])[0]
        info=classify_gpr31(w)
        info["source_unit_offset"]=f"+0x{off:04X}"
        sites.append(info)
    target=sites[3]
    return {
        "kind":"S002-P0-R31-OPCODE-QUALIFIED-LOCAL-SLICE",
        "source_game":"RSPE01","disc_revision":1,
        "source_unit":UNIT,
        "copy_source_site":"+0x1BE8","store_source_site":"+0x1C18",
        "exact_copy_and_store_source_verified":True,
        "target_site":"+0x1C00",
        "target_opcode_family":target["opcode_family"],
        "target_r31_direct_write_confirmed":target["r31_direct_instruction_write_confirmed"],
        "target_r31_write_unknown":target["r31_gpr_write_possible_unknown"],
        "local_source_sites":sites,
        "static_abi_assumption_is_runtime_callee_proof":False,
        "source_receiver_is_selected_player_record_verified":False,
        "dynamic_store_execution_verified":False,
        "source_geometry_or_physical_xyz_verified":False,
        "velocity_power_contact_score_verified":False,
        "approved_for_training":False,"allowed_to_publish":False
    }


def audit(session:Path,data_root:Path)->dict:
    # Parent audits the identical original-B0 before these instructions.
    parent.audit(session,data_root)
    try:
        bank=upstream.checked_private_b0(session,data_root)
    except upstream.UntrustedInput:
        raise ValueError("B0 provenance not qualified") from None
    if not any(n==UNIT and lo==START and lo<=FIRST<LAST<hi
               for n,lo,hi in upstream.UNITS):
        raise ValueError("public source source-unit mismatch")
    with bank.open("rb") as fh:
        fh.seek(FIRST-upstream.MEM1_START)
        data=fh.read(LAST-FIRST+4)
    if len(data)!=LAST-FIRST+4:
        raise ValueError("source read short")
    try:
        upstream.checked_private_b0(session,data_root)
    except upstream.UntrustedInput:
        raise ValueError("B0 SHA changed") from None
    result=analyze_window(data)
    result["original_private_B0_SHA_verified_before_and_after"]=True
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    d=Path(__file__).resolve().parents[2]/"Wii-AI-Golf-Data"
    p.add_argument("--data-root",type=Path,default=d)
    p.add_argument("--private-session",type=Path)
    args=p.parse_args(argv)
    session=args.private_session or args.data_root/"ball-study-20261027-212633"
    try:
        out=audit(session,args.data_root)
    except (OSError,ValueError,TypeError,KeyError,OverflowError,AttributeError,ImportError,struct.error):
        print("P0 R31 OPCODE ABSTAINED: original SHA, PPC source or strict site gate failed; no private values/paths disclosed.",file=sys.stderr)
        return 2
    print(json.dumps(out,sort_keys=True,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
