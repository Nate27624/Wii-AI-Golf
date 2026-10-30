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


## Live A candidate automatic fallback + reduced source round trips (follow-up)

The operator reported **A UNKNOWN** despite the earlier one-boot blind study and
**~700 ms** full sampling at their local Felk bridge. Prior UI required exact
pointer-derived SHA source identity from a stored private trial, so a new
Dolphin boot or a missing local file could permanently force UNKNOWN.

The inspector now always requests a bounded source-qualified 51-word selected
player record **as part of the same bulk-read packet**, rather than doing a
second series of 51 individual reads. It first prefers the previous
SHA-verified per-session blind trial if the full actor identity matches.
Otherwise, in a fresh ready-to-hit source epoch it uses the *eight selected
player offsets* published by the successful earlier operator trial:
+0x74, +0x94, +0x9C, +0xA0, +0xA8, +0xB0, +0xB8 and +0xC0.

**To see the automatic candidate**: before clicking Connect LIVE, ensure
A is **RELEASED**, and keep A released for the first **two completed stable
samples** (not two display frames). These define a tentative same-boot
RELEASED signature, with no dialogs or A calibration buttons. Afterwards,
a stable **two-sample** change in **all eight offsets** is shown as
`A PRESSED`. A stable two-sample **partial change in 1–7 of the eight offsets**
shows `A RELEASED`, following the operator's observation that the partial
readings they checked occurred while A was released. A stable exact baseline
match also shows `A RELEASED`. This partial→released rule is an adjustable
**operator-specified UI heuristic**, not a proven native A-button latch or
training label. Transient/disagreeing samples, missing source data, moving ball
or aim, actor/scene mismatch, stale or changed source still produce `A UNKNOWN`.
After aim or ball motion, classification resumes once two stable same-source
reads agree; a changed selected actor/scene still requires a new connection.
Motion never by itself means release. The chart's upper-right shows the A status and a
small explanation of the inference mode / reason for UNKNOWN.

**Crucial**: This is an explicit **operator-observation-based candidate**, not
a confirmed native A-button bit. The initial released baseline is a human
operating assumption, not a game-attested input state; starting the viewer
while A is already held can invalidate the labels. No A button commands,
input injection, saved raw private words, power or training approval are added.
Do not use this readout to timestamp game input or train a model.

The inspector's compact source-packet reader groups the four known MEM1
static roots, the player manager, selected player, ball, field, scene and
config into **bounded contiguous reads** and groups the post-packet link
rechecks. This retains the source/actor/hole/type identity validations and
returns the same original candidate fields. Host RPC calls are reduced and
the fixed post-read idle period is now zero, but **actual Dolphin latency is not
predictable from synthetic tests**. The LIVE status provides measured read
milliseconds, RPC calls per sample, and achieved samples/s; the operator
reported approximately 230 ms per complete read on the prior version. The bridge polls on emulator frames, so changing
Dolphin speed or `poll_pause_s` alone is not a substitute for fewer round trips.

## P0 live A recovery and opt-in private KCL terrain (after #408)

**A state:** The existing candidate-only A text now recovers automatically after
ball movement or an aim adjustment: the immediate moving packet is UNKNOWN,
then two consecutive stable A signatures can display PRESSED/RELEASED again
without requiring a reconnect. The original session-local released baseline is
**not relearned from movement**. Changing selected actor/source identity still
requires a fresh connection. The eight-offset classifier remains an observed
correlation from #396, **not a verified game-owned A-input bit**, and must not
be used as a training feature. To bootstrap the candidate baseline, connect
with A initially released; no A calibration controls are added.

**Terrain:** The 3D viewer now includes optional **Load PRIVATE terrain OBJ**,
**Clear terrain**, **Show**, and **Focus tee/flag** controls. Use a locally
source/SHA-qualified KCL-candidate triangle OBJ from the terrain research
exporter, stored **outside Git**. The picker accepts only bounded, SHA-hashed,
ASCII `v x y z` and `f i j k` triangle OBJ; invalid indices, nonfinite or
degenerate faces, materials, symlinks and files in Git worktrees are refused.
Only the operator-selected file is read, and no geometry is uploaded or
extracted from live RAM. The graph draws up to 1,200 triangles offline or 600
triangles while live, behind the existing flag/tee/ball/cache/aim overlays;
right-drag orbit still works. If a source-qualified game sample is unavailable,
the terrain is hidden. The optional Focus filter is an uncalibrated component
0/2 vicinity, **not** a world transform. No fake surface is generated.

The original captures 1/5/7 have operator-reported 2,498/2,498
source-qualified reconstructed KCL prism triangles near tee/pin, but octree
reachability, active physics ownership and visible model alignment remain
**UNVERIFIED**. The separately owned #403/#406 exporter must write the local
OBJ before the viewer can display the actual private terrain. Mesh/texture
assets never belong in the public repo. `training_approved=false`.

**Sampling:** Default post-read sleep is zero; sample interval is still limited
by the read-only source checks and emulator-polled bridge RPC latency. The
user reported ~232ms cycle on #408; no stronger real performance result is
claimed until tested on the user's Dolphin. To improve substantially beyond
that, a separately reviewed bridge-side *single source-gated snapshot* RPC may
be necessary; do not skip source/epoch checks.

## P0 surface coloring / layered object-readiness contract (OGWS original Golf)

The **Color source surface IDs** checkbox controls experimental *wireframe*
colors on individually source-labeled collision triangles. The default is ON,
but it cannot color a legacy untyped OBJ. A private OBJ with only `v`/`f`
lines remains fully compatible and appears in the neutral color. The viewer
never infers material from elevation, distance to flag, or triangle normals.

The new **backward-compatible private mesh ABI** is a normal ASCII OBJ with
optional exact **Wavefront groups**, placed immediately before the matching
triangle(s):

```text
# synthetic example — not game geometry
v 0 0 0
v 20 0 0
v 0 0 20
g KCL_OGWS_0006
f 1 2 3
```

The group consists of literal `g KCL_OGWS_` followed by exactly four uppercase
hex digits. It must be emitted from the **original Wii Sports Golf per-prism
BE16 attribute at KCL prism +0x0E**, not from guessed visuals, source
proximity or a private histogram joined by face order without identity proof.
Each `f` inherits the most recently declared group. A face with no group
is **UNCLASSIFIED/neutral**. The full private file is still SHA-hashed,
strictly bounded and limited to positive plain triangle indices. All other
OBJ groups, `usemtl`, `mtllib`, textures, external includes and object/model
records remain rejected.

The source-candidate categories currently drawn in different colors are:
fairway `0001`, rough `0002`, bunker `0003`, out of bounds `0004`, green
`0006`, water `0007`, fringe `0009`, and cliff `000C`. Other attributes,
including camera-lock `0005`, get **neutral** coloring, never mislabeled
as grass. The inspector uses the numeric original game attribute mapping
from source research #411 and never downloads assets; this is not verified
surface physics or texture artwork. `Color source surface IDs` OFF uses the
original single-color collision wireframe. A colored legend labels the
categories in the viewer. Deterministic filtering/decimation preserves the
face-to-material assignment; the live face-draw bound remains 600 and
offline bound 1,200. The loaded geometry, flag/tee/ball/aim/A labels and
right-click orbit remain independent.

**Object and tree layer coordination:** original source-gated phase-7 inventory
has **94 reported trees** (manager field `+0x1C`), but neither the contiguous
object stride nor pointer-table layout has yet produced qualified individual
positions. The viewer does **not** draw 94 imagined trees. The tree research
agent #411 will first qualify individual tree positions and source record type
before agreeing on a private opt-in object artifact; independent BRRES models
are not present in the collision OBJ and should not be invented. Planned
future objects will have an independently validated source-epoch/hole and
local asset provenance, position/size/unit guards and a separate Show toggle;
they must not alter terrain triangles or player positions. Terrain OBJ export
from #413 is separately owned and currently blocked on an operator-local
OUTPUT_DESTINATION gate; this viewer change does not assert a successful
private material-bearing OBJ export or active-collision octree status.

In all cases the 3D rendering is a **candidate source-component scene, not a
verified visual-world alignment or trainable physics map**.
`training_approved=false`.

## Scene-style 3D camera navigation (viewer-only)

The terrain/ball/flag inspector now supports Unity Scene-view-inspired camera
interaction, independent of game input or source-component data:

- **Scroll wheel up/down** over the 3D canvas: continuous multiplicative zoom
  **toward the mouse pointer**, bounded to 0.04×–64× of the automatically
  fitted scene. Windows/macOS MouseWheel and Linux/X11 buttons 4/5 are
  supported; the amount is proportional to normal wheel notches.
- **Middle mouse drag**: pan the viewport in screen pixels. Pan persists as
  new live source-qualified samples arrive; it does not translate the course
  or affect any memory reading.
- **Left or right mouse drag**: orbit as before (orthographic yaw/pitch,
  no game-camera calibration). A-button text stays screen-anchored.
- **F** when the canvas has keyboard focus (click/drag/scroll inside it) or
  **Frame view (F)** button: restore fitted zoom and centered pan while
  keeping your current viewing orientation. Terrain focus checkbox still
  controls which collision faces are included in the fit.

This is orthographic canvas navigation, **not full Unity's perspective/flight
camera**, and it does not modify Dolphin, source coordinates, contact/physics,
terrain identity, or training eligibility. Camera functions are synthetic-tested
with zoom-pointer invariants, bounds, platform wheel events and UI interactions.
