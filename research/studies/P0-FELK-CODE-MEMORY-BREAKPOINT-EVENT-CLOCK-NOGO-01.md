# P0 — Felk breakpoint events cannot serve as a Wii Golf game-physics-step clock

**Status 2026-10-28: SOURCE-VERIFIED NO-GO for `CodeBreakpoint` event-count-as-execution and `MemoryBreakpoint` event-count-as-simulation-frame.** This is public C++ source research only, no Dolphin, scripts, local executable, emulation, breakpoints, RAM, shots, uploads or new captures. Source is the public `Felk/dolphin` fork, **not yet proven to match the user's installed executable**.

## Independently inspected immutable upstream sources

| Public source | Blob SHA | What source actually says |
| --- | --- | --- |
| [`Source/Core/Core/PowerPC/BreakPoints.cpp`](https://github.com/Felk/dolphin/blob/master/Source/Core/Core/PowerPC/BreakPoints.cpp) | `510d2f5e48d486ff0969ff61295bb7e39d52585b` | `GetRegularBreakpoint(u32 address)` emits `CodeBreakpoint{address}` **before** searching installed breakpoints; `GetBreakpoint`, `IsAddressBreakPoint`, `IsBreakPointEnable` are lookup routes; `Add(TBreakPoint)` calls `IsAddressBreakPoint` while registering a breakpoint. `TMemCheck::Action` emits the memory event before read/write-condition tests. |
| [`Source/Core/Core/API/Events.h`](https://github.com/Felk/dolphin/blob/master/Source/Core/Core/API/Events.h) | `39daf9080c5c65eb3dad1467de22a1d7dab125de` | `CodeBreakpoint` holds only `addr`; `MemoryBreakpoint` holds `write, addr, value`; both **lack guest simulation step, CPU state snapshot, rendering frame ID or callback-order witness**. `EventContainer::EmitEvent` asserts CPU thread, locks listener iteration, and synchronously calls listeners. |
| [`Source/Core/Core/API/Memory.cpp`](https://github.com/Felk/dolphin/blob/master/Source/Core/Core/API/Memory.cpp) | `c63e2cf52770350971d8b4ba19856ef23cbc573d` | `AddMemcheck` installs one-address memory check, `Read_U32` acquires `Core::CPUThreadGuard`. No source basis for treating Python callback memory read under reentrancy as safe/noninterfering. |

## Decisive counterexample — the event can describe a lookup, not execution

Exact source relationship from `BreakPoints.cpp`:

```cpp
bool BreakPoints::IsAddressBreakPoint(u32 addr) const {
  return GetBreakpoint(addr) != nullptr;
}
const TBreakPoint* BreakPoints::GetBreakpoint(u32 addr) const {
  // unless temporary breakpoint matches
  return GetRegularBreakpoint(addr);
}
const TBreakPoint* BreakPoints::GetRegularBreakpoint(u32 addr) const {
  API::GetEventHub().EmitEvent(API::Events::CodeBreakpoint{addr});
  // only afterward find regular breakpoint, possibly returning nullptr
}
void BreakPoints::Add(TBreakPoint bp) {
  if (IsAddressBreakPoint(bp.address)) return;
  // then cache invalidation and registration
}
```

This code excerpt is **an abbreviated explanatory reconstruction**, not a verbatim source listing. `GetRegularBreakpoint` emits the event before any test of whether the PC has a registered breakpoint, and the call graph contains non-guest-execution lookup paths. Thus `CodeBreakpoint{0x8028DFA8}` or `{0x8028E158}` would not by itself show that the OnCalculate thunk or main function has executed **even once**, let alone exactly once per completed physical ball update. A programmatic `IsAddressBreakPoint` query and breakpoint registration are specific non-execution causes. The CPU-thread assertion may also reject unsafe host-thread queries; that does not turn the event into an execution witness.

**Rule:** `code_breakpoint_callback_event_seen` cannot be promoted to `guest_instruction_executed`, `game_physics_update_completed`, `exact_guest_physics_step_index`, or `visual_frame_matches_measured_state`. No callback count calibration/trajectory from this event without independent execution and source-proven update entry/exit evidence.

## Memory-breakpoint does not repair the clock

`TMemCheck::Action` returns early when disabled; otherwise `EmitEvent(MemoryBreakpoint{write,addr,value})` happens **before** evaluating `is_break_on_write`, `is_break_on_read`, the configured condition, log and break-on-hit. Although the action is associated with memory access instrumentation, the event by itself is **not a qualified triggered break** and its payload has no emitting guest PC, callback index, guest physics-step ID, source selected/global ball ownership, scene or synchronized rendered frame.

Even seeing a specific source-cache write does not prove exactly one ball integration or one physics frame; multiple writes per update, unrelated data writes, missing writes, callback overhead and JIT/interpreter differences are unexcluded. Do not attach this event to a private game-memory address or enable `memory.add_memcheck` as a shortcut.

## Host threading/reentrancy concerns

`EventContainer::EmitEvent` comments explicitly say events must originate on the CPU thread to avoid Python/CPU-lock deadlocks and threading invariant violations. It asserts `Core::IsCPUThread()`, holds a listener-iteration mutex, copies listener callbacks and calls each synchronously. `API::Memory::Read_U32` itself acquires a `Core::CPUThreadGuard`. These are **not** proof that a script may safely snapshot selected and source-global ball under a code/memory breakpoint. A callback may block the emulation CPU, perturb frame cadence, or encounter reentrancy issues. The user's exact binary and script revision are still not attested. No automatic breakpoint test is approved.

## Relation to current P0 evidence

- #281 separately showed `FrameAdvance` emitted from Video Interface field begin, not a Golf simulation step; `event.on_framedrawn` is a rendered-frame callback with no guest update identity. **Neither VI event nor CodeBreakpoint nor MemoryBreakpoint supplies the required source-attested guest game simulation-step witness.**
- #279 **real original** 14-bank SHA-preserved seven Rev1 captures established the `RPGolScene::OnCalculate` source thunk `lwz r3,+0x9C(r3); b 0x8028E158`; #283 owns the target 101-word static call census. This does **not** grant a dynamic callback or step index.
- #284 is a separate **OnUserDraw** two-word static drawing-route candidate, also not a runtime draw or physics step.
- #240 original source shows a source-global MapObjBall distinct from four player roster objects; #248 validates synthetic dual-object relationships only. #215 currently uses `bridge_coroutine_tick_not_guest_physics_frame`; it cannot honestly feed #248's `machine_guest_physics_frame` requirement.
- #282 owner is preparing a read-only local executable identity probe. A local hash alone would still not identify scripting source revision or certify callback behavior without verifiable build provenance.

## Source-backed priority and stop criteria

1. **S001 #272/#215 owner:** keep guest clock **NO-GO**. Any proposed future hook must have exact source-defined Golf *update-complete* site (possibly informed by #283) and independently establish one-to-one or explicit many-to-one guest simulation-step semantics. A callback name, code lookup, UI VI field or host wall clock is insufficient.
2. **S001 emulator source + S000 owner:** inspect exact locally installed fork's source/build identity before any experimentation. Require callback ordering/thread, CPU-lock/reentrancy safety, strict <=5ms worst-case read budget, and observer-vs-no-observer cadence comparison. **Do not enable breakpoints/pause/resume, threads or game input** for feasibility-only source work.
3. **S002 #240/#248 owner:** only after valid guest game-step witness exists, sample both source-qualified selected and distinct global objects and pin/start/config in the same uninterrupted callback with before/after step IDs. Confirm stable source pointers, shot identity and initial no-input absolute-anchor stationarity. Then design a separate independently joined rendered-frame witness.
4. If no safe update-complete callback can be established, **STOP**: maintain `guest_physics_step_clock_verified=false`, `rendered_ball_identity_verified=false`, `physical_xyz_velocity_impact_power_score_verified=false`, `training_approved=false`, `allowed_to_publish=false`.

**No new owner action, local executable run, game interaction or user command is requested by this document.** This is a negative technical result and review handoff, not authorization for a watched shot or automatic merge.
