#!/usr/bin/env python3
"""P0 Golf: narrow local lookup->formatted UI call pairing and argument count.

Reads only canonical B0 Rev1 Golf code via inherited #219 SHA gate and
#256 published source units. Reports source code-unit offsets + *classes*;
no native instructions, RAM data, message/group IDs, pane names or strings.
A fallthrough pair/argc is not a verified Hitting-the-Green result or
runtime executed UI/dataflow; indirect dispatch and unknown source remain.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_p0_golf_layout_text_wrapper_xrefs_private as xref
import audit_p0_golf_sprintf_format_types_private as src

base = xref.base
pub = xref.source
MAX_DISTANCE = 0x40
MAX_REPORTED = 32
MAX_SITES = 200
LOOKUP = "layout_find_textbox"
FORMATTED = frozenset((
    "textbox_set_message_variadic", "textbox_set_text_variadic",
    "textbox_set_message_va",
))
# The format-message va_list variant receives a pointer to an arg list,
# NOT varargs in r8. This conservative local test does not decode it.

def _word(buf: bytes, offset: int) -> int:
    return struct.unpack_from(">I", buf, offset)[0]

def _arg_class(segment: list[int], reg: int):
    """Only last recognized assignment syntax *after* preceding direct call."""
    writes = [w for w in segment if src._potential_write(w, reg)]
    if not writes:
        return "unresolved"
    w = writes[-1]
    op, rt, ra, imm = src._decode_d(w)
    if op == 14 and rt == reg and ra == 0:
        return ("zero" if imm == 0 else
                "one" if imm == 1 else
                "small_positive" if 1 < imm <= 4 else "other_literal")
    return "non_literal_or_ambiguous_write"

def _source_class(segment: list[int], reg: int):
    writes = [w for w in segment if src._potential_write(w, reg)]
    if not writes:
        return "not_resolved"
    op, rt, ra, _ = src._decode_d(writes[-1])
    if op == 14 and rt == reg and ra != 0:
        return "addi_from_nonzero_base"
    if op in (32, 34, 40, 42) and rt == reg:
        return "source_memory_load"
    if op == 31:
        xo = (writes[-1] >> 1) & 1023
        rs = rt
        rb = (writes[-1] >> 11) & 31
        if xo == 444 and rs == rb and ra == reg:
            return "mr_from_nonvolatile_or_other_register"
    return "other_or_ambiguous_source"

def classify_pair(buf: bytes, unit: str, find_off: int,
                  sink_off: int, sink_method: str) -> dict:
    base.ensure(type(buf) is bytes and len(buf) % 4 == 0
                and unit.startswith(pub.GOLF_PREFIX)
                and sink_method in FORMATTED
                and 0 <= find_off < sink_off < len(buf)
                and find_off % 4 == sink_off % 4 == 0
                and sink_off - find_off <= MAX_DISTANCE)
    # Verify exact caller symbols at source-code sites.
    begin_pc = 0x80280000  # relative verifier below uses decoded displacement
    # Native absolute PCs are supplied through caller, not from this helper.
    words = [_word(buf, o) for o in range(find_off+4, sink_off, 4)]
    # Reject if branch/call/return between calls: no straight-line pairing.
    barriers = [w for w in words if src.prior._control_barrier(w)]
    r3_clobbers = [w for w in words if src._potential_write(w, 3)]
    # This is ONLY local syntactic fallthrough. Incoming branches not checked.
    method = "set_text" if sink_method == "textbox_set_text_variadic" else (
        "set_message_variadic" if sink_method ==
        "textbox_set_message_variadic" else "set_message_va")
    argc_reg = 5 if method == "set_text" else (
        7 if method == "set_message_variadic" else None)
    first_arg_reg = 6 if method == "set_text" else (
        8 if method == "set_message_variadic" else None)
    return {
        "source_unit": unit,
        "lookup_offset": f"+0x{find_off:05X}",
        "formatted_call_offset": f"+0x{sink_off:05X}",
        "method_kind": method,
        "gap_bytes": sink_off-find_off,
        "intervening_branch_or_call": bool(barriers),
        "receiver_r3_possible_clobber": bool(r3_clobbers),
        "linear_receiver_return_candidate": not barriers and not r3_clobbers,
        "argc_post_lookup_last_assignment_class":
            _arg_class(words, argc_reg) if argc_reg is not None else
            "va_list_overload_not_gpr_varargs",
        "first_argument_post_lookup_source_class":
            _source_class(words, first_arg_reg) if first_arg_reg is not None else
            "va_list_overload_not_gpr_varargs",
        "formatting_numeric_value_verified": False,
        "pane_identity_or_result_ui_verified": False,
    }

def extract_pairs(buf: bytes, start: int, unit: str):
    base.ensure(type(buf) is bytes and len(buf)%4==0
                and type(start) is int and start%4==0
                and unit.startswith(pub.GOLF_PREFIX))
    calls = xref.source_calls([(unit, start, buf)])
    find_sites = [off for _,off,name,_,linked in calls
                  if name == LOOKUP and linked]
    sinks = [(off,name) for _,off,name,_,linked in calls
             if name in FORMATTED and linked]
    base.ensure(len(calls) <= MAX_SITES)
    result=[]
    for sink_off,name in sinks:
        previous = [off for off in find_sites
                    if 0 < sink_off-off <= MAX_DISTANCE]
        if not previous:
            continue
        lookup_off = max(previous)
        # Include only actual same-source direct fallthrough candidates.
        # Reject pairs with intervening branch/call, no claim about incoming CFG.
        row=classify_pair(buf,unit,lookup_off,sink_off,name)
        if not row["intervening_branch_or_call"]:
            result.append(row)
    return len(find_sites),len(sinks),result

def summarize(lookups: int, sinks: int, rows: list[dict]):
    base.ensure(type(rows) is list and type(lookups) is int
                and type(sinks) is int and 0 <= len(rows) <= sinks)
    classes=Counter(r["argc_post_lookup_last_assignment_class"]
                    for r in rows if r["linear_receiver_return_candidate"])
    # Put numeric-argument count leads first, but no result screen promotion.
    ranked=sorted(rows,key=lambda r: (
        -int(r["linear_receiver_return_candidate"]
             and r["argc_post_lookup_last_assignment_class"] in
             ("one","small_positive","other_literal")),
        -int(r["linear_receiver_return_candidate"]),
        r["source_unit"],r["formatted_call_offset"]))
    return {
        "kind":"P0-GOLF-LOOKUP-FORMATTED-MESSAGE-LOCAL-FALLTHROUGH-V1",
        "game_id":"RSPE01","disc_revision":1,
        "original_b0_sha_source_and_golf_units_verified":True,
        "direct_textbox_lookup_count":lookups,
        "direct_formatted_wrapper_call_count":sinks,
        "local_no_intervening_branch_pair_count":len(rows),
        "pairs_without_r3_write_or_branch_count":
            sum(r["linear_receiver_return_candidate"] for r in rows),
        "argument_count_syntax_categories":dict(sorted(classes.items())),
        "prioritized_source_pairs":ranked[:MAX_REPORTED],
        "omitted_pairs":max(0,len(ranked)-MAX_REPORTED),
        "incoming_cfg_edges_unchecked":True,
        "arg_count_may_be_setup_before_lookup_and_clobbered":True,
        "hitting_green_result_display_and_message_ids_verified":False,
        "typed_numeric_value_source_or_units_verified":False,
        "frame_visual_association_verified":False,
        "training_approved":False,"allowed_to_publish":False,
    }

def audit(baseline: Path, root: Path):
    bank=base.checked_private_b0(baseline,root)
    units=pub.golf_units(base.load_public_text_units())
    lookups=sinks=0
    rows=[]
    with bank.open("rb") as fh:
        base.ensure(fh.read(6)==base.GAME_ID)
        fh.seek(7)
        base.ensure(fh.read(1)==b"\x01")
        for start,end,unit in units:
            fh.seek(start-base.MEM1_START)
            data=fh.read(end-start)
            base.ensure(len(data)==end-start and any(data))
            a,b,c=extract_pairs(data,start,unit)
            lookups+=a; sinks+=b; rows.extend(c)
    base.ensure(lookups==60 and sinks==60)
    base.ensure(base.checked_private_b0(baseline,root)==bank)
    return summarize(lookups,sinks,rows)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        root=Path(__file__).resolve().parents[2]/"Wii-AI-Golf-Data"
        report=audit(args.baseline,root)
    except (base.UntrustedInput,ValueError,TypeError,KeyError,OSError,
            OverflowError,IndexError,AttributeError):
        print("P0_GOLF_MESSAGE_PAIR_ABSTAIN: source or strict pair validation failed",
              file=sys.stderr)
        return 2
    print(json.dumps(report,sort_keys=True,indent=2,allow_nan=False))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
