# Integrator research — protocol verification and priorities

Research date: 2026-10-24; status: **external code inspection + offline mock tests only**.

## Confirmed from published primary sources

1. Dolphin's [controller guide](https://dolphin-emu.org/docs/guides/configuring-controllers/) documents emulated Wii Remotes, motion bindings and alternate inputs; ordinary controller mapping does **not** by itself expose a stable public Python automation API.
2. The upstream [mcp-dolphin 0.2.0 changelog (2026-05-19)](https://github.com/dmang-dev/mcp-dolphin/blob/main/CHANGELOG.md) adds `dolphin_set_wiimote_acceleration`, pointer and angular velocity. Its [Python bridge source](https://github.com/dmang-dev/mcp-dolphin/blob/main/bridge/mcp_bridge.py) actually exposes JSON-lines over loopback TCP 55355; requests look like `{"id":1,"method":"bridge.ping","params":[]}` and return `result`/`error`. The bridge script runs **inside Felk's scripting-enabled Dolphin**, not stock Dolphin.
3. The same bridge implements `controller.set_wiimote_buttons`, `controller.set_wiimote_acceleration`, `frame.get_count` and `bridge.ping`, and processes socket messages while its emulator coroutine advances frames. Its commands are cleared on the next frame; two separate calls may be delivered on different frames. Pausing the emulated game can deadlock response handling. **A TCP client cannot promise frame-perfect simultaneous A + acceleration using the existing RPC interface.**
4. Nintendo's [original Wii Sports Golf instructions](https://www.nintendo.co.jp/wii/rspj/5sports/golf.html) describe holding **A** while swinging to take a real shot. The [Hitting the Green training text](https://wiisports.fandom.com/wiki/Golf_%28training%29) likewise mentions holding A to approach the ball. This makes atomic button+motion replay a critical integration hypothesis, not an optimization detail.
5. Dolphin's [2503 progress report](https://dolphin-emu.org/blog/2025/03/10/dolphin-progress-report-release-2503/) describes a revised Wii Remote TAS input recording format, worth assessing as a deterministic replay alternative, though generating compatible DTMs is out of current scope.

## Candidate pathways ranked

| Path | Benefit | Main limitation | Recommendation |
| --- | --- | --- | --- |
| Felk scripting + v0.2 bridge | Direct frame counter, remote buttons and accelerometer; inspectable protocol | Frame-atomic multi-channel events not exposed; Felk version sensitivity | Start here: safe read-only preflight, then add tested atomic sequencer if needed |
| Mainline Dolphin controller mappings / DSU | Stable GUI-supported emulated remote mappings | DSU timing, action reset/score extraction and API complexity | Secondary fallback |
| TAS recording/DTM replay | Potentially deterministic long traces | Format and Wii Remote state complexity; not an interactive online environment | Investigate only after first successful manual trace |
| Real Wii Remote via Bluetooth | Reproduces human control path | Hard to optimize or replay repeatably from code | Calibration reference, not first automated backend |

## S001 experiment plan (not executed)

**Question:** Do repeatable control traces drive actual ball-contact events in Hitting the Green with A held, and do different acceleration profiles change resulting shot power?

- Preregister three treatments on one fixed shot: A-only + neutral acceleration; impulse without A; combined A+acceleration, followed by at least three distinguishable combined profiles if any swings register.
- Begin with 30 total attempts, interleave treatments and use a predetermined seed/order; document every reset, missed swing, frame drift and failure. Do not exclude failures from denominator.
- Save screen-recording hashes and raw input traces. Ask evaluation agent for score units and 30 double-annotations; do not self-certify score extraction.
- If RPC command acknowledgement-frame separation is nonzero/variable, switch to an atomic sequencer *inside* the emulator loop before trusting game results.
- Success is a measured, replayable, real game swing, not a working mock.

## Reproducible code evidence

Use `PYTHONPATH=src python -m unittest discover -s tests -v`; 21 passing tests cover the transport and simulated orchestration. `scripts/probe_dolphin_bridge.py` defaults to mock mode; `--read-only-live` checks the live scripting bridge without modifying game inputs. Live input requires an explicit second flag. The code intentionally does not fetch or manipulate game ROMs.
