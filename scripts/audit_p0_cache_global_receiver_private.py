"""Source-gated source-global-ball and cache receiver PROVENANCE, not physics.

Novel scope relative to #183/#219/#236:
1) Exact PPC load-site check for fn_80299C70's source-global ball object.
2) Runtime compare of that global object's identity and translation to
   source-selected player-owned ball/CC at seven already captured phases.
3) Bounded static input-r3 def classification at the TWO documented callers.
Never prints private source instructions, runtime addresses, pointer values,
float bits, bank hashes or file paths. No emulator, game input, writes or uploads.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import mmap
import re
from pathlib import Path
import sys

_HERE = str(Path(__file__).resolve().parent)
if _HERE in sys.path:
    sys.path.remove(_HERE)
sys.path.insert(0, _HERE)
import audit_p0_seven_source_trajectory_private as seven

ROSTER = seven.ROSTER
R13_ANCHOR_PC = 0x80299EE4
GLOBAL_LOAD_PC = 0x80299CD0
TRANSLATION_FOLLOW_PC = 0x80299CD4
RECEIVER_SAVE_PC = 0x80299C90
CACHE_WRITER_ENTRY = 0x80299C70
CALLS = (
    ("ball_local_fn_80299ACC", 0x80299B64, 0x80299ACC),
    ("ball_local_fn_80299C20", 0x80299C58, 0x80299C20),
)
# PPC constant r13 derived using source-confirmed FieldManager singleton
# at -23320(r13) from fn_80299C70 and known public Rev1 small-data slot.
SDA_BASE = ROSTER.GOLF_FIELD_STATIC + 23320
SDA_OFFSET_FIELD = -23320
PHASES = tuple(range(1, 8))
SHOTS = ((1, 2), (5, 6), (6, 7), (5, 7))


def _sign16(v: int) -> int:
    return v - 0x10000 if v & 0x8000 else v


def dform(word: int) -> dict:
    if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
        raise ValueError("not a PPC instruction word")
    return {
        "op": (word >> 26) & 63,
        "rt": (word >> 21) & 31,
        "ra": (word >> 16) & 31,
        "imm": _sign16(word & 65535),
    }


def _mr_source(word: int) -> int | None:
    # or rA,rS,rB with identical rS and rB = mr rA,rS.
    if word >> 26 != 31 or (word >> 1) & 1023 != 444:
        return None
    rs = (word >> 21) & 31
    ra = (word >> 16) & 31
    rb = (word >> 11) & 31
    return rs if ra == 3 and rb == rs else None


def _origin_for_r3(word: int) -> str | None:
    d = dform(word)
    if d["op"] in (14, 15, 32, 33, 34, 35, 40, 42, 46):
        if d["rt"] != 3:
            return None
        if d["op"] == 32:
            return f"lwz_from_r{d['ra']}"
        if d["op"] == 14:
            return f"addi_from_r{d['ra']}"
        if d["op"] == 15:
            return f"addis_from_r{d['ra']}"
        return "other_integer_load_into_r3"
    if d["op"] == 31:
        src = _mr_source(word)
        if src is not None:
            return f"mr_from_r{src}"
        if (word >> 16) & 31 == 3:
            return "other_X_form_possible_r3_write"
    return None


def branch_target(pc: int, word: int) -> tuple[int,bool] | None:
    if word >> 26 != 18:
        return None
    imm = word & 0x03FFFFFC
    if imm & 0x02000000:
        imm -= 0x04000000
    target = (imm if word & 2 else pc + imm) & 0xFFFFFFFF
    return target,bool(word & 1)


def caller_input_probe(read_u32) -> list[dict]:
    """Static linear window only, never asserts an executed receiver identity."""
    result = []
    for name,pc,entry in CALLS:
        # Source-boundary gate: exact bl cache routine, expected enclosing caller.
        branch = branch_target(pc,read_u32(pc))
        if branch != (CACHE_WRITER_ENTRY,True):
            raise ValueError("caller does not directly link to known cache writer")
        lower=max(pc-0x40,entry)
        defs=[]
        branch_hazard=False
        for addr in range(lower,pc,4):
            word=read_u32(addr)
            op=word >> 26
            if op in (16,18,17) or (op == 19 and (word >> 1) & 1023 in (16,528)):
                branch_hazard=True
            candidate=_origin_for_r3(word)
            if candidate is not None:
                defs.append((addr,candidate))
        last=defs[-1][1] if defs else "no_supported_r3_definition"
        result.append({
            "known_source_caller_function":name,
            "exact_bl_to_cache_writer_entry":True,
            "nearest_bounded_r3_definition_class":last,
            "bounded_pre_call_control_transfer_present":branch_hazard,
            "nearest_definition_not_global_control_flow_proof":True,
            "runtime_r3_receiver_resolved":False,
            "r27_receiver_is_current_selected_ball_proven":False,
        })
    return result


def source_global_slot(read_u32) -> dict:
    """Strict static PPC anchor + lwz + translation-follow verification.

    If fn_80299CD0 is NOT an r13-relative lwz into r3, don't guess an
    alternate source address; return a categorical abstention.
    """
    anchor=dform(read_u32(R13_ANCHOR_PC))
    if (anchor["op"],anchor["rt"],anchor["ra"],anchor["imm"]) != (32,3,13,SDA_OFFSET_FIELD):
        raise ValueError("source PPC FieldManager small-data anchor changed")
    # Source builder #183 established r3 = other object's +0x4C pointee
    follow=dform(read_u32(TRANSLATION_FOLLOW_PC))
    if (follow["op"],follow["rt"],follow["ra"],follow["imm"]) != (32,3,3,0x4C):
        raise ValueError("source global translation follow absent")
    save=read_u32(RECEIVER_SAVE_PC)
    # Exact PPC mr r27,r3 from #183; do not reinterpret as runtime object.
    rs=(save >> 21)&31
    ra=(save >> 16)&31
    rb=(save >> 11)&31
    if not (save >> 26 == 31 and ((save >> 1)&1023) == 444
            and (rs,ra,rb)==(3,27,3)):
        raise ValueError("fn_80299C70 no longer saves receiver r3 to r27")
    load=dform(read_u32(GLOBAL_LOAD_PC))
    if (load["op"],load["rt"],load["ra"]) != (32,3,13):
        return {
            "global_load_type":"unsupported_not_direct_lwz_r3_disp_r13",
            "static_source_global_slot_supported":False,
            "slot":None,
        }
    slot=SDA_BASE+load["imm"]
    if ROSTER._bank(slot) != "MEM1":
        raise ValueError("global source slot outside native MEM1")
    return {
        "global_load_type":"lwz_r3_disp_r13_then_lwz_r3_0x4c_r3",
        "static_source_global_slot_supported":True,
        "slot":slot,
    }


def _eq(a,b):
    if len(a) != 3 or len(b) != 3:
        raise ValueError("expected two source triples")
    return sum(x==y for x,y in zip(a,b))


def sample_runtime(read_u32, source_snapshot:dict, code:dict) -> dict:
    if not code["static_source_global_slot_supported"]:
        return {"supported":False,"reason":"no_supported_r13_global_load_pattern"}
    ptr=read_u32(code["slot"])
    if ROSTER._bank(ptr,0x50) != "MEM2":
        raise ValueError("global ball pointer invalid or not in native MEM2")
    nested=read_u32(ptr+0x4C)
    if nested != ptr+0x30 or ROSTER._bank(nested,12) != "MEM2":
        raise ValueError("global ball object lacks Rev1 translation selfref")
    global_vec=tuple(read_u32(nested+4*i) for i in range(3))
    rec=source_snapshot["triplets"]
    selected=source_snapshot["refs"]["ball"]
    return {
        "supported":True,
        "source_global_is_source_selected_ball_object":ptr==selected,
        "global_current_equals_selected_current_components":
            _eq(global_vec,rec["ball_nested_plus_0x4c"]),
        "global_current_equals_selected_cache_CC_components":
            _eq(global_vec,rec["ball_cache_0x0cc"]),
        "global_current_equals_source_START_components":
            _eq(global_vec,rec["source_current_start"]),
        # Private state returned internally only. Removed before public output.
        "_private_runtime_source_global_pointer":ptr,
        "_private_runtime_global_current_words":global_vec,
    }


def summarize(samples, codes, callers) -> dict:
    if set(samples)!=set(PHASES) or set(codes)!=set(PHASES):
        raise ValueError("seven phases required")
    for a,b in SHOTS:
        x,y=samples[a],samples[b]
        if x["selected_index"]!=y["selected_index"] or x["hole"]!=y["hole"]:
            raise ValueError("player slot or hole changed in same-shot pair")
        if any(x["refs"][name]!=y["refs"][name] for name in
               ("scene_field","ball","pin","start")):
            raise ValueError("source object pointers changed in same-shot pair")
        if any(x["triplets"][name]!=y["triplets"][name] for name in
               ("source_selected_pin","source_current_start")):
            raise ValueError("pin or start vector changed in same-shot pair")
        if x["config_selector_words"]!=y["config_selector_words"]:
            raise ValueError("GolfConfig selectors changed in same-shot pair")
    # Verified source code should remain immutable across all phases.
    signature=[(c["global_load_type"],c["static_source_global_slot_supported"]) for c in codes.values()]
    if len(set(signature))!=1:
        raise ValueError("PPC global source dataflow changed between snapshots")
    rows=[]
    for phase in PHASES:
        s=samples[phase]
        data=codes[phase]["runtime"]
        row={"phase":phase}
        for key in ("supported","source_global_is_source_selected_ball_object",
                    "global_current_equals_selected_current_components",
                    "global_current_equals_selected_cache_CC_components",
                    "global_current_equals_source_START_components"):
            if key in data:
                row[key]=data[key]
        rows.append(row)
    global_identity_stable = (all(c["runtime"].get("supported") is True for c in codes.values())
            and len({codes[i]["runtime"]["_private_runtime_source_global_pointer"] for i in (5,6,7)})==1)
    return {
        "kind":"P0-SANITIZED-SEVEN-GLOBAL-BALL-AND-CACHE-RECEIVER-SOURCE-AUDIT",
        "phase_count":7,
        "canonical_archive_sha_verified":True,
        "within_shot_pin_start_config_stability_verified":True,
        "source_pcc_anchor_confirmed":True,
        "source_global_load_type":codes[1]["global_load_type"],
        "source_global_pointer_resolution_supported":codes[1]["static_source_global_slot_supported"],
        "source_global_ball_pointer_stable_W5_to_W7":global_identity_stable,
        "per_phase_source_global_vs_selected_ball_and_cache":rows,
        "static_cache_writer_call_sites":callers,
        "cache_writer_receiver_saved_from_r3_into_r27_source_verified":True,
        "cache_writer_runtime_receiver_equals_selected_ball_verified":False,
        "cache_writer_executed_in_human_wedge_phases_verified":False,
        "cache_writer_global_source_runtime_identity_inferred_from_r13_only":True,
        "global_source_semantics_as_predicted_ball_verified":False,
        "same_guest_frame_MEM1_MEM2_verified":False,
        "actual_ball_world_xyz_verified":False,
        "ball_velocity_verified":False,
        "score_power_contact_verified":False,
        "training_approved":False,
        "allowed_to_publish":False,
    }


def _canonical_archive_sha(directory: Path) -> dict[int, dict[str, bytes]]:
    """Require #231's original numbered-capture manifest and all 14 SHA256.

    This is a narrow input-identity adapter to #230's existing source reader,
    not a competing reader or a new capture schema. Never emit digests/paths.
    """
    root = seven.source.selected.DATA_ROOT.resolve(strict=True)
    capture_root = (root / "captures").resolve(strict=True)
    if directory.parent != capture_root:
        raise ValueError("only canonical ignored private capture archives permitted")
    manifest_path = directory / "manifest-PRIVATE.json"
    if (manifest_path.is_symlink() or not manifest_path.is_file()
            or manifest_path.stat().st_size > 65536):
        raise ValueError("missing or invalid canonical archive manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if (type(manifest) is not dict
            or manifest.get("kind") != "p0-private-numbered-capture-inventory"
            or manifest.get("training_approved") is not False
            or manifest.get("human_phase_file_mapping_verified") is not False
            or type(manifest.get("capture_count")) is not int
            or manifest["capture_count"] != 7
            or manifest.get("capture_numbers") != list(PHASES)
            or not isinstance(manifest.get("captures"), list)
            or len(manifest["captures"]) != 7):
        raise ValueError("noncanonical seven-shot identity or false safety claim")

    expected = {}
    for item in manifest["captures"]:
        if type(item) is not dict:
            raise ValueError("invalid capture descriptor")
        phase = item.get("capture_number")
        if type(phase) is not int or phase not in PHASES or phase in expected:
            raise ValueError("duplicate or invalid capture phase")
        descs = item.get("banks")
        if not isinstance(descs, list) or len(descs) != 2:
            raise ValueError("incomplete bank manifest")
        expected[phase] = {}
        for index, (bank, size) in enumerate(
                (("MEM1", seven.MEM1_SIZE), ("MEM2", seven.MEM2_SIZE)), 1):
            desc = descs[index - 1]
            filename = f"{phase}.{index}.raw"
            if (type(desc) is not dict or desc.get("file") != filename
                    or desc.get("bank") != bank or desc.get("bytes") != size
                    or desc.get("copy_verified") is not True):
                raise ValueError("bank identity or archive copy verification mismatch")
            digest = desc.get("sha256")
            if type(digest) is not str or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
                raise ValueError("invalid preserved bank digest")
            path = directory / filename
            if (path.is_symlink() or not path.is_file()
                    or path.stat().st_size != size):
                raise ValueError("bank missing, linked, or incorrect length")
            expected[phase][bank] = bytes.fromhex(digest)
            if seven._hash(path) != expected[phase][bank]:
                raise ValueError("bank no longer matches canonical preserved SHA256")
    if set(expected) != set(PHASES):
        raise ValueError("canonical seven-phase capture inventory incomplete")
    return expected


def run_local(directory:Path) -> dict:
    directory=seven._private_directory(directory)
    expected=_canonical_archive_sha(directory)  # all 14 archive SHA before reads
    pairs={i:seven._phase_banks(directory,i) for i in PHASES}
    if any(value is None for value in pairs.values()):
        raise ValueError("incomplete seven source-selected native bank pairs")
    samples={}
    codes={}
    callers=None
    for phase in PHASES:
        pair=pairs[phase]
        with ExitStack() as stack:
            mm={}
            for bank,p in pair.items():
                fh=stack.enter_context(p.open("rb"))
                mm[bank]=stack.enter_context(mmap.mmap(
                    fh.fileno(),0,access=mmap.ACCESS_READ))
            rd=ROSTER.TwoBankReader(mm["MEM1"],mm["MEM2"])
            samples[phase]=seven._source_sample(mm["MEM1"],mm["MEM2"])
            config=rd.u32(ROSTER.GOLF_CONFIG_STATIC)
            if ROSTER._bank(config,0xC8)!="MEM2":
                raise ValueError("source GolfConfig outside native MEM2")
            samples[phase]["config_selector_words"]=tuple(
                rd.u32(config+offset) for offset in (0xBC,0xC0,0xC4))
            code=source_global_slot(rd.u32)
            codes[phase]={k:v for k,v in code.items() if k!="slot"}
            codes[phase]["runtime"]=sample_runtime(rd.u32,samples[phase],code)
            if callers is None:
                callers=caller_input_probe(rd.u32)
        for bank,p in pair.items():
            if seven._hash(p)!=expected[phase][bank]:
                raise ValueError("bank differs from canonical archive after inspection")
    # Revalidate the entire cohort: all seven pairs, including earlier phases.
    _canonical_archive_sha(directory)
    return summarize(samples,codes,callers)


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump-directory",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        report=run_local(args.dump_directory)
    except (OSError,ValueError,TypeError,KeyError,OverflowError,AttributeError):
        print("P0 GLOBAL BALL RECEIVER PROVENANCE ABSTAIN: untrusted native",
              "bank, Rev1 instruction, source-selected owner, or source-global slot.",
              file=sys.stderr)
        return 2
    print(json.dumps(report,sort_keys=True,indent=2,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
