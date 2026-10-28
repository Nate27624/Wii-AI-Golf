# S001 support — source-gated, one-tick selected ball micro-watch

**Status: CODE-ONLY / DISABLED / NOT DEPLOYED. NO DOLPHIN OR GAME ACTION.**

Parent S001 source-pinned [PR #147](https://github.com/Nate27624/Wii-AI-Golf/pull/147) owns immutable A45 89-sample V1 waveform and frame event manifest. S002 [PR #160](https://github.com/Nate27624/Wii-AI-Golf/pull/160) owns executable-backed selected player/ball roster source identity. S002 [PR #163](https://github.com/Nate27624/Wii-AI-Golf/pull/163) owns static full-bank snapshot and vector equality. Independent [PR #165](https://github.com/Nate27624/Wii-AI-Golf/pull/165) owns temporal **private JSON consumer**. S000 #154 owns data publication. This research component uses **NEW paths only** and does not change any of those owners' files, CLI, controller, scheduler, publisher or live bridge.

## What was built

- `src/wii_ai_golf/integration/selected_ball_micro_watch.py` contains `SelectedBallMicroWatch`, a pure Python *optional* read-only helper. **Nothing calls it yet.** No auto patch to `mcp_bridge.py`; no second socket/RPC, no timer/thread, no emulator/Controller calls, no save/load, no filesystem output. No model training.
- Designed to be **explicitly reviewed and invoked by the EXISTING Felk emulated-frame coroutine**, with the caller passing its existing `memory.read_u32` API and `_frame_count` callback. Actual upstream `mcp-dolphin/bridge/mcp_bridge.py` has single frame loop `_frame_count += 1` and `_poll_sockets()`; `read_u32` is a direct memory API, unlike per-byte `read_bytes`. S001 must validate the operator's installed bridge matches that source before use.
- Each explicit stage capture performs **at most 48** direct aligned 32-bit reads (strict budget). Most are one-off source-path/PPC opcode checks; game pointers are resolved once per capture and only for registered objects. A production speed/overhead guarantee is **NOT** established. It never walks arbitrary pointer chains or sweeps MEM1/MEM2.
- Checks exact MEM1 Rev1 header, source PPC instruction shapes for four-record index selection, ball translation writer and FieldManager current-start getter, scene ID5/sport2/backlink, config mode4 and bounded hole, selected manager record index0..3, Ball-module first word, Ball +0x4C -> Ball +0x30 Base selfref, current-start +0x48/+0x4C selfrefs and valid MEM2 mapping. Reads **only** current start translation, selected nested Ball translation, selected record position at +0x54 and +0x60, each three 32-bit unmodified words.
- Requires one private operator-generated per-boot string **not inferred from matching files**, actual frame start/end callbacks, max two-frame read span, increasing non-overlapping frame brackets, and four explicit stages exactly `idle_before` → `idle_after` → `event_before` → `event_after` (stage labels MUST be provided by a real S001/human-verified protocol, not inferred from commanded waveform).
- Stores private sample dictionaries **only in memory** in exactly the key shape needed for #165's eventual private temporal JSON. Source-gated `source_path_gates_passed` is based on bounded runtime and selected PPC syntax, but is NOT independently verified physical identity. It does not create #165's report (human observations and waveform attestations remain entirely outside this code).
- Returns only a safe `CaptureEnvelope(stage, read_count, frame_span, verified_source_shape)` plus safe diagnostics. Raw private 32-bit words, session token, runtime pointers, frame numbers remain accessible **only via an explicitly-named `private_samples()` in-memory API**, never stdout, GitHub or a generated file. Review S000 privacy before any future recorder uses that interface.

## Unit testing and owner integration gate

`tests/test_selected_ball_micro_watch.py` synthesizes Rev1 PPC instructions and a fully fabricated scene/manager/selected-record/ball/start pointer graph. Tests enforce no emulator/controller integration, strict source opcode checks, selected-pointer/cross-bank validation, four phase order, 2-frame span and non-overlap, invalid game/rev/mode/hole, invalid slot and ball pointers, no-value leaks and clean error handling, bounded reads and private-copy separation. CI Windows+Ubuntu uses mock data only; **passing tests do not prove Felk Preview4 runtime timing or gameplay**.

**Owner acceptance steps before any live use**:
1. S001 reviews exact `_frame_count` coroutine and current generated V2 swing bridge; the micro-watch must run **only in that existing coroutine**, not a second RPC or process. No source-socket reads inside a paused emulator. Preserve SHA256 baseline `b63a1818ba5086c64b0fe7338236a498240e4be97bbd111809a772d783699891`, 89 samples and A45 button lead unchanged. No waveform writes in the new helper.
2. S002 verifies hardcoded Rev1 PPC instruction matches against private US Rev1 DOL / MEM1 and checks selected marker/ball ownership across same boot. These syntax checks do **NOT** prove actual physics or world XYZ.
3. S001 measures actual CPU/gameframe cost with instrumentation enabled versus completely disabled, and checks no perturbation of V1 contact. The **<=2 game frame** constraint is a **limit checked**, not demonstrated in live Dolphin. Failure must ABSTAIN and not run a shot.
4. S000 reviews private-only on-disk artifact code to be authored by the S001 owner (if needed). The present helper has **no file persistence**, no approval for public data. #165 supplies the offline temporal consumer, which requires explicit human observations and four actual frame-marked samples.
5. Only after owner approval ask operator to consent to **one** known-state single-boot control and movement trial. Do NOT ask for more identical GUI dumps, run an unattended A45 waveform, change the controller, or train a model. Unknown units, 3D world coordinate/ball velocity, source-selected actual human and recognized swing power remain FALSE.

## Safe action now

The only user-side test worth running is **synthetic, offline**; live instrumentation is NOT ready. From a fresh isolated worktree of this branch, run:

```powershell
py -m unittest discover -s tests -p "test_selected_ball_micro_watch.py" -v
```

S001/S002 owner can inspect the sample's schema keys against #165 without importing Felk. There is no command to safely run this against live Dolphin yet; we will not pretend otherwise.
