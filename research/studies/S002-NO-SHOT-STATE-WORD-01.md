# S002 selected-player candidate state word: no-shot B0–B3 study

Status: OFFLINE SOURCE-GATED ONLY; no human memory data run in this PR.

## Evidence
RSPE01 Rev1 RPGolPlayer.cpp PPC source inspection (S002 #162) identified five immediate integer writes to receiver+0x24. The values look state-like, but neither their completeness nor game meaning is established. Existing S002 #163 observed stationary ball/record/start translation candidates in four no-shot paused snapshots despite visible WASD aim changes and independent full-bank differences.

## Implementation
- Additive private script audit_selected_player_state_word_private.py; imports existing #160 and #163 source-gated roster and four-phase bank validators.
- Requires exact manifest hashes and B0–B3 native dimensions, RSPE01 scene/source pointer gates, five matched PPC li/stw sites, stable selected-record pointer/slot/hole.
- Reads selected_record+0x24 only in process; reports boolean per-phase membership in the five source-literal candidates, boolean changed-by-idle/aim/idle phase and strict nontraining flags. Never prints raw words, pointers, numeric vectors, hashes or file paths.
- Seven new synthetic tests including forged source PPC, unknown literal, changed pointer, state drift, conservative outputs; CI on Windows and Linux.

## Local run (no Dolphin)
Use the distinct worktree branch agent/research/selected-player-state-word-private-20261027 and the existing private B0–B3 folder under sibling Wii-AI-Golf-Data:

    py scripts/audit_selected_player_state_word_private.py --private-root "PATH-TO-EXISTING-B0-B3-FOLDER"

Do not upload private .bin files or manifests. Only human-approved count/boolean summary may be handed to S000. A stable or changing candidate state word during a NO-SHOT control cannot identify ball flight, impact or power. Current Felk-Clean V1 startup recovered but V1 actual shot unverified.