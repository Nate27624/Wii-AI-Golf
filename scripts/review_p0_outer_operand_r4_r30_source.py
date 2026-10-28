"""P0 pure source-only operand provenance for observed outer mr r3,r4/r30.

No native input, runtime data, Dolphin, files, upload, or training. This helper
requires an independently original-SHA/RSPE01 Rev1 authenticated source-word
read callback. Backward linear source syntax is NOT all-path reaching-def proof.
"""
from __future__ import annotations

# Public source entry + exact #219 call targets; #255 proved nearest mr to r3
SOURCES = (
    ("SimulateManager_outer_to_ball_local", 0x8029B43C, 0x80299ACC, 4),
    ("MapObjBall_outer_to_ball_local", 0x8029A204, 0x80299C20, 30),
)
SOURCE_WINDOW = 0x100
DEF_WINDOW = 0x100

def _word(x):
    if type(x) is not int or not 0 <= x <= 0xFFFFFFFF:
        raise ValueError("unqualified source PPC instruction")
    return x

def _bl(pc, w):
    w=_word(w)
    if w >> 26 != 18 or not w & 1:
        return None
    disp=w & 0x03FFFFFC
    if disp & 0x02000000: disp-=0x04000000
    return (disp if w & 2 else pc+disp) & 0xFFFFFFFF

def _mr(w):
    if w >> 26 != 31 or (w >> 1)&1023 != 444:
        return None
    rs,ra,rb=(w>>21)&31,(w>>16)&31,(w>>11)&31
    return (ra,rs) if rs==rb else None

def _control(w):
    op=w>>26
    return (op in (16,17,18) or
            (op==19 and (w>>1)&1023 in (16,50,528)))

def _source_write(w, reg):
    """Conservative destination-aware PPC effect classes; unknown means unknown.

    PPC D-form stores have RS in RT field and do not overwrite RS. Update
    stores do write RA. op46 lmw loads a GPR range. op47 stmw stores only.
    X-form op31 is not comprehensively decoded and is always marked unknown
    if operand names overlap; compare/cr logic never promoted as a definition.
    """
    w=_word(w)
    op,rt,ra=(w>>26)&63,(w>>21)&31,(w>>16)&31
    moved=_mr(w)
    if moved and moved[0]==reg:
        return f"mr_from_r{moved[1]}"
    if op in (14,15) and rt==reg:
        return ("addi_literal" if ra==0 else f"addi_from_r{ra}")
    if op in (32,33,34,35,40,41,42,43) and rt==reg:
        return f"integer_load_base_r{ra}"
    if op==46 and rt<=reg:
        return "lmw_range_load_candidate"
    if op in (33,35,41,43,37,39,45,49,51,53,55) and ra==reg:
        return "update_base_register_written"
    if op in (20,21,23,24,25,26,27,28,29) and ra==reg:
        return "rotate_or_logic_immediate_ra_writer"
    if op==31:
        xo=(w>>1)&1023
        if xo in (0,32):  # compare changes CR only
            return None
        if rt==reg or ra==reg:
            return "unknown_X_form_write_or_operand"
    return None

def _source_load_detail(w, reg):
    """Public PPC *code* immediate, never a private heap/runtime address.

    Only exact D-form integer loads with RT==observed operand. No decoded
    instruction bytes, memory contents, provenance of RA object, or dereference.
    """
    w=_word(w)
    op, rt, ra=(w>>26)&63,(w>>21)&31,(w>>16)&31
    names={32:"lwz",33:"lwzu",34:"lbz",35:"lbzu",
           40:"lhz",41:"lhzu",42:"lha",43:"lhau"}
    if op not in names or rt!=reg:
        return None
    imm=w&65535
    signed=imm-65536 if imm&0x8000 else imm
    return {
        "candidate_D_form_integer_load_mnemonic": names[op],
        "candidate_base_register":f"r{ra}",
        "candidate_source_field_displacement":
            ("-" if signed<0 else "+")+f"0x{abs(signed):03X}",
        "base_register_runtime_object_class_proven":False,
        "candidate_load_reaches_receiver_on_all_paths_proven":False,
    }

def analyze(read_u32):
    if not callable(read_u32):
        raise ValueError("qualified read_u32 callback required")
    rows=[]
    for name,entry,target,operand in SOURCES:
        words=[_word(read_u32(pc)) for pc in range(entry,entry+SOURCE_WINDOW,4)]
        calls=[i for i,w in enumerate(words)
               if _bl(entry+4*i,w)==target]
        r={
            "outer_source_function":name,
            "tracked_source_operand":f"r{operand}",
            "exact_inner_bl_in_bounded_0x100_window_count":len(calls),
            "mr_r3_from_expected_operand_confirmed":False,
            "mr_r3_entry_relative_offset":None,
            "nearest_pre_mr_operand_write_class":None,
            "nearest_pre_mr_operand_write_entry_relative_offset":None,
            "nearest_pre_mr_integer_load_source_detail":None,
            "control_transfer_before_mr":None,
            "control_transfer_after_candidate_write":None,
            "status":"ABSTAIN",
            "source_window_is_verified_function_extent":False,
            "all_path_reaching_definition_verified":False,
            "actual_operand_is_global_or_roster_ball_verified":False,
        }
        if len(calls)!=1:
            r["status"]="ABSTAIN_AMBIGUOUS_OR_OUT_OF_WINDOW_INNER_CALL"
            rows.append(r)
            continue
        call=calls[0]
        defs_r3=[i for i in range(max(0,call-16),call)
                 if _mr(words[i]) is not None and _mr(words[i])[0]==3]
        # Do not claim observed mr if any closer r3 writer could supersede it.
        if not defs_r3 or _mr(words[defs_r3[-1]])!=(3,operand):
            r["status"]="ABSTAIN_EXPECTED_MR_R3_NOT_LAST_MOVE"
            rows.append(r)
            continue
        mr_index=defs_r3[-1]
        # Any later possible r3 write makes this syntactic link unqualified.
        for w in words[mr_index+1:call]:
            if _source_write(w,3) is not None or _control(w):
                r["status"]="ABSTAIN_MR_R3_MAY_BE_CLOBBERED_AFTER_MOVE"
                break
        else:
            r["mr_r3_from_expected_operand_confirmed"]=True
            r["mr_r3_entry_relative_offset"]=f"+0x{mr_index*4:03X}"
            r["control_transfer_before_mr"]=any(_control(w) for w in words[:mr_index])
            start=max(0,mr_index-DEF_WINDOW//4)
            found=[(i,_source_write(words[i],operand))
                   for i in range(start,mr_index)
                   if _source_write(words[i],operand) is not None]
            if not found:
                r["status"]="ABSTAIN_NO_SUPPORTED_OPERAND_DEFINITION"
            else:
                last,kind=found[-1]
                r["nearest_pre_mr_operand_write_class"]=kind
                r["nearest_pre_mr_integer_load_source_detail"]=(_source_load_detail(words[last],operand))
                r["nearest_pre_mr_operand_write_entry_relative_offset"]=f"+0x{4*last:03X}"
                r["control_transfer_after_candidate_write"]=any(
                    _control(w) for w in words[last+1:call])
                r["status"]=("SOURCE_SYNTAX_CANDIDATE_WITH_CONTROL_HAZARD"
                             if r["control_transfer_before_mr"] or
                             r["control_transfer_after_candidate_write"] or
                             kind.startswith("unknown")
                             else "SOURCE_SYNTAX_CANDIDATE_NOT_CFG_PROOF")
        rows.append(r)
    return {
        "kind":"P0-SANITIZED-OUTER-OPERAND-R4-R30-SOURCE-CANDIDATES",
        "all_two_source_windows_analysed":True,
        "input_code_SHA_authenticated_by_pure_helper":False,
        "candidate_source_semantics_are_syntax_only":True,
        "real_receiver_global_or_player_ball_verified":False,
        "runtime_invocation_verified":False,
        "rendered_ball_physics_xyz_velocity_verified":False,
        "training_approved":False,
        "allowed_to_publish":False,
        "outer_operand_source_rows":rows,
    }
