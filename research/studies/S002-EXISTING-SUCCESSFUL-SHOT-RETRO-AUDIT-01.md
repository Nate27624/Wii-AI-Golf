# S002: Retrospective audit of the ALREADY successful V1 golf shot

## Existing evidence, not an invitation to run another shot

An operator-controlled V1 shot ALREADY made human-observed contact. Preserve and analyze it before requesting new controller input.

- Exact run ID: outcome-20261028T033948Z-5cd47f00
- Hardware workflow: clean portable Felk Dolphin, isolated no-autoload V1 swing bridge, canonical green-pre-start slot2 and A / A+B / A intro.
- Controller: A-button lead 45 OBSERVED Dolphin frames before the swing trace; separate A-prime request count 0. This timing is not proof that the game accepted the A state.
- Human outcome: contact=yes, on-green=no; UI distance 100.0 ft; UI power 75%. These are human annotations, not decoded RAM or game-verified units. Off-green 100 ft may represent capped/censored feedback.
- Original local files in ignored sibling Wii-AI-Golf-Data/captures: outcome-20261028T033948Z-5cd47f00-RAW-PRIVATE.jsonl and outcome-20261028T033948Z-5cd47f00-candidates.json.
- 3 PRE, 2 POST, 3 SETTLED bounded snapshots, 8 persistently changed words. These were narrow windows read across multiple emulator frames, NOT full MEM1/MEM2 exports, NOT per-frame selected player 51-u32 samples and NOT proof of physics.

Previous miss experiments used V2 and/or a different A-priming program; changing more than one factor means neither change can yet be assigned causality. The observed V1 hit does establish that a successful contact capture exists.

## Read-only analysis implemented

The new scripts/audit_existing_successful_shot_private.py reuses the existing canonical rank_outcome_candidates algorithm and validates the saved candidate summary against the RAW-PRIVATE snapshots. It checks Hitting the Green mode, complete swing dispatch, frame-observed A-lead provenance, human contact label and chronological stages. It groups changed candidates by stable source-relative region/offset only; reports early POST vs SETTLED-only appearance, pointer-like bit patterns and possible render/effect windows. No raw addresses, native values, float words, file paths, memory dumps, new emulator action or write operation appear in stdout.

Results are strictly candidate classifications. Training, publication and verified ball-world-XYZ, velocity, game power and official shot score remain false.

### Runnable local read-only command

Run in a single PowerShell scriptblock and validate the exact existing two private files. Use branch agent/research/s002-existing-hit-retro-audit-20261028 in its own isolated worktree Wii-AI-Golf-Existing-Hit-Audit. Run test_existing_successful_shot_private.py first; then run:

    py -I D:\Projects\Wii Golf AI\Wii-AI-Golf-Existing-Hit-Audit\scripts\audit_existing_successful_shot_private.py --run-id outcome-20261028T033948Z-5cd47f00 --data-dir "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures"

Do not paste either RAW-PRIVATE or the old -candidates.json wholesale in chat or commit them: those contain native absolute addresses and raw values. The NEW analyzer output contains relative offsets and boolean/phase flags only; it can be reviewed by S002 and S000.

## Cross-agent handoff

- S002 #184/#180: reuse this measured V1 hit for PRE/POST/SETTLED variable triage and capture synchronization caveats. No need to rerun canonical menu intro now.
- S001 #166/#189: 51-word phase watcher remains prospective and draft; it was NOT used in this successful shot. Do not claim per-frame swing power from the outcome cohort.
- S002 #188: plan negative controls only AFTER examining existing eight candidates; avoid more idle aim scans.
- S000 #154: privacy gate and typed evidence; only relative offsets are safe; model/training zero.
- S003 #125: labels are human contact and UI, not validated physical input-target pairs.

## Operator-run REAL eight-word result and aliased-effect discovery

The operator ran the original private existing-shot script and all 7 synthetic tests passed; real data confirmed **8/8** stable PRE-to-SETTLED word changes. The run used **3 PRE / 2 POST / 3 SETTLED** snapshots, complete 89-frame controller dispatch, and the preserved 45-frame observed A lead. Human labels contact=yes, off-green=yes, displayed 100.0ft, displayed power=75%; neither distance nor power matched any candidate as a literal numeric reading. The samples are multi-frame/non-atomic, and all eight candidates were already different from PRE in **both** POST snapshots.

**All eight are solely in MINIMAP EFFECT windows**; not in the retained golf_config/golf_field/sports_sequence object windows. Exactly four candidates are pointer-shaped u32 words in Wii MEM1/MEM2 ranges, at the second +4-byte position of each repeating pair. A pointer-like value remains only a bit-pattern heuristic, not a proved pointer, geometry, game score or physics.

Observed source-relative de-aliasing for the three overlapping effect windows:

| Pair | Stable source-relative owner(s) | Immediately POST? | Pointer-like second word? |
| --- | --- | --- | --- |
| 0 | minimap_player_effect +0x078/+0x07C | both POST | yes |
| 1 | minimap_player_effect +0x108/+0x10C = minimap_shot_line_effect +0x078/+0x07C | both POST | yes |
| 2 | minimap_player_effect +0x198/+0x19C = minimap_shot_line_effect +0x108/+0x10C = minimap_ball_effect +0x078/+0x07C | both POST | yes |
| 3 | minimap_shot_line_effect +0x198/+0x19C = minimap_ball_effect +0x108/+0x10C | both POST | yes |

These aliases imply **minimap_shot_line_effect base = minimap_player_effect base +0x90** and **minimap_ball_effect base = minimap_player_effect base +0x120**, assuming the overlapping offsets reference the same absolute words (the source de-duplicator uses whole-word addresses). Thus the eight candidates plausibly form four repeated **two-word pairs** separated by 0x90 bytes. This does NOT by itself prove four class instances, a 0x90 byte C++ struct size, component names or effect semantics. The 0x200-byte watch windows overlap substantially; it is vital to de-duplicate by actual source absolute address internally but never publish those addresses.

The script was subsequently upgraded with `_effect_stride_layout` to test this exact +0x90/+0x90 three-window base relationship in **all eight real snapshot records** (rather than infer it only from displayed offsets), and `_effect_slot` to assign each of eight candidate words to a hypothetical slot 0–3 and within-slot fields +0x078 / +0x07C only when verified. The new booleans are `effect_pointer_bases_spaced_0x90_in_all_phases` and `repeating_two_word_effect_pairs_observed`; the script leaves them **false** and slot indices **null** if any phase violates the spacing or field pattern. No original game memory is uploaded or modified. Two new alias/invalid-spacing synthetic tests augment the original seven.

### Next source-level priority

1. Have source/decomp agents trace effect pointer ownership through `RPGolField` offsets +0x94, +0x98, +0x9C, and identify whether the +0x90 index stride represents entries in a shared effect pool, cloned/linked render structures or other aliasing. Do not assume the labels ball/player/shot_line mean actual motion vectors.
2. Check `+0x78 / +0x7C` writes and downstream readers in the owned object type, using the already-preserved code/source snapshots or public RSPE01 Rev1 decomp; classify storage type using PPC instruction, not float guesswork.
3. Since all eight are render/effect candidates, **exclude them from ball-physics and power training claims** until a causally controlled, temporally precise paired shot/no-shot sample and source type attribution. Do not require another live trial just to complete this existing-shot analysis.

## Confirmed on the **operator's real capture**: four paired effect locations

The owner fetched PR #197 revision `a8635ed03337df8acf55b9c87078daa7a0a267fa` and ran `audit_existing_successful_shot_private.py` against preserved `outcome-20261028T033948Z-5cd47f00` (the same successful shot, no emulator action). Actual command output:

- `EffectSpacingVerified: True` — all 8 PRE/POST/SETTLED snapshots have the three effect window bases separated by +0x90 and +0x90.
- `FourPairsVerified: True` — exactly four two-word pairs de-aliased to hypothetical slot indices 0,1,2,3 at common within-slot offsets +0x078 and +0x07C.
- `CandidateCount: 8`; `PhysicalVariablesVerified: False`.
- All 8 fields have `temporal_pattern = post_all_changed` in BOTH available POST snapshots.
- Each +0x078 value is NOT pointer-like; each +0x07C is pointer-like according to the bounded MEM1/MEM2-range heuristic. This is an **untyped representation pattern**; not proof that +0x078 is a coordinate float or +0x07C is a valid live C++ pointer.

**What is established:** three named observation windows are overlapping views into a repeatedly spaced native memory region, and the four same-relative-position pairs respond to the completed shot. The `minimap_ball_effect` name is an acquisition label; it is not proof any of these values is physics ball position. The stride might reflect subobjects, linked effects, or shared allocation; do NOT infer real 0x90 C++ object size without writers, constructor/class provenance and independent read paths. The capture is non-atomic over multiple emulated frames, and the UI 100.0ft off-green result could be censored.

### Prioritize source writer sites, not another live swing

Source-linked RSPE01 Rev1 code unit boundaries from the public `doldecomp/ogws` linker split to prioritize: `RPGolFieldManager.cpp` 0x80290B44..0x80294184; `RPGolDrawManager.cpp` 0x80294184..0x8029528C; `RPGolMapObjBall.cpp` 0x80296FD8..0x8029B240. These are **search regions**, not known owners of the +0x078/+0x07C fields. Any candidate `stw/lwz/stfs/lfs` with immediate +0x78/+0x7C must have register receiver provenance traced into the effect-window allocation before a member type claim. Inspect writers of the *actual active object*, not all numeric displacement coincidences.

Expected next source deliverable: a safe table of `(source compilation unit, PPC PC, opcode, base-register provenance, field offset)` for each effect pair, with source ownership verified/unverified and publication/training flags still FALSE. Retain original local private raw snapshots and the working 45-observed-frame V1 contact sequence unchanged. No new operator launch or capture is necessary.

## Source-type breakthrough: the eight words fit four effect handles

Primary decomp data independent of this RAM audit:

- `doldecomp/ogws` `include/Pack/RPKernel/RPSysEffectBase.h` defines `RPSysEffect::mHandle` at wrapper offset +0x78.
- Its `include/nw4r/ef/ef_handle.h` defines inherited `HandleBase` fields `u32 mObjectID` at relative +0 and `LinkedObject* mObject` at relative +4. Thus wrapper +0x78 is ID, wrapper +0x7C is object pointer.
- `src/nw4r/ef/ef_handle.cpp` assigns/copies both ID and pointer, and IsValid() compares saved ID to the pointed-to object's ID.
- `src/Pack/RPKernel/RPSysEffectBase.cpp` create(), fade(), forceKill(), reset() change or clear the effect's handle.
- Public `kiwi515/ogws_info` FieldManager header types manager +0x94/98/9C as three `RPSysEffect*` minimap wrappers.

**This precisely explains the observed four paired words in the original successful-shot 3 PRE / 2 POST / 3 SETTLED capture:** nonpointer-like +0x78 corresponds to an effect object ID; pointer-like +0x7C corresponds to a LinkedObject*. All four apparent entries show the same source-consistent arrangement. The measured +0x90 pointer spacing might come from allocator stride/padding; it has NOT proven sizeof(RPSysEffect)=0x90. No pointer-target ID/vtable identity check has been performed and the snapshots span multiple Dolphin frames, so this is a **strong source-layout concordance, not a runtime owner identity proof**.

Updated `audit_existing_successful_shot_private.py` adds `source_RPSysEffect_HandleBase_pair_layout_concordant`, source expected member labels, and explicitly false `RPSysEffect_runtime_object_identity_verified`, `HandleBase_pointer_target_ID_verified` and `RPSysEffect_object_size_or_0x90_stride_source_verified`. Candidate rows gain only safe source labels when exact all-phase pointer spacing and pair offsets exist. New negative synthetic test ensures reversed ID/pointer patterns cannot be promoted to matching source layout.

**Research consequence:** none of the eight candidates should be used as physics ball XYZ, velocity, display distance, or swing power. The changed handle pairs fit a minimap effect lifecycle reaction to the shot. The actual effect lifecycle cause (create/clear/replace) and runtime pointed-to identities remain unverified. Source P0: inspect Rev1 `RPSysEffectBase.cpp` CODE 0x80194158..0x801957C0, trace FieldManager r31 loop ownership, and the effect pointer constructors/callers. This task uses existing immutable B0 code only; no live shot.
