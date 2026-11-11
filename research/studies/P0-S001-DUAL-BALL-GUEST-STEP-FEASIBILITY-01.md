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


## New decisive upstream bridge audit — render-frame and paused-emulator traps (2026-10-28)

Independent source: [dmang-dev/mcp-dolphin `bridge/mcp_bridge.py` main](https://github.com/dmang-dev/mcp-dolphin/blob/main/bridge/mcp_bridge.py), inspected source lines 62–76, 141–153 and 292–306; [upstream July 2026 CHANGELOG](https://github.com/dmang-dev/mcp-dolphin/blob/main/CHANGELOG.md). This is the upstream **bridge design**, not proof of the user's installed Felk binary revision.

**Three distinct clocks/exposures, NONE currently a Wii Golf simulation-step witness**:

1. Bridge `_frame_count` increments exactly once after `await event.frameadvance()` in the coroutine (bridge lines 303–305). The consumer `frame.get_count` just returns that counter (line 141). It measures wakeups of the emulator frameadvance event; it does not attest execution of `RPGolSimulateManager` or a CPU/physics-state update within that period. Game physics may be paused/skipped/multi-updated; do not substitute this value into #248's `guest_frame_index`.
2. `event.on_framedrawn(_on_framedrawn)` independently receives `(width,height,rgb_bytes)` and the callback caches **only the latest frame** as `_last_frame=(width,height,data)` (lines 64–76, 292–300). The screenshot RPC returns this cached buffer (line 143 onward) with **NO frame ID, guest CPU step ID, producer timestamp or game-physics field**. It may be older/different from any source-selected/current ball RAM sample, even when requested within a short host-time interval. The screenshot callback is optional and probed on start; don't assume every installed Felk revision supports it. A GUI frame appearing 'current' cannot be used as a synchronized physics label without a verified join mechanism.
3. Host `time.perf_counter()` in #166 watcher only measures **observer overhead**, not guest simulation delta-t. A <=5ms individual read budget controls a portion of performance risk, but does not prove no game-frame timing perturbation or that source identities are read atomically across guest state updates.

**Critical control hazard**: upstream [CHANGELOG 0.3.0 (July 2026)](https://github.com/dmang-dev/mcp-dolphin/blob/main/CHANGELOG.md) states the bridge cannot safely implement `dolphin_pause`/`resume` from its event-driven single-threaded coroutine: when paused, no events wake the loop to receive a resume command. It also documents Felk Preview 4 crashes/segfaults from background Python threads or removing a script in the Scripting panel, and large `framedrawn()` framebuffer-byte memory cleanup hazards. Do **not** propose 'pause game, read objects atomically, then unpause using the same RPC' or a background worker as a shortcut; this contradicts tested upstream behavior. No method in the installed user's setup has yet been verified to safely suspend/resume physics while preserving observed registers and correspondence.

**Memory-breakpoint distinction:** Felk-compatible Python documentation mentions `event.on_memorybreakpoint` and the upstream changelog mentions unwrapped `memory.add_memcheck`, but this is **not** evidence that the exact installed Preview4 exposes a safe, non-stalling, read-only per-instruction guest update callback. Do not enable execution/memory breakpoints without S001 review of the exact emulator build, callback thread, latency, reentrancy and address provenance.

### Minimal verifiable engineering deliverable for S001 (not another abstract schema)

A single human-reviewed, **OFFLINE provenance report before any runtime interaction**, prepared from the *exact local installed Felk build* and pinned upstream bridge code, must answer:

- Which documented callback, if any, executes **after a verified source-defined golf physics update** and before the next update? Identify producer C++ path, exact callback/step ordering and whether one call may represent multiple updates. `frameadvance` alone is NOT a positive answer.
- Can this one hook read both source objects, the selected cache and source pin/start/config in one uninterrupted guest-state interval without unsafe pause, background threads or breakpoint interference? If uncertain, **NO-GO**.
- How is a rendered frame bound to that **same measured guest update**? If on_framedrawn yields only its current `(width,height,data)` tuple and cannot produce a matched simulation-step ID, a later screenshot is **NOT a synchronized visual witness**. Propose an upstream callback frame/guest-step correlation first or abstain.
- What is the non-interfering observer overhead baseline measured on a human-approved stationary session? Existing 5ms cap is necessary but insufficient; compare with no-observer cadence in identical scene before any allowed swing.

**Owner decision:** until a source-attested guest update boundary AND visual/guest link are available, `dual_object_same_guest_physics_frame_ready=false`, `screenshot_frame_matches_RAM_sample=false`, and **do not request a new live shot**. S001 #215 owns emulator/bridge readiness; S002 #240 owns actual global source identity; S000 #205 owns privacy and training veto. Only an operator-approved action after their review may change NO-GO.


## HIGH-IMPACT SOURCE CORRECTION: breakpoint event != executed game update (2026-10-28)

Independently fetched exact public Felk/dolphin source via GitHub connector (upstream `master`, **NOT locally installed build attestation**):

| File | Immutable Git blob SHA | Critical lines / code |
|---|---|---|
| `Source/Core/Core/API/Events.h` | `39daf9080c5c65eb3dad1467de22a1d7dab125de` | `CodeBreakpoint {u32 addr}`, `MemoryBreakpoint {bool write,u32 addr,u64 value}`; `EventContainer<T>::EmitEvent` asserts CPU thread and calls handlers synchronously, with CPU/GIL deadlock comments |
| `Source/Core/Core/PowerPC/BreakPoints.cpp` | `510d2f5e48d486ff0969ff61295bb7e39d52585b` | `BreakPoints::GetRegularBreakpoint(u32 address)` emits `CodeBreakpoint{address}` at line 53 **BEFORE** searching `m_breakpoints` and before determining if any enabled breakpoint exists; `BreakPoints::Add` invalidates JIT instruction cache (lines 112–119, 127–152); `TMemCheck::Action` emits `MemoryBreakpoint{write,addr,value}` BEFORE checking trigger/break conditions (lines 384–403). |
| `Source/Core/Core/PowerPC/PowerPC.cpp` | `3cc1112bd7bf31db3570aa24ecce29d75c1a3ee4` | `PowerPCManager::CheckBreakPoints()` requests `GetBreakpoint(m_ppc_state.pc)` and only **after** lookup evaluates enabled/condition; `CheckAndHandleBreakPoints` may actually break the CPU if triggered, so event emission and CPU pause are distinct stages. |
| `Source/Core/Core/API/Memory.cpp` | `c63e2cf52770350971d8b4ba19856ef23cbc573d` | `AddMemcheck` registers a `TMemCheck`; ordinary read methods call `Core::CPUThreadGuard` and guest MMU HostRead methods; this is NOT an atomic multi-field physics-state snapshot guarantee. |

**Consequences for trustworthy P0 evidence:**

1. A `CodeBreakpoint` subscriber gets an address **from a lookup event** in this source implementation. Crucially, `GetRegularBreakpoint` emits **even when that function later returns no matching regular breakpoint**. `GetBreakpoint` can also be called by code querying configured breakpoints, not only the actually executing guest CPU. Therefore `CodeBreakpoint(addr)` alone is **not an authenticated instruction-executed event**, much less a completed `RPGolSimulateManager` step. Discriminate actual CPU execution from mere queries/lookup, breakpoint enable state and exact callback placement before accepting a clock.
2. `MemoryBreakpoint(write,addr,value)` is emitted in `TMemCheck::Action` prior to the condition/stop decision; it contains **no guest instruction PC, no guest physics tick**, and may incur expensive callback frequency. A memory event does not establish that a given position writer committed a complete 3-component vector or that both game objects are consistent.
3. Registering/altering code breakpoints invalidates JIT I-cache. `break_on_hit` can pause the CPU, and CPU-thread callback Python code may deadlock if reentrant/threading/locks violate the source's own comments. Even 'non-breaking' breakpoints may change JIT execution path or timing. **NO automatic code breakpoint/memcheck registration or live P0 watcher through these APIs** until source-to-installed-build match and S001 owner explicitly verifies safety, callsite semantics, and no-baseline observer perturbation.
4. Neither `CodeBreakpoint` nor `MemoryBreakpoint` exposes a reliable *frame/step ID* in its payload. A named game-specific `OnCalculate` code target (original 7-bank source #279 `0x8028E158`) is a much better static entrypoint lead but **still not proof** of actual per-physics-step callback or visual correspondence.

**Recommended S001 decision:** keep `authenticated_guest_physics_step_clock=false`, `code_breakpoint_event_is_execution_witness=false`, `memory_breakpoint_event_is_complete_ball_update=false`, `live_breakpoint_monitor_authorized=false`. Request a bounded **installed-binary source identity** review (#282/#286) first, then a **no-execution static C++ callback-origin feasibility** determination from actual Felk build and Wii Golf `RPGolMain`/SimulateManager callgraph. Do not ask the operator for another shot, code breakpoint, pausing or unrestricted memory scan.

The public sources can be inspected at:
- https://github.com/Felk/dolphin/blob/master/Source/Core/Core/PowerPC/BreakPoints.cpp
- https://github.com/Felk/dolphin/blob/master/Source/Core/Core/PowerPC/PowerPC.cpp
- https://github.com/Felk/dolphin/blob/master/Source/Core/Core/API/Events.h
- https://github.com/Felk/dolphin/blob/master/Source/Core/Core/API/Memory.cpp

No Dolphin, game or user archives accessed in this review. All training/physics/frame/render/score flags remain false.


**Additional high-confidence observer-effect proof (same pinned `BreakPoints.cpp` blob):** `MemChecks::Add` lines 290–316 explicitly says *"If this is the first one, clear the JIT cache so it can switch to watchpoint-compatible code."* and calls `GetJitInterface().ClearCache(guard)` then `GetMMU().DBATUpdated()`. `MemChecks::Remove` and `Clear` can also clear JIT cache (lines 330–352). Thus adding an apparently read-only memory monitor to the running emulator **changes the compiled execution path** and can influence timing; it is not equivalent to a passive RAM read. Any future approved probe must measure observer/no-observer cadence separately, and synthetic no-interference from an offline test cannot prove real-time noninterference. No memcheck/watchpoint is authorized by this research.


### Verified actual false-positive producers: JIT/CachedInterpreter compile-time checks

Independent sibling studies #287/#288 retrieved and pinned the **public** Felk source behind `CodeBreakpoint` events. I checked their exact upstream files and blob IDs:

- [`Jit64/Jit.cpp`](https://github.com/Felk/dolphin/blob/a22afcb10b97c251e17e46f2982d4e37729d32a1/Source/Core/Core/PowerPC/Jit64/Jit.cpp), blob `b09279d45850a8ad0b14b5ad1ffb60c401cad3f0`: line ~1050, under `IsDebuggingEnabled()`, **JIT compiler** calls `GetBreakPoints().IsAddressBreakPoint(op.address)` to decide whether to generate later runtime breakpoint handling. This registration/check path eventually calls `GetRegularBreakpoint`, which emits `CodeBreakpoint` before any real regular breakpoint lookup. Consequently a Python callback can see a PC **while compiling code rather than executing that instruction**.
- [`CachedInterpreter.cpp`](https://github.com/Felk/dolphin/blob/a22afcb10b97c251e17e46f2982d4e37729d32a1/Source/Core/Core/PowerPC/CachedInterpreter/CachedInterpreter.cpp), blob `b281ac0300bb750c12b2ede6f4e7e7d7536a7304`: near line 365, checks `IsAddressBreakPoint(js.compilerPC)` **during code compilation**, producing the same false-positive event path.
- [`Python eventmodule.cpp`](https://github.com/Felk/dolphin/blob/a22afcb10b97c251e17e46f2982d4e37729d32a1/Source/Core/Scripting/Python/Modules/eventmodule.cpp), blob `d3d9ef29519cb3c627e3099b910e001d173144f9`: exposes `on_codebreakpoint`, `codebreakpoint()`, but translates `CodeBreakpoint` into **only a guest address**; no producer phase flag, executed-instruction witness, simulation-step sequence, render frame ID or actor context. Python event callbacks create thread-state objects and have unsubscribing constraints. This reinforces CPU-lock/reentrancy risk when attempting heavy RAM sampling in callbacks.

**Proof strength:** this is an actual explicit code path showing why a *single* `CodeBreakpoint` event is not equivalent to `RPGolScene::OnCalculate` executing. It does not mean every such event is a compile-time lookup, nor does it rule out a future **separately authenticated** runtime instrumentation interface. The installed Dolphin EXE has not been matched to this public fork build. Until then, the guest simulation clock, rendered-actor correspondence and training gates stay **NO-GO**.

**Dedup assignment:** #287 contains the original independently pinned nonexecution-event study; #288 added the compile-time examples but its author has designated it redundant and proposed closure. This #272 feasibility note integrates only those new compiler/ABI facts, and S001 should **select one canonical source-of-truth study**, not merge all three docs as independent runtime features.
