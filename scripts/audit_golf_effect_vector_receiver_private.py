"""Rev1 narrow PPC source receiver trace for two observed field triplet sites.

Uses the SAME immutable private B0 banks/manifest/selected-record source gates
as the broader S002 effect-writer audit. Inspect only code PCs from three
publicly mapped RPGol compilation units. No memory data/pointers or uploads.

Do not infer RPSysEffect member types or runtime effect-window ownership from
matching C++ field offsets. This scanner is static, not CFG/ABI decompilation.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
from pathlib import Path
import sys

SCRIPTS = str(Path(__file__).resolve().parent)
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import audit_golf_effect_source_writers_private as effect
import audit_golf_two_bank_roster_private as roster
import audit_golf_aim_ppc_context_private as context
import audit_golf_aim_ppc_offsets_private as offsets
import audit_selected_ball_start_link_private as selected
import audit_selected_ball_four_phase_private as four


# Code addresses and instruction words from the operator's REAL source scan.
FIELD_SITES = {
    # Real operator B0 source inspection established r29 <- r31 inside the
    # loop and r29 += 4 after BOTH alternate three-float stores.
    # This is pointer-table-like iteration, NOT the manager's this pointer.
    0x80290E4C: 0x7FFDFB78,  # mr r29,r31
    0x80290E74: 0x480128E5,  # BL math helper at 0x802A3758
    0x80290E78: 0x807D0004,  # lwz r3,+0x04(r29)
    0x80290E7C: 0xC0010010,  # lfs f0,+0x10(r1)
    0x80290E80: 0xD0030078,  # stfs f0,+0x78(r3)
    0x80290E84: 0xC0010014,
    0x80290E88: 0xD003007C,
    0x80290E8C: 0xC0010018,
    0x80290E90: 0xD0030080,
    0x80290E98: 0x807D0004,  # alternate path same child pointer load
    0x80290E9C: 0xC001001C,
    0x80290EA0: 0xD0030078,
    0x80290EA4: 0xC0010020,
    0x80290EA8: 0xD003007C,
    0x80290EAC: 0xC0010024,
    0x80290EB0: 0xD0030080,
    0x80290EB4: 0x3B9C0001,  # addi r28,r28,1
    0x80290EB8: 0x3BBD0004,  # addi r29,r29,4 (next word in pointer walk)
}
BALL_SITES = {
    # Previous method ends 0x802977C4 blr, next starts at 0x802977C8.
    0x802977C8: 0x9421FFF0,  # stwu r1,-0x10(r1)
    0x802977D8: 0x7C7F1B78,  # mr r31,r3 (save incoming receiver)
    0x802977FC: 0x88030050,  # lbz r0,+0x50(r3)
    0x8029780C: 0x9883005C,  # stb r4,+0x5C(r3)
    0x80297810: 0xD0030078,  # stfs f0,+0x78(r3)
    0x80297814: 0xD003007C,
    0x80297818: 0xD0030080,
    0x8029781C: 0xD00301A0,
    0x80297820: 0xD00301A4,
    0x80297824: 0xD00301A8,
}

FOCI = (
    ("field_triplet_from_child", "RPGolFieldManager.cpp",
     0x80290E80, 0x80290CD0, 0x80290EC0, FIELD_SITES),
    ("ball_triplet_reset", "RPGolMapObjBall.cpp",
     0x80297810, 0x802976D0, 0x80297854, BALL_SITES),
)


def _candidate_prologue(word: int) -> bool:
    # PPC stwu r1,-N(r1). May be a function prologue; not proof of entry.
    return (word >> 26 == 37 and
            ((word >> 21) & 31) == 1 and
            ((word >> 16) & 31) == 1 and
            bool(word & 0x8000))


def analyze(read_word) -> dict:
    results = []
    for name, unit, center, start, end, sites in FOCI:
        bound_start, bound_end = effect.TEXT_UNITS[unit]
        if not (bound_start <= start <= center < end <= bound_end
                and not ((start | center | end) & 3)
                and end-start <= 0x240):
            raise ValueError("Unbounded source focus")
        for pc, expected in sites.items():
            if not start <= pc < end or read_word(pc) != expected:
                raise ValueError("Source focus instruction signature mismatch")
        # Search only this bounded neighborhood for possible function
        # prologues and the literal r29 = incoming r3 pattern.
        candidates = []
        saved_arg = []
        for pc in range(start, center, 4):
            word = read_word(pc)
            if _candidate_prologue(word):
                candidates.append(f"0x{pc:08X}")
            if word == 0x7C7D1B78:
                saved_arg.append(f"0x{pc:08X}")
        lines = []
        # Print the first 128 code bytes of context closest to the site.
        for pc in range(max(start, center-0x80), min(end,center+0x3C),4):
            word=read_word(pc)
            lines.append({
                "pc":f"0x{pc:08X}",
                "word":f"0x{word:08X}",
                "approximate_asm":context.decode(word,pc)
            })
        results.append({
            "code_focus":name,
            "source_unit":unit,
            "center_pc":f"0x{center:08X}",
            "source_signature_verified":True,
            "possible_prologue_pcs_not_cfg_verified":candidates,
            "r29_preserved_from_r3_literal_pcs":saved_arg,
            "exact_receiver_chain":(
                "0x80290E4C mr r29,r31; +4(r29) loads child pointer in both alternatives; after stfs triplet, 0x80290EB8 addi r29,r29,4"
                if name=="field_triplet_from_child" else
                "0x802977C8 method-shaped entry; 0x802977D8 mr r31,r3; incoming r3 directly used in conditional 2x3 stfs triplets"
            ),
            "field_r29_from_r31_before_loop_static_verified": name=="field_triplet_from_child",
            "field_pointer_table_like_word_stride_4_static_verified": name=="field_triplet_from_child",
            "field_two_alternative_child_vector_stores_static_verified": name=="field_triplet_from_child",
            "ball_method_shaped_entry_static_verified": name=="ball_triplet_reset",
            "ball_incoming_r3_saved_to_r31_static_verified": name=="ball_triplet_reset",
            "ball_direct_receiver_conditional_float_reset_static_verified": name=="ball_triplet_reset",
            "field_r31_origin_proven":False,
            "field_effect_object_pointer_proven":False,
            "ball_effect_object_pointer_proven":False,
            "ball_source_selected_runtime_instance_verified":False,
            "minimap_effect_object_receiver_verified":False,
            "float_triplet_store_source_verified":True,
            "active_ball_object_receiver_verified":False,
            "function_boundary_proven":False,
            "source_context":lines,
        })
    return {
        "kind":"S002-Rev1-two-vector-write-source-receiver-narrow-audit",
        "game":"RSPE01 Rev1",
        "source_foci":results,
        "public_header_fieldmanager_effect_offsets":{
            "mMapPlayerEff":"+0x094",
            "mMapShotLineEff":"+0x098",
            "mMapBallEff":"+0x09C",
        },
        "public_header_fieldmanager_offsets":{
            "mMapTreesObj":"+0x078", "mShowGreenSlope":"+0x07C",
        },
        "public_header_not_independent_runtime_identity_proof":True,
        "RPSysEffect_field_078_07C_type_proven":False,
        "float_triplet_store_is_minimap_effect_writer_proven":False,
        "receiver_identity_static_vs_runtime_distinguished":True,
        "physical_ball_XYZ_verified":False,
        "training_allowed":False,
        "allowed_to_publish":False
    }


def run_local(folder:Path)->dict:
    source=effect.offsets.run_local(folder)
    if source.get("source_selected_record_snapshot_gated") is not True:
        raise ValueError("Selected golfer source gate missing")
    root=selected.DATA_ROOT.resolve(strict=True)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Private checkpoint missing")
    folder=folder.resolve(strict=True)
    if folder==root or not folder.is_relative_to(root):
        raise ValueError("Private checkpoint outside approved data root")
    manifest=four._validate_manifest(folder)
    files={k:four._approved_bank(folder,f"B0-{k}.bin",
        roster.MEM1_SIZE if k=="MEM1" else roster.MEM2_SIZE)
        for k in ("MEM1","MEM2")}
    if any(four._hash(file)!=manifest["B0"]["sha256"][key]
           for key,file in files.items()):
        raise ValueError("B0 bank SHA mismatch")
    with ExitStack() as stack:
        maps=[]
        for file in files.values():
            f=stack.enter_context(file.open("rb"))
            maps.append(stack.enter_context(
                mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)))
        reader=roster.TwoBankReader(*maps)
        return analyze(reader.u32)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        print(json.dumps(run_local(args.private_root),indent=2,sort_keys=True))
    except (OSError,ValueError,TypeError,KeyError,OverflowError) as exc:
        print("Targeted effect source receiver audit failed closed: "+
              type(exc).__name__,file=sys.stderr)
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
