# S002-EXISTING-HIT-EFFECT-HANDLE-LIFECYCLE-01

**Status: DRAFT, offline-only, no new swing, no physics or training approval.**
**Owner:** S002 evaluation support via [issue #121](https://github.com/Nate27624/Wii-AI-Golf/issues/121); upstream [#197](https://github.com/Nate27624/Wii-AI-Golf/pull/197) verified 4 pairs, [#199](https://github.com/Nate27624/Wii-AI-Golf/pull/199) private triage, [#181](https://github.com/Nate27624/Wii-AI-Golf/pull/181) independent no-shot B0–B3. New code paths only; no edits to any S000–S005 canonical CLI, bridge, launch, collector, training schema or shared registry.

## Research question

The successful human-confirmed isolated V1 hit (run `outcome-20261028T033948Z-5cd47f00`) has **3 PRE, 2 POST and 3 SETTLED** narrow read-only windows. All eight stable PRE-to-SETTLED changes are in three OVERLAPPING minimap effect windows, not ball physics windows. Source-based layout concordance from #197 identifies four apparent `RPSysEffect::mHandle` ID/pointer pairs: **+0x078 / +0x07C** relative to each possible effect wrapper. The window bases are +0x90 apart, but that does not prove a C++ object size of 0x90.

This new **independent private offline** tool asks which two words in each pair changed **together**, whether either changed within PRE/POST/SETTLED phases, and whether the pair merely has source-plausible ID/pointer representation. Previous #197 ranked changed words individually and established pair layout, not the per-pair temporal joint patterns. It does **not** dereference object pointers. The linked NW4R effect object `mObjectID` has NOT been checked against the saved HandleBase ID.

## Source-backed candidate field map, not physical training fields

| Source-relative pair | Candidate role | Allowed interpretation |
|---|---|---|
| effect slot 0..3 +0x078 | `RPSysEffect.mHandle.mObjectID` | untyped saved effect handle object ID (u32) |
| effect slot 0..3 +0x07C | `RPSysEffect.mHandle.mObject` | pointer-shaped `LinkedObject*`; **target and matching ID unverified** |
| selected PlayerManager record +0x03C, +0x040..0x04C, +0x094..0x0C0 | angle, transform and pose-like hypotheses from S002 #181/#178 | NO evidence in this 8-snapshot successful hit, because those objects were not sampled by this collector |
| selected RPGolMapObjBall +0x30/+0xCC/+0xF0/+0xFC | initialized vector/cache hypotheses from #181/#183 | static source copies; NOT flight XYZ or ball velocity |
| field manager selected start/pin/cup +0x30 translation | scene landmark hypotheses from #192/#162 | require independent course/target and unit controls |
| actual ball trajectory/velocity, collision, power, true distance | P0 unknowns | **NOT captured or verified** by the successful-hit eight changed words |

Sources: `doldecomp/ogws/include/Pack/RPKernel/RPSysEffectBase.h` (+0x78 handle), `doldecomp/ogws/include/nw4r/ef/ef_handle.h` (ID and pointer), #197's source-concordance evidence, S002 #181/#183. A render-effect handle may react to a hit without encoding trajectory or impact. The old 100.0-ft off-green readout is possibly censored; human 75% UI meter is not an internal RAM power label.

## Exact offline behavior

`scripts/audit_effect_handle_lifecycle_private.py` opens only the existing two original private files, in ignored sibling `Wii-AI-Golf-Data/captures`. It requires the exact source, RSPE01 Rev1, mode 4, ordered 3/2/3 samples, known-good human contact, frozen 45 OBSERVED-frame A-lead plus 89 trace ACK frames, eight expected candidate addresses, source window base spacing, unmoved bases across eight captures, and consistent overlapped RAM words in each alias. Any mismatch fails closed.

It reports for each of four anonymous ordinal slots whether the ID and pointer changed together in BOTH POST reads against a stable PRE baseline, phase-internal stability, change persistence, null pointer flags, and representation plausibility. It **never** returns private u32, addresses, bytes, real pointer targets, full paths, screenshots or hashes. All non-atomic frame warnings remain; it does not claim exact impact frame or shot cause.

### Operator execution gate

**No live Dolphin/game action is needed.** The file and tests are on an unmerged DRAFT branch, not main. The user has requested automatically uploaded SANITIZED outputs from an approved CLI. This stand-alone private-only analyzer **does not implement or claim automatic publication**: S002/S000 must review output allowlists and integrate the existing trusted `scripts/research_cli.py` publisher, with mocked publishing/privacy tests, before providing a normal user-run PowerShell block. Do not ask operator to manually upload raw reports or run Dolphin to satisfy this study.

For reviewer-only offline synthetic validation (in an explicitly isolated checkout of this branch):

```powershell
$ErrorActionPreference = 'Stop'
$root = 'D:\Projects\Wii Golf AI'
$repo = Join-Path $root 'Wii-AI-Golf'
Set-Location -LiteralPath $repo
$branch = 'agent/research/s002-existing-hit-effect-handle-lifecycle-20261028'
$work = Join-Path $root 'Wii-AI-Golf-P0-Handle-Lifecycle'
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
if (-not (Test-Path -LiteralPath $work)) {
    git -C $repo worktree add --detach $work "origin/$branch"
    if ($LASTEXITCODE -ne 0) { throw 'Isolated worktree creation failed' }
} else {
    $dirty = @(git -C $work status --porcelain)
    if ($LASTEXITCODE -ne 0 -or $dirty.Count -gt 0) { throw 'Existing worktree is dirty' }
    $have = (git -C $work rev-parse HEAD).Trim()
    $want = (git -C $repo rev-parse "origin/$branch").Trim()
    if ($have -ne $want) { throw 'Worktree version does not match remote; preserve other agent state' }
}
py -m unittest discover -s (Join-Path $work 'tests') -p 'test_effect_handle_lifecycle_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Offline-only synthetic tests failed' }
Write-Output 'OFFLINE SYNTHETIC TESTS DONE; no private RAM read; NOT A GAME RESULT; NOT UPLOADED'
```

Do not run the data-bearing audit without the approved publisher. Tests may run in hosted Windows/Ubuntu CI because they are fully synthetic.

## Exit / review criteria

1. Both Windows and Ubuntu focused CI + FULL Windows repo suite green and exact code review; report any failing test.
2. Original source-window alias/handle class interpretation reviewed by #197 author, S002 and S000. Unexpected ID/pointer joint patterns are recorded as **negative evidence**, never corrected by editing raw captures.
3. Output privacy gate and existing publisher integration reviewed separately by S000 before operator invocation. No user click, manual GUI, bash command or alternate swing recipe.
4. If the four handle pairs are merely effect lifecycle state, return to actual dynamic ball-object ownership through PPC writer reads and pre/flight/post **same-shot** frame brackets before ever labeling ball XYZ/velocity/contact/power or model training.
5. Preserve operator's report that a separate prior JSON may have been captured while the ball was descending/slowing; its direction and relationship to the 3/2/3 hit cohort remain **unknown**, not a stationary label.
