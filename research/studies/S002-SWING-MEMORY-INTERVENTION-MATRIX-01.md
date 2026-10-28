# S002-SWING-MEMORY-INTERVENTION-MATRIX-01 — identify Wii Sports Golf swing state without false labels

**2026-10-27; status: PREREGISTERED / documentation only.** Scope: RSPE01 US Rev1, Golf scene 5, sport 2, mode 4 Hitting the Green. S002 owns source and RAM semantics (#160/#163/#181/#183); S001 owns any live emulator/bridge/frame reader (#166/#147); S000 owns the publish allowlist and field dictionary (#154); S003 owns calibration/training (#125). This study adds NO new Python reader, Dolphin action, controller waveform, repo-public raw RAM, bridge, training, or field promotion. All cited branches are draft until their own gates pass.

## Observations already in hand (not a new run)

The operator's existing B0 idle, B1 delayed idle, B2 visible WASD aim, B3 after release full MEM1+MEM2 native pair cohort was compared by S002 #181; both banks changed on every transition. Selected inline player record (source PlayerManager 4 slots, 0xCC stride, code-derived selector at +0x334) showed 17 aligned words that were unchanged during initial idle, changed at B1→B2, and persisted at B3. These cover relative +0x03C,+0x040,+0x044,+0x048,+0x04C,+0x094..+0x0C0. An additional +0x090 changed across idle and aim and is a nuisance control. All three inactive player records in those target offsets stayed unchanged. S002's #181 pose math found +0x03C angle-like, +0x040..+0x04C numerically consistent with an orthogonal 2x2 sine/cosine transform, two unit-norm four-float groups +0x0A0..+0x0BC, +0x094..+0x09C a three-float position-like group, +0x0C0 unknown scalar. This is **aim-correlated structural evidence, NOT club rotation/angle or swing power**.

The selected ball-like object and four position/cache buffer candidates stayed constant in the no-shot B0–B3 trial. S002 #183 traced conditional *cache-update* code for ball-like +0xF0/+0xFC, with initialization from +0x4C; their B0 value matching source start cannot be counted as independent ball position proofs. Main+0x74 and other clock-like words have already shown idle/frame-scaled behavior. 88MiB whole-bank scan #181 identified large unrelated changes, so do not promote an arbitrary changed address.

**Missing verified targets:** actual club head orientation/position, swing stage, game power meter, contact/collision edge, ball world XYZ, velocity, exact landing/ball-stop transition, ball-hole distance in game/world units, visual score/distance and shot reset. None is presently model-training eligible. Existing observations are mainly one boot/session and UI/operator phase labels, not independently established emulated game frames.

## The identifying experiments, ranked by information gain

| Stage | Intervention / negative control | Fields to test | Falsification / required distinction |
| --- | --- | --- | --- |
| A (already collected) | B0 idle → B1 idle → B2 visible WASD aim → B3 idle | selected record +0x03C..0x04C, +0x094..0x0C0; 256B bank hotspots | Aim-responsive ≠ swing-responsive; isolate idle noise and persistent aim |
| B (next, no shot) | Two separately reset no-shot sessions: deliberate LEFT versus deliberate RIGHT WASD aim, each B0→B3 | same 17 words, especially +0x03C and 2x2, and other top MEM2 blocks | Reverse control must produce repeatable opposite relative angle/rotation changes; each session has own idle control; source owner resolves any relocated object |
| C (next, only if A/B pass) | Camera/pointer-only movement against aim (if the game supports a distinct action) | 17 source-relative words and out-of-object hotspots | Reject fields that follow camera/HUD without golfer aim; do not assume WASD exclusively rotates golfer |
| D (later; S001 approval) | A held without swing; back/forward swing; no-contact/miss; one human-observed contact | current unknown club/power/contact windows; selected player object; ball+0x4C,+0xCC,+0xF0,+0xFC; trusted frame clock | A-hold alone must not be classified as contact; require real ball movement and same-stream input/read provenance |
| E (later; S001/S002 approval) | PRE still → visually moving → landed/settled → idle; separately a shot that resets immediately | selected ball-like translation vs start/pin/cup; independent camera/UI distance | Distinguish initialization/cache/animation, actual displaced ball and reset; a PRE/POST GUI pair is not velocity |
| F (training gate) | ≥3 distinctly witnessed in-game swing-power bins, replicated on held-out boots, fixed aim and course | verified game power + impact state + physical ball motion/outcome | No training on strength labels derived solely from A-lead/scaled RPC requests or unverified UI percentages |

Avoid changing multiple factors together. Preserve trial metadata (same source revision, scene/hole/mode, operator-observed direction, source field identity, emulator build, boot/reset, waveform hash if any, capture pause time and independent visual observation), stored **locally only**.

## PowerShell A: extract NEW candidates from the existing full-bank report (zero new gameplay)

This runs against the existing #181 *private local* JSON. Use the real preserved session folder on the operator PC; do not guess it. No need to create a second raw memory dump if the report exists.

~~~powershell
$private = (Read-Host 'Existing B0-B3 session folder inside Wii-AI-Golf-Data').Trim('"')
$report = Join-Path $private 'fullbank-fourphase-atlas-PRIVATE.json'
if (-not (Test-Path -LiteralPath $report -PathType Leaf)) { throw 'Missing fullbank report; use PowerShell B first' }
$atlas = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
if ($atlas.kind -ne 'local-private-fullbank-fourphase-golf-source-overlay' -or
    $atlas.game_id -ne 'RSPE01' -or $atlas.revision -ne 1 -or $atlas.mode -ne 4) {
    throw 'Wrong schema, revision or game mode'
}
$record = $atlas.source_overlay.source_resolved_regions.selected_player_record
if (-not $record.source_object_address_constant_all_phases) {
    throw 'Selected record relocated: S002 source review required'
}
Write-Host 'Selected-record aim-correlated relative offsets (UNKNOWN semantics):'
$record.changed_word_details |
    Where-Object { $_.changed_on_aim_and_stable_after -and -not $_.changed_idle } |
    Select-Object source_object_relative_word_offset, changed_after_aim_release |
    Format-Table -AutoSize
Write-Host 'Top 30 MEM2 256-byte candidate blocks (PRIVATE bank-relative indices; NOT typed fields):'
$atlas.bank_diff_results.MEM2.top_changed_256byte_blocks |
    Select-Object -First 30 bank_relative_block_index, aim_with_quiet_prior_idle, aim_persistent, aim_reverted, idle |
    Format-Table -AutoSize
Write-Host 'Source-object word-change counts:'
$atlas.source_overlay.source_resolved_regions.PSObject.Properties |
    ForEach-Object { [pscustomobject]@{ Object=$_.Name; Changed=$_.Value.counts.changed_words; AimQuietIdle=$_.Value.counts.aim_no_idle_words } } |
    Sort-Object AimQuietIdle -Descending |
    Select-Object -First 25 |
    Format-Table -AutoSize
~~~

Treat region overlap correctly: player_manager overlaps selected_player_record; duplicate counts are NOT independent witnesses. The unowned MEM2 hotspot blocks should go to **S002 source PPC writer/caller attribution** before anyone assumes a float/club/power meaning. Reported bank-relative indices are locally useful and not approved for public GitHub publication.

## PowerShell B: regenerate the #181 atlas only if it is missing

These are read-only offline commands and do not interact with Dolphin. Branches are deliberately isolated with detached worktrees. If an existing worktree is stale, STOP instead of force-resetting somebody else's code.

~~~powershell
$root = 'D:\Projects\Wii Golf AI'
$repo = Join-Path $root 'Wii-AI-Golf'
$work = Join-Path $root 'Wii-AI-Golf-Fullbank-Atlas'
$branch = 'agent/research/fullbank-fourphase-source-overlay-20261027'
$private = (Read-Host 'Existing preserved B0-B3 session folder').Trim('"')
if (-not (Test-Path (Join-Path $private 'checkpoint-manifest-PRIVATE.json'))) {
    throw 'Preserved session manifest missing'
}
$refspec = 'refs/heads/{0}:refs/remotes/origin/{0}' -f $branch
git -C $repo fetch origin $refspec
if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed' }
if (-not (Test-Path $work)) {
    git -C $repo worktree add --detach $work "origin/$branch"
    if ($LASTEXITCODE -ne 0) { throw 'Worktree creation failed' }
} elseif ((git -C $work rev-parse HEAD) -ne (git -C $repo rev-parse "origin/$branch")) {
    throw 'Existing worktree stale; inspect it without resetting'
}
py -m unittest discover -s "$work\tests" -p 'test_golf_fullbank_fourphase_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Synthetic tests failed' }
$out = Join-Path $private 'fullbank-fourphase-atlas-PRIVATE.json'
if (Test-Path $out) { throw 'Report already exists; never overwrite' }
py "$work\scripts\audit_golf_fullbank_fourphase_private.py" --private-root $private --output $out --top-blocks 2000 --max-object-offsets 4096
if ($LASTEXITCODE -ne 0) { throw 'Fullbank offline study failed' }
~~~

## PowerShell C: prepare the future LEFT/RIGHT no-shot paired-bank trial (operator actions only)

Do **not** collect new runs merely to duplicate earlier same-direction B0–B3. For the discriminating Stage B, two separately reset conditions are needed, one intentionally aimed LEFT and another RIGHT. Keep all conditions except direction as constant as practical. These captures are allowed only after S001 confirms the working Felk build/debugger and normal mode4 state, without changing the bridge or installing a second controller. Create a **different** private directory for each condition; use the canonical keeper on S002 PR #151. The keeper validates 24MiB+64MiB, source scene/mode and SHA256 manifest; the native MRAM and ExRAM export are sequential, not an atomic frame snapshot.

~~~powershell
$root = 'D:\Projects\Wii Golf AI'
$repo = Join-Path $root 'Wii-AI-Golf'
$keeperWork = Join-Path $root 'Wii-AI-Golf-MEM1-Offline'
$keeperBranch = 'agent/research/offline-mem1-checkpoint-diff'
$privateData = Join-Path $root 'Wii-AI-Golf-Data'
git -C $repo fetch origin ('refs/heads/{0}:refs/remotes/origin/{0}' -f $keeperBranch)
if ($LASTEXITCODE -ne 0) { throw 'Fetch keeper failed' }
if (-not (Test-Path $keeperWork)) {
    git -C $repo worktree add --detach $keeperWork "origin/$keeperBranch"
    if ($LASTEXITCODE -ne 0) { throw 'Keeper worktree failed' }
} elseif ((git -C $keeperWork rev-parse HEAD) -ne (git -C $repo rev-parse "origin/$keeperBranch")) {
    throw 'Keeper worktree is stale; do not force-reset'
}
py -m unittest discover -s "$keeperWork\tests" -p 'test_preserve_golf_checkpoint_pair.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Keeper tests failed' }

# Choose a NEW folder for each directional session; never reuse the B0-B3 original.
$session = Join-Path $privateData 'captures\AIM-LEFT-01-PRIVATE'
if (Test-Path $session) { throw 'Choose a NEW never-used session folder' }
New-Item -ItemType Directory -Path $session | Out-Null

# Verify these native dump source paths manually in the ACTIVE CLEAN Felk Dolphin.
# Do not assume the default AppData Dump folder.
$mem1Raw = (Read-Host 'Absolute current Felk Dump\mem1.raw path').Trim('"')
$mem2Raw = (Read-Host 'Absolute current Felk Dump\mem2.raw path').Trim('"')

# AFTER manually GUI-pausing and exporting Dump MRAM then Dump ExRAM at B0:
py "$keeperWork\scripts\preserve_golf_checkpoint_pair.py" --private-root $session --checkpoint B0 --paused-confirmed --mem1-source $mem1Raw --mem2-source $mem2Raw
if ($LASTEXITCODE -ne 0) { throw 'B0 preservation refused; STOP' }

# Only AFTER resuming, waiting idle, GUI-pausing and re-exporting BOTH banks:
# Repeat the SAME invocation with --checkpoint B1
# At B2: aim LEFT ONLY, GUI-pause, export BOTH banks, use --checkpoint B2
# At B3: release controls, settle, GUI-pause, export BOTH banks, use --checkpoint B3
~~~

Never run the B1/B2/B3 keeper invocation without first refreshing **both** native dump sources in the paused UI; the exporter overwrites its default output. Then run PowerShell B against the new LEFT session. For RIGHT, **reset normally to an equivalent first-ball state**, use a fresh AIM-RIGHT-01-PRIVATE folder, repeat B0–B3 with rightward aim, then run B. Do not introduce a shot in these controls. S002 can compare source-relative signatures and ask whether the angle/rotation response reverses between directions; change in bank offset alone cannot prove matching semantics across boots.

The direction-specific operator label is additional local provenance (LEFT or RIGHT) and is NOT independently checked by the existing keeper's generic wasd_aim_only label. An on-screen observation or screenshot should be retained locally; do not claim it was auto-validated.

## Later shot-phase protocol — not an instruction to swing now

Only after S001 demonstrates successful real-contact baseline and watcher noninterference, do exactly one operator-approved shot with fixed aim and familiar V1 waveform. S001 #166 has an opt-in in-Felk-loop selected-ball watcher; do not launch a competing loop or stream 88MiB through RPC. Preflight must verify frame sample overhead, uninterrupted A/waveform provenance, and ball visual motion. If the ball fails to move, keep negative-result trace and abstain; no forceful repeats. Use #180 PRE/POST source-gated native banks only if operator visibly sees displaced ball in the same hole **before reset**. Separate the candidate ball+0x4C translation, conditional +0xF0/+0xFC caches, selected player record aim matrix, and visually observed ball displacement. Coordinate any new compact read-only club/power watchlist with S001 rather than editing its bridge without review.

Capture minimal human-observed metadata for each attempt in the ignored private Data directory: fixed aim direction and hole, controller/waveform identifier, A-hold or shot, **whether contact actually happened**, whether ball visibly moved, whether reset occurred, UI distance/landing only when readable, and checkpoint time/order. Do not convert guessed power or the 100ft penalty into a distance label. Before numerical modeling, S003 needs real power bins and held-out boots/trials; S000 must promote each field individually in the evidence ledger.

## Stop/accept rules for cross-agent handoff

1. Fail closed on wrong revision/game/mode, changed selected slot/hole, source owner/selector mismatch, wrong-size or duplicate native images, missing manifest/hash, stale worktree or changed snapshot provenance. Distinguish selected and unselected ball records.
2. Never map the selected-record +0x03C angle to an actual game aim convention, or +0x0A0..+0x0BC to typed quaternions, without source-write provenance **and** opposite-direction interventions. A numeric sin/cos match is necessary structural evidence only.
3. Do not infer world XYZ, velocity, club head state, contact, power or distance from no-shot B0–B3 changes or a single static same-start vector. Snapshot times do not prove same emulator frame.
4. No unsupervised shot sweep, input waveform mutation, second RPC writer, raw binary upload, public memory report, auto-merge or model training. All candidate flags remain UNKNOWN / training false; S000 reviews any sanitized disclosure.
5. Owners: S002 analyzes repeated source-relative aim signatures, source writers and out-of-object MEM2 hotspots; S001 provides safe live frame/camera/contact provenance; S003 aligns at least three independently observed power bins with verified fields; S000 reviews ledger and privacy. Reuse #181 detailed atlas, #183 caches, #166 watcher, #180 shot pre/post—do not fork their parsers.
6. Do not label PR #181's broad memory scan as proof of unknown club/power semantics. A ranked offset is a *lead* requiring source read/write PC, independent intervention and gameplay correspondence.

**Status:** this documentation was constructed from existing code/PR findings only. No new real Dolphin/shot/dump experiment, new motion verification, or branch-specific Windows full-suite run was performed by this author.

## Operator readback: fullbank MEM2 priority clusters and Golf Main transient (2026-10-27)

This section records real **existing** B0–B3 private-atlas *aggregate metadata* reported by the operator after the study was written; **no new raw capture, instruction trace, shot or verified game field** was obtained. All indices below are **MEM2 256-byte bank-relative block indices**, not object-member offsets or approved world coordinates. No full RAM, float word, runtime heap pointer or local private report is checked in.

- Selected player 0 record: exactly 17 candidate u32 offsets +0x03C,+0x040,+0x044,+0x048,+0x04C,+0x094,+0x098,+0x09C,+0x0A0,+0x0A4,+0x0A8,+0x0AC,+0x0B0,+0x0B4,+0x0B8,+0x0BC,+0x0C0 were idle-stable, aim-changed and persisted B2=B3; record, slot0 and encompassing player_manager *overlap*.
- Golf Main +0x1DC: **B0=B1 and B3=B1 but B2 differs** (reverted after release); good **transient aim-associated candidate**, not power/contact or typed game flag. Golf Main +0x074 changes at every transition, idle nuisance.
- Dense MEM2 blocks 114551..114563 (13 blocks): 781 quiet-idle aim-changed words, 364 persisted, 0 reverted and 0 idle changes; 417 aim-changed words evolved to a third value after release. This looks like a bulk-updated region but source ownership is unverified.
- MEM2 blocks 117016 and 117017: respectively **47/47** and **31/31** quiet-idle aim-changed words persisted, 0 reverted, 0 idle. Operator's first 12 persisted word offsets in block 117016 were +0x00,+0x14,+0x18,+0x34,+0x38,+0x3C,+0x40,+0x44,+0x48,+0x4C,+0x50,+0x54; in block 117017 +0x00,+0x08,+0x10,+0x1C,+0x24,+0x28,+0x2C,+0x30,+0x34,+0x3C,+0x48,+0x4C.
- MEM2 blocks 117095 and 117096: respectively **57/57** and **59/61** quiet-idle aim-changed words persisted, 0 reverted, 0 idle. Operator's first 12 persisted offsets in block 117095 are +0x18..+0x44 at 4-byte intervals; in block 117096 +0x00..+0x2C at 4-byte intervals. Nonpersistent two words changed after release without reverting to B1.

**Interpretation limits:** sequential changed words may be buffer/copy/graphics/state arrays, not gameplay control. 117016..117017 and 117095..117096 are adjacent *within* each pair but not a known shared object. Do NOT add unowned block ranges to the frame watcher, use them as a supervised swing-power label or imply they are independent player records. Before typing any of them, S002 should trace source owner and write PC, compare independent left/right and camera-only controls; S000 should approve any evidence promotion. The 51-word *source-selected player-record* read-only swing watch is already separately owned in S001/S002 PR #189 (stacked on #166); do not duplicate its watcher, modify its waveform or run a shot before the S001 contact, ABI, read budget, full test and privacy gates.

### Safe next preflight: #189 whole-record watcher, no Dolphin input

The #189 owner has an existing dry-run/test runbook at \`research/studies/S001-S002-SWING-RECORD-01.md\` on branch \`agent/research/swing-selected-record-watch-20261027\`. Run its **offline-only** tests and \`py scripts/record_selected_ball_swing_private.py\` with no flags, which explicitly returns \`live_input_sent=false\`. Do **not** run \`--send-live-swing\`, \`--send-live\`, bridge generation, or a fresh Dolphin process based on this addendum; S001/S000 owners still require a proven non-watched contact baseline and approval. No new memory data should be assumed from synthetic-green tests.
