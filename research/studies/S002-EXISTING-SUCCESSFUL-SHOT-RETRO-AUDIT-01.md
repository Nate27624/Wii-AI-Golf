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
