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

## Passive A-state text (automatic, evidence-gated)

The header displays **A PRESSED**, **A RELEASED** or **A UNKNOWN**. There are **no A-specific buttons, reset controls or on-screen calibration prompts**. Simply connect the inspector to the already running, source-qualified read-only bridge and use your controller normally. The viewer **does not press A**, write memory or start Dolphin.

A native game-owned instantaneous A bit has **not** been identified. The original human-labeled A-only blind trial in PR #396 distinguished three blind windows after 3/3 heldout checks in one boot, before an aim-change abort. The prior training UI asked the user to repeat seven calibration windows; that was not the requested interface. Instead this version can *silently load the previously completed local A-state experiment* from the sibling **`Wii-AI-Golf-Data/captures/p0-a-state-blind-*-PRIVATE`** directory (relative to the inspector worktree). Original private files are **read-only**, bounded, never uploaded or stored in Git, and a valid SHA-256 manifest, original 7-window R/H calibration, 3/3 withheld checks, and independently correct pressed/released blind truth labels are all required. The original study's final `ABORTED` status from a later aim change is permitted only when the earlier full calibration and blind windows are intact and SHA verified. The detector uses these *actual privately observed words*, not hardcoded arbitrary values.

The local reference must match **the current source identity**. Two consecutive consistent read-only selected player records are required before showing PRESSED or RELEASED. If no validated original trial exists, Dolphin is from a different source epoch, no reference can be matched, ball/aim changes invalidate a record, memory readings disagree or are stale, or the study has not actually verified the native input bit, the viewer reports **A UNKNOWN**. It cannot promise binary detection in new boots without independent repeat evidence. This is a conservative **human-label-correlated memory candidate**, not proof of game A acceptance or a zero-latency hardware input state. `training_approved=false`.

The 51-word selected-player scan, source gates, post-scan ball+aim checks and GUI thread safety remain read-only. To minimize overhead, this extra scan is enabled only when a usable verified local reference was found. The original long UI calibration controls have been removed entirely; there is no unobserved automatic assumption that A is released at launch.

## Readout placement and faster source-gated polling (v4)

- The status is **always text**, including offline/connecting: prominent **A UNKNOWN**, **A PRESSED**, or **A RELEASED** immediately below the top connection line **and inside the upper-right corner of the 3D plot**. No A calibration buttons and no player model. A binary A status requires a SHA-verified local trial from the current source identity; if absent or after an aim/ball/scene change it remains UNKNOWN. This is not a verified universal game-owned A latch.
- The live inspector now defaults to an **inspector-local batched reader** matching the canonical source-gated P0 packet's word names, pointer/scene/Rev1/selected-player checks and before/after source epoch checks. It replaces ten 3-word vectors with ten `memory.read_bytes` calls rather than thirty scalar `memory.read_u32` calls. The optional 51-word A candidate record is now a single bounded 204-byte `memory.read_bytes` call instead of 51 separate RPCs, and the post-record ball recheck uses one bounded 12-byte read instead of three. The host brackets still cover non-atomic sequential operations, not guest frame/physics.
- The top LIVE line displays measured achieved **samples/s**, full **read cycle ms**, and **RPCs per sample**, to distinguish polling sleep from actual bridge latency. The pause remains 150 ms; reducing sleep cannot overcome bridge-side round-trip delay. Real-world sampling improvements must be measured locally; 600 ms before optimization is an operator observation, not an offline benchmark. The bridge polls on Dolphin's emulator thread and can stall if paused.
- Fail closed on malformed/short/non-hex read responses, source identity changes, post-probe ball/aim changes or RPC disconnects. No write, controller or pause/launch operations. No background recorder, training or capture publication. If your local bridge does not support these bounded byte reads, the inspector reports a source/bridge failure instead of presenting stale data; diagnostics can be run with the existing canonical collector separately.

## Private collision terrain overlay — opt-in experimental

The operator's original, SHA-verified numbered phase-7 MEM1/MEM2 captures independently yielded one source/scene-qualified **MEM2 file-style KCL candidate with 2,498/2,498 prism triangles reconstructed**, no invalid records, source component spans approximately 3373.222, 192.513, 4258.662. This is an operator-run result (not a repository fixture). It is **not** yet evidence of matching the visible terrain mesh, collision contact semantics, axis calibration, or tee/pin alignment.

Once an **independently source-gated private offline extractor** has written a local ASCII OBJ containing only lines `v x y z` and `f i j k` with plain positive triangle indices (no textures/materials), open the existing inspector and click **Load PRIVATE terrain OBJ**. The viewer deliberately does **not** scan RAM or launch Dolphin to obtain terrain; it merely reads the operator-selected local file from outside any Git checkout. There is no automatic filesystem search, network upload, memory write, texture interpretation or training feature.

The checked file is SHA-256 hashed in memory, bounded to 16MiB / 90k vertices / 30k faces, and nonfinite coordinates, invalid/degenerated faces, symlinks and OBJ extensions (including texture/material references) are rejected. The renderer draws at most 1,200 deterministic, decimated triangle outlines under the existing ball/cache/tee/pin/aim markers. **Show** toggles the overlay; **Focus tee/flag** defaults on and selects source-component horizontal-nearby triangles, otherwise the full mesh is decimated and fitted. Existing right-drag camera orbit is unchanged. **Clear terrain** drops the loaded data from memory; the original private file is untouched.

This overlay deliberately assumes **identity transform in the source component 0/1/2 coordinate system** and visibly reports **UNVERIFIED VISUAL ALIGNMENT / physics**. Proximity to a tee/pin is useful falsification but not proof; a different course/model transform may put geometry outside the source marker frame. A missing source-qualified sample hides the wireframe. No guessed player location is introduced. Do not commit the local OBJ or native RAM to Git. Training remains disabled. The inspector branch does not create the private OBJ; the separately owned KCL study must validate the export before declaring the layer calibrated.
