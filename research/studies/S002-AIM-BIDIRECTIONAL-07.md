# S002-AIM-BIDIRECTIONAL-07 — discriminate golfer aim from idle/rendering motion

**Status: preregistered PROPOSAL, NOT LIVE-APPROVED and NOT implemented by the current 4-phase analyzers.**
Owner of this document: supporting research/handoff. S002 owns native paired-bank capture, source-validated readers and semantics; S001 owns input and emulator startup; S000 owns private/public evidence boundaries; S003 owns downstream training and validation. Coordinates via [issue #121](https://github.com/Nate27624/Wii-AI-Golf/issues/121). No alternative bridge, launcher or RAM writer is introduced.

## Baseline and why a different experiment is warranted

The privately collected RSPE01 USA Rev1 mode-4 B0/B1/B2/B3 no-shot controls used paired 24 MiB MEM1 and 64 MiB MEM2 snapshots. B0->B1 was elapsed idle, B1->B2 was a human-observed WASD aim change, B2->B3 was release/idle. Existing S002 [#181](https://github.com/Nate27624/Wii-AI-Golf/pull/181) and [aim-source study](https://github.com/Nate27624/Wii-AI-Golf/blob/agent/research/fullbank-fourphase-source-overlay-20261027/research/studies/S002-AIM-POSE-SOURCE-XREF-01.md) found 17 selected inline-player-record aligned fields with aim association, no observed idle change and persistence across post-aim idle:
- +0x03C: rotation/angle-like 32-bit float candidate.
- +0x040..+0x04C: four matrix-like floats consistent with `[sin(a),cos(a);-cos(a),sin(a)]` to roughly 1e-4 in one session; this is **mathematical shape**, not proven yaw or club-head orientation.
- +0x094..+0x09C: a three-float candidate. +0x0A0..+0x0AC and +0x0B0..+0x0BC: norm-near-one four-float candidates; their meaning is unknown.
- +0x0C0: an aim-associated scalar.
- +0x090 **changed with idle** and is a negative/confounding control, not an aim target.
The three inactive player records, source-selected nested ball/start position and static map objects were stable under this particular no-shot contrast. Candidate owner pointers and some PPC write sites have source support, but exact `this` register identity and semantics remain unproven. None of these observations establishes physical club pose, velocity, swing power, contact, physics ball XYZ or a training-ready feature.

This proposal **does not** rerun B0–B3, duplicate the private fullbank scanner (#181), private object window scanner (#178), source callsite tracing (#183), frame-watched single-shot S001 work (#166), or shot PRE/POST protocol (#180). It adds the missing **counter-direction causal discrimination plan**.

## Hypothesis and falsification

**H1:** One or more of the 17 fields encodes the applied golfer aiming state, rather than generic time, camera, animation or selected-ball state.

**Alternative H0:** The fields reflect render/UI changes, pose animation without input semantics, transitions between states or coincidental time/idle drift.

The crucial discriminator is a *paired sign reversal* under matched left-vs-right visual aiming, with center recovery; a single changed WASD phase cannot distinguish these.

## Seven checkpoints — one operator-approved live process, no ball hit

Do not create these snapshots until S001/S002/S000 explicitly approve a separate typed seven-phase keeper and the clean Felk Dolphin launch/input path. Never issue arbitrary savestate or A/A+B/A commands from a live at-ball screen. Save every screenshot and native RAM pair locally only.

| Phase | Human-visible condition | Control intent |
| --- | --- | --- |
| P0 | First-ball ready, stationary, centered | Establish baseline |
| P1 | Same screen, timed idle (no input) | Time/render negative control |
| P2 | Deliberate RIGHT aim of predeclared magnitude | Positive direction A |
| P3 | Visibly recentered and stationary | Recovery/reversion control |
| P4 | Deliberate LEFT aim of comparable magnitude | Opposite-direction control |
| P5 | Visibly recentered and stationary | Second recovery control |
| P6 | Further timed idle, no input | Late drift control |

Use one controlled hole, selected slot and revision throughout; do not shoot, move the ball, rotate the camera independently, change hole/game mode, vary controller timings, or restart Dolphin between these seven pauses. Use the same human-observed aiming displacement magnitude/duration for P2 and P4 where feasible; if exact parity cannot be established, mark as *unmatched* instead of fabricating equality. Export MEM1 and MEM2 under each **same GUI pause**; copy to unique phase files before resuming, with per-bank SHA and phase metadata. A GUI-paired export remains **human attested** and does not by itself prove atomic guest frame IDs.

Require seven distinct phase-specific pairs; **do not relabel old B0–B3 as P0–P6 or mix prior independent boots**. Store in a NEW ignored `Wii-AI-Golf-Data/captures/...` folder. First pilot = 1 process x 7 checkpoints, then >=2 additional independent-boot replications with counterbalanced first direction if safe. All counts are proposals, not claims of execution.

Stop at any missing/wrong-sized bank, stale export, changing scene/hole/selected slot/owner, failed recenter, ambiguous GUI pause or button state. No automatic reattempt or mass live shots.

## Predeclared candidate analyses (S002 implementation only, not yet callable)

1. **Strict source/pair gates:** full MEM1+MEM2 dimensions 24+64 MiB, per-phase hashes, source revision/mode4/scene5, source-selected PlayerManager record and identical canonical source-owner tuple or explicit relocation-aware re-resolution. Invalid pairs never contribute a candidate score.
2. **No-shot specificity:** inspect field changes P0->P1 and P5->P6 first. Demote any candidate already drifting in either idle control. Exclude source current-start, selected ball translation, inactive records, pin/cup, scene and camera/render confounds from positive labels.
3. **Reversal:** for +0x03C evaluate *circular* normalized changes from center to P2 and P4 (do not subtract raw wrapped angles); look for opposite direction and center recovery at P3/P5. For +0x040..+0x04C verify orthonormality/determinant and angle-to-matrix consistency, not just independent float changes. For +0x094..+0x0C0, compare signed/normalized changes and stability; avoid guessing vectors or quaternion roles.
4. **Source witness:** audit producers at PPC PCs `0x8029ED90..0x8029EE44` and `0x8029FAEC..0x8029FBA8`; trace the register-provenance chain to source-selected inline record, confirm helpers `0x802A3894`, `0x80295304`, `0x8029528C` and reject stack/other-object offset collisions.
5. **Replication:** report separate independent-boot n, direction-order counterbalance, per-field idle false-positive rate, reversible-pose effect and human visual agreement. Never use repeated frames from one run as independent boots. Maintain holdout boots/directions for downstream S003.
6. **Abstention:** possible candidate field can be promoted from *aim associated* to *source+direction supported* only after repeatable opposite-direction/center controls and owner-linked code trace. World-space yaw, club head angle, in-swing power and model-training permission **remain false** without separately verified game semantics and impact/shot data.

## Immediate safe, private, offline work from existing B0–B3 captures

The fullbank atlas in #181 already examines every aligned 32-bit word in the two banks for B0–B3; use its frozen **draft** worktree, *not* the main operator checkout. Before running, validate that the B0–B3 folder contains the approved source manifest `checkpoint-manifest-PRIVATE.json` and all eight native images. This command **does not capture a new phase**:

```powershell
$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
$work = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Aim-Fullbank-Audit'
$branch = 'agent/research/fullbank-fourphase-source-overlay-20261027'
$private = (Read-Host 'EXISTING B0-B3 private session folder').Trim('"')
if (-not (Test-Path -LiteralPath (Join-Path $private 'checkpoint-manifest-PRIVATE.json'))) { throw 'No valid phase manifest' }
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw 'Branch fetch failed' }
if (-not (Test-Path -LiteralPath $work)) {
    git -C $repo worktree add --detach $work "origin/$branch"
    if ($LASTEXITCODE -ne 0) { throw 'Worktree creation failed' }
} else {
    if ((git -C $work rev-parse HEAD) -ne (git -C $repo rev-parse "origin/$branch")) { throw 'Existing worktree is stale; do not reset' }
}
Push-Location $work
try {
    py -m unittest discover -s tests -p 'test_golf_fullbank_fourphase_private.py' -v
    if ($LASTEXITCODE -ne 0) { throw 'Focused offline test failed' }
    $output = Join-Path $private 'fullbank-aim-PRIVATE.json'
    if (Test-Path -LiteralPath $output) { throw 'Private report exists; do not overwrite' }
    py scripts/audit_golf_fullbank_fourphase_private.py --private-root $private --output $output --top-blocks 1000 --max-object-offsets 4096
    if ($LASTEXITCODE -ne 0) { throw 'Source-gated fullbank audit failed' }
} finally { Pop-Location }
```

Output `fullbank-aim-PRIVATE.json` may contain detailed source-relative candidates and is **LOCAL PRIVATE, NOT FOR GITHUB**. CLI counts are unreviewed for publishing unless S000 explicitly allowlists. This draft worktree is an *offline analysis*, not an authorization to run a live experiment or self-merge the PR.

## Follow-on dependency for physical swinging and learning

The unlocated swing-power/club motion signals require S001's frame-aligned watcher and a later separately approved **visible ball-displacement** PRE/POST pair (#166/#180). Even if the aim protocol confirms a direction encoding, it is not a substitute for a verified A/button state, club pose in motion, contact and ball-speed/time measurement. `100 ft` off-green is a *penalty display*, not measured carry distance. Once S002 proves a dynamic source ball vector, use actual frame intervals/dt to evaluate velocity candidates (not just `Δposition` from two distant GUI dumps); join to S001's exact shot-event trace only with stable same-shot IDs, not timestamps alone. Labels stay `approved_for_training=false` until source and outcome gates are satisfied.

## Merge and privacy gates

This document adds no executable path and has not performed live Dolphin, RAM capture, Windows tests or full suite. The command is an unexecuted offline recipe. S002/S001/S000 approval is required before extending a live collector. Authors of any future code must add synthetic tests, validate Windows host and full repository suite, and use a separate PR rather than silently editing S001/S002 integration. Raw RAM, ROM, savestates, game executable bytes, private hashes/pointers/paths and detailed private reports must not be uploaded to GitHub. Only an approved count-only/source-relative *sanitized* summary may enter the shared evidence ledger.
