# P0 offline memory inspector (experimental, read-only)

An offline + operator-opt-in live Tkinter viewer for source-gated **candidate** memory observations. It does not start Dolphin or send controller/game-write commands; it attaches read-only to an already running bridge only after the Connect button is pressed. It does **not** establish actual ball world XYZ, screen coordinates, physical velocity, frame timing, game accepted A, contact or power. `training_approved=false` always.

## Windows PowerShell — one-paste launcher

From the Wii-AI-Golf repository directory after the inspector PR has been merged (or from this branch), paste:

```powershell
py -I scripts/p0_memory_inspector.py
```

Use the two **Browse** buttons to choose your existing LOCAL event JSONL and matching SHA-256 manifest, then click **Verify SHA-256 and Open**. Both files remain local. No ZIP, separate Python code, game startup or console memory dump is needed. Optional command arguments are `--capture "<local-file>.jsonl" --manifest "<local-manifest>.json"`. The viewer requires standard Python Tkinter on Windows; it is not supported on headless CI.

## Schema / integrity

The pinned replay schema matches `scripts/p0_live_directional_aim_series.py`: one JSON object per line with `phase`, `sample_index`, `start_monotonic_ns`, `end_monotonic_ns`, `source_identity_digest_private`, `source_layout_qualified`, and `candidate_words_private_be_u32_hex` (field names -> arrays of exactly eight-digit hexadecimal BE u32 words). The original complete SHA is verified **before parsing**. The manifest must explicitly supply an unambiguous `sha256`, `capture_sha256`, `jsonl_sha256`, `event_stream_sha256`, or a matching `files` / `artifacts` entry with `path` / `filename` and `sha256`; `capture_file` if present must match. Invalid hashes fail closed. The archived `manual-a-miss-v1` stream is also accepted: mixed `operator_phase_marker`, `human_visual_observation`, and 46 `candidate_sample` events; `private_sha256` in the original ABORTED manifest, legacy monotonic host timestamps and owner-digest key. Its five control phases (I0/AH/AR/M0/I1) and six M1 HIT-associated packets are kept separate; all M1 packets are marked QUARANTINED. This matches the published schema and synthetic tests; the actual private original has not been mounted or replayed in this session.

Per-word IEEE-754 float32 is only a *hypothesis*. Non-finite candidate floats cannot be plotted but their raw hex remains visible. Records without source qualification are displayed with a warning; source identity switches break visual trajectories. M1 contact in an aborted run is only human observed; the exact impact frame is unknown. A malformed final partial JSONL packet is flagged incomplete and earlier verified complete records remain visible. Malformed earlier packets fail closed. A 32 MB / 30,000-sample bound applies to offline loads.

## Controls

The left panel shows phase segments and raw aim hypothesis with a manual baseline; the middle panel has a scrubber and rotatable orthographic **3D source-component** trajectory with selected ball +0x30 white, cache +0xCC amber, a cyan **PIN / FLAG (candidate)** marker and a green **TEE (candidate)** marker when those source-qualified fields are available in the selected sample. **Camera:** hold **left mouse button or right mouse button** and drag on the plot to orbit the source-coordinate view. Releasing either button stops its drag gesture; camera rotation never affects the actual game or memory.

**Aim guide (flag-reference, still experimental):** The magenta dashed guide is anchored to the source-qualified **TEE candidate** solely as a *reference*, never an inferred player location. The *baseline* direction is the tee-to-flag vector, **independent of the ball's current or final position**. On the first qualified capture/live packet, the viewer tentatively assumes the starting aim was directed at the flag and stores the current raw +0x3C BE-f32 as its baseline. If the initial packet was already aimed elsewhere, click **Set aim baseline (point at flag)** only when you've visually returned to flag aim; this replaces the provisional baseline. Subsequent guide directions rotate that tee-to-flag vector by the **change** in the candidate float (Δ+0x3C), not by its absolute value. The **radian conversion and rotation sign remain unverified hypotheses**, and the guide is hidden for absent source/tee/pin/aim or an unrelated source epoch. No player coordinates/body model are read or displayed. The guide's drawn length is 23% of the tee-to-pin horizontal candidate distance; it is not a power or flight prediction.


The right panel retains each raw 32-bit hex and tentative float32. The bottom area warns about elapsed host read duration, non-atomic alias reads, phase-abort status and source identity. 3D rotation **is not a camera-calibrated projection into Dolphin**. The pin/tee are **independent static markers**, not trajectories or verified rendered-object/world coordinates. They are included in plot framing; missing, non-finite or unqualified markers are explicitly noted rather than synthesized. Older captures that omit pin/tee cannot show them. Power remains an unverified candidate and has no percent gauge.

## Testing

```powershell
py -m unittest discover -s tests -p test_p0_memory_inspector.py -v
py -m unittest discover -s tests -v
```

The isolated workflow runs on Windows and Ubuntu with **synthetic fixtures only**. No private game captures/paths, ROM, savestates or screenshots may be committed. Live read-only bridge integration and optional image calibration require separately scoped review and evidence gates.

## Live read-only mode (v1)

The same UI has **Connect LIVE (read-only)** and **Disconnect** buttons. First start a compatible RSPE01 Rev1 Hitting-the-Green scene and the existing Felk bridge by your own operator workflow; then intentionally click Connect. The inspector **does not** launch Dolphin, change game state, send controller buttons, load savestates or record RAM to files. It never connects automatically when the window opens. You may run the same `py -I scripts/p0_memory_inspector.py` command without arguments, then click Connect.

The worker reuses the already-existing source-gated `p0_live_directional_aim_series.packet`, with source-layout checks before and after each packet. A separate `ReadOnlyRPC` allowlist accepts only `memory.read_u32`, `memory.read_bytes` and `frame.get_count`; all controller, memory-write, savestate and unknown RPC calls fail closed. The UI sampling worker is off Tkinter's main thread; the chart trail and pending UI events are bounded. New snapshots stop upon source/selected-player identity changes, bridge errors or disconnection, with **no auto-retry**. The status shows scene 5/mode 4, hole, selected slot, achieved host samples/s, age/staleness and source check. These are source candidates, *not* proven physics or frame-synchronous ball positions. No `Power %` gauge or training approval is added.

This version is verified by synthetic `FakeRPC`/threaded-worker and A-calibration tests only; no live game bridge was accessed by the developing agent. Running it against an actual bridge is an explicit local operator action and remains subject to the project's private-data and evidence boundaries.

## Live A-button indicator (operator-calibrated candidate, v2)

The GUI shows a prominent **A BUTTON: UNKNOWN**, **PRESSED**, or **RELEASED** label in live mode. This is a *memory-derived candidate* discriminator, **not** proof of the game's internal A-acceptance bit or guaranteed instantaneous state. An authentic operator-supervised no-swing blind trial in #396 showed 3/3 correctly withheld truth labels after 3/3 held-out calibration checks within **one** boot/scene, but the run stopped when aim changed and did **not** verify cross-boot generalization or a native button latch. Raw calibration words from that private experiment are **not** embedded in this viewer. The UI therefore starts as **UNKNOWN** and demands local calibration for the current owner/aim/ball context.

1. Start the game and its already-running bridge yourself; click **Connect LIVE (read-only)** in the inspector. No controller input is generated by this software.
2. At the ready-to-hit screen with ball stationary, click **Capture next A window** for each of: **R0 (released), H0 (held), R1 (released), H1 (held), R2 (released), H2 (held), R3 (released)**. After each click, you have **three seconds to focus Dolphin and set the instructed button state**, then maintain it until the UI reports three valid memory samples. Do not swing or aim during calibration. Return to the inspector to start the next window. The inspector never presses/releases A for you.
3. The classifier considers candidate offsets only if they are *stable* within each three-sample window, match repeated R0/R1 and H0/H1 windows, differ across classes, and predict the withheld R2/H2/R3 windows exactly. Any failure leaves **UNKNOWN**, and **Reset A detector** restarts calibration.
4. After successful calibration, the indicator uses **two consecutive matching read-only samples** to report PRESSED or RELEASED; contradictory, moving/stale, unqualified, or epoch-changed data produce UNKNOWN. A changed scene or selected record stops the live worker. The reference ball and aim must remain unchanged from calibration for binary labeling; if you swing or steer, expect UNKNOWN rather than an invented button state.

For each live refresh, the source-gated packet is followed by **51 additional BE-u32 reads** from the selected player record, a post-record source identity recheck and another read of the ball+0x30 and aim+0x3C words; changed ball/aim disables A classification for that packet without affecting the ordinary plotted ball. These are **sequential host reads**, not one atomic physics frame. Sampling may become slower. The viewer never writes game memory, sends A, launches Dolphin, saves snapshots, uploads a private record, or approves training. +0x74/+0x94 and other offsets observed in the prior experiment are not hardcoded as native bits; this session must independently choose its own signatures.

Focused synthetic checks:
```powershell
py -m unittest discover -s tests -p "test_p0_memory_inspector*.py" -v
```
