# S001/S002: in-frame selected-ball read preflight for S001 owner

**Status: OFFLINE only, review helper. No live Felk bridge modification, activation, Dolphin runs, extra controller writer, new RPC, file logging, schema publisher, training or operator capture is implemented or approved.**

This is a narrow support branch stacked on the existing S001 frozen swing-phase PR #147. It complements offline temporal evidence gate #165 and source-selected static player/ball PRs #160/#163. Neither existing collector, player-source parser nor the game testing launcher has been changed.

## Exact source integration point (not an instruction to execute live)

In pinned mcp-dolphin bridge upstream source the single coroutine calls await event.frameadvance(), increments _frame_count, then polls sockets. Our existing atomic patch inserts _wii_ai_tick() **between the increment and socket polling**. This makes _wii_ai_tick the only appropriate integration site if S001 later implements an explicit opt-in read, pre-dispatch before set_wiimote_buttons and set_wiimote_swing/accel. Do not launch a second polling RPC, replace the installed script or introduce another controller writer.

Upstream bridge already exposes native memory.read_u32(address) through its single coroutine. That is the ONLY operation the helper requires, along with a callback returning bridge _frame_count (read twice). There are no writes or low-level emulation.pause calls. The helper DOES NOT install itself in the frame loop. In a future approved integrated bridge, S001 can review/inject the small core function in the very same script with the original version pin retained, using a single callback invocation at a human-approved stage. Do not use an imported host Python module blindly inside embedded Dolphin; exact Felk Python environment and source version must be checked first.

**Critical provenance:** _frame_count is a bridge callback counter following event.frameadvance(), not independently certified as CPU/game emulated-frame timing or in-game button application. A same-tick 0-frame span is NOT proof the memory read costs less than one real emulated frame. Measure callback wall-clock latency and instrumented vs uninstrumented A45/V1 trace performance before any same-shot experiment. S001 PR #147's 0..88 indices are controller command indices, not ball physics frames. PR #165's frame_start/frame_end must not be populated from raw bridge ticks without explicitly validating the relationship.

## Read-only S002 source chain and bounds

New file src/wii_ai_golf/integration/ball_watch_preflight.py contains an injected function sample_pre_dispatch(read_u32, bridge_tick, stage, source_contract_reviewed=False). Source review flag defaults to False and must only be explicitly provided by S001 after reviewing source/field owner and operator consent.

It reads only known Rev1 addresses:
- Game MEM1 RSPE01 Rev1 two-word header; static scene manager -> MEM1 manager Golf scene ID5 -> MEM2 scene own ID5, sport2, manager backlink and unit data interval.
- RPGolConfig singleton source mode4/raw hole index bounded.
- RPGolFieldManager -> current start object -> self-pointing translation vec at +0x4C/+0x30.
- RPGolPlayerManager static candidate -> MEM2 manager data interval; selected record pointer manager+0x334 must equal manager+4+slot*0xCC, slot0..3.
- Selected record+0x88 ball-related object whose first word is in documented RPGolMapObjBall .data; that object's +0x4C pointer to 3 source-related VEC3 words.
- Four PRIVATE 3-word arrays: selected nested-ball translation, current-start translation, selected record+0x54..+0x5C and +0x60..+0x68.
- Rechecks selected-record selector, selected ball pointer, nested destination and current-start object after the vectors; any change or wrong bank fails closed. 48-word maximum (no arbitrary RAM scan).

Returned evidence dictionary contains raw words, runtime object addresses and bridge callback ticks. **It is PRIVATE ONLY.** It MUST NOT be sent over RPC, printed in public console, stored in GitHub, submitted through an existing publisher or copied into a public report. S000 must approve a separate typed sanitized evidence schema if future samples are to be shared, and S001 must handle private storage. The helper makes no IO and no remote connections itself.

## Test and owner acceptance plan

15 synthetic fake-memory tests in tests/test_ball_watch_preflight.py cover source positive, bounded word budget, no controller modifications, default opt-out, wrong game/scene/mode/sport, bad vtable/unit data interval, wrong slot selector, start selfpointer mismatch, object relocation during one read, bridge callback tick changed, native reader exception privacy suppression, bad read type and source label. Windows/Linux focused CI is included. No real game RAM read by this helper and its exact source path was not independently accepted by S002.

S001 may later create *one* opt-in caller within its existing Felk frame coroutine, but only after:
1. S002 #160/#163 explicitly signs off on source/selected slot and ball-related owner offsets (0x88, +0x4C).
2. S001 proves source-pinned generated bridge identity, measured per-read overhead (<2 actual emulated frames under observed control, not estimated from tick equality), stable known-good V1 89-sample and A45 behavior, and no duplicate controller setters or RPC client.
3. S000 reviews any local recorder output shape and rejects unreviewed raw publication; full Windows regression at final head plus all bridge/swing patch tests pass.
4. Operator specifically authorizes ONE real in-game control trial after the above. No live run is authorized by this PR.

In the first real test use time-matched no-shot controls plus independently witnessed ball move; compare selected ball-related nested vector to immutable field current start and record vectors. Dynamic correlation alone still does not prove world XYZ, velocity or physical power.

## Optional offline unit test (no Dolphin)

From an isolated worktree of the PR, run the focused synthetic tests:

    py -m unittest discover -s tests -p "test_ball_watch_preflight.py" -v

Then the full regression suite:

    py -m unittest discover -s tests -v

The helper is not an operator-facing live command. The only safe immediate activity is offline tests and S001/S002/S000 review.


## Generated swing-tick parity proof (synthetic; not a live measurement)

A second new test file, tests/test_ball_watch_swing_tick_parity.py, builds the actual generated patch source using the canonical source-pin patch_bridge() and extend_atomic_bridge_with_swing(), extracts its real _wii_ai_tick() AST, and executes that exact generated tick against a fake controller. It compares two executions of a fabricated 4-sample A-held swing: baseline unchanged tick, and observer invoked BEFORE the unchanged tick. A third case injects native memory-read failure into the observer and deliberately discards the invalid sample.

All three cases require byte-identical (list-equal) controller call order/arguments and trace.submit_swing acknowledgment + trace.status outcomes regardless of added observer or failed observation. They also assert that frame-tick labels remain unverified game frames. This tests **logical controller noninterference**, not real bridge callback wall-clock cost, emulated-frame jitter, game-applied A, actual contact or live phase alignment. Do not confuse the fabricated four-sample test trace with the frozen 89-sample V1 in #147.

The branch has 18 focused synthetic tests in two test files, and CI runs both on Windows and Linux. No live bridge or public result was produced. Because the in-frame helper returns raw PRIVATE word arrays, the S001 caller must never print or automatically publish its dictionary; a future private recording mechanism and S000 typed sanitizer remain separate owner work.
