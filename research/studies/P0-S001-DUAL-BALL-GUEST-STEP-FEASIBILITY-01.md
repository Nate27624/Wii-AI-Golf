# P0 S001 dual-ball / machine guest-physics-frame acquisition: source feasibility and no-go decision

**Status 2026-10-28: NO-GO for live physics/world-XYZ/velocity/impact capture. Review-only source feasibility.** No Dolphin session, new swing, raw RAM, file export, bridge patch, or training change is performed by this document. Owner approval still required.

## Executive implementation decision

The existing watcher is **NOT** sufficient to feed #248's claimed same-*guest-physics-frame* object contract. The smallest meaningful engineering task is not another offline changed-word study or synthetic-only schema: **identify and independently validate a true *guest game simulation-step boundary* and its sample clock, then sample source-selected and source-global ball objects in the *same single callback***. Even a valid Dolphin *render/video/frameadvance* event does not, by itself, prove one completed game *physics* step.

Do not execute another shot to answer this question until the clock, actor ownership, stationary negative control, visual association, source provenance, and read overhead have been independently reviewed.

## Actual source audit — verified against exact previously reviewed GitHub PR heads

| Gate / field | Current implementation and evidence | Feasibility now |
| --- | --- | --- |
| Source-selected ball and scene | #166 `src/wii_ai_golf/integration/ball_watch_patch.py`, SHA `da3b6f7308caca0b65247426822bd7791101fd6f`: `_wii_ball_snapshot` checks RSPE01 Rev1, scene ID 5, sport 2, Config mode 4, source PlayerManager selected record, selected ball `+0x4C -> +0x30`, and start self-reference; reads selected `+0x30`. | **Source-backed candidate: yes**, not rendered identity. |
| Separate source-global ball | #240 source research (PR current 2026-10-28) established singleton MapObjBall outside **all four** roster balls in seven preserved samples. #166 snapshot reads **neither the source-global pointer nor its `+0x4C -> +0x30`**. | **No live acquisition**. Add independently validated singleton owner chain with bounds/class, no guessed alias. |
| Selected cache CC / F0 / FC | #166 snapshot returns selected ball `+0x30`, selected player record `+0x54`, start `+0x30`; DOES NOT read selected ball `+0xCC/+0xF0/+0xFC`. #248 schema only includes CC, not F0/FC. | **Missing for full differential**; start minimal with CC, make F0/FC optional review-only controls after overhead test. |
| Pin and configuration selector controls | #166 checks Config mode +0x94 and hole +0x98, field/start, but does not capture/pin-lock `FieldManager+0x44` selected PIN geometry or `Config+0xBC/C0/C4` selector triplet. | **Incomplete** for same-shot target stability. Need both pointer and vector checks and selector words. |
| Guest callback counter | #166 `_wii_ball_snapshot` sets `frame_tick_index = _frame_count`; `_wii_ball_watch_arm` advertises `frame_count_source=bridge_coroutine_tick_only`. Hook is inserted immediately **before `_wii_ai_tick()` and `_poll_sockets()`** in the same loop. | **NO guest-physics clock**. A bridge coroutine tick is NOT a physics step. |
| Existing frameadvance API | Felk-style embedded Python scripting publicly documents `await event.frameadvance()` and `event.on_frameadvance(...)`. This establishes a scripting event exists in that documented fork; it does **NOT** establish a guest physics-step counter or callback ordering to game `RPGolSimulateManager`. Other forks/build revisions may differ. | **Candidate sync mechanism only**, NOT sufficient attestation. Check exact installed fork API offline before choosing hook. |
| Stationary no-swing proof | #215 `scripts/qualify_v1_selected_watch_readonly.py`, SHA `e9153e1a660bf1e44384cd59415c84291719163f`: requires 32 samples, stable selected/record/start vectors, <=5ms, consistent *bridge ticks*, and no sent swing. Returns `frame_counter_type=bridge_coroutine_tick_not_guest_physics_frame`. | **A qualifying negative-control design only**, not a positive same-physics-frame observation. |
| Sample integration | #166 `_wii_ball_watch_tick()` samples before the existing motion dispatch and clocks `time.perf_counter`, aborts if a read >5000 microseconds; it reads one selected source chain per sample. | In-process read bounded, but no demonstrated same game update, current overhead or observer noninterference for *dual* reads. |
| Offline consumer | #248 `scripts/review_p0_dual_source_frame_contract.py`, SHA `5415fc1d8f5a533cf648b5347ad6a27ead856141`, accepts caller-provided `guest_frame_clock_type='machine_guest_physics_frame'` and `same_callback_guest_frame_observation_attested=true`. It **explicitly says it cannot authenticate those claims**. | **Schema validation, not a source/timing proof**. Cannot upgrade to physical XYZ merely by setting flags. |
| Rendered/visual actor | Neither #166 nor #215 has a same-guest-frame framebuffer/visual object identity. Operator now explicitly warns some seven-snapshot W5/W6/W7 and D1/D2 human phase labels may be wrong. | **No rendered-ball association**. External visual witness and frame linkage required. |

**Exact source anchors**: #166 file `_wii_ball_snapshot` (source ball/current-start), `_wii_ball_watch_tick` (pre-motion observer and 5ms cutoff), and generated patch `_wii_ball_watch_tick() -> _wii_ai_tick() -> _poll_sockets()`; #215 `summarize_qualification` `frame_counter_type`; #248 `_checked_row` and `summarize_private_samples`. Public emulator documentation (NOT operator fork validation): `https://github.com/got4n/dolphin-pycore#events`, `https://github.com/dmang-dev/mcp-dolphin/blob/main/CHANGELOG.md`.

## Smallest safe S001 implementation path

1. **Prove guest-game step boundary before collecting data.** Review the *exact installed Felk binary/source* for a callback or read-only event tied to the guest's **RPGol simulation update** (not an arbitrary VI/video/frameadvance or host `_frame_count` sequence). A scripted memory-breakpoint event may exist in some forks; this is only a lead, and breakpoints can pause/interfere. Do not enable a breakpoint, patch guest code, hook emulator execution, or launch Dolphin merely because a different public fork documents an API. If no noninvasive guest-physics step ID exists, **ABSTAIN** and request owner-level implementation review.
2. **Attest atomic same-step read**, inside the existing single emu-thread observer, with independent physics_step_before and physics_step_after (and preferably a stable callback identity). Both must be **the same independently sourced guest step ID**, with exactly one stable scene/mode/selected slot/hole/boot and selected/global/pin/start/config source owner. Reject torn/no-frame/mismatched-step or pointer changes; do not infer atomicity from two host timestamps. A bridge tick cannot fill either physics-step field.
3. **Read only an explicit small source allowlist**, once per attested step: selected player record pointer -> ball child+0x88 -> ball+0x4C->+0x30; separately source-global singleton pointer -> object+0x4C->+0x30; selected ball+0xCC; PIN and START object pointer/selfref/vector; FieldManager and Config BC/C0/C4; source game/revision/scene/mode/hole/player and 5ms elapsed. Never conflate global and roster ball even if triples equal. Source/global pointer provenance must use latest #240 review and bounds/class/ownership gates; never reimplement the pointer by filename proximity.
4. **Use no-contact first**: human visually verifies stationary first ball; gather 32 consecutive source-qualified **same-step** dual-object records without controller input, with first-sample absolute-anchor stationarity plus adjacent checks. Run this only after S001/S002/S000 review. If read overhead exceeds 5ms, or observer changes cadence, stop without a shot. Ignore elapsed wall time as physics dt.
5. **Only then propose one human-controlled shot**, with exact labeled visual frame/shot and machine guest-step correspondence, both objects measured in the same step; compare which source actor changes during visibly moving ball. Do not trust old phase/filename labels as ground truth. Unmatched visual/guest frame = abstain. No automatic controller swing, savestate overwrite, unreviewed upload or training.

## Explicit readiness / owners

- `source_selected_chain_feasible=true` **offline layout only**.
- `source_global_chain_source_candidate=true` **offline seven-bank identity only**.
- `dual_source_live_watcher_implemented=false`.
- `independent_game_physics_step_clock_available_or_verified=false`.
- `same_guest_physics_step_atomicity_verified=false`.
- `live_dual_source_5ms_noninterference_verified=false`.
- `rendered_ball_correspondence_verified=false`.
- `physically_calibrated_xyz_or_velocity_or_impact_or_power_or_score=false`.
- `operator_new_gameplay_required_now=false`.
- `live_shot_authorized=false`, `training_approved=false`, `allowed_to_publish=false`.

**Who does what:** S001 owner #215/#166 must establish true physics-step hook and a separate reviewed dual-object no-input probe. S002 #240/#219 must provide canonical reviewed source-global owner/constructor/singleton chain and required identity checks. S000 #205 must review evidence labels/privacy/disable training; #248 may update its pure contract only after the clock is independently provable, not from a forged attestation flag. S002 #184 still owns a distinct optional human result/distance observation and must not be claimed same guest frame automatically.

## Stop rule

Do not create further micro-PRs for nearest PPC register, general UI xrefs, score table comparisons, or a third synthetic-only frame contract. The next deliverable is a **source- and emulator-verified yes/no feasibility of guest game-step identity and dual actor same-step capture**; if no hook exists, a bounded source+emulator instrumentation proposal with explicit S001 approval, not a production memory or training label.

**No execution in this research turn.** The recorded code snippets are available in the linked exact PR heads; this file is a design/review handoff only.
