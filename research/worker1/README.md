# Worker 1 research handoff — 2026-10-24

Owner: integrator, issue [#2](https://github.com/Nate27624/Wii-AI-Golf/issues/2). Consult `research/claims/worker-1.json` and `research/coordination.md` before touching integration files.

## Verified locally

- Read `mcp-dolphin` v0.2 source and designed a compatible local-only JSON-lines RPC client.
- Tests exercise real loopback **fake server** transport (round trip, fragmented reply, bridge errors, ID mismatch, response limits and remote-address denial).
- Offline mock trace rehearsal reports target/request/acknowledgement frame counters, normalized source, trace SHA-256, and best-effort button release.
- Full existing + new suite: **21 unit tests passed** locally with `PYTHONPATH=src python -m unittest discover -s tests -v`.
- `PYTHONPATH=src python scripts/probe_dolphin_bridge.py` runs deterministic mock rehearsal; no Wii game was used.

## Not verified

- No Felk Dolphin process, Nintendo software, real Wii Remote bridge or game-state readings were available.
- No real swing recognized; no score or medal confirmed; no 30-shot or 100-shot real experiment conducted.
- Sending A and accelerometer in different RPC commands is NOT synchronous. This is a blocking limitation for accurate shot reproduction.

## Next action for Worker 1

1. On local Windows machine, install tested Felk scripting Dolphin and matching `mcp-dolphin` v0.2 bridge; verify read-only preflight.
2. Record Dolphin build, region, game screens and emulated-controller configuration.
3. Probe whether A and acceleration are observed together; if not, implement an atomic bridge-side per-frame scheduler as a **separate, version-pinned patch** (do not assert compatibility without running it).
4. Only after reliable atomic input, run predeclared S001 swing/no-swing control experiment and share footage/trace hashes with evaluation agent for score audit.

## Scripts

```
PYTHONPATH=src python scripts/probe_dolphin_bridge.py
PYTHONPATH=src python scripts/probe_dolphin_bridge.py --read-only-live
PYTHONPATH=src python scripts/probe_dolphin_bridge.py --send-live-probe --i-understand-active-input
```

The live probe **alters the running emulator** and is best effort; do not use it for scored experiments. Read-only mode is the recommended first step.

## Additional research: emulator-side atomic trace scheduler

The second branch provides a version-pinned *patch generator*, a client, 9 additional offline tests and [setup/testing notes](../../docs/felk-atomic-scheduler.md). This is a candidate response to the separate-RPC timing limitation: two input writes happen inside one emulator coroutine tick rather than two client requests. It is **not yet hardware validated**. Do not merge downstream real-game claims without proof of actual input recognition.

## 2026-10-24 live update: controller test negative; generic savestate feature

- User-provided live atomic bridge response was `state=complete`, `total_frames=15`, `applied_frames=15` (bridge frames 3455–3470), but **no visible game response**. Do not count this as a swing.
- Felk's scripting-preview4 official Python stubs document acceleration in **m/s²**, correcting earlier approximate-g wording. Small 1–2 m/s² trace may be insufficient; do not infer a motion threshold from one negative test.
- New generic named profiles and `StateManager` allow slot 0..99 capture (explicit overwrite) and reload by name; registry remains local and untracked.
- `scripts/savestate_session.py` provides register/list/capture/reset/start; script generator accepts `--startup-profile` or `--startup-slot` for optional one-shot state restoration after script starts.
- New `scripts/probe_wiimote.py --send-live-button --button Plus` is an explicit visually audited Wii Remote connection check. Controller input must be observed in-game.
- **Ten targeted tests and CLI register/list smoke passed in local sandbox.** Neither named savestate reset nor startup auto-load nor button test has been tried on user's Dolphin yet. Guide: `docs/savestate-workflow.md`. Issue #2 remains open.


## 2026-10-24 next step: recognized golf swing after confirmed Wii Remote routing

- User visibly confirmed Python A now works when Wii Remote 1 is **Emulated** and Extension **None**, removing the unexpected Nunchuk warning.
- Integration-owned optional `trace.submit_swing` based on Felk's documented Preview4 swing primitive, generated with `--enable-swing` and tested by `scripts/probe_swing.py` (one human-authorized shot, optional named reset).
- `docs/first-swing-experiment.md` explains local setup, expected dispatcher ACK vs game-visible hit, bounded motion parameters, and local recording. **No live swing trial run or user observation exists for this new experiment yet.**
- Continue to coordinate physical calibration with Issue #4 and automatic scoring/collection with Issue #3.

## 2026-10-24 one-command training session launcher

- User requested eliminating manual Felk Dolphin startup, Scripting attachment and separate named savestate load before every live AI trial. New `scripts/launch_golf.py` invokes existing `savestate_session.py start`, defaulting to already-generated `tools/mcp_bridge_swing.py` and local named `green-first-shot` profile.
- Wii Sports game path unknown: on first execution prompts for actual RVZ/ISO path and writes only `research/launch.local.json` (gitignored); later runs need only `py scripts/launch_golf.py`. Optional `--swing` runs one explicitly user-confirmed trial after launch/reset. Does NOT save/overwrite states or repeat experiments unattended.
- Tests: offline mocks added to `tests/test_integration_launcher.py`, **not executed in current GitHub connector environment**. The single-command startup restore is an experiment to validate on Windows; don't claim success just because request ACKs.
- Full instructions: `docs/one-command-launch.md`. Next user action: pull main, run focused tests and one launcher start; report whether Wii Sports comes up on correct saved screen.

## 2026-10-24: Dolphin controller mode is a launch-time invariant

- **Live human observation:** one-command Felk Dolphin startup succeeded and restored a state, but it came up using **Real Wii Remote** instead of **Emulated Wii Remote** even though the prior AI A-button test worked when emulated with Extension=None. Thus startup success alone cannot certify controller readiness.
- **Upstream source facts:** Dolphin's `WiimoteSettings.cpp` uses `[Wiimote1] Source` (1=Emulated, 2=Real), and `CommonPaths.h` uses `WiimoteNew.ini`. Extension=None removes Nunchuk. Python pre-launch must update the EXISTING user settings file before the emulator loads it; never create a new Dolphin user profile and lose existing savestates.
- **Implementation staged:** new `integration/dolphin_controller_config.py` with conservative config resolution, surgically preserve key bindings, set Source=1/Extension=None, idempotency and one-time backup. Launcher `scripts/launch_golf.py` now refuses a busy bridge, requires correct controller settings before spawning, logs mode/path/backup, and remembers an explicitly selected `--dolphin-user` path in locally ignored config. Focused offline tests added; **not yet user-verified or full-suite-tested**.
- **Experimental gate:** before `--swing`, verify controller UI reads Emulated Wii Remote 1 / Extension None and savestate is the intended slot. A changed INI is not a direct runtime controller-state measurement. If still Real, inspect which Dolphin user folder and per-game GameSettings overrides are loaded.

## 2026-10-24: prevent stale editable Python installs breaking every new bridge module

- **Negative user evidence:** after a successful Git pull to new `main`, `py -m unittest discover -s tests -p "test_integration_launcher.py" -v` and `py scripts/launch_golf.py --slot 2` both fail on Windows `ModuleNotFoundError: wii_ai_golf.integration.dolphin_controller_config`. Same earlier regression occurred with `swing_patch`. Git checkout is current but pip editable installation resolves to a *different source checkout*, and scripts run without adding their local `src` to `sys.path`.
- **Root-cause fix:** Worker 1's eight owned CLI entrypoints prepend the path resolved from their OWN `__file__` (`<repo>/src`) before any package imports; launcher's `savestate_session.py` and `probe_swing.py` subprocesses bootstrap independently. Test files `test_integration_launcher.py` and `test_integration_controller_config.py` also prefer checked-out source during Python's unittest discovery without `pip install -e .`.
- **Regression evidence plan:** new `test_integration_source_bootstrap.py` launches each CLI from a temporary unrelated working directory with a **fake stale `wii_ai_golf` package** on PYTHONPATH; also verifies isolated Python `-I` startup. This tests the exact import-shadowing class of bugs rather than assuming install state. Integration with actual Windows interpreter requires host tests.
- **Scope boundary:** scripts under other workers (e.g. evaluation collector or modeling sweep) remain their ownership; notify teams to use the same explicit source-priority bootstrap or package entrypoints when needed. All changes only modify source and tests, not Dolphin savestate/profile bytes.

## 2026-10-24: first qualitative motion recognition, A release too early

- User reports that the `probe_swing.py` dedicated Felk swing **almost worked** but the A button released before the club completed movement. This is qualitative human-reported partial swing response, **not a confirmed golf-ball strike**. Earlier 15-frame acceleration trace had no visible response; the new dedicated swing path progressed further.
- Original trace held A for 12 setup + 15 backswing + 20 forward = 47 frames, then released for 12. Focused change adds `--follow-through-frames` (default 30, range 0..180) after forward motion, keeps `A=True` with neutral dedicated swing during this phase, and retains a final 12-frame release. The default has A held for 77 frames and a total 89 samples. No changes to swing direction, strength, source bridge patch, menu intro or transport.
- Source-level regression tests cover exact A transition timing, all presets, return to old behavior with `--follow-through-frames 0`, input rejection, 600-frame budget, and live-sourced shape via existing client mock; Windows user tests and new in-game observation still pending.
- Modeling Issue #4 owns physical swing calibration; Worker 1 only varies timing initially to prove a repeatable hit. Other Worker 1 PR #25 owns standard menu intro and must not be overwritten. Parent PR handoff: `docs/first-swing-experiment.md`.

## 2026-10-24: fix repeated bare-probe connection refused and enforce intro contract

- Live negative evidence from user: `py scripts/probe_swing.py --preset forward --follow-through-frames 30 --send-live-swing` failed with `[WinError 10061]` because the previous probe immediately connected to 127.0.0.1:55355 when Dolphin/bridge was not listening. No shot dispatched, and no new club/ball behavior observed. User reiterates **all** normal runs must launch Felk and restore Slot 2 with the A -> pause -> A+B -> pause -> A known-good menu sequence, not bypass intro.
- Reused **already merged** PR #25 canonical `launch_golf.py -> launch_hitting_green.py -> menu_sequence.py` for controller config, Dolphin process/bridge startup, registered `green-pre-start` Slot 2 restore, known-good menu button dispatch and settling. **No reimplementation or hard-coded new menu delays**. Newly changed `probe_swing.py` delegates to `launch_golf.py --swing` by default instead of making a premature RPC call. The launcher now passes `--attach-running` to the child swing probe (no recursion), plus explicit `--follow-through-frames` and `--remote`; direct attach is an ADVANCED opt-in only for a confirmed ready-running game.
- Test additions: `tests/test_integration_swing_startup.py` asserts bare swing requires a full launch delegation without any initial FelkRPC; tests cover Slot 2, motion delay forwarding, dry-run, bad reset/options and child error propagation. Extended `test_integration_launcher.py` asserts the intro precedes an attached swing; `test_integration_source_bootstrap.py` now also covers `launch_hitting_green.py`. Tests are source-committed **not executed on user's Windows runtime yet**.
- Correct operator next step: close Dolphin fully; from canonical checkout pull main; run focused tests; `py scripts/launch_golf.py --slot 2 --swing --follow-through-frames 30` or equivalent `py scripts/probe_swing.py --slot 2 --preset forward --follow-through-frames 30 --send-live-swing`. At ENTER confirm visibly at ball. Report whether club moved/ball hit. The correct fallback for a knowingly running game is explicitly `py scripts/probe_swing.py --attach-running ...` but NOT the default training path.

## 2026-10-24: button-before-motion timing regression after unified CLI

- **Live user observation:** `py scripts/golf.py swing --slot 2` ran Felk startup and canonical A/A+B/A menus correctly. User later clarified the swing attempt visually **swung too early**, with club motion happening before the in-game A press. This is not a verified new ball hit; it suggests A press registration/latency race even when an earlier human-observed 89-frame forward trial struck the ball.
- **Single-factor hypothesis:** default `build_probe` begins with only 12 A-held neutral frames, then sends nonzero `set_wiimote_swing` for 15 backswing +20 forward. Increase neutral A setup to 45 samples (1..180 configurable), keep follow-through 30, physical swing shape identical. CLI `--a-setup-frames` propagates through `golf.py` -> `launch_golf.py` -> attached `probe_swing.py`; retains full fresh boot/Slot 2/canonical menu phase invariant. New default 122 frames; old known-good 89 can be replayed using `--a-setup-frames 12`.
- **Verification plan:** offline unit tests assert all A setup samples have zero motion, first nonzero swing sample occurs only after setup, timing bounds, exact old trace reproduction, and argument forwarding through canonical launch and fallback. **No new real-game hit or score is claimed** until user validates onscreen. If longer prep fails, investigate intra-bridge A press recognition instead of changing swing speed/strength. Preserve full observation JSONL with timing metadata.

## 2026-10-24: failed 45-sample in-trace A prehold; real button-only priming trial

- **Confirmed negative user evidence:** After fresh canonical Dolphin startup, Slot 2 restoration and A / A+B / A intro, the user explicitly reported **swung, THEN pressed A; ball NOT struck**, even after `--a-setup-frames 45`. Do NOT add it to successful hits. No score/landing measurement from this attempt.
- **Source-grounded failure mechanism:** In `swing_patch.py`, `trace.submit_swing` calls BOTH `controller.set_wiimote_buttons` and `controller.set_wiimote_swing` for each trace sample, including every zero-motion prelude sample. Thus a longer supposed A-only prelude within `build_probe` was **not independent button-only operation**; causal relevance to Wii Sports internals remains a hypothesis.
- **Code correction:** New `integration/button_prime.py::prime_a_button` makes 60 configurable `controller.set_wiimote_buttons(A=True,B=False)` calls **before** `trace.submit_swing` (no motion calls until those requests finish). If priming fails, best-effort release and do not submit any swing; after swing or failure, release A/B. Restore `build_probe` default neutral in-trace setup from 45 to exact human-confirmed first-hit 12; keep 15 back/20 forward/30 follow/12 off -> 89 frame trace; `--a-prime-frames` controls separate priming 0..180, defaults 60, `--a-setup-frames` controls in-trace neutral samples defaults 12. API output logs requested priming separately from frame dispatch and human outcome.
- **Tests added/updated:** `test_integration_button_prime.py` explicitly mocks Felk RPC order and insists no `trace.submit_swing` before 60 A-only requests, exactly 89-frame payload and no physical motion change, fail-closed if A prime errors, release after errors. Swing, launcher, canonical startup and universal CLI tests updated to ensure no accidental behavior change. Offline tests COMMITTED but awaiting Windows host execution.
- **Next user attempt:** close Dolphin; `git pull --ff-only`; run focused suites; `py scripts/golf.py swing --slot 2 --a-prime-frames 60 --a-setup-frames 12 --follow-through-frames 30`. Visual gate is **A visibly engaged before club motion AND ball moved**. If still broken, isolate bridge-side event-generation and button-state sampling; do not keep increasing setup frame count. No new successful shot claimed.

## 2026-10-24: another 60-button-only+89-swing failure; bridge neutral V2 source fix

- **New user output:** `Button prehold completed: 60 RPC requests`; trace `state=complete, id=1, start_frame=1646, completion_dispatch_frame=1735, total_frames=89, applied_frames=89`; human reports A released too early and ball still NOT struck. This is negative actual-game evidence even though Felk completed all controller RPC dispatches.
- **Verified source-level implementation flaw:** Current **generated V1** `_wii_ai_tick` in `integration/swing_patch.py` calls both `set_wiimote_buttons` and `set_wiimote_swing` for ALL samples, including the 12 initial neutral A-held samples, 30 neutral follow-through samples, and 12 A-off neutral samples. It cannot be relied on to hold A without simultaneously resetting/sending a swing primitive. Exact in-game causality remains unproven.
- **New bridge V2 implementation:** `set_wiimote_buttons` still called per emulated frame; `set_wiimote_swing` now dispatched **only for nonzero motion samples**. Preserves A-held neutral tail without swing primitive. Add `trace.swing_capabilities` (read-only) reporting v2; probe refuses V1 before pressing any buttons, and the canonical launcher checks V2 source marker before launching Dolphin. Generated bridge must be **regenerated LOCALLY** after a Git pull; `golf bridge upgrade-swing` supplies known ../tools paths, rejects an already-running bridge, backs up prior generated file, and uses SHA-pinned upstream original.
- **Tests committed:** bridge tick fake controller asserts 35 swing calls and 149 button ticks for 12+15+20+90+12 trial, advertised V2, old bridge preflight failure, source marker fail-before-boot, and CLI upgrade behavior. These mock tests have NOT been executed in the user's Windows setup. Existing native game dynamics may react differently to skipping neutral swing calls, so no contact success claimed.
- **Proposed next ONE shot:** After `git pull --ff-only`, close Dolphin, `py scripts/golf.py bridge upgrade-swing`, run focused tests, then `py scripts/golf.py swing --slot 2 --a-prime-frames 60 --a-setup-frames 12 --follow-through-frames 90`. Report whether A stays engaged until club motion/ball contact and the actual ball outcome. If still a miss, stop changing frame counts and capture synchronized game input state before optimizing power.
