#!/usr/bin/env python3
"""Offline selected-player Golf club-source context, not a live club detector.

Read the original source-gated Rev1 seven-pair archive by existing SHA
verifier, decode only the public RPGolPlayer source unit, and show bounded
PPC mnemonics around accesses to observed field displacements. Decoded code
context is not proof a register points at the selected player or that
an instruction executes when a club is changed. No game instructions or
memory bytes are emitted verbatim.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import json
import mmap
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_p0_club_selection_code_private as prior

PLAYER = "Pack/RPSports/RPGolScene/RPGolPlayer.cpp"
CONFIG = "Pack/RPSports/RPGolScene/RPGolConfig.cpp"
UNITS = {"player": PLAYER, "config": CONFIG}
WATCH = (0x34, 0x94, 0x98, 0x9C, 0xA0, 0xA4, 0xA8,
         0xAC, 0xB0, 0xB4, 0xB8, 0xBC, 0xC0)
FP = {48: "lfs", 50: "lfd", 52: "stfs", 54: "stfd"}
ALL_STORE = {"stb", "sth", "stw", "stfs", "stfd"}
ALL_LOAD = {"lbz", "lhz", "lha", "lwz", "lfs", "lfd"}

def access(word):
    result = prior.decode_access(word)
    if result is not None:
        return result
    op = prior.op(word)
    if op in FP:
        return {"op": FP[op], "reg": (word >> 21) & 31,
                "base": (word >> 16) & 31,
                "disp": prior.signed16(word)}
    return None

def decode(pc, word, unit_lo, unit_hi):
    a = access(word)
    if a is not None:
        r = "f" if a["op"] in FP.values() else "r"
        return "%s %s%d,%+d(r%d)" % (a["op"], r, a["reg"],
                                    a["disp"], a["base"])
    opcode = prior.op(word)
    rd, ra, rb = (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31
    if opcode in (14, 15):
        value = prior.signed16(word)
        if ra == 0:
            return ("%s r%d,%+d" % (
                "li" if opcode == 14 else "lis", rd, value))
        return "%s r%d,r%d,%+d" % (
            "addi" if opcode == 14 else "addis", rd, ra, value)
    if opcode in (10, 11):
        name = "cmplwi" if opcode == 10 else "cmpwi"
        return "%s r%d,%+d" % (name, ra, prior.signed16(word))
    if opcode in (28, 29):
        return "%s r%d,r%d,mask=0x%04X" % (
            "andi." if opcode == 28 else "andis.", ra, rd, word & 0xffff)
    if opcode == 21:
        return "rlwinm r%d,r%d,sh=%d,mb=%d,me=%d" % (
            ra, rd, rb, (word >> 6) & 31, (word >> 1) & 31)
    if opcode == 16:
        target = (pc + prior.signed16(word & 0xfffc)) & 0xffffffff
        where = "+0x%05X" % (target - unit_lo) if unit_lo <= target < unit_hi else "OUTSIDE_UNIT"
        return "bc BO=%d BI=%d -> %s" % (
            (word >> 21) & 31, (word >> 16) & 31, where)
    b = prior.decode_branch(pc, word)
    if b is not None:
        where = ("+0x%05X" % (b["target"] - unit_lo)
                 if unit_lo <= b["target"] < unit_hi else "OUTSIDE_UNIT")
        return ("bl" if b["link"] else "b") + " " + where
    if word == 0x4e800020:
        return "blr"
    if opcode == 31:
        xo = (word >> 1) & 1023
        if xo == 444 and rb == rd:
            return "mr r%d,r%d" % (ra, rd)
        if xo == 444:
            return "or r%d,r%d,r%d" % (ra, rd, rb)
        if xo in (266, 40):
            return ("%s r%d,r%d,r%d" % (
                "add" if xo == 266 else "subf", rd, ra, rb))
        return "op31 xo=%d registers=r%d,r%d,r%d" % (xo, rd, ra, rb)
    return "opcode=%d (not decoded)" % opcode


def immediate_definition(words, index, register):
    """Only nearby PPC li; unknown if any control transfer or register rewrite.

    Conservative local symbolic witness. No interprocedural or CFG analysis.
    """
    for i in range(index - 1, max(-1, index - 8), -1):
        word = words[i]
        opcode = prior.op(word)
        if opcode in (16, 18, 19):
            return None
        dest = (word >> 21) & 31
        if opcode == 14 and dest == register:
            if (word >> 16) & 31 == 0:
                return prior.signed16(word) & 0xff
            return None
        if opcode in (14, 15, 24, 25, 26, 27, 28, 29, 31) and dest == register:
            return None
        if opcode == 18 and (word & 1):
            return None
    return None


def flag_pair_summary(words):
    """Find same-base +0x34/+0x35 byte pairs; constant values only if local."""
    result = []
    for i, w in enumerate(words):
        a = prior.decode_access(w)
        if not (a and a["op"] == "stb" and a["disp"] == 0x34
                and a["base"] not in (0, 1)):
            continue
        matches = []
        for j in range(max(0, i-4), min(len(words), i+5)):
            b = prior.decode_access(words[j])
            if b and b["op"] == "stb" and b["disp"] == 0x35 and b["base"] == a["base"]:
                if any(prior.op(words[k]) in (16,18,19)
                       for k in range(min(i,j)+1, max(i,j))):
                    continue
                matches.append((abs(i-j),j,b))
        if not matches:
            continue
        _,j,b = min(matches, key=lambda m:(m[0],m[1]))
        r = {"source_relative_store_34": "+0x%05X" % (4*i),
             "source_relative_store_35": "+0x%05X" % (4*j),
             "same_base_register": "r%d" % a["base"],
             "store_34_local_li_or_unknown": immediate_definition(words,i,a["reg"]),
             "store_35_local_li_or_unknown": immediate_definition(words,j,b["reg"]),
             "source_reaches_live_selected_player_verified": False,
             "dpad_state_or_club_index_verified": False}
        result.append(r)
    return result


def counted_loop_summary(words):
    """Strict local PPC +0xBC counter-loop signature; not field ownership."""
    results = []
    for i in range(len(words)-5):
        a = prior.decode_access(words[i])
        b = words[i+1]
        c = prior.decode_access(words[i+2])
        d = prior.decode_access(words[i+3])
        e = words[i+4]
        f = words[i+5]
        if not (a and c and d and a["op"] == "lwz"
                and a["disp"] == 0xBC and a["base"] not in (0,1)
                and prior.op(b) == 14 and prior.signed16(b) == 1
                and ((b>>16)&31) == a["reg"]
                and c["op"] == "stw" and c["disp"] == 0xBC
                and c["base"] == a["base"] and c["reg"] == ((b>>21)&31)
                and d["op"] == "lwz" and d["disp"] == 0xBC
                and d["base"] == a["base"]
                and prior.op(e) == 11 and prior.signed16(e) == 16
                and ((e>>16)&31) == d["reg"]
                and prior.op(f) == 16):
            continue
        results.append({
            "source_relative_counter_read": "+0x%05X" % (4*i),
            "source_relative_increment_store": "+0x%05X" % (4*(i+2)),
            "source_relative_upper_bound_compare": "+0x%05X" % (4*(i+4)),
            "observed_compare_bound": 16,
            "receiver_is_golf_config_verified": False,
            "selected_club_semantics_verified": False,
        })
    return results


def describe_player(code, address, limit=18, context=6, target_offset=None, source_unit=PLAYER):
    prior.require(address % 4 == 0 and len(code) % 4 == 0
                  and len(code) > 0 and len(code) <= 0x40000,
                  "BAD_PLAYER_SOURCE_WINDOW")
    prior.require(source_unit in UNITS.values(), "UNQUALIFIED_SOURCE_UNIT")
    prior.require(target_offset is None or target_offset in WATCH,
                  "UNQUALIFIED_TARGET_OFFSET")
    prior.require(1 <= limit <= 50 and 1 <= context <= 12,
                  "BAD_OUTPUT_LIMIT")
    words = struct.unpack(">" + "I" * (len(code) // 4), code)
    found = []
    counts = {}
    for i, w in enumerate(words):
        a = access(w)
        if not (a and a["disp"] in WATCH
                and (target_offset is None or a["disp"] == target_offset)
                and a["base"] not in (0, 1)
                and a["op"] in ALL_LOAD | ALL_STORE):
            continue
        k = "+0x%03X" % a["disp"]
        counts[k] = counts.get(k, 0) + 1
        if a["op"] in ALL_STORE:
            score = (10 if a["disp"] == 0x34 and a["op"] == "stb" else
                     7 if a["disp"] == 0xC0 else 3)
        else:
            score = 5 if a["disp"] == 0x34 else 1
        if a["base"] in (3, 30, 31):
            score += 2
        found.append((score, i, a))

    found.sort(key=lambda t: (-t[0], t[1]))
    result = []
    for score, i, a in found[:limit]:
        lo, hi = max(0, i - context), min(len(words), i + context + 1)
        decoded = [{"unit_relative_pc": "+0x%05X" % (j * 4),
                    "mnemonic_not_ownership_proof":
                        decode(address + j*4, words[j], address,
                               address + len(code)),
                    "is_target": j == i}
                   for j in range(lo, hi)]
        result.append({
            "site": "+0x%05X" % (i*4),
            "access": a["op"],
            "field_offset_hypothesis": "+0x%03X" % a["disp"],
            "base_register": "r%d" % a["base"],
            "stored_or_loaded_register": (
                ("f" if a["op"] in FP.values() else "r")
                + str(a["reg"])),
            "priority_score_only": score,
            "context": decoded,
            "receiver_proven": False,
            "club_enum_proven": False
        })
    return {
        "status": "SOURCE_PLAYER_CLUB_CONTEXT",
        "unit": source_unit,
        "requested_target_offset": ("+0x%03X" % target_offset if target_offset is not None else "ALL_WATCHED"),
        "monitored_displacements": ["+0x%03X" % x for x in WATCH],
        "matching_access_counts_by_offset": counts,
        "matching_access_total": len(found),
        "paired_adjacent_byte_state_stores": flag_pair_summary(words) if source_unit == PLAYER else [],
        "plus_bc_counter_loop_patterns": counted_loop_summary(words) if source_unit == CONFIG else [],
        "sites_in_report": result,
        "sites_omitted": max(0, len(found) - limit),
        "nearby_code_is_not_dataflow_proof": True,
        "pc_or_runtime_execution_verified": False,
        "native_selected_club_field_verified": False,
        "training_approved": False
    }

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive", type=Path)
    ap.add_argument("--capture", type=int, choices=range(1, 8), default=5)
    ap.add_argument("--limit", type=int, default=18)
    ap.add_argument("--context", type=int, default=6)
    ap.add_argument("--target-offset", type=lambda x: int(x, 0), choices=WATCH, default=0x34)
    ap.add_argument("--source-unit", choices=tuple(UNITS), default="player")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        code = struct.pack(">4I", 0x38600002, 0x2C030002,
                           0x98640034, 0x4e800020)
        r = describe_player(code, 0x8029e62c, 3, 2)
        prior.require(r["matching_access_total"] == 1
                      and r["sites_in_report"][0]["access"] == "stb",
                      "SYNTHETIC_TEST_FAILED")
        print(json.dumps({"status": "SELFTEST_PASS", "native_ram_used": False}))
        return 0
    if args.archive is None or not 1 <= args.limit <= 50 or not 1 <= args.context <= 12:
        print(json.dumps({"status": "ABSTAIN_ARGUMENTS",
                          "training_approved": False}))
        return 2
    try:
        bank = prior.sealed_bank(args.archive, args.capture)
        index = prior.source_units(json.loads(prior.INDEX.read_text("utf-8")))
        chosen = UNITS[args.source_unit]
        lo, hi = index[chosen]
        with bank.open("rb") as fh, closing(mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)) as mm:
            prior.require(hi <= prior.MEM1 + len(mm), "WINDOW_OUTSIDE_MEM1")
            result = describe_player(bytes(mm[lo-prior.MEM1:hi-prior.MEM1]),
                                     lo, args.limit, args.context, args.target_offset, chosen)
        result["original_archive_sha_preflight_passed"] = True
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (prior.Abstain, ValueError, OSError, TypeError,
            KeyError, ImportError, IndexError):
        print(json.dumps({"status": "ABSTAIN_SOURCE_OR_ARCHIVE",
                          "training_approved": False}))
        return 3

if __name__ == "__main__":
    raise SystemExit(main())
