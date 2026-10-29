"""Offline P0 event-pair validator for a *hypothetical* future Golf CPU probe.

NO emulator integration and NO physics-clock proof. Native execution-site
provenance is NOT verified by this code: all input event labels/tokens are
synthetic or externally claimed. Source-backed static candidates are:
  RPGolScene OnCalculate -> main fn_8028E158,
  +0x7C BL fn_8029B554 (possibly repeated by BC +0x88 -> +0x6C),
  +0x90 BL fn_8029B43C, +0x168 BL fn_8029B57C,
  B57C+0x50 contains stfs f1,0(r26). Actual original B0 (#270)
  independently found the nearest recognized r26 write was addi/addis
  from r1 (stack pointer), with an intervening control-flow barrier.
  This is a STACK-DERIVED SCRATCH/OUTPUT CANDIDATE, NOT a source-typed
  ball integrator or a verified persistent ball-state destination.
A matched return after that stfs is only an *untrusted possible return
after scratch-output write*, NOT a ball update, guest physics step,
rendered XYZ, shot outcome, or model training sample.
"""
from __future__ import annotations

CALLS = ("B554", "B43C", "B57C")
EVENTS = frozenset(("scene_enter", "scene_exit", "sim_enter",
                    "sim_return", "b57c_store_candidate"))
FIELDS = frozenset(("ordinal", "scene_token", "event", "call_token", "callee"))
MAX_EVENTS = 10000


def _number(x: object) -> bool:
    return type(x) is int and 1 <= x <= 0x7FFFFFFF


def inspect_events(events: list[dict]) -> dict:
    if type(events) is not list or not 1 <= len(events) <= MAX_EVENTS:
        raise ValueError("bounded event list required")
    current_scene = None
    scene_ids = set()
    call_ids = set()
    call_stack = []
    total_calls = {key: 0 for key in CALLS}
    completed_scenes, calls_with_store, repeated_b554_scenes = 0, 0, 0
    last_sequence = 0
    scene_b554 = 0

    for event in events:
        if type(event) is not dict or set(event) != FIELDS:
            raise ValueError("exact event schema required")
        ordinal = event["ordinal"]
        scene = event["scene_token"]
        kind = event["event"]
        call = event["call_token"]
        callee = event["callee"]
        if (not _number(ordinal) or ordinal != last_sequence + 1 or
                not _number(scene) or type(kind) is not str or
                kind not in EVENTS):
            raise ValueError("unqualified event order or scene")
        last_sequence = ordinal

        if kind == "scene_enter":
            if current_scene is not None or scene in scene_ids or (
                    call is not None or callee is not None):
                raise ValueError("overlapping or reused scene entry")
            current_scene = scene
            scene_ids.add(scene)
            scene_b554 = 0
            continue
        if current_scene != scene:
            raise ValueError("event outside its active scene")
        if kind == "scene_exit":
            if call_stack or call is not None or callee is not None:
                raise ValueError("scene exit with unpaired calls or identities")
            completed_scenes += 1
            if scene_b554 > 1:
                repeated_b554_scenes += 1
            current_scene = None
            continue
        if not _number(call) or callee not in CALLS:
            raise ValueError("missing bounded source call identity")
        if kind == "sim_enter":
            if call in call_ids:
                raise ValueError("reused source call token")
            call_ids.add(call)
            call_stack.append({"call": call, "callee": callee, "store": False})
            total_calls[callee] += 1
            if callee == "B554":
                scene_b554 += 1
        elif kind == "b57c_store_candidate":
            if (callee != "B57C" or not call_stack or
                    call_stack[-1]["call"] != call or
                    call_stack[-1]["callee"] != "B57C" or
                    call_stack[-1]["store"]):
                raise ValueError("syntactic store site not in a matching active call")
            call_stack[-1]["store"] = True
        elif kind == "sim_return":
            if (not call_stack or call_stack[-1]["call"] != call or
                    call_stack[-1]["callee"] != callee):
                raise ValueError("out of order or unmatched callee return")
            item = call_stack.pop()
            if item["store"]:
                calls_with_store += 1
    if current_scene is not None or call_stack or not completed_scenes:
        raise ValueError("truncated or incomplete event sequence")
    return {
        "kind": "P0-GOLF-POTENTIAL-POSTSTORE-PAIRING-SYNTHETIC-V1",
        "externally_supplied_event_semantics_source_verified": False,
        "scene_exit_event_count_unverified": completed_scenes,
        "source_call_entry_counts_unverified": total_calls,
        "scene_event_groups_with_multiple_B554_entries": repeated_b554_scenes,
        # Historical v1 output retained for existing consumers. Never use
        # this as a game-ball or guest-frame counter. Independent original
        # B0 Rev1 source #270 found r26 from stack pointer r1 with a
        # control-transfer hazard; not a proven dynamic stack store either.
        "B57C_callee_returns_after_same_call_syntactic_store_candidates":
            calls_with_store,
        "B57C_static_r26_nearest_recognized_def_class":
            "addi_or_addis_from_r1_with_control_barrier",
        "B57C_store_source_role_class":
            "stack_derived_scratch_or_output_candidate_not_typed_ball",
        "B57C_stfs_actual_runtime_receiver_verified": False,
        "B57C_store_is_eligible_ball_update_completion_anchor": False,
        "eligible_ball_update_completion_observations": 0,
        "per_scene_event_count_is_not_guest_physics_step": True,
        "B57C_stfs_receiver_is_selected_or_global_ball_verified": False,
        "source_qualified_post_ball_integrator_completed_verified": False,
        "actual_felk_execution_provenance_and_backend_verified": False,
        "guest_physics_step_clock_verified": False,
        "same_callback_rendered_ball_visual_join_verified": False,
        "training_approved": False,
        "allowed_to_publish": False,
    }
