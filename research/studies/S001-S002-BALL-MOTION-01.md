# S001/S002 BALL-MOTION-01: opt-in selected-ball frame watch

This is a DRAFT integration experiment. No live Dolphin action has been executed by this author. All new paths, no edits to existing bridge/controller/roster owner files. The user explicitly requested one swing with position-memory observation, but owner review and Windows safety tests are required before activating it.

## Evidence basis

Existing private RSPE01 Rev1 MEM1/MEM2 and S002 PRs #160/#162 identify four player records spaced by 0xCC, source-selected record index 0, its record+0x88 ball-like object, nested ball+0x4C translation pointer and FieldManager current-start translation accessor. All three components of selected record position, ball object translation and current start vector match in ONE unique still state. Duplicate preserved pairs are bitwise identical, not independent observations. This does NOT establish actual ball motion or world axes.

## Implementation

- src/wii_ai_golf/integration/ball_watch_patch.py extends the existing pinned Felk Swing V2 generated source, with one extra read-only sampler invoked before the unchanged existing _wii_ai_tick inside the same frame coroutine. Zero new controller calls, threads, sockets, or waveform modifications.
- New opt-in RPC methods golf.ball_watch.arm, .status and .drain. Source gates each sample on RSPE01 Rev1 header, manager/scene5/sport2/backlink, config mode4, current hole, PlayerManager source data interval, source-selected slot, ball firstword region, nested translation self-pointer, current-start self-pointer. Bounded MEM2 read_u32 calls obtain selected ball, record and start vector triples.
- Up to 80 observations, configurable bounded timer with pre-dispatch tick index and optional commanded swing sample index. 5ms sampled-read budget auto-disarms without disrupting controller dispatch. A read inside one coroutine tick is NOT verified CPU/video game-frame atomicity, nor proof that A was game-applied in that tick.
- scripts/prepare_ball_watch_bridge.py creates a NEW .py source outside Git; never overwrites the installed working bridge.
- scripts/record_selected_ball_swing_private.py accepts only explicit --attach-running --send-live-swing for game input. One RPC connection. At ready ball operator types SWING. Sequence: 24 read-only no-button RPC frame-count calls, 45 A-button-only prime calls, unchanged 89-sample forward Swing V2 trace, 36 posttrace frame-count calls. Button cleanup in finally. Human yes/no/unknown observed motion prompt.
- Numeric vectors, requested input trace result and per-frame timing are saved only as a new -PRIVATE.json under ignored sibling Wii-AI-Golf-Data/captures. Console prints only aggregate booleans/counts and no raw coordinates or pointers. No GitHub publication or training.

## Offline Windows tests, no Dolphin

    $root = "D:\Projects\Wii Golf AI"
    $repo = "$root\Wii-AI-Golf"
    $work = "$root\Wii-AI-Golf-Selected-Ball-Frame-Watch"
    git -C $repo fetch origin
    if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
    if (Test-Path $work) { throw "Do not overwrite prior worktree" }
    git -C $repo worktree add --detach $work origin/agent/integration/selected-ball-frame-watch-20261027
    if ($LASTEXITCODE -ne 0) { throw "Worktree failed" }
    Set-Location $work
    py -m unittest discover -s tests -p "test_ball_watch_*.py" -v
    if ($LASTEXITCODE -ne 0) { throw "Focused tests failed" }
    py -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "Full suite failed" }
    py scripts/record_selected_ball_swing_private.py

## Preparation after S001/S000 owner review and test PASS

Do NOT run another Dolphin process concurrently. Offline bridge generation from the existing reviewed V2 generated bridge:

    $old = "$root\tools\mcp_bridge_swing.py"
    $new = "$root\tools\mcp_bridge_ball_watch.py"
    if (-not (Test-Path $old)) { throw "Original bridge absent" }
    if (Test-Path $new) { throw "Experiment bridge already exists; preserve it" }
    py scripts/prepare_ball_watch_bridge.py --source $old --output $new

Only with the user at the keyboard ready to start ONE test:

    py scripts/launch_golf.py --bridge $new

Visually confirm the ready first ball, then in this research worktree:

    py scripts/record_selected_ball_swing_private.py --attach-running --send-live-swing --a-prime-frames 45

The operator will explicitly type SWING to authorize the controller input and then report if the visible ball moved. Share only sanitized console summary, never the private numeric JSON.

## Promotion gates

First confirm stationary negative-control vector, stable current-start marker, stable source-selected slot/hole, then visually verified ball movement correlated to a ball-vector change. Verify read overhead and intact known-good contact behavior. Repeat across independent clean boots and distinguish actual guest frame time from scheduler tick before assigning physics meaning. None of this proves XYZ units, active human ball, velocity, impact/contact timing, or swing power. All model-training permissions remain false. Abort on gate failure, too-slow sample, inconsistent scene, or failed tests.

S001 owns canonical bridge/swing; S002 owns source fields; S000 owns privacy; S003 models only after causal verification. No extra full-RAM scans, savestate creation or automatic publication.


## First actual operator trial: no visible ball movement, incomplete watch

The operator ran the opt-in watched Swing V2 session and reported visible ball movement NO. Sanitized output: 50 bridge callback ticks sampled (18 pretrace, 22 active trace, 10 after); candidate ball translation unchanged all 50; selected record vector equals nested ball vector in all 50; start, selected slot and hole stable. This is an internally consistent stationary negative result, NOT proof that the vector senses an actual moving physics ball.

Important scientific defect in ORIGINAL version: the watch requested 256 frame-callback ticks but runner drained at ~200, with just 50 observed samples; original runner accepted a nonterminal recording status. Therefore treat this capture as PARTIAL exploratory no-contact, not a complete temporal study. The exact private status was not supplied; incompleteness is inferred from source loop behavior and sample count.

### Fixes on same draft PR #166

- Bridge refuses to drain unless terminal state is complete. Runner now performs bounded read-only polling to completion; no partial positive studies.
- Stage tags idle_control, a_prime, trace, posttrace separate button-only priming from genuine idle control, still without proving game-applied A or contact.
- Across-sample owner tuple validated only inside bridge; all heap pointers are stripped before RPC.
- Exact 89-sample canonical waveform SHA256 b63a1818ba5086c64b0fe7338236a498240e4be97bbd111809a772d783699891 checked prior to any input, not just sample count.
- Temporal summary accepts a positive candidate only with terminal complete state, >=2 idle control samples, stable pretrace, stable source identity, stable start/hole/slot, acceptable read overhead, stable non-null trace ID, all four stages, ball candidate change after active trace begins and explicit human ball-moved YES. Still not world coordinates, ball velocity, impact or power.
- New code passed 19/19 synthetic tests Windows and Ubuntu in CI run 40615327108. Full canonical Windows suite and instrumented-vs-uninstrumented actual shot parity remain unverified; owner approval is still required.

### Next task: restore ball contact

Earlier repository docs/bridge-compatibility-audit.md records successful game-visible contacts with an earlier V1 bridge and later no-contact sessions under modified Swing V2, but this is confounded, NOT proven causation. Request offline local source audit with scripts/audit_local_swing_bridge.py, and learn whether the club actually animated and A was held. Do not repeat a blind live shot or change power until canonical input/contact works consistently. Position traces from no-hit sessions cannot calibrate moving ball, and model training remains disabled.
