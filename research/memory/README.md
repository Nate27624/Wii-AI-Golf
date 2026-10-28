# Wii Sports Golf — game-memory field evidence ledger

**Owner:** S000 schema/claims gate. S002 owns source and capture facts; S001 owns controller/frame-callback timing; S003 reviews identifiability before any training. **Status:** proposal, not merged, no new live capture.

The machine-readable [field-evidence-ledger.json](field-evidence-ledger.json) contains **16 entries**: six source/runtime structural or negative-control candidates and ten deliberately **unlocated** gameplay variables. Nothing is labelled verified game power, ball velocity or club pose. Synthetic tests reject guessed offsets, untrusted URLs, raw runtime pointers, unsupported private fields, and unsupported training promotion.

## Exactly what a field claim must establish

Do not conflate these separate dimensions:

| Evidence dimension | Minimum proof | Failure example |
| --- | --- | --- |
| **Static source lead** | Correct RSPE01 Rev1 source/symbol unit, exact code range/member or dataflow, ABI register provenance | A PPC `lwz 0x74(r3)` without proving `r3` points to golfer |
| **Runtime ownership** | Independently checked live scene ID, sport2, manager backlink, stable pointer chain, proper object lifetime and scene transitions | A pointer-shaped first-level word of a correct range but unknown class |
| **Value representation** | Verified u32/s32/f32/fixed-point/enum semantics, endianness, range, init and update; distinguish same-address reload from alias | A changing 32-bit word that resembles a float |
| **Behavioral controls** | Time-matched idle, pointer-only, A-held without motion, scene transition, contact/no-contact; repeated independent boots | A word changing 10/10 idle and 7/7 aim incorrectly named power |
| **Writer provenance** | PPC instruction/function that writes field, causal phase, read/write access trace captured without upsetting game timing | Two unrelated words sharing increment pattern and assumed to be aliases |
| **Game-verified meaning** | Distinct observed game outcome tied to same source-backed field across controlled intervention and independent boots | 100ft off-green challenge penalty treated as physical ball carry |
| **Training readiness** | Proven writer+semantics, independent clean boots, reciprocal shot/bridge/trace identity and **measured** frame brackets, not RPC request/ACK only | A perfect 17/17 frame correlation treated as supervised strength labels |

The schema validates these flags separately. An entry's `training_eligible` boolean **cannot** turn true merely because a field changes, a source has a suggestive name, or its float values correlate with a visual gauge. All existing entries are false. Positive promotions require fresh evidence and S000/S002/S003 review before modifying the ledger.

### Current negative controls

- `candidate_gameplay_main +0x074`: separate private source-backed 20-row capture showed 17/17 within-stage u32 delta equals emulator frame-start gap; 10/10 of those change opportunities were in idle stages. **Time-linked/background candidate**, not a source-named clock or verified golf power. Operator report via [S002 PR #138](https://github.com/Nate27624/Wii-AI-Golf/pull/138).
- Three source-relative child words `+0x008/+0x050`, `+0x020/+0x038`, `+0x044/+0x060`: [published 16-child controls](https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/20261025T034248Z-7c597d65.json) each changed in 10/10 within-idle and 7/7 aim-only pairs. Their *numeric deltas* must not be declared equal to main without the existing same-capture temporal review.
- Earlier source-led `RPGolScene +0x9C` resembles a gameplay-main pointer but one code source types it `RPGolMain*` and another leaves it unknown; even matching live scene ID and a RAM-looking target does not prove the object class. See S002 source [PR #122](https://github.com/Nate27624/Wii-AI-Golf/pull/122) and enhanced probe [PR #132](https://github.com/Nate27624/Wii-AI-Golf/pull/132).

## Full-MEM1 checkpoints are discovery data, NOT instant semantic labels

The S000/S002 [full-state pivot PR #148](https://github.com/Nate27624/Wii-AI-Golf/pull/148) calls for four *operator-local* paused raw MEM1 checkpoints (B0 ready/idle, B1 later idle, B2 pointer-only, B3 return idle). These are ordered within one boot. All three pairwise changes are **confounded by elapsed game time**. A field varying only between B1 and B2 may be timer-driven; a field returning by B3 may be pointer-related but also autonomously oscillating. Report **descriptive** word/page/struct changes only, never `game_power_verified`, `aim_specific` or other causal labels based on these four points.

A robust **second study**, only after safe native dump capability is demonstrated, should include *time-matched idle-only sham checkpoints* and preferably counterbalanced scene/pointer input order across fresh boots. Distinct clean boots are independent units; thousands of changed bytes in one dump are not independent trials. Pausing and exporting may disturb timing, so record whether game execution was actually paused, dump read-span if known, and any scene/boot/checkpoint discontinuity.

**Format/ownership gate before diff:** verify CURRENT Felk Dolphin debugger offers an actual native MEM1 export, not merely a savestate or older mainline-Dolphin example; verify exact plain file size and MEM1 base/alias mapping *on that build* before interpreting offsets. Wii MEM1 is 24MiB in the documented CPU memory map, but an emulator's export may include distinct padding/segments. Never force a 24MiB interpretation onto an unverified dump; stop with a format error instead. The old guide calls the buttons `Dump MRAM`/`Dump ExRAM` (https://mariokartwii.com/showthread.php?tid=1141), but that does not validate Felk Preview 4. Dolphin mainline's `MemoryWatcher` is a **Unix-domain-socket** implementation (https://github.com/dolphin-emu/dolphin/blob/master/Source/Core/Core/MemoryWatcher.h); do not prescribe it as an unchanged native Windows solution.

**Privacy:** full RAM may contain runtime personal/account/device data and arbitrary game information. Keep all raw dumps, executable extracts, savestates, raw word values, absolute pointers, device details, local paths and per-dump hashes *outside Git and ChatGPT* in the ignored sibling `Wii-AI-Golf-Data` directory. Publish only a reviewed typed capped aggregate or source-relative code/field hypothesis. A GitHub green CI test does not approve a new observation kind.

## Source-led next study (zero Dolphin, preferred while dump capability unknown)

S002 owns the offline Rev1 `RPGolMain`, `RPGolPlayerManager`, `RPGolPlayer` caller/callee/dataflow investigation. Two stacked PRs currently overlap: [PPC atlas #144](https://github.com/Nate27624/Wii-AI-Golf/pull/144) (float stores, D-form and r13 patterns), [xref #146](https://github.com/Nate27624/Wii-AI-Golf/pull/146) (direct `bl` edges, r3-relative operands and potential code-pointer tables). Before merging, S002 should choose one authoritative combined source-field report or consume one as a secondary static check; both are based on source PR #122. No inferred `this` pointers or ROM source ranges as verified player members.

If the operator **already has** a lawfully extracted local Rev1 `main.dol` under the sibling private symbols directory, an offline focused+full Windows test and a run of *one* approved source atlas yields the next useful public **source-only** evidence without touching Dolphin. If no local DOL exists, check debugger dump capability first; do not ask the operator to upload a game image.

## Roles and next milestone

- **S000:** maintain this evidence/meaning gate and reconcile duplicate comparator claims on #148; review typed publication and protected training flags.
- **S001:** verify real Felk fork's snapshot/debugger UI capability and lack of paused-loop deadlock; preserve canonical single launcher, one bridge and frozen A45/89 trace. Avoid new live controller commands.
- **S002:** own one canonical offline whole-MEM1 comparator, memory identity graph and PPC writer tracing. Nominate at most 1–4 source-backed fields with controlled relevance; report no match when appropriate.
- **S003:** decide which proposed state quantities would actually be identifiable from observations, and reject negative-control/time-correlated words and score penalties as training labels.
- **S004/S005:** remain gated until S002/S003 positively verify a state schema and same-shot events, then define held-out boot/hole benchmarks.

**Verification command on the review branch:**

```powershell
py -m unittest discover -s tests -p "test_game_memory_evidence_ledger.py" -v
py -m unittest discover -s tests -v
```

These are offline metadata tests. They do not validate RAM semantics, do not start Dolphin, and do not authorize any live study.
