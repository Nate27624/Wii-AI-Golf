# P0 successful V1 hit: private source-relative memory audit

**Owner review:** S002 source/RAM; S000 privacy; S001 timing and controller. Draft only. No Dolphin, input, network publication, or training.

## Established operator evidence

The October 28, 2026 UTC session used clean Felk portable Dolphin with the registered green-pre-start slot 2, exact historical isolated V1 bridge SHA-256 fe04cb0ba312c559d5cb7edb8d0ac2185aca72046839a903160929ee7c58ca19, 45 *observed Dolphin frames* of A lead, zero separate A prime RPC requests, and one 89-sample swing. The golfer began with the club back; user reported visible ball contact, off-green, 100.0ft displayed, 75% approximate power meter. UI power/100ft are human labels, **not game-RAM-verified physical fields**. The original S002 collector produced 3 PRE, 2 POST, 3 SETTLED non-atomic snapshots and found 8 stable changed words.

## Existing memory dataset vs necessary live variable capture

The existing local private files are a RAW-PRIVATE JSONL and an unsanitized candidates JSON under the ignored sibling Wii-AI-Golf-Data/captures directory. The source-controlled windows cover golf_config (0x1C74 bytes), golf_field (0xA8 bytes), sports_sequence (0xD0 bytes) and optional minimap-ball/player/shot-line effects (0x200 bytes each). **These are neither full MEM1/MEM2 bank exports nor the S001/S002 51-word selected player record under swing phases.** A stable word may be a timer, visual effect, pointer or unrelated state, not a swing or ball-physics value.

## PowerShell-only execution (no ZIP)

Fetch branch agent/research/p0-private-positive-hit-triage-20261028 from GitHub into a detached sibling worktree named Wii-AI-Golf-P0-Hit-Audit. Run only tests/test_p0_successful_shot_private.py and scripts/audit_p0_successful_shot_private.py, passing the two *existing* matching private files. The auditor prints **only** source-relative window offsets, C01.. candidate IDs, source family, post-change counts, pointer-shaped flags, UI numeric coincidence types and explicit unverified/training=false flags. Its source rejects wrong disc/revision/mode, nonchronological/incomplete phases, malformed or moved source windows, contradictory alias reads and any saved word that disagrees with the raw sample. It is read-only; do not upload private inputs, their absolute addresses or values.

## Next P0 work

- S002: for the eight redacted relative offsets, map source PPC readers/writers and separate config, sequence and rendering/timer confounds. Investigate the selected 0xCC-byte player record +0x024 (source-written small integers 5/1/2/3/4; **not proven** a contact flag).
- S002: validate actual moving ball source/physics after source-selected record +0x088 -> ball-like object +0x04C -> Base translation +0x030; start equality for record +0x054/+0x060 and ball caches +0x0CC/+0x0F0/+0x0FC is *initialization*, not flight.
- S001: do not replace the verified V1 +45 observed-frame A lead with 45 RPC requests, an incompatible V2 probe or unreviewed watched V2. Require same effective swing and <5ms 51-read callback cost before new approved live shot.
- S000: public evidence may include only validated redacted relative-offset/count/boolean facts, never raw words, pointers or local memory files.
- S003: no training until live same-shot guest-frame verified ball motion, contact, physical outcome semantics, repeated independent clean boots and distinct non-censored power results.

Related drafts: #154 evidence dictionary, #166 S001 watcher, #189 player-record sampling, #191 negative-controls, #193 trace linkage, #184 shot PRE/POST/RESULT. No verified ball velocity, swing power, contact RAM flag, or score address as of this audit.
