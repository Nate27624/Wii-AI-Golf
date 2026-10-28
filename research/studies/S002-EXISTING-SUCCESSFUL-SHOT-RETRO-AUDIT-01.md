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
