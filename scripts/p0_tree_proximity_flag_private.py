#!/usr/bin/env python3
"""Source-qualified tree proximity flag and model-pattern read-only audit.

Inspect exactly 94 original Wii Sports Golf tree records (0x54 bytes each),
original phase1/5/7 captures and native PPC calls to public symbol
PSVECSquareDistance. Summarize +0x48 flag, +0x4C unknown word, scale axis
uniformity and repeated mModel/mMapObj words. No private RAM pointers,
XYZ, model content, raw PPC code or potential physics numbers emitted.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
import json
import math
import mmap
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_seven_numbered_source_pairs_private as seven
import p0_tree_hitbox_source_callgraph_private as source

MEM1=0x80000000
COUNT=94
STRIDE=84
TREE=source.UNITS["Tree"][0]
BALL=source.UNITS["Ball"][0]
DISTANCE_FN=0x800E86D0 # public RSPE_r1.map.csv: PSVECSquareDistance
CAPTURES=(1,5,7)
MONITORED=("Tree","FieldManager","Ball","Simulation","GolfKCol")


def u32_to_float(word):
    return struct.unpack(">f",word.to_bytes(4,"big"))[0]


def fingerprint(read):
    """Strict source-native receiver+threshold+flag pattern, not behavioral proof."""
    checks={
        TREE+0x0020: 0x38630030, # r3=tree translation
        TREE+0x0034: 0xC002C5C0, # lfs f0, small-data threshold
        TREE+0x0038: 0xFC010040, # floating compare f1, f0
        TREE+0x0044: 0x981F0048, # stb flag,+0x48(r31)
    }
    if any(read(pc)!=expected for pc,expected in checks.items()):
        return False
    for site in (TREE+0x0030,BALL+0x0750,BALL+0x0760):
        target=source.direct_b(site,read(site))
        if target!=(DISTANCE_FN,True):
            return False
    return True


def inspect_records(u32, base, count, bank):
    if count!=COUNT or not bank(base,count*STRIDE,"MEM2"):
        raise ValueError("Tree source element count or bounds mismatch")
    flags=Counter()
    models=Counter()
    pmp=Counter()
    pairs=Counter()
    word4c=Counter()
    model4c_matching_translation_word=0
    scale_uniform=0
    scale_finite=0
    scale_ranges=[]
    word4c_finite_float=0
    word4c_finite_float_nontrivial=0
    word4c_pointer_like=Counter()
    trailing_flag_bits_nonzero=0
    for i in range(count):
        at=base+i*STRIDE
        a=u32(at+4)
        b=u32(at+8)
        models[a]+=1;pmp[b]+=1;pairs[(a,b)]+=1
        sc=tuple(u32_to_float(u32(at+0x3C+j*4)) for j in range(3))
        if all(math.isfinite(v) and abs(v)<10000 for v in sc):
            scale_finite+=1
            scale_ranges.extend(sc)
            if math.isclose(sc[0],sc[1],rel_tol=1e-5,abs_tol=1e-5) and math.isclose(
                sc[1],sc[2],rel_tol=1e-5,abs_tol=1e-5):
                scale_uniform+=1
        raw_flagword=u32(at+0x48)
        flags[(raw_flagword>>24)&0xFF]+=1
        trailing_flag_bits_nonzero+=int(bool(raw_flagword&0xFFFFFF))
        unknown=u32(at+0x4C)
        word4c[unknown]+=1
        for j in range(3):
            if unknown==u32(at+0x30+4*j):
                model4c_matching_translation_word+=1
                break
        value=u32_to_float(unknown)
        if math.isfinite(value):
            word4c_finite_float+=1
            if 1e-10<=abs(value)<=10000:
                word4c_finite_float_nontrivial+=1
        if unknown%4==0 and bank(unknown,4,"MEM1"):
            word4c_pointer_like["mem1"]+=1
        elif unknown%4==0 and bank(unknown,4,"MEM2"):
            word4c_pointer_like["mem2"]+=1
        else:
            word4c_pointer_like["not_qualified_ptr"]+=1
    return {
        "source_tree_count":count,
        "byte_0x48_flag_counts":{str(k):v for k,v in sorted(flags.items())},
        "byte_0x49_to_0x4B_any_nonzero_count":trailing_flag_bits_nonzero,
        "source_scale_finite_triplets":scale_finite,
        "source_scale_equal_xyz_within_float_tolerance":scale_uniform,
        "source_scale_min_max_over_all_axes":[round(min(scale_ranges),5),round(max(scale_ranges),5)]
            if scale_ranges else None,
        "model_word_distinct_count":len(models),
        "model_word_group_sizes":sorted(models.values(),reverse=True),
        "mapobj_word_distinct_count":len(pmp),
        "mapobj_word_group_sizes":sorted(pmp.values(),reverse=True),
        "model_mapobj_pair_distinct_count":len(pairs),
        "model_mapobj_pair_group_sizes":sorted(pairs.values(),reverse=True),
        "unknown_0x4c_distinct_raw_words":len(word4c),
        "unknown_0x4c_matches_any_inobject_translation_component":model4c_matching_translation_word,
        "unknown_0x4c_plausible_finite_f32_count":word4c_finite_float,
        "unknown_0x4c_nontrivial_finite_f32_count":word4c_finite_float_nontrivial,
        "unknown_0x4c_pointer_region_buckets":dict(sorted(word4c_pointer_like.items())),
        "native_tree_hitbox_verified":False,
        "flag_is_collision_or_visibility_proven":False,
        "training_approved":False,
    }


def potential_flag_consumers(read):
    """Syntax-only non-stack memory field loads, not source-owner proof."""
    result={}
    for unit in MONITORED:
        lo,hi=source.UNITS[unit]
        sites=[]
        for pc in range(lo,hi,4):
            w=read(pc)
            op=w>>26
            ofs=w&0xFFFF
            base=(w>>16)&31
            if base==1:
                continue
            if (op in (34,38,32,36) and ofs==0x48) or (
                    op in (32,36) and ofs==0x4C):
                if len(sites)<20:
                    sites.append({
                        "site":f"+0x{pc-lo:04X}",
                        "kind":{34:"lbz",38:"stb",32:"lwz",36:"stw"}[op],
                        "field":f"+0x{ofs:02X}",
                        "base_register":f"r{base}",
                    })
        result[unit]=sites
    return result


def run(archive, captures=CAPTURES):
    if tuple(captures)!=CAPTURES:
        raise ValueError("Only original 1/5/7 source cohort allowed")
    folders=seven._check_archive(archive)
    records=[]
    for capture in captures:
        with ExitStack() as stack:
            banks=[]
            for index,size in enumerate(seven.SIZE,1):
                p=seven.src._file(folders[capture],f"{capture}.{index}.raw",size)
                handle=stack.enter_context(p.open("rb"))
                banks.append(stack.enter_context(
                    mmap.mmap(handle.fileno(),0,access=mmap.ACCESS_READ)))
            rd=seven.roster.TwoBankReader(*banks)
            field=seven._get(rd)["field"]
            count=rd.u32(field+0x1C)
            base=rd.u32(field+0x20)
            if count!=COUNT or seven.roster._bank(base,COUNT*STRIDE)!="MEM2":
                raise ValueError("Tree source array or bounds unqualified")
            def word(pc):
                if not MEM1<=pc<=MEM1+len(banks[0])-4:
                    raise ValueError("Invalid native source PPC location")
                return struct.unpack_from(">I",banks[0],pc-MEM1)[0]
            if not source.tree_loop_source_gated(word) or not fingerprint(word):
                raise ValueError("Native tree proximity or loop fingerprint changed")
            def bank(ptr,length,name):
                return seven.roster._bank(ptr,length)==name
            report=inspect_records(rd.u32,base,count,bank)
            if capture==7:
                readers=potential_flag_consumers(word)
        records.append({"capture":capture,**report})
    seven._check_archive(archive)
    return {
        "kind":"P0_GOLF_SOURCE_TREE_PROXIMITY_FLAG",
        "status":"SOURCE_FLAG_AND_OBJECT_PATTERNS_READ_ONLY",
        "source_tree_position_field_offset":"0x30",
        "source_tree_proximity_flag_byte_offset":"0x48",
        "source_distance_function":"PSVECSquareDistance",
        "source_flag_threshold_numeric_value_verified":False,
        "source_flag_meaning_verified":False,
        "source_84_byte_tree_stride_verified":True,
        "captured_original_sha_scene_gated":True,
        "records":records,
        "candidate_flag_consumer_instructions":readers,
        "tree_hitbox_geometry_verified":False,
        "contact_response_verified":False,
        "training_approved":False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        print(json.dumps(run(args.archive),sort_keys=True,separators=(",",":")))
        return 0
    except (OSError,ValueError,IndexError,OverflowError,TypeError,
            AttributeError,KeyError,struct.error):
        print('{"status":"ABSTAIN_TREE_PROXIMITY_FLAG_SOURCE","training_approved":false}')
        return 2


if __name__=="__main__":
    raise SystemExit(main())
