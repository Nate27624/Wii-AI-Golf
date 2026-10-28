"""Offline Rev1 FieldManager +0x44/+0x50 store-site register provenance.

Public **source-relative** PPC decoding ONLY: never raw code words, raw
numeric game data, heap pointers, float values or private hashes in output.
Nearest linear definition is NOT SSA/call-graph or executed receiver proof.
Requires upstream #223 independently SHA-gated B0 and flight banks FIRST.
No Dolphin, bridge, inputs, network, file writes or model training.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_inflight_vs_b0_private as audit
import audit_golf_two_bank_roster_private as roster

UNIT_LO, UNIT_HI = 0x80290B44, 0x80294184
GETTERS = (
    (0x802922A8, 0x44),
    (0x802922AC, 0x4C),
    (0x802922EC, 0x50),
    (0x802922F0, 0x4C),
)
# Source-relative offsets identified by the operator's exact Rev1
# published RPGolFieldManager.cpp direct stw displacement scan.
CANDIDATES = (
    (0x2CCC, 0x50, 5, 3),
    (0x2CF0, 0x50, 0, 5),
    (0x2D14, 0x44, 4, 3),
    (0x2EA8, 0x50, 4, 31),
    (0x2ECC, 0x50, 0, 4),
    (0x2EF4, 0x44, 4, 31),
)
CONTEXT_WINDOWS = ((0x2C80, 0x2D24), (0x2E70, 0x2F04))
MAX_PREVIOUS_BYTES = 0xC0


def source_offset(pc: int) -> str:
    if not UNIT_LO <= pc < UNIT_HI or pc % 4:
        raise ValueError("source PC out of published unit")
    return f"+0x{pc - UNIT_LO:04X}"


def instr_u32(source_unit: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(source_unit) or offset % 4:
        raise ValueError("source instruction range invalid")
    return struct.unpack_from(">I", source_unit, offset)[0]


def _signed(x: int) -> int:
    return x - 0x10000 if x & 0x8000 else x


def decode(word: int) -> dict:
    """Instruction sketch, not a complete PPC disassembler/control-flow proof."""
    if type(word) is not int or not 0 <= word <= 0xffffffff:
        raise ValueError("invalid PPC word")
    op = word >> 26
    s, a, b = (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31
    imm = word & 0xffff
    row = {"kind": "other", "defines": None, "branch": False}
    if op in (32, 33, 34, 35, 40, 42, 48, 50):
        name = {32:"lwz",33:"lwzu",34:"lbz",35:"lbzu",40:"lhz",
                42:"lha",48:"lfs",50:"lfd"}[op]
        return dict(row, kind=f"{name} r{s}, signed_offset(r{a})", defines=s)
    if op in (36, 37, 38, 39, 44, 46, 52, 54):
        name={36:"stw",37:"stwu",38:"stb",39:"stbu",44:"sth",
              46:"lmw",52:"stfs",54:"stfd"}[op]
        return dict(row,kind=f"{name} r{s}, signed_offset(r{a})")
    if op in (14, 15):
        name="addi" if op == 14 else "addis"
        return dict(row,kind=f"{name} r{s}, r{a}, signed_imm",defines=s)
    if op in (24, 25, 26, 27, 28, 29):
        names={24:"ori",25:"oris",26:"xori",27:"xoris",28:"andi.",29:"andis."}
        return dict(row,kind=f"{names[op]} r{a}, r{s}, imm",defines=a)
    if op in (20, 21, 23):
        names={20:"rlwimi",21:"rlwinm",23:"rlwnm"}
        return dict(row,kind=f"{names[op]} r{a}, r{s}, ...",defines=a)
    if op == 18:
        return dict(row,kind="bl" if word & 1 else "b",branch=True)
    if op == 16:
        return dict(row,kind="bcl" if word & 1 else "bc",branch=True)
    if op == 19:
        xo=(word >> 1) & 1023
        return dict(row,kind={16:"bclr",528:"bcctr"}.get(xo,f"op19_xo{xo}"),
                    branch=xo in (16,528))
    if op == 31:
        xo=(word >> 1) & 1023
        if xo == 444:
            return dict(row,kind=(f"mr r{a}, r{s}" if s==b else
                                  f"or r{a}, r{s}, r{b}"),defines=a)
        if xo in (266, 40, 28, 0, 24):
            names={266:"add",40:"subf",28:"and",0:"cmp",24:"slw"}
            return dict(row,kind=f"{names[xo]} r{s}, r{a}, r{b}",
                        defines=s if xo!=0 else None)
        if xo in (339, 371):
            return dict(row,kind=("mfspr" if xo==339 else "mftb")+f" r{s}",
                        defines=s)
        return dict(row,kind=f"op31_xo{xo} regs({s},{a},{b})")
    return row


def store_fields(word: int) -> tuple[int,int,int] | None:
    if word >> 26 != 36:
        return None
    return word & 0xffff, (word >> 21) & 31, (word >> 16) & 31


def verify_source(b0: bytes, airborne: bytes) -> bytes:
    needed=UNIT_HI-UNIT_LO
    if len(b0)!=needed or len(airborne)!=needed or b0!=airborne:
        raise ValueError("source unit missing or differs between phases")
    for pc,disp in GETTERS:
        word=instr_u32(b0,pc-UNIT_LO)
        expected=(32<<26)|(3<<21)|(3<<16)|disp
        if word!=expected:
            raise ValueError("exact Rev1 getter source assertion failed")
    for offset,disp,value,base in CANDIDATES:
        if store_fields(instr_u32(b0,offset))!=(disp,value,base):
            raise ValueError("exact expected Rev1 write candidate changed")
    return b0


def prior_definition(unit: bytes, site_offset: int, register: int) -> dict:
    """Nearest linear definition, never across a previous LR/CTR branch boundary.

    In the real Rev1 source +0x2C80 is a bclr (likely prior function return)
    and +0x2C84 starts a new stack-frame prologue. An earlier unrelated
    arithmetic definition at +0x2C4C MUST NOT be attributed to the new r3
    receiver. Conditional branches within the remaining range are recorded
    as hazards; a recognized definition is still not a dataflow proof.
    """
    begin=max(0,site_offset-MAX_PREVIOUS_BYTES)
    boundary=None
    for o in range(site_offset-4,begin-1,-4):
        name=decode(instr_u32(unit,o))["kind"]
        if name in ("bclr","bcctr"):
            boundary=o
            begin=o+4
            break
    found=None
    for o in range(site_offset-4, begin-1,-4):
        item=decode(instr_u32(unit,o))
        if item["defines"]==register:
            found=(o,item)
            break
    basis=begin if found is None else found[0]+4
    result={
        "nearest_linear_definition_found":found is not None,
        "bounded_window_crosses_branch":any(
            decode(instr_u32(unit,o))["branch"]
            for o in range(basis,site_offset,4)),
        "preceding_lr_or_ctr_boundary_found":boundary is not None,
        "not_proven_register_receiver_identity":True,
    }
    if boundary is not None:
        result["source_relative_boundary"]=source_offset(UNIT_LO+boundary)
    if found is not None:
        o,item=found
        result["source_relative_pc"]=source_offset(UNIT_LO+o)
        result["operation"]=item["kind"]
    return result


def report(unit: bytes) -> dict:
    verify_source(unit,unit)
    selected=[]
    for offset,disp,value,base in CANDIDATES:
        selected.append({
            "source_relative_pc":source_offset(UNIT_LO+offset),
            "member_offset":f"+0x{disp:02X}",
            "value_register":f"r{value}",
            "base_register":f"r{base}",
            "base_nearest_prior_definition":prior_definition(unit,offset,base),
            "value_nearest_prior_definition":prior_definition(unit,offset,value),
            "source_receiver_proven_field_manager":False,
            "executed_during_airborne_proven":False,
        })
    context=[]
    for lo,hi in CONTEXT_WINDOWS:
        for off in range(lo,hi,4):
            ins=decode(instr_u32(unit,off))
            context.append({
                "source_relative_pc":source_offset(UNIT_LO+off),
                "instruction_class":ins["kind"],
                "defines_register":None if ins["defines"] is None else
                    f"r{ins['defines']}",
                "has_branch_control_flow":ins["branch"],
            })
    return {
        "kind":"S002-REV1-FIELDMANAGER-PIN-START-STORE-PROVENANCE",
        "schema_version":1,
        "game_id":"RSPE01", "revision":1,
        "source_revisions_equal_b0_vs_airborne":True,
        "exact_getter_and_six_store_opcodes_verified":True,
        "candidate_site_count":len(selected),
        "candidate_sites":selected,
        "bounded_context_rows":context,
        "operator_attested_mem1_mem2_same_paused_frame":True,
        "machine_frame_index_independently_verified":False,
        "one_boot_across_b0_airborne_verified":False,
        "pin_object_lifecycle_explained":False,
        "dynamic_ball_xyz_verified":False,
        "power_ram_verified":False,
        "training_approved":False,
        "allowed_to_publish":False,
        "note":("Source-byte static decode only, not dynamic executed writer or "
                "receiver proof; nearest prior definition can cross branches "
                "and indirect callees, so requires full PPC dataflow review."),
    }


def run_local(baseline:Path,flight:Path) -> dict:
    # Use all native game/layout/scene/player/selected-ball + original
    # both-bank SHA gates before accepting source-only bytes.
    qualified=audit.run_local(baseline,flight)
    if (qualified.get("source_gated_both_snapshots") is not True or
            qualified.get("selected_slot_and_hole_match") is not True):
        raise ValueError("source owner identities did not qualify")
    private_root=audit.selected.DATA_ROOT.resolve(strict=True)
    b0=audit._under_data(baseline,private_root)
    f=audit._under_data(flight,private_root)
    with ExitStack() as stack:
        source=[]
        for folder,name in ((b0,"B0-MEM1.bin"),(f,"mem1.raw")):
            stream=stack.enter_context(audit._file(
                folder,name,roster.MEM1_SIZE).open("rb"))
            mp=stack.enter_context(mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ))
            source.append(mp[UNIT_LO-roster.MEM1_BASE:UNIT_HI-roster.MEM1_BASE])
        verify_source(*source)
        return report(source[0])


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline",type=Path,required=True)
    p.add_argument("--flight",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        out=run_local(args.baseline,args.flight)
    except (ValueError,OSError,KeyError,TypeError,OverflowError,struct.error):
        print("P0 source provenance ABSTAIN: private SHA, source scene or exact PPC instructions failed.",file=sys.stderr)
        return 2
    print(json.dumps(out,indent=2,sort_keys=True,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
