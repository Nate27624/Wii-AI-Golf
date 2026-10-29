"""Conservative Rev1 Golf OnCalculate POST-CALL control-flow audit (source only).

Consumes the SAME 101 authenticated words already read by #283. It cannot
observe CPU execution, prove callee side effects, infer that a guest state
update finished, or turn a static BL into a per-physics-step clock.

This is a may-CFG: conditional branches take both successors; unknown branch
targets are exits, never silently ignored. Direct BL is modeled as a
POSSIBLE returning call solely for callsite continuation analysis; this
does not prove the callee returns. The end-exclusive next function address
is an EXIT HAZARD, never a purported post-OnCalculate callback.
"""
from __future__ import annotations

ENTRY = 0x8028E158
COUNT = 101
END = ENTRY + COUNT * 4
CALLS = ((0x007C, 0x8029B554), (0x0090, 0x8029B43C),
         (0x0168, 0x8029B57C))
EXIT = -1


def _target(pc: int, word: int, conditional: bool) -> int:
    bits = 16 if conditional else 26
    mask = 0xFFFC if conditional else 0x03FFFFFC
    raw = word & mask
    if raw & (1 << (bits - 1)):
        raw -= 1 << bits
    return ((raw if word & 2 else pc + raw) & 0xFFFFFFFF)


def _index_or_exit(pc: int) -> int:
    return (pc - ENTRY) // 4 if ENTRY <= pc < END and pc % 4 == 0 else EXIT


def _reachable(graph: tuple, source: int, goal: int, forbidden: int = -2) -> bool:
    """A conservative path exists if a successor reaches goal without forbidden."""
    if source == forbidden:
        return False
    todo, seen = [source], set()
    while todo:
        node = todo.pop()
        if node == forbidden or node in seen:
            continue
        if node == goal:
            return True
        seen.add(node)
        if node != EXIT:
            todo.extend(graph[node])
    return False


def review_source_words(words: tuple[int, ...]) -> dict:
    if type(words) is not tuple or len(words) != COUNT or any(
            type(w) is not int or not 0 <= w <= 0xFFFFFFFF for w in words):
        raise ValueError("exact 101 integer source instructions required")
    for offset, target in CALLS:
        word = words[offset // 4]
        if (word >> 26 != 18 or (word & 1) == 0 or
                _target(ENTRY + offset, word, False) != target):
            raise ValueError("source-approved three direct BL entries drifted")

    graph = []
    possible_lr_exits, indirect_exits, other_exits = [], [], []
    implicit_next_function_fallthrough = False
    for i, word in enumerate(words):
        pc, op = ENTRY + i * 4, word >> 26
        nxt = i + 1 if i + 1 < COUNT else EXIT
        if op == 18:
            if word & 1:
                # It is only a POSSIBLE returning call, not proof of a
                # completed callee or state update.
                successors = [nxt]
            else:
                dest = _index_or_exit(_target(pc, word, False))
                successors = [dest]
                if dest == EXIT:
                    other_exits.append(i)
        elif op == 16:
            dest = _index_or_exit(_target(pc, word, True))
            successors = [nxt, dest]  # both BO/BI outcomes are possible
            if dest == EXIT:
                other_exits.append(i)
        elif op == 19 and ((word >> 1) & 1023) in (16, 528):
            # BO=20 is an unconditional bclr/bcctr (including plain BLR);
            # other BO modes can fall through. Unknown register targets may
            # escape the source function. Never pretend LR == ball update.
            bo = (word >> 21) & 31
            # LK=1 saves a return address: blrl/bctrl MAY resume at nxt.
            # Keep EXIT too: a linked target might never return. Plain
            # unlinked BO=20 blr/bctr is an exit, not a call continuation.
            successors = [EXIT] if bo == 20 and not (word & 1) else [EXIT, nxt]
            (possible_lr_exits if ((word >> 1) & 1023) == 16
             else indirect_exits).append(i)
        elif op == 19 and ((word >> 1) & 1023) == 50:
            successors = [EXIT]  # rfi; do not assume normal return
            other_exits.append(i)
        elif op == 17:
            successors = [EXIT, nxt]  # unknown syscall/exception effects
            other_exits.append(i)
        else:
            successors = [nxt]
        # Explicitly distinguish ordinary last-word fallthrough from
        # branch exits. An I-form linked BL in the final word returns to
        # END (= the distinct NextShot entry) and is also a hazard.
        # A plain BO=20 BLR exits through LR. Linked indirect forms can
        # call an external subroutine and MAY return to the next PC.
        is_indirect = op == 19 and ((word >> 1) & 1023) in (16, 528)
        has_sequential_fallthrough = (
            (op == 18 and bool(word & 1)) or
            op in (16, 17) or
            (is_indirect and (((word >> 21) & 31) != 20 or bool(word & 1))) or
            (op == 19 and not is_indirect and
             ((word >> 1) & 1023) != 50) or
            op not in (16, 17, 18, 19)
        )
        if i == COUNT - 1 and has_sequential_fallthrough:
            implicit_next_function_fallthrough = True
        graph.append(tuple(sorted(set(successors))))
    graph = tuple(graph)

    entries = []
    for offset, target in CALLS:
        at = offset // 4
        after = at + 1
        entries.append({
            "call_function_relative_pc": f"+0x{offset:04X}",
            "callee_published_source_entry": f"0x{target:08X}",
            "return_continuation_function_relative_pc": f"+0x{offset + 4:04X}",
            "callsite_may_be_reached_from_main_entry": _reachable(
                graph, 0, at),
            "continuation_reachable_without_callsite": _reachable(
                graph, 0, after, forbidden=at),
            "continuation_can_recur_via_source_backedge": _reachable(
                graph, after, at),
            "callee_return_and_writes_complete_at_continuation_verified": False,
            "continuation_is_unique_post_ball_update_witness_verified": False,
        })

    return {
        "kind": "P0-REV1-GOLF-MAIN-101-SOURCE-POSTCALL-CFG-V1",
        "source_code_window_stable_original_gates_required": True,
        "source_direct_sim_call_count": len(CALLS),
        "callsite_return_continuation_candidates": entries,
        "source_LR_branch_possible_exit_offsets": [
            f"+0x{i * 4:04X}" for i in possible_lr_exits],
        "source_CTR_indirect_exit_offsets": [
            f"+0x{i * 4:04X}" for i in indirect_exits],
        "source_other_or_external_exit_offsets": [
            f"+0x{i * 4:04X}" for i in other_exits],
        "source_possible_fallthrough_into_distinct_next_function":
            implicit_next_function_fallthrough,
        "source_qualified_scene_completion_site_verified": False,
        "typed_ball_integrator_or_actual_store_receiver_verified": False,
        "source_qualified_post_integrator_completion_site_verified": False,
        "runtime_guest_physics_step_or_backend_execution_verified": False,
        "rendered_ball_and_training_approved": False,
    }
