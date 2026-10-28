# Wii Sports Golf — game-memory field evidence ledger

**Owner:** S000 schema/claims gate. S002 owns source and capture facts; S001 owns controller/frame-callback timing; S003 reviews identifiability before any training. **Status:** proposal, not merged, no new live capture.

The machine-readable [field-evidence-ledger.json](field-evidence-ledger.json) contains **32 entries**: twenty-two source/runtime structural, base-class, source-writer or negative-control candidates (including eight named environment references, one constructor-backed Base member, two unverified selected-object hypotheses, three PPC writer/roster leads and two source-identified raw wind lookup tables), plus ten deliberately **unlocated** gameplay variables. Nothing is labelled verified game power, ball velocity or club pose. Synthetic tests reject guessed offsets, untrusted URLs, raw runtime pointers, unsupported private fields, and unsupported training promotion.

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

## Operator-confirmed MEM1 + MEM2 structural inventory (saved single pair)

Operator executed the PR #157 offline source-gated audit against **preserved**
native MEM1 24 MiB and MEM2 64 MiB and pasted only sanitized JSON.
Its results exactly reproduce the existing S002 #151/#156 source-compatible
object inventory: RSPE01 Rev1, scene ID5, sport2, mode4, raw hole1, manager
MEM1, Golf scene/main candidate/config/field manager MEM2; **six** source-named
field references all present in MEM2 (current pin, start, cup, wind object,
course object, map data); field manager **six pin objects and 31 start
markers**. Candidate main's first 256 bytes contain **25 pointer-shaped
MEM2 words and four MEM1 words**; first word lies in a publicly documented
Rev1 module data interval but that is NOT class/vtable proof.

This new result is now represented as **eight extra source-labelled
configuration/reference entries** in the dictionary with explicit no-training
flags. Crucially, an `RPGolFieldManager+0x44` pin pointer is *not pin XYZ*;
`+0x50` current start marker is *not moving ball XYZ*; `+0x68` wind object
is *not wind speed*. The ten original unlocated physical/state targets remain
unlocated and nothing is training-ready. No numeric world coordinates,
velocities, club kinematics or power are decoded.

The two GUI exports were approximately **111 seconds apart**. Both
`same_frame_verified` and `same_boot_verified` remain false. The audit
success only shows that the pair's stored scene references are mutually
plausible; it cannot assert atomicity or prove temporal changes.

S000 independently identified overlapping one-pair readers in #156 and
canonical #151 and closed duplicate PR #157 **without merge**, retaining
the real sanitized operator result as PR evidence. S002 should consolidate
any unique privacy tests into #151 instead of creating three readers.
The next new measurement should prioritize existing-bank source owner
and selected-map-object hypotheses (#151 player-object source evidence;
stacked #159 selected pin/start candidate vectors) with no Dolphin.

## Real selected-map-object test and stronger DOL constructor evidence

The user executed S002 [map candidate PR #159](https://github.com/Nate27624/Wii-AI-Golf/pull/159)
against existing **saved** source-gated MEM1/MEM2, and provided only the
sanitized JSON:

- Both current pin and start objects resolve into MEM2. The supposed Base
  `+0x30` VEC3 and hypothesized backing PMP `+0x08` triplets are each
  finite, bounded and nonzero. They are candidate **numbers**, not verified
  positions or calibrated world units.
- **Pin**: the two candidate triplets agree within the preregistered
  tolerance 0.1 (unknown units).
- **Start**: the two candidate triplets **disagree**. This rules out the
  blanket assertion that both selected map objects share equivalent
  runtime-vs-PMP position values.
- **Both** selected object first-words do not land in the narrow proposed
  Golf map-object module `.data` interval; a negative range hint, not
  proof the pointers are bad or that no object exists.
- Explicit `source_known_derived_class_inheritance=false`,
  `runtime_pmp_layout_verified=false`, `pin_world_xyz_verified=false`,
  `start_world_xyz_verified=false`,
  `same_boot_proven=false`, `same_emulated_frame_proven=false`.

**Material new static provenance:** S002 separately read the user's private
RSPE01 Rev1 DOL constructor `RPGolMapObjBase::RPGolMapObjBase` and
reported three receiver-relative f32 stores at `+0x30/+0x34/+0x38` (initial
translation zeros), scale stores `+0x3C/+0x40/+0x44` (ones), and
**internal self pointers** at `+0x48` to `base+0x0C`, `+0x4C` to
`base+0x30`. The public `RPGolMapObjBase.h` had wrongly annotated
the two pointer fields at `+0x40/+0x44`, overlapping scale storage. The
**constructor evidence resolves the Base struct layout**, but it does
NOT prove that selected `RPGolMapObjPin*` or `RPGolMapObjPlayer*`
points to a Base subobject at offset zero.

Therefore the dictionary now carries **three separate entries**:
`environment.map_base_translation` (static source type and constructor
initializing writer corroborated, not verified live pin XYZ);
`environment.selected_pin_translation_candidate` (runtime numerics
plausible and map-entry agreement, untyped);
`environment.selected_start_translation_candidate` (runtime
numerics plausible but second representation DISAGREES, untyped).

**Next offline controlled falsification, S002 #159 owner:** using the **same
preserved MEM2** and source-gated selected pointer, test two constructor
invariants as pointer **equality only**:
`*(obj+0x48)==obj+0x0C`, `*(obj+0x4C)==obj+0x30`.
No second pointer dereference is required. Compare pin vs start, and test
known mock lookalikes, invalid pointers and nonzero base offsets. If both
match, this is **Base-layout consistency evidence**, not proof of class
inheritance, game coordinate units, or live ball identity. If they fail,
the selected object may use a different base location or layout; do
not search blindly or rename fields as XYZ. No fresh Dolphin session,
RAM dump or model training is needed for this experiment.

## New selected-object constructor invariants and ball-related writer lead

A second operator execution of S002 PR #159 on the **existing single saved
pair** found BOTH selected pin and start pointers match the DOL-derived Base
constructor self-reference invariants: object `+0x48==obj+0x0C` and
`+0x4C==obj+0x30`. Each also has a finite/nonzero candidate three-float
translation. Crucially, X and Z match the **hypothesized** backing map entry
for BOTH, while the Y candidate matches the pin and **disagrees for the
start marker**. This rejects any universal raw equality between the two
representations, not the Base self-pointer layout itself. A vertical
position offset, base-vs-map semantics and terrain height are *competing
hypotheses*, with none demonstrated. The selected object first word
does not fall within the very narrow checked Base/FieldManager data
region, which is not a complete derived-class vtable test.

Separately, S002 source investigators report a stronger **static** DOL
dataflow from four source-defined inline player-manager records at
204 bytes each to 428-byte simulation records. Player code writes an
indexed simulation pointer at the **record-relative +0x88** and obtains
a candidate three-float write destination through the simulation
record's `+0x4C` pointer. Source code executes three `stfs` to
the destination and that pointer is consistent with the separately
verified Base constructor `+0x4C -> +0x30` self-reference. This
supports a ball-related **translation writer path**, not the actual
active physics ball coordinate, animation semantics, scene selection,
same-frame sensor or calibrated power. S002 #160 holds bounded runtime
roster evidence and no true gameplay XYZ claim.

The three NEW ledger entries here are `golfer.player_record_sim_object_ref`,
`golfer.ball_related_translation_write_path`, and
`golfer.player_manager_inline_roster`. Each has
`writer_instruction_verified=true` for its *specific static code
operation* but `source_typed_member_verified=false` for the
proposed full object identity, `gameplay_value_verified=false` and
`training_eligible=false`. Do not infer that the four allocated records
mean four active golfers or independent observations.

**Next specific study:** S002 map owner #159 should trace
`RPUtlMapData.cpp` and `RPGolFieldManager.cpp` reads/writes of the start
marker through their proven receiver/base-register flows and explain
why candidate vertical Y differs while X/Z match. S002 roster owner #160
should resolve source-selected-record pointer and read-only
same-B0 static cross-check between the source-linked simulation object's
self-pointer and player-record float triplet, emitting counts only.
Only when independent frame observations across controlled conditions
show the correct moving ball may S003 discuss physics labels. Neither
study needs more Dolphin input now.

## Latest selected-record source and saved B0 candidate evidence

The user executed the current S002 #160 source-gated roster CLI on the already
preserved 24MiB MEM1 + 64MiB MEM2 pair. It returned four distinct ball-like
and four player-like source-data hints, exact constructor firstword matches
for all four allocated player subobjects, four valid nested ball-like +0x4C
translation destination pointers, **one** exact equality between a player's
three-word record translation and its nested candidate vector, and selected
record **index zero** as a source-backed hypothesis.

**Important precision:** the sanitized operator JSON says `1/4` nested
vectors match and separately says selector candidate `0`. It does **not**
identify which of four slots matched. Another S002 source researcher's
private B0 note asserts the matching slot was selector0 and that it equals
the source-named start translation, but the currently shared safe report
does **not** independently reproduce that association. To close this
specific gap, S002 #160 should add **three boolean/count-only
source-controlled checks** to the SAME canonical private reader:
selected slot triple equals nested translation; selected nested vector
equals current start marker getter translation; nonselected slot exact
match count (0..3). Also independently match each source-derived
SimulateManager+4+0x1AC*i pointer to the corresponding roster record+0x88.
No addresses, words or floats should leave the private environment.
Negative mocks should cover wrong selected index, matching stale unselected
slot, scene transition and false pointer aliases.

PR #162 [Rev1 PPC source evidence](https://github.com/Nate27624/Wii-AI-Golf/pull/162)
also identifies a distinct `RPGolConfig::GetWind` lookup that uses
the source-backed raw current-hole index to select **two** nine-element
MEM1 BSS arrays (raw wind direction and speed values).
The raw integer storage and indexing are code-backed, but no safe
runtime value/category, physical units, display matching or changed-hole
control has been validated. These have separate ledger entries from the
still-unlocated `gameplay.wind` quantity.

**Training remains blocked:** source-typed lookup or an exact single-frame
source/runtime equality is not equivalent to actual dynamic ball-motion
labels. No same-frame independent snapshot, ball-on-screen intervention,
velocity, contact, club pose or power has been established.

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
