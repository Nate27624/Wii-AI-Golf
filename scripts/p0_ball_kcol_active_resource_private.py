#!/usr/bin/env python3
"""Original Wii Golf Ball->KCol active resource identity audit (READ ONLY).

Starts from exactly SHA/scene/source-loop-qualified private seven-pair
RSPE01 Rev1 memory. Reuses all prior 5+7 Ball/KCol call, primitive+0x0E,
and narrowphase return-to-Ball gates.

1. Verify source r13-relative collision object pointer at Ball+0x0A80.
2. Recover r13 only from public-symbol __init_registers at 0x80006290,
   using original native lis+ori/addi register initialization syntax.
3. Follow ONLY the qualified r13 global to KCol+0x04/+0x08/+0x0C
   memory pointers, then compare the three active vector/prism arrays
   against the unique original 2498-prism terrain KCL's buffer contents.

Never infer a tree hit, a collision radius, class 13 = tree, velocity,
or active KCL ownership from source names. No runtime register guessing.
If register initialization cannot be established, report abstention.
Original bytes/addresses/XYZ stay on the operator's computer.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as seven
import p0_ball_kcol_prism_type_origin_private as upstream
import p0_tree_hitbox_source_callgraph_private as native
import p0_tree_hitbox_five_calls_private as decoder
import p0_tree_kcl_spatial_broadphase_private as broad

MEM1=0x80000000
INIT_REGISTERS=0x80006290  # Public Rev1 symbol map: __init_registers
MAX_INIT_WORDS=36
EXPECTED_GLOBAL_SITE=0x0A80
GLOBAL_DISP=-23160
EXPECTED_KCOL_FIELD_OFFSETS=(0x04,0x08,0x0C)
MAX_KCL_HEADERS=2


def signed16(x):
    return x-65536 if x&32768 else x


def recover_r13_base(read):
    """Return unique immediate r13 initializer from original symbol window.

    PPC EABI instruction forms:
      lis r13,hi  := addis r13,r0,hi
      ori r13,r13,lo OR addi r13,r13,signed(lo).
    Do not silently assume any SDA base if no intact initializer.
    """
    seen=[]
    for pc in range(INIT_REGISTERS,INIT_REGISTERS+4*MAX_INIT_WORDS,4):
        op=read(pc)
        if op==0x4E800020:
            break
        if (op>>26)!=15 or ((op>>21)&31)!=13 or ((op>>16)&31)!=0:
            continue
        high=op&0xFFFF
        for after in (4,8,12):
            nxt=read(pc+after)
            opc=nxt>>26
            rt=(nxt>>21)&31
            ra=(nxt>>16)&31
            low=nxt&0xFFFF
            if opc==24 and rt==13 and ra==13:
                seen.append(((high<<16)|low)&0xFFFFFFFF)
                break
            if opc==14 and rt==13 and ra==13:
                seen.append(((high<<16)+signed16(low))&0xFFFFFFFF)
                break
    if len(set(seen))!=1:
        return None
    base=seen[0]
    return base if MEM1<=base<MEM1+seven.roster.MEM1_SIZE else None


def valid_bank_slice(banks,address,size):
    """Bounds-safe view of the original banks; never emit pointer values."""
    kind=seven.roster._bank(address,size)
    if kind is None:
        return None
    i=0 if kind=="MEM1" else 1
    base=seven.roster.MEM1_BASE if i==0 else seven.roster.MEM2_BASE
    return memoryview(banks[i])[address-base:address-base+size]


def locate_exact_terrain_kcl(banks):
    """Locate the existing *unique* fully validated 2498 KCL, not an active one."""
    found=[]
    for i,bank in enumerate(banks):
        for prefix in broad.KCL_PREFIXES:
            mark=struct.pack(">I",prefix)
            start=-1
            while True:
                start=bank.find(mark,start+1)
                if start<0:
                    break
                if start%4:
                    continue
                parsed=broad.parse_candidate(bank,start)
                if parsed and parsed[1]==broad.EXPECTED_FLAGS:
                    found.append((i,start))
                    if len(found)>=MAX_KCL_HEADERS:
                        raise ValueError("Ambiguous qualified terrain KCL headers")
    if len(found)!=1:
        raise ValueError("Exact terrain KCL source candidate not unique")
    return found[0]


def resource_comparison(rd,banks,global_slot):
    if seven.roster._bank(global_slot,4)!="MEM1":
        raise ValueError("r13-relative global slot outside original MEM1")
    kcol=rd.u32(global_slot)
    if seven.roster._bank(kcol,0x60) is None:
        raise ValueError("Collision object global is not a captured pointer")
    pointers=tuple(rd.u32(kcol+off) for off in EXPECTED_KCOL_FIELD_OFFSETS)
    if any(seven.roster._bank(p,12) is None for p in pointers):
        raise ValueError("Collision source object vector/prism pointers absent")

    index,start=locate_exact_terrain_kcl(banks)
    bank=banks[index]
    po,no,pr,octo=struct.unpack_from(">4I",bank,start)
    sections=(start+po,start+no,start+pr+16)
    section_sizes=(no-po,(pr+16)-no,octo-(pr+16))
    src_base=seven.roster.MEM1_BASE if index==0 else seven.roster.MEM2_BASE
    source_addrs=tuple(src_base+p for p in sections)
    exact_ptr=[p==s for p,s in zip(pointers,source_addrs)]
    same_bytes=[]
    for pointer,section,sz in zip(pointers,sections,section_sizes):
        view=valid_bank_slice(banks,pointer,sz)
        same_bytes.append(
            view is not None and bytes(view)==bytes(memoryview(bank)[section:section+sz]))
    return {
        "global_pointer_is_captured":True,
        "active_kcol_object_bank":seven.roster._bank(kcol,0x60),
        "active_source_buffer_pointer_banks":[
            seven.roster._bank(p,12) for p in pointers],
        "unique_2498_terrain_candidate_found":True,
        "active_buffers_exact_address_equal_to_terrain_candidate":exact_ptr,
        "active_buffers_byte_equal_to_terrain_candidate":same_bytes,
        "all_three_active_buffers_match_terrain_candidate":all(same_bytes),
        "candidate_2498_prism_histogram_has_13":False,
        "class13_from_other_active_kcl_proven":False,
        "tree_specific_collision_proven":False,
        "training_approved":False,
    }


def inspect_source(read):
    prior=upstream.inspect(read,detail=False)
    if not (
        prior["original_source_gates_passed"]
        and prior["main_query_classification_from_prism_offset_0x0E"]
        and prior["narrowphase_classification_from_prism_offset_0x0E"]
    ):
        raise ValueError("Earlier exact KCol provenance not qualified")
    lo,hi=native.UNITS["Ball"]
    word=read(lo+EXPECTED_GLOBAL_SITE)
    if ((word>>26,(word>>21)&31,(word>>16)&31,signed16(word&65535))
            !=(32,27,13,GLOBAL_DISP)):
        raise ValueError("Native Ball global collision object load changed")
    return True


def run(archive:Path,capture:int,detail:bool):
    if capture not in range(1,8):
        raise ValueError("Only original seven source captures supported")
    folders=seven._check_archive(archive)
    with ExitStack() as stack:
        banks=[]
        for i,size in enumerate(seven.SIZE,1):
            p=seven.src._file(folders[capture],f"{capture}.{i}.raw",size)
            handle=stack.enter_context(p.open("rb"))
            banks.append(stack.enter_context(
                mmap.mmap(handle.fileno(),0,access=mmap.ACCESS_READ)))
        rd=seven.roster.TwoBankReader(*banks)
        field=seven._get(rd)["field"]
        count=rd.u32(field+0x1C)
        treeptr=rd.u32(field+0x20)
        if count!=94 or seven.roster._bank(treeptr,count*84)!="MEM2":
            raise ValueError("Original tree array provenance changed")

        def read(pc):
            if pc<MEM1 or pc+4>MEM1+len(banks[0]):
                raise ValueError("Original source code outside MEM1")
            return struct.unpack_from(">I",banks[0],pc-MEM1)[0]

        if not native.tree_loop_source_gated(read):
            raise ValueError("Original 94x84 FieldManager PPC changed")
        inspect_source(read)
        base=recover_r13_base(read)
        report={
            "kind":"P0_BALL_KCOL_GLOBAL_ACTIVE_RESOURCE_IDENTITY",
            "status":"REGISTER_BASE_RESOLVED" if base is not None
                     else "REGISTER_BASE_UNRESOLVED",
            "original_archive_sha_scene_and_84_stride_verified":True,
            "original_ball_kcol_5_plus_7_and_classification_gates":True,
            "public_rev1_init_registers_symbol_window_verified":True,
            "native_r13_base_recovered_from_init_registers":base is not None,
            "ball_global_slot_displacement_verified":GLOBAL_DISP,
            "capture":capture,"source_trees":94,
            "tree_hitbox_geometry_verified":False,
            "class13_tree_semantics_proven":False,
            "ball_velocity_semantics_proven":False,
            "training_approved":False,
        }
        if detail:
            report["local_init_code_source_relative_only"]=[
                f"__init_registers+0x{off:04X}  "
                f"{decoder.ppc(INIT_REGISTERS+off,read(INIT_REGISTERS+off))}"
                for off in range(0,4*MAX_INIT_WORDS,4)
            ]
        if base is not None:
            report.update(resource_comparison(rd,banks,base+GLOBAL_DISP))
            report["status"]="ACTIVE_KCOL_TERRAIN_BUFFER_COMPARISON"
    seven._check_archive(archive)
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--capture",type=int,choices=range(1,8),default=7)
    p.add_argument("--detail",action="store_true")
    a=p.parse_args(argv)
    try:
        report=run(a.archive,a.capture,a.detail)
        print(json.dumps(report,sort_keys=True,separators=(",",":"),allow_nan=False))
        return 0
    except (ValueError,OSError,IndexError,TypeError,OverflowError,
            AttributeError,KeyError,struct.error):
        print('{"status":"ABSTAIN_ACTIVE_KCOL_RESOURCE_IDENTITY",'
              '"training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
