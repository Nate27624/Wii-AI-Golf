# S002-SELECTED-PLAYER-STATE-01 — untyped 5-literal state field B0/B1/B2/B3

**Status:** new, offline-only, source-anchored negative-control study; no result from user's B0–B3 executed by this branch yet. Source owner S002 #162 (Rev1 PPC store instruction), S002 #160 (roster and selected index), S002 #163 (selected ball/start and private checkpoint manifest), S001 #166 (sole live watcher), S000 #154 (canonical evidence ledger), S003 #125 (training abstention). This PR is *stacked on #163* to reuse source checks and avoid a competing RAM parser.

## Existing real evidence vs missing state-field evidence

User successfully preserved B0 initial idle, B1 delayed idle, B2 visibly changed WASD aim (no shot), B3 return idle. Both complete MEM1 and MEM2 hashes differ at B0→B1, B1→B2 and B2→B3. Source gates (RSPE01 Rev1, Golf scene5, sport2, training mode4, selector index0, same hole) hold for all four. Selected record +0x54, nested ball-related translation +0x4C and source-defined start translation are **bitwise identical across B0..B3** (3/3 each). This is a strong *no-shot stationary candidate* negative control, NOT physical world ball XYZ, velocity or swing power.

New independent Rev1 DOL source analysis in #162 identified `RPGolPlayer.cpp` around PPC 0x8029F0C0 with `mr r29,r3`, then five small integer literal branches writing receiver `+0x24`:

| LI PC | STW PC | Literal | Record receiver base |
|---|---|---|---|
| 0x8029F0C8 | 0x8029F0CC | 5 | r3 |
| 0x8029F0D4 | 0x8029F0DC | 1 | r3 |
| 0x8029F0F4 | 0x8029F0F8 | 2 | r29 |
| 0x8029F134 | 0x8029F138 | 3 | r29 |
| 0x8029F1BC | 0x8029F1C0 | 4 | r29 |

These prove only **five observed store instructions**, not a complete enum or any gameplay meaning. Source code also traverses player record +0x88 to a Ball unit; does not make +0x24 a power meter or contact detector. A state outside {1,2,3,4,5} must remain unknown rather than fail or be clamped.

## Implementation

`scripts/audit_selected_player_state_four_phase_private.py` is a strictly offline read-only audit. It imports #163's selected-ball and four-phase checkpoint readers and #160's source PPC verifier. Each of the four exact native 24MiB MEM1+64MiB MEM2 banks is SHA256-compared to the operator's **private** checkpoint-manifest; game/scene/mode/hole/selected record/ball/start sources are re-resolved individually. The analyzer then verifies actual PPC source code against all five pinned li/stw patterns and receiver register move. It reads **only** source-selected record +0x24 one 32-bit integer per snapshot, compares equal/change across phases and whether each falls within the 5-literally-observed set. Numeric state values are never printed. It reports source start/ball stability independently to detect phase/actor confusion.

Output: per-stage *boolean* `observed_value_in_source_literal_set`, per-transition *boolean* `selected_player_state_word_changed`, per-transition `ball_candidate_components_changed` and `source_start_components_changed` counts (0..3), and an overall aim-change boolean. All reported phase state meanings, true emulated-frame timing, real shot, ball XYZ, velocity, power, and training remain unverified. The output explicitly states `allowed_to_publish=false`; it is not a S000-approved automatic public schema.

`tests/test_selected_player_state_four_phase_private.py`: synthetic tests for known stable states, aim-contrasted changes, unknown values, five source writer and receiver PC corruption, invalid scene/revision, selected-record/hole swap, bank provenance, incomplete pairs, privacy and explicit no-training gates. CI tested separately on Windows and Linux.

## One-time operator invocation — uses existing B0–B3, no Dolphin

```powershell
$root = 'D:\Projects\Wii Golf AI'
$repo = "$root\Wii-AI-Golf"
$workState = "$root\Wii-AI-Golf-Selected-State-Offline"
$branch = 'agent/research/player-state-literal-fourphase-20261027'
# Reuse the current $private variable from the B0-B3 paired dump session.
if (-not $private -or -not (Test-Path (Join-Path $private 'checkpoint-manifest-PRIVATE.json'))) {
    $private = (Read-Host 'Paste the EXISTING private B0-B3 folder').Trim('"')
}
if (-not (Test-Path (Join-Path $private 'B3-MEM2.bin'))) { throw 'Missing old B0-B3 pair files' }
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
if (-not (Test-Path $workState)) {
    git -C $repo worktree add --detach $workState "origin/$branch"
    if ($LASTEXITCODE -ne 0) { throw 'Worktree add failed' }
} else {
    $expected = git -C $repo rev-parse "origin/$branch"
    $actual = git -C $workState rev-parse HEAD
    if ($expected -ne $actual) { throw 'Existing worktree stale; do not reset automatically' }
}
py -m unittest discover -s "$workState\tests" -p 'test_selected_player_state_four_phase_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'State source tests failed' }
py "$workState\scripts\audit_selected_player_state_four_phase_private.py" --private-root $private --aim-visibly-moved --operator-same-session
if ($LASTEXITCODE -ne 0) { throw 'Private selected-player state study refused checkpoint source' }
```

## Decision rules

- `selected_player_state_word_stable_in_no_shot=true` AND B0–B3 ball/start stable and both banks changed: supports source state as a *stationary no-shot baseline*. Does NOT prove it changes during a shot, or that all known states can be classified.
- `selected_player_state_word_changed_during_aim=true`: mark candidate as **input-sensitive**, not a contact/power-only state indicator. Cannot use as contact event without additional controls.
- Changed during B0→B1 or B2→B3 idle: time/animation/proxy nuisance may exist; do not interpret it as a shot phase.
- Some state values outside literal-known-set: flag unknown categories; avoid training or printing raw numbers; follow additional actual PPC write sites later.
- Source, selector, revision, hole, native-size or manifest mismatch: **STOP** and investigate, no state claim.
- Even a perfectly stable no-shot B0–B3 result is insufficient to prove dynamic ball, same-frame timestamps, contact, club rotation or swing power. S001 #166 alone owns future one-shot watch after repaired reliable swing and independent noninterference review.

## Coordination

- User reports another agent has resolved the Dolphin startup failure, but as of this documentation the exact patch and reproducible test outcome have **not** yet appeared in current #166/#172/#173 PR descriptions. Treat as pending publication, not a verified fix or authorization for a shot.
- When published, compare actual bridge changes, no-watch contact and frame watcher behavior; do not presume previous instrumented V2 weak-no-ball and legacy native boot crash have the same cause.
- S000 #154 is the sole source of verified training readiness. Keep world-ball XYZ, velocity, club pose, power and actual-contact semantics false until direct game evidence is collected. Never push raw RAM or private hashes to GitHub.