# P0 offline memory inspector (experimental, read-only)

An offline Tkinter viewer for source-gated **candidate** memory observations. It is not an experiment runner and does not start/attach Dolphin or send any guest commands. It does **not** establish actual ball world XYZ, screen coordinates, physical velocity, frame timing, game accepted A, contact or power. `training_approved=false` always.

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

**Aim guide (experimental):** The magenta dashed `AIM? (+0x3C)` ray illustrates the existing `aim_candidate_plus_0x3c` raw BE-f32 value **only as a possible radian yaw** in the source component0/component2 plane, using zero toward negative component2. Neither the angle units, reference orientation nor real player facing have been calibrated. Its starting point is the already captured **TEE candidate**, purely a reference marker; it is **not a player location**. No player coordinates, golfer body marker, or 3D player model are inferred or displayed. Ray length is an illustrative fraction (23%) of the source-horizontal tee-to-pin distance, not power, travel distance, swing bearing proof or target prediction. The ray appears only when the same sample has a qualified identity, finite tee/pin triples with nondegenerate separation, and a single finite aim value within [-2π, +2π]. Otherwise the UI reports it unavailable instead of inventing data. This is not an independently verified yaw decoding; use the raw word and the existing manual aim-baseline comparison to assess directional behavior.

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

This version is verified by synthetic `FakeRPC`/threaded-worker tests only; no live game bridge was accessed by the developing agent. Running it against an actual bridge is an explicit local operator action and remains subject to the project's private-data and evidence boundaries.
