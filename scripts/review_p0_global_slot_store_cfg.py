"""A bounded, fail-closed STATIC PPC CFG summary for one global-pointer stw.

No native-file access or game-state interaction. Given a caller-provided,
source-validated PPC read_u32, this follows branch edges only inside an
11-instruction window ending at the sole verified global-ball slot store.
An external entry into this window is never ruled out. This is NOT runtime
writer execution, exact pointer value, or branch-sensitive whole-function
proof. Registers and source-relative code locations are public SOURCE labels.
"""
from __future__ import annotations

START=0x8029A030
ADDI_PC=0x8029A040
STORE_PC=0x8029A05C
UNIT_BASE=0x80296FD8
MAX_VISITS=2048


def _d(word):
    if type(word) is not int or not 0 <= word <= 0xFFFFFFFF:
        raise ValueError("bad PPC word")
    imm=word&65535
    return (word>>26,(word>>21)&31,(word>>16)&31,
            imm-65536 if imm&32768 else imm)


def _loc(pc):
    return f"+0x{pc-UNIT_BASE:04X}"


def _branch(pc,word):
    op=word>>26
    if op==18:
        raw=word&0x03FFFFFC
        if raw&0x02000000: raw-=0x04000000
        dest=(raw if word&2 else pc+raw)&0xffffffff
        return {"kind":"bl" if word&1 else "b","target":dest,"fallthrough":bool(word&1)}
    if op==16:
        raw=word&0xFFFC
        if raw&0x8000: raw-=0x10000
        dest=(raw if word&2 else pc+raw)&0xffffffff
        return {"kind":"bcl" if word&1 else "bc","target":dest,"fallthrough":True}
    if op==19 and ((word>>1)&1023) in (16,50,528):
        return {"kind":"indirect_or_return","target":None,"fallthrough":False}
    if op==17:
        return {"kind":"system_call","target":None,"fallthrough":False}
    return None


def _r3_written(word):
    op,rt,ra,imm=_d(word)
    # PowerPC rotate/mask and immediate logical operations write rA,
    # while bits 21..25 name SOURCE rS. Ignoring these would let a previous
    # addi-to-r3 appear to reach the global-pointer store after e.g.
    # `ori r3,r4,0` or `rlwinm r3,r4,...` overwrote it. Conversely,
    # `xori r4,r3,1` reads r3 and must NOT invalidate its provenance.
    # Classify conservatively without inferring the resulting r3 value.
    if op in (20,21,23,24,25,26,27,28,29):
        return "ra_form_r3_assignment_unknown" if ra==3 else None
    # lmw rT,d(rA) loads *every* GPR numbered rT..r31; r3 is changed
    # for rT in 0..3, even when the instruction does not name r3 as rT.
    # stmw is the opposite (memory STORE), and cannot redefine r3.
    if op==46:
        return "lmw_range_overwrites_r3" if rt<=3 else None
    # Ordinary integer GPR loads/arithmetic write rT; update forms also
    # write their address base rA. A load into r0 with rA=r3 is therefore
    # an r3 write despite rT!=3.
    if op in (12,13,14,15,32,33,34,35,40,41,42,43):
        if rt==3:
            if op==14:
                if ra==0:
                    return "addi_literal_zero" if imm==0 else "addi_literal_nonzero"
                return "addi_from_r3" if ra==3 else "addi_from_other_register"
            return "other_r3_value_assignment"
        if op in (33,35,41,43) and ra==3:
            return "integer_load_update_base_r3"
        return None
    # Store-update writes the effective address back into rA. The
    # immediate here is not a new value for source register rS.
    # Floating loads/stores use FPR rT/fS, NOT GPR r3; only their
    # update forms can change a tracked GPR base.
    if op in (37,39,45,49,51,53,55):
        return "memory_update_base_r3" if ra==3 else None
    if op in (36,38,44,47,48,50,52,54):
        return None
    if op==31:
        xo=(word>>1)&1023
        rs=(word>>21)&31
        rb=(word>>11)&31
        if xo==444 and ra==3 and rb==rs:
            return "mr_r3_from_r3" if rs==3 else "mr_r3_from_other_register"
        # Some X-form instructions set rA (including r3); do not claim a
        # surviving r3 value on such paths. Others may set rT.
        if ra==3 or rt==3:
            return "unknown_X_form_r3_effect"
    # No universal PPC register write decoder here: any other opcode might
    # overwrite r3. Only report candidate sources, never MUST-reach proof.
    if rt==3 and op not in (16,18,19,24):
        return "unclassified_possible_r3_overwrite"
    return None


def analyze(read, expected_disp:int)->dict:
    if type(expected_disp) is not int or not -32768<=expected_disp<=32767:
        raise ValueError("invalid source-global displacement")
    words={pc:read(pc) for pc in range(START,STORE_PC+4,4)}
    o,rs,ra,imm=_d(words[STORE_PC])
    if (o,rs,ra,imm)!=(36,3,13,expected_disp):
        raise ValueError("source-global sole stw changed")
    aop,art,ara,aimm=_d(words[ADDI_PC])
    if (aop,art)!=(14,3):
        raise ValueError("reviewed addi r3 definition no longer present")

    branches=[]
    unsupported=[]
    for pc in range(START,STORE_PC,4):
        branch=_branch(pc,words[pc])
        if branch:
            target=branch["target"]
            if target is None:
                category="indirect_unresolved"
            elif START<=target<=STORE_PC and target%4==0:
                category="inside_bounded_window"
            elif target>STORE_PC:
                category="after_store_or_other_function"
            else:
                category="before_window_or_other_function"
            branches.append({
                "source_pc":_loc(pc),
                "branch_type":branch["kind"],
                "target_class":category,
                "target_source_pc":_loc(target) if category=="inside_bounded_window" else None,
            })

    # Explore only *bounded* local flow; each path accumulates possible last
    # r3 assignments. We NEVER claim there are no external predecessors.
    pending=[(START,"unknown_entry_r3",tuple())]
    seen=set()
    reaching=set()
    unknown_external=False
    visit=0
    while pending:
        pc,value,path=pending.pop()
        if pc==STORE_PC:
            reaching.add(value)
            continue
        if not START<=pc<STORE_PC or pc%4:
            unknown_external=True
            continue
        key=(pc,value)
        if key in seen:
            continue
        seen.add(key)
        visit+=1
        if visit>MAX_VISITS:
            raise ValueError("unbounded local CFG")
        word=words[pc]
        branch=_branch(pc,word)
        if branch is not None:
            if branch["kind"] in ("b","bc"):
                if branch["target"] is not None:
                    pending.append((branch["target"],value,path+(pc,)))
                if branch["fallthrough"]:
                    pending.append((pc+4,value,path+(pc,)))
            elif branch["kind"] in ("bl","bcl"):
                # Function call can change volatile r3, and its return
                # cannot be equated to pre-call r3.
                unknown_external=True
                if branch["kind"]=="bcl":
                    pending.append((branch["target"],value,path+(pc,)))
                pending.append((pc+4,"unknown_after_call",path+(pc,)))
            else:
                unknown_external=True
            continue
        assigned=_r3_written(word)
        if assigned is not None:
            value=assigned+("@"+_loc(pc))
        pending.append((pc+4,value,path+(pc,)))

    cat=lambda v:v.split("@",1)[0]
    classes=sorted({cat(v) for v in reaching})
    return {
        "source_unit":"RPGolMapObjBall",
        "source_store_pc":_loc(STORE_PC),
        "source_addi_candidate_pc":_loc(ADDI_PC),
        "addi_base_register_class":(
            "r0_zero_base" if ara==0 else
            "r3_self" if ara==3 else "other_register"
        ),
        "addi_immediate_class":"zero" if aimm==0 else ("positive" if aimm>0 else "negative"),
        "addi_constructs_zero_literal":ara==0 and aimm==0,
        "bounded_cfg_branch_sites":branches,
        "bounded_cfg_paths_reach_store":bool(reaching),
        "bounded_cfg_reaching_r3_candidate_classes":classes,
        "bounded_cfg_multiple_candidate_sources":len(classes)>1,
        "bounded_cfg_escape_or_unknown_control_flow":unknown_external,
        "external_entries_to_window_not_excluded":True,
        "full_function_cfg_or_reaching_definition_proven":False,
        "store_runtime_value_verified":False,
        "store_runtime_execution_verified":False,
        "source_global_owner_created_here_verified":False,
        "source_window_starts_at_verified_function_entry":False,
        "physical_ball_position_verified":False,
        "model_training_approved":False,
    }
