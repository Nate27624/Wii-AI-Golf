# Next P0 memory experiment: reuse verified source paths, improve capture granularity

**Owner proposal for S000/S001/S002, 2026-10-28. No live execution has occurred from this plan.** S001 owns bridge and input; S002 owns source memory validation and pause/phase capture; S003 observes. No duplicate offline atlas, bridge, native full-bank exporter, or GUI introduced.

## What existing source work already found

- S002 [#160](https://github.com/Nate27624/Wii-AI-Golf/pull/160) and [#162](https://github.com/Nate27624/Wii-AI-Golf/pull/162) locate four player records (stride `0xCC`), selected record pointer/index, record `+0x88` link to a source-ball-related object, its `+0x4C` translation pointer (self-target `+0x30`) and copy paths from record `+0x54/+0x60`. **Source-linked initial equality is not verified dynamic physics.**
- S002 [#181](https://github.com/Nate27624/Wii-AI-Golf/pull/181) maps three candidate ball cache triplets `+0xCC`, `+0xF0`, `+0xFC`. S002 [#183](https://github.com/Nate27624/Wii-AI-Golf/pull/183) traces conditional cache writes and target/pin fallback, but receiver lifetime and dynamic semantics remain unknown.
- Real B0–B3 source overlay in #181 indicates **all four source ball objects unchanged** across no-shot/aim transitions, while 17 selected player-record offsets are aim-correlated. This is a valuable negative control; do not describe B0–B3 as proof of flight. Another human-observed JSON-associated capture had a ball that was **not fully stationary**, with only a *hypothesis* of downward velocity; exact JSON-to-B0–B3 association is unknown.
- S001 [#166](https://github.com/Nate27624/Wii-AI-Golf/pull/166) is the existing opt-in same-tick selected-ball watcher. S002 [#184](https://github.com/Nate27624/Wii-AI-Golf/pull/184) and [#185](https://github.com/Nate27624/Wii-AI-Golf/pull/185) own PRE/POST/SETTLED timing studies. Do not introduce a second controller/bridge path.

## Actual operator inventory result and interpretation (2026-10-28)

The operator successfully ran the first private JSON inventory, 9/9 synthetic tests passing. It scanned **181 JSON/JSONL files**, skipped **one** for exceeding the initial 8 MiB cap, and found **zero changing three-float ball-vector paths by its schema heuristic**. This is a **negative syntactic finding only**, not a ball-stationarity result. Known high-priority private files include `ball-study-20261027-212633/golf-object-windows-PRIVATE.json`, `captures/selected-ball-frame-watch-20261028T012527Z-PRIVATE.json` and one earlier Hitting the Green observation. *Only* path patterns/field names are referenced here, no contents.

Important cross-check from S001 [#166](https://github.com/Nate27624/Wii-AI-Golf/pull/166): its first actual selected-ball watcher trial observed **no human-visible ball movement**, 50 candidate samples with **unchanged** vector, and an **incomplete** watch recording. It is a likely **stationary/no-contact negative control**, not a confirmed instance of the operator's separate moving-ball recollection; verify file identity and the watcher's `safe_summary` before making that association. There is no basis to declare any B0/B1/B2/B3 state or a particular JSON 'falling'.

Inventory scanner update (draft PR #205) ignores its own previously generated JSON inventory reports to avoid polluting later scans, explicitly lists skipped file IDs/sizes, and recognizes the S001 frame watcher's whitelisted `safe_summary` booleans / human observation without publishing raw vectors. Rerun at `--max-file-mib 64 --max-total-mib 256` to assess the earlier oversize skip; this is bounded JSON parsing, not any new Dolphin or RAM capture. Even a moving candidate vector requires exact per-shot clock/frame and physical verification.

## Immediate, zero-Dolphin analysis (first)

1. Run the new private read-only `scripts/inventory_private_golf_json_motion.py` on the existing ignored `Wii-AI-Golf-Data` directory, after targeted tests. Index only JSON/JSONL field-name shapes, phase/shot/frame key presence, and whether a JSON file has repeated distinct numerical candidate ball-position vectors. The result is a **PRIVATE** local manifest; stdout omits numerical values.
2. Operator identifies which JSON the visual nonstationary ball recollection refers to. S002 checks the actual source and timing schema, preserves exact original labels, uses same-shot IDs not filenames or fuzzy timestamps to relate files, and distinguishes downwards hypothesis from measured motion.
3. Apply the existing S002 source-gated #160/#163/#181 audit to the matching native bank pairs **if** a verified link exists; do not infer a B index from the two changing floats in unrelated global memory.

## Phase-anchored next capture (requires reviewed S001/S002 work and operator approval)

Prefer **short source-targeted memory windows sampled during motion**, not an 88-MiB rolling RPC scan:
- Snapshot whole `RPGolPlayer` selected record (`0xCC` bytes), selected ball-related object (`0x1AC` bytes), current-start/pin/cup map-object spatial controls and the selected-index/source manager/scene/mode gates. Include ball current translation pointer and candidate caches `+0xCC/+0xF0/+0xFC`; do not read only one triplet.
- Record both before and after bounded reads' timing/frame information, bridge tick ID, exact trace sample index, A state dispatched versus game-observed if available, phase `pre_swing / backswing / forward / followthrough / flight / settled`, and an explicit **same-shot** identity, with capture-duration thresholds. **Bridge callback/tick is not proof of guest CPU/video frame.** 
- Use one already reviewed Dolphin/bridge and canonical swing trace; do not simultaneously attach independent controller processes, create a fresh Dolphin session unexpectedly, or generate new waveform timings.
- Require stationary no-swing / aim-only negative and a human-confirmed real ball-motion positive. Compare current ball object translation against fixed start, pin, cup and each cache before/during/after; cache updates may be conditional or lagged, not instantaneous ball positions.
- Preserve detailed private raw sampled region bytes and per-frame metadata under ignored `Wii-AI-Golf-Data`, with local-only SHA, game version and phase confirmation; optionally take entire-bank pre/post files **only via a demonstrated consistent pause/freeze mechanism** after source-owner review. No raw publication.

## Capture-technology choice

- S002 [#203](https://github.com/Nate27624/Wii-AI-Golf/pull/203) is a CLI read of all native 88 MiB **while emulator progresses**. Its reports explicitly set `same_guest_frame_verified=false`: useful for stationary scene inventory, **not an in-flight physical trajectory or same-frame pair**. Do not feed it into the stricter paused pre/post comparator.
- S002 [#201](https://github.com/Nate27624/Wii-AI-Golf/pull/201) uses an external memory engine with `--paused-confirmed`, but currently requires manual attestation and has not proven consistent bank read or Felk integration. User requires **PowerShell/CLI**, no Dolphin memory GUI. To make this the preferred full-memory route, S001/S002 must first design and validate a CLI-controlled freeze/resume and crash-safe cleanup; no assumption that frame-polled RPC can pause and then stream while halted.
- **Best immediate P0 data per unit time**: existing source-field watcher + bounded samples spanning witnessed movement and stop, with repeated independent shots. Full-bank native snapshots remain useful for source mapping/stationary geometry, not a replacement for temporal resolution.

## Acceptance / training

All fields added to `research/memory-variables/registry.json` remain `training.approved=false`. A training promotion requires typed source proof, independently reproduced actual ball-motion and idle negatives, source-to-RAM pointer resolver in a different boot, frame-joined before/during/after samples, known unit/coordinate basis, censor handling, and S002/S000 review. The existing [33-field source/behavior evidence ledger](https://github.com/Nate27624/Wii-AI-Golf/pull/154) remains the granular evidence history; the new registry is an access/eligibility index and must cross-reference it, not replace it.
