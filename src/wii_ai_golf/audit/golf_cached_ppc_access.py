"""Offline Rev1 Wii Sports Golf PPC read/write atlas from the EXISTING MEM1 dump.

No extracted main.dol is needed: native MEM1 includes the game's cached code
at published PPC addresses. Decode source-unit D-form accesses only.
D-form r3/r30/r31 operands do NOT prove C++ "this", object ownership,
actual write sites in a live object, or field semantics. Never output code
bytes, private runtime pointers, executable binaries, or user file paths.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import json
import mmap
from pathlib import Path
import struct

MEM1_SIZE=0x1800000
BASE=0x80000000
UNITS={
    "RPGolMain":(0x8028E098,0x8028E900),
    "RPGolPlayer":(0x8029E62C,0x802A2210),
    "RPGolPlayerManager":(0x802A2210,0x802A3560),
}
D_FORM={
    32:("lwz","load",False),34:("lbz","load",False),
    36:("stw","store",False),38:("stb","store",False),
    40:("lhz","load",False),42:("lha","load",False),
    44:("sth","store",False),48:("lfs","load",True),
    50:("lfd","load",True),52:("stfs","store",True),
    54:("stfd","store",True),
}
MAX_OFF=0x1000
MAX_ROWS=72
MAX_SITES=4
OBJECT_REGS=frozenset((3,30,31))


def _sign16(value):
    return value-65536 if value&0x8000 else value


def analyze_cached_ppc(mem1,*,strict_size=True,max_rows=MAX_ROWS):
    if (not isinstance(mem1,(bytes,bytearray,mmap.mmap,memoryview))
            or strict_size and len(mem1)!=MEM1_SIZE
            or len(mem1)<0x802A3560-BASE
            or bytes(mem1[:8])!=b"RSPE01\x00\x01"
            or type(max_rows) is not int or not 1<=max_rows<=MAX_ROWS):
        raise ValueError("Expected Rev1 native cached MEM1 image")
    rows=[]
    meta={}
    counts=Counter()
    for unit,(start,stop) in UNITS.items():
        matches=defaultdict(lambda:{"load":0,"store":0,"float_load":0,
                                    "float_store":0,"mnemonics":Counter(),"pcs":[]})
        nonzero=0
        decoded_memops=0
        for pc in range(start,stop,4):
            instruction=struct.unpack_from(">I",mem1,pc-BASE)[0]
            nonzero+=int(instruction!=0)
            opcode=instruction>>26
            if opcode not in D_FORM:
                continue
            decoded_memops+=1
            mnemonic,kind,float_mode=D_FORM[opcode]
            base_reg=(instruction>>16)&31
            disp=_sign16(instruction&0xFFFF)
            if base_reg not in OBJECT_REGS or not 0<=disp<=MAX_OFF:
                continue
            record=matches[(base_reg,disp)]
            record[kind]+=1
            record["mnemonics"][mnemonic]+=1
            if float_mode:
                record["float_"+kind]+=1
            if len(record["pcs"])<MAX_SITES:
                record["pcs"].append(f"0x{pc:08X}")
        total=(stop-start)//4
        if nonzero<total//2 or decoded_memops<8:
            raise ValueError("Expected source-mapped cached code absent")
        meta[unit]={
            "code_unit_source_span":[f"0x{start:08X}",f"0x{stop:08X}"],
            "aligned_instructions_checked":total,
            "nonzero_code_words":nonzero,
            "decoded_d_form_memory_instructions":decoded_memops,
            "distinct_candidate_base_displacements":len(matches),
        }
        for (base_reg,disp),record in matches.items():
            counts[(unit,"float_stores")]+=record["float_store"]
            counts[(unit,"integer_stores")]+=record["store"]-record["float_store"]
            rows.append({
                "code_unit":unit,
                "base_register":f"r{base_reg}",
                "candidate_relative_offset":f"+0x{disp:03X}",
                "loads":record["load"],"stores":record["store"],
                "float_loads":record["float_load"],
                "float_stores":record["float_store"],
                "mnemonics":dict(sorted(record["mnemonics"].items())),
                "source_code_sites":record["pcs"],
                "receiver_this_pointer_verified":False,
                "writer_to_live_player_object_verified":False,
            })
    rows.sort(key=lambda x:(-x["float_stores"],-x["stores"],
                            -(x["loads"]+x["stores"]),x["code_unit"],
                            x["base_register"],x["candidate_relative_offset"]))
    return {
        "schema_version":1,
        "kind":"local-private-rev1-golf-cached-ppc-access-atlas",
        "source":"doldecomp/ogws config/RSPE01_01/splits.txt",
        "data_origin":"native_B0_cached_MEM1_no_main_dol_required",
        "game_id":"RSPE01","revision":1,
        "source_units":meta,
        "all_candidate_operand_rows":len(rows),
        "top_candidate_operand_rows":rows[:max_rows],
        "operand_rows_omitted":len(rows)-min(max_rows,len(rows)),
        "store_counts_by_source_unit":{
            name:{
                "float_store_in_candidate_reg_offsets":counts[(name,"float_stores")],
                "integer_store_in_candidate_reg_offsets":counts[(name,"integer_stores")],
            } for name in UNITS
        },
        "source_unit_not_proven_function":True,
        "receiver_register_not_proven_this":True,
        "raw_runtime_pointers_exported":False,
        "raw_executable_instructions_exported":False,
        "actual_field_semantics_verified":False,
        "swing_power_verified":False,
        "ball_xyz_velocity_verified":False,
        "allowed_to_publish":False,
        "next_action":"Review each candidate PPC instruction and register dataflow; "
                      "prove r3/r30/r31 ownership before a tiny same-frame "
                      "player/club watch. Never call these offsets power.",
    }


def audit_local_cached_mem1(path,*,private_root,output,max_rows=MAX_ROWS):
    root=Path(private_root).resolve(strict=True)
    p=Path(path)
    out=Path(output)
    if (not root.is_dir() or not p.is_file() or p.is_symlink()
            or not p.resolve(strict=True).is_relative_to(root)
            or p.stat().st_size!=MEM1_SIZE
            or out.exists() or out.is_symlink() or out.suffix.lower()!=".json"
            or out.parent.resolve(strict=True)!=root):
        raise ValueError("Invalid private cached code image or output")
    with open(p,"rb") as fp,mmap.mmap(fp.fileno(),0,access=mmap.ACCESS_READ) as raw:
        result=analyze_cached_ppc(raw,max_rows=max_rows)
    with out.open("x",encoding="utf-8") as dest:
        json.dump(result,dest,indent=2,sort_keys=True,allow_nan=False)
        dest.write("\n")
    return result
