"""S002 P0: bounded Rev1 PPC direct-store candidate map for changing player-record words.

Offline static source evidence only. Does NOT prove rA points to the selected
RPGolPlayer record or that an instruction executed during a real swing.
Uses upstream #219's original-B0 native SHA/manifest gate and code-unit map.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import sys

PLAYER_UNITS = frozenset({"RPGolPlayer", "RPGolPlayerManager"})
RECORD_OFFSETS = (0x30, 0x34, 0x38, 0x54, 0x60, 0x90)
PPC_STORES = {36: "stw", 37: "stwu", 52: "stfs", 53: "stfsu",
              54: "stfd", 55: "stfdu", 44: "sth", 45: "sthu",
              38: "stb", 39: "stbu"}
DIRECT_FULL_WORD = frozenset({"stw", "stwu", "stfs", "stfsu"})
SITE_CAP = 12


def decode_dform_store(word):
    """Return source syntax, never value/type/owner/runtime address."""
    if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
        raise ValueError("Malformed PPC word")
    op = PPC_STORES.get(word >> 26)
    if op is None:
        return None
    d = word & 0xFFFF
    if d >= 0x8000:
        d -= 0x10000
    return (op, (word >> 21) & 31, (word >> 16) & 31, d)



def inspect_local_base_definition(data: bytes, start: int, unit_start: int,
                                  site_pc: int, base_reg: int) -> dict:
    """Bounded straight-line register-origin HINT; never a receiver identity proof.

    Stop on branches and unclassified possible GPR writers. Do not cross
    compilation-unit boundary, a caller, or a dynamic execution path.
    """
    if base_reg == 0:
        return {"origin_class": "zero_base_not_object_pointer",
                "source_relative_definition": None,
                "runtime_selected_record_base_verified": False}
    distance = 0
    for pc in range(site_pc - 4, max(start, unit_start, site_pc - 64) - 1, -4):
        distance += 1
        word = struct.unpack_from(">I", data, pc-start)[0]
        primary = word >> 26
        rt = (word >> 21) & 31
        ra = (word >> 16) & 31
        # Any flow transfer (including calls) invalidates local linear reach.
        if primary in (16, 17, 18, 19):
            kind = "control_flow_barrier"
        elif primary in (32, 34, 40, 42):
            kind = "memory_load_candidate" if rt == base_reg else None
        elif primary in (33, 35, 41, 43):
            kind = ("memory_load_candidate" if rt == base_reg else
                    "update_form_base_modified" if ra == base_reg else None)
        elif primary in (49, 51):
            # lfsu/lfdu update the GPR address base, not the floating dest.
            kind = "update_form_base_modified" if ra == base_reg else None
        elif primary in (14, 15):
            kind = "immediate_arithmetic_candidate" if rt == base_reg else None
        elif primary in (24, 25, 26, 27, 28, 29):
            kind = "immediate_logical_candidate" if ra == base_reg else None
        elif primary == 31:
            xo = (word >> 1) & 0x3ff
            if xo == 444 and ra == base_reg and rt == ((word >> 11) & 31):
                kind = "register_copy_candidate"
            elif rt == base_reg or ra == base_reg:
                kind = "unknown_xform_possible_definition"
            else:
                kind = None
        elif primary in (37, 39, 45, 53, 55):
            kind = "update_form_base_modified" if ra == base_reg else None
        elif primary in (7, 8, 12, 13, 20, 21, 22, 23, 30):
            kind = "unknown_integer_possible_definition" if (
                rt == base_reg or ra == base_reg) else None
        elif primary not in (36, 38, 44, 48, 50, 52, 54, 59, 63, 4):
            kind = "unknown_opcode_barrier"
        else:
            kind = None
        if kind is not None:
            return {
                "origin_class": kind,
                "source_relative_definition": f"+0x{pc-unit_start:04X}",
                "instructions_back": distance,
                "runtime_selected_record_base_verified": False,
            }
    return {"origin_class": "no_qualifying_local_definition",
            "source_relative_definition": None,
            "instructions_back": distance,
            "runtime_selected_record_base_verified": False}


def scan_candidate_stores(data: bytes, base: int, units):
    """Only published Player/PlayerManager .text, not a RAM or data scan.

    D-form displacement is relative to the instruction base register, NOT
    necessarily the RPGolPlayer record base; callers may adjust rA. Indexed
    forms, 64-bit overlap, vector stores and other units are not attributed.
    """
    if (type(data) is not bytes or type(base) is not int or
            base < 0x80000000 or base % 4 or len(data) % 4 or
            not 0 < len(data) <= 0x100000 or not isinstance(units, tuple)):
        raise ValueError("Invalid bounded public code window")
    selected = [(name, lo, hi) for name, lo, hi in units
                if name in PLAYER_UNITS]
    if (len(selected) != 2 or len({x[0] for x in selected}) != 2 or
            any(type(lo) is not int or type(hi) is not int or
                lo % 4 or hi % 4 or not base <= lo < hi <= base+len(data)
                for _, lo, hi in selected)):
        raise ValueError("Missing or incompatible player source boundaries")
    out = []
    for member in RECORD_OFFSETS:
        candidates = []
        for unit_name, lo, hi in selected:
            for pc in range(lo, hi, 4):
                word = struct.unpack_from(">I", data, pc-base)[0]
                parsed = decode_dform_store(word)
                if parsed is None or parsed[3] != member:
                    continue
                op, rs, ra, _ = parsed
                candidates.append({
                    "source_unit": unit_name,
                    "source_relative_instruction": f"+0x{pc-lo:04X}",
                    "opcode": op,
                    "value_register": f"r{rs}" if not op.startswith("stf") else f"f{rs}",
                    "base_register": f"r{ra}",
                    "full_4byte_direct_store_candidate": op in DIRECT_FULL_WORD,
                    "local_base_definition_hint": inspect_local_base_definition(
                        data, base, lo, pc, ra),
                })
        out.append({
            "record_relative_displacement_candidate": f"+0x{member:03X}",
            "dform_store_count": len(candidates),
            "word_width_store_count": sum(x["full_4byte_direct_store_candidate"] for x in candidates),
            "candidate_sites": candidates[:SITE_CAP],
            "additional_sites_omitted": max(0,len(candidates)-SITE_CAP),
            "base_register_is_selected_player_record_verified": False,
        })
    return {
        "kind": "S002-P0-REV1-PLAYER-RECORD-STORE-CANDIDATES",
        "source_game": "RSPE01", "disc_revision": 1,
        "scanned_units": [x[0] for x in selected],
        "read_only_public_source_code_scan": True,
        "exact_dform_displacement_not_runtime_record_member": True,
        "indexed_store_and_other_unit_coverage_complete": False,
        "straightline_register_hints_are_full_dataflow_proof": False,
        "record_word_changes_source_attributed": False,
        "runtime_store_execution_verified": False,
        "physical_ball_xyz_verified": False,
        "ball_velocity_verified": False,
        "game_power_ram_verified": False,
        "same_guest_frame_verified": False,
        "approved_for_training": False,
        "allowed_to_publish": False,
        "candidates": out,
    }


def audit(session: Path, data_root: Path):
    # Upstream source and SHA-gated B0 owns provenance, not this module.
    import audit_ball_xyz_source_callers_private as upstream
    def checked_b0():
        try:
            return upstream.checked_private_b0(session, data_root)
        except upstream.UntrustedInput:
            raise ValueError("Untrusted source provenance") from None
    file = checked_b0()
    lo = min(x[1] for x in upstream.UNITS if x[0] in PLAYER_UNITS)
    hi = max(x[2] for x in upstream.UNITS if x[0] in PLAYER_UNITS)
    with file.open("rb") as fh:
        header = fh.read(8)
        if header[:6] != upstream.GAME_ID or len(header) != 8 or header[7] != 1:
            raise ValueError("Wrong native game or revision")
        fh.seek(lo-upstream.MEM1_START)
        data = fh.read(hi-lo)
    if len(data)!=hi-lo or all(data[i:i+4]==b"\0\0\0\0" for i in range(0,len(data),4)):
        raise ValueError("Absent source code")
    # Reject mutation between source-provenance check and source read.
    checked_b0()
    report = scan_candidate_stores(data, lo, upstream.UNITS)
    report["native_source_b0_sha256_verified_before_and_after_read"] = True
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    root_default = Path(__file__).resolve().parents[2]/"Wii-AI-Golf-Data"
    p.add_argument("--data-root", type=Path, default=root_default)
    p.add_argument("--private-session", type=Path)
    args = p.parse_args(argv)
    location = args.private_session or args.data_root/"ball-study-20261027-212633"
    try:
        result = audit(location, args.data_root)
    except (OSError,ValueError,TypeError,OverflowError,KeyError,AttributeError,ImportError):
        print("P0 player field store source audit ABSTAINED; private B0 provenance or Rev1 source checks failed. No private bytes/paths reported.",file=sys.stderr)
        return 2
    print(json.dumps(result,sort_keys=True,allow_nan=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
