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
