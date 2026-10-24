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
