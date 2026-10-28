"""P0: validate _savegpr_26 compiler prologue before SimulateManager +0x6B4.

Source-only PPC instruction effects; separately original-14-bank SHA and
RSPE01 Rev1 source-qualified caller provides read_u32. The public ogws Rev1
unit index locates target in runtime/runtime.c; a separate Rev1 public symbol
map assigns 0x800B1D40 to _savegpr_26. Verify REAL PPC semantics here:
six stw r26..r31 through r11 followed by exact blr. Check bounded pre-call
prologue does not modify r3; no invented struct/ball/runtime identity.
"""
from __future__ import annotations

ENTRY = 0x8029B43C
CALL = ENTRY + 0x10
LOAD = ENTRY + 0x14
SAVE_HELPER = 0x800B1D40
HELPER_INSTRUCTIONS = 7
EXPECTED_LOAD_DISP = 0x6B4


def _word(read, pc):
    w = read(pc)
    if type(w) is not int or not 0 <= w <= 0xFFFFFFFF:
        raise ValueError("unverified PPC source")
    return w


def _bl(pc, w):
    if w >> 26 != 18 or not (w & 1):
        return None
    d = w & 0x03FFFFFC
    if d & 0x02000000:
        d -= 0x04000000
    return (d if w & 2 else pc + d) & 0xFFFFFFFF


def _prologue_safe(w):
    """Allow only ordinary direct no-r3-write prologue opcodes.

    Unknown PPC instruction/branch/call returns ABSTAIN; not a heuristic
    permissive 'nonmatching bits imply no r3 clobber' decoder.
    """
    op, rt, ra = w >> 26, (w >> 21) & 31, (w >> 16) & 31
    if op == 31:
        xo = (w >> 1) & 1023
        if xo == 339 and rt != 3:  # mflr/mfspr -> GPR RT
            return True
        if xo == 444:  # or/mr -> GPR RA
            return ra != 3
        return False
    if op in (14,15):  # addi/addis -> GPR RT
        return rt != 3
    if op in (24,25,26,27,28,29):  # immediate GPR -> RA
        return ra != 3
    if op in (36,38,44):  # stw/stb/sth: source RT unchanged; RA non-update
        return True
    if op in (37,39,45):  # stwu/stbu/sthu updates RA
        return ra != 3
    if op in (32,34,40,42):  # lwz/lbz/lhz/lha -> RT, non-update
        return rt != 3
    if op in (33,35,41,43):  # update loads also write RA
        return rt != 3 and ra != 3
    if op in (52,54):  # stfs/stfd no GPR write
        return True
    if op in (53,55):  # stfsu/stfdu update RA
        return ra != 3
    return False


def inspect(read_u32):
    """Return only categorical static effect, never private words/pointers."""
    if not callable(read_u32):
        raise ValueError("authenticated read callback required")
    prefix = [_word(read_u32, ENTRY+i*4) for i in range(4)]
    call = _word(read_u32, CALL)
    load = _word(read_u32, LOAD)
    body = [_word(read_u32, SAVE_HELPER+i*4)
            for i in range(HELPER_INSTRUCTIONS)]
    call_exact = _bl(CALL, call) == SAVE_HELPER
    load_exact = (load >> 26 == 32 and
                  (load >> 21)&31 == 4 and
                  (load >> 16)&31 == 3 and
                  load & 65535 == EXPECTED_LOAD_DISP)
    precursor = all(_prologue_safe(w) for w in prefix)
    stores = body[:6]
    # ABI save helper uses r11 stack pointer anchor and does not write any
    # GPR (stw source reg is RT; r11 is non-update base). Enforce r26..31.
    saves = all(w >> 26 == 36 and
                (w >> 21)&31 == i+26 and
                (w >> 16)&31 == 11
                for i,w in enumerate(stores))
    disps = [w & 65535 for w in stores]
    ordered = all(((disps[i+1]-disps[i]) & 65535) == 4
                  for i in range(5))
    returns = body[6] == 0x4E800020
    verified = bool(call_exact and load_exact and precursor and
                    saves and ordered and returns)
    reason = (
        "STATIC_PROLOGUE_PRESERVES_ENTRY_R3_UNDER_DIRECT_RETURN" if verified
        else "ABSTAIN_SOURCE_PROLOGUE_OR_SAVE_HELPER_UNVERIFIED"
    )
    return {
        "kind": "P0-PPC-STATIC-SIMULATE-ENTRY-R3-SAVEGPR26-PROLOGUE",
        "source_provenance_authenticated_by_pure_helper": False,
        "public_rev1_call_target_symbol": "_savegpr_26",
        "public_rev1_call_target_unit": "runtime/runtime.c",
        "exact_linked_call_to_savegpr26": call_exact,
        "exact_lwz_r4_plus_0x6b4_r3_after_call": load_exact,
        "four_entry_pre_call_instructions_have_only_supported_non_r3_writes":
            precursor,
        "six_save_gpr26_to31_stores_via_r11_no_r3_write": bool(saves and ordered),
        "source_helper_ends_with_plain_blr": returns,
        "status": reason,
        "entry_r3_preserved_to_6b4_load_under_bounded_prologue": verified,
        "function_entry_and_link_return_assumed_not_runtime_attested": True,
        "actual_r3_dynamic_object_type_verified": False,
        "member_6b4_semantic_role_verified": False,
        "value_loaded_from_member_is_global_or_roster_ball_verified": False,
        "rendered_ball_and_physics_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }
