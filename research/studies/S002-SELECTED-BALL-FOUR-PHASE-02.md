# S002-SELECTED-BALL-FOUR-PHASE-02 — real preserved B0–B3 candidate-position null controls

**Purpose:** On user-provided one-session Wii Sports RSPE01 Rev1 native MRAM/ExRAM pairs, compare only SOURCE-GATED selected player record, nested ball-related translation and current course start. Do not scan arbitrary pages, guess velocity or call a field game-physics world coordinates before source and movement verification.

## Why this is now possible

Operator reports four B0/B1/B2/B3 paired MRAM+ExRAM checkpoints preserved with the S002 keeper in one intended session. Their private local manifest SHA digests show **MEM1 and MEM2 both differ** for each of B0→B1 (idle), B1→B2 (WASD aim), B2→B3 (idle after aim). Operator separately confirms that WASD caused a visible aiming direction change in B2. The existing S002 128-byte `RPGolMain+0x030` player-like window 32/32 aligned 32-bit words showed no change across all phases. This is a scoped negative observation only; it does NOT mean the selected record nested ball position was unchanged. No shot/landing was performed.

## Implementation and ownership

`scripts/audit_selected_ball_four_phase_private.py` is an **additive file in stacked PR #163**, importing existing #160 authoritative `audit_golf_two_bank_roster_private.py` and existing #163 `audit_selected_ball_start_link_private.py` without duplication or modification. `tests/test_selected_ball_four_phase_private.py` has 10 license-safe synthetic tests, CI uses the preexisting #163 Windows/Linux workflow. No new ROM, Dolphin, controller, RPC, memory-reader or GitHub uploader. Existing private RAM never leaves the operator computer.

The CLI takes a single private folder with exact preserved `B0-MEM1.bin`, `B0-MEM2.bin` ... `B3-MEM2.bin` and its `checkpoint-manifest-PRIVATE.json`, under the canonical sibling ignored `Wii-AI-Golf-Data`. It validates source revision, Golf scene, mode, source PPC roster/player-selected slot, field current start and all four native bank dimensions. It checks each source-bank SHA256 against the preserved private manifest, plus expected source pauses/phase-label sequence, and re-resolves all addresses per pair. It never emits actual RAM bytes, absolute pointers, float values, file paths or SHA256 hashes.

Output only: paired-bank changed booleans for three transitions, selected-record/selected-ball/start `VEC3` bitwise changed-component counts (0..3), equality counts (0..3) per phase, selected slot/hole stability, input provenance as **operator report only**, candidate stationary no-shot consistency, explicit `ball_world_xyz_verified=false`, `velocity_verified=false`, `approved_for_model_training=false`, `allowed_to_publish=false`. Operator flags do not independently prove same boot/frames.

## Reproduction (safe, private, no emulator)

Run on PowerShell with existing folder variable `$private` pointing to preserved B0-B3 images. If it is unset, paste the exact existing session folder. Use a fresh standalone checkout of **the stacked #163 branch**, not raw main or #151:

```powershell
$root = 'D:\Projects\Wii Golf AI'
$repo = "$root\Wii-AI-Golf"
$workSelected = "$root\Wii-AI-Golf-Selected-Ball-Four-Phase"
$branchSelected = 'agent/research/selected-ball-start-link-20261027'
if (-not $private -or -not (Test-Path (Join-Path $private 'checkpoint-manifest-PRIVATE.json'))) {
    $private = (Read-Host 'Existing B0-B3 session folder (Wii-AI-Golf-Data)').Trim('"')
}
if (-not (Test-Path (Join-Path $private 'B3-MEM2.bin'))) { throw 'Missing private B0-B3 session' }
git -C $repo fetch origin "refs/heads/${branchSelected}:refs/remotes/origin/${branchSelected}"
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
if (-not (Test-Path $workSelected)) {
    git -C $repo worktree add --detach $workSelected "origin/$branchSelected"
    if ($LASTEXITCODE -ne 0) { throw 'Worktree checkout failed' }
} else {
    $expected = git -C $repo rev-parse "origin/$branchSelected"
    $actual = git -C $workSelected rev-parse HEAD
    if ($expected -ne $actual) { throw 'Existing checkout is stale; do not force reset' }
}
py -m unittest discover -s "$workSelected\tests" -p 'test_selected_ball_four_phase_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Four-phase tests failed' }
py "$workSelected\scripts\audit_selected_ball_four_phase_private.py" --private-root $private --aim-visibly-moved --operator-same-session
if ($LASTEXITCODE -ne 0) { throw 'Private selected ball study failed' }
```

## Falsification and next move

- If the B0 selected record/ball/start match and B0-B3 ball candidate and course start triplets stay unchanged while both banks and the visible aim change, **no-shot position stability is supported**, but NOT physics ball identity or dynamic XYZ; next S001/S002 request one operator-approved small field-specific post-shot/flight study.
- If nested ball changes during B1 idle, B2 aim or B3 no-shot idle while the source current start remains stable, investigate whether it is render/camera/pointer-interpolation or collision proxy. Do NOT call it motion without visible ball movement.
- If selected record/hole change between phases, refuse comparison and investigate mode/scene/reset/reallocation. Do NOT invent a continuous ball series.
- If selected ball and current-start vector both change, investigate game reset/hole change; never assume actual ball flight.
- If hashes/pair files unchanged, wrong-sized or scene/source PPC gates fail, abort and preserve the user's existing files; do not silently generate plausible results.
- Even passing null controls cannot measure velocity, swing power, club angle, collision, impact time or landing; need separate same-frame S001 frame-hook and at least two independent observed shot outcomes, then S003 model evidence gates. Keep ALL training flags false.

### Privacy

The stdout JSON is marked local-private, not automatically GitHub-approved. Other agents may receive an operator-reviewed aggregate count-only subset with S000 review; never upload raw `.bin`, `.raw`, private manifest, source runtime addresses/values or DOL to the public repo.