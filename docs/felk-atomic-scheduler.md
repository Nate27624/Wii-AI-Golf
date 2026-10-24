# Experimental atomic Wii Remote trace scheduler (Worker 1)

**Status: user-reported live 15/15 bridge dispatch on 2026-10-24; no visible Wii Sports response.** Not yet validated as a recognized golf swing or save-state reset. See [savestate workflow](savestate-workflow.md). Issue [#2](https://github.com/Nate27624/Wii-AI-Golf/issues/2).

## Motivation

The published `mcp-dolphin` bridge clears button and accelerometer commands after one frame and handles JSON RPC messages in a coroutine polled once per frame. Sending two separate RPC commands cannot guarantee that Wii Sports sees A held during a swing on the same game frame. See [research notes](integrator-research.md).

This experimental patch modifies the **upstream bridge** to add three RPC methods, applied inside one coroutine tick:

- `trace.submit`: args `[remote_port, [[hold_a, accel_x, accel_y, accel_z], ...]]` — 1 to 600 frames; rejects concurrent traces and invalid accelerations.
- `trace.status`: returns scheduled/running/complete/aborted, dispatched-frame counters and number of applied samples.
- `trace.abort`: clears the active trace and issues best-effort A release.

An atomic scheduler calls `controller.set_wiimote_buttons` and `controller.set_wiimote_acceleration` together for **each emulated frame**. This fixes the *software call ordering problem*, not necessarily motion interpretation, Wii Remote calibration, emulator/device integration, or true game-frame timing. All such claims remain unverified.

## Reproducible local setup

1. Obtain a lawful Wii Sports copy, Felk's Dolphin scripting fork, and a copy of `bridge/mcp_bridge.py` from `dmang-dev/mcp-dolphin` matching the reviewed Git blob **`8e70624680a365707f844b322f5b093746a1c022`** (bridge script reports v0.3.0 at time of research). Preserve upstream MIT license notice.
2. In your repository checkout, run `python -m pip install -e .` then:

```
python scripts/patch_felk_bridge.py --source path/to/mcp_bridge.py --output path/to/mcp_bridge_atomic.py
```

If the upstream blob hash has changed, **the script refuses to patch**. Investigate new source, document its interfaces and pin a new version; don't bypass the check.
3. In Felk's Dolphin, load **only the patched bridge script** through View → Scripting; don't run original and patched copies together on port 55355. Boot the game, keep emulation unpaused.
4. Preflight read-only with `python scripts/probe_dolphin_bridge.py --read-only-live`.
5. For an explicitly acknowledged experimental 15-frame sample sequence, run `python scripts/probe_atomic_trace.py --send-live-trace`. This **changes game input**. Its output confirms only the patched script's dispatch counter, NOT a recognized golf swing.
6. Review whether a held-A impulse makes actual on-screen contact. Check traces across repeats and compare physical/manual swing against synthesized motion, then coordinate score reading with evaluation Agent #3.

## Offline verification

- `tests/test_integration_atomic_patch.py` validates sample rejection, same-tick button+accelerometer order, abort behavior, source-version pinning and Python compile check of generated code.
- `tests/test_integration_atomic_client.py` validates submit/acknowledge/abort/polling logic against a mock extension.
- Full suite: 30 passing unit tests (original 8 + Worker 1's earlier 13 + atomic 9) on 2026-10-24.

## High-priority unknowns

- The simulator may advance frames differently from the scheduler's `event.frameadvance()` callback; verify with screenshots/manual state inspection.
- Felk's `controller.set_wiimote_acceleration` might not map to Wii Sports' expected swing detector under selected Wii Remote emulation options.
- A sustained A press must be confirmed in-game; the bridge returns dispatch status but cannot measure it.
- Repeatable shot reload/state restoration, ball contact and final distance extraction remain undone.

## User-operated live integration evidence, 2026-10-24

- Atomic trace `state=complete`, frames 3455–3470, 15/15 dispatch acknowledgements; user saw **no on-screen response**.
- Independent heartbeat demonstrated ~60 script frames per second; original bridge recovered after restarts. Failure to see a golf swing does not imply IPC failure.
- Felk scripting-preview4 `controller.pyi` documents acceleration in **m/s²**. Earlier 1–2-unit test was **1–2 m/s², not 1–2 g**. Calibration remains an open modeling research question.
- New `--startup-slot` patching option requests one load after the first frame; named catalog and reset/start/capture in `scripts/savestate_session.py` documented in `docs/savestate-workflow.md`.
