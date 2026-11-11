# P0 — two-label selector-global Wedge/Iron probe (2026-11-10)

Status: SOURCE-CANDIDATE; **not** verified native selected club ID.
Training approved: **false**. No controller outputs, no swing, no A, no
savestate load, no guest memory write, no private data upload.

## Why this experiment is necessary

The earlier #401 broad-memory club study stopped before sampling because the
operator supplied only Wedge. A later real operator D-pad test demonstrated
**Wedge -> Iron -> Wedge** in Rev1 Hitting the Green (scene 5, mode 4)
while the previously tested PlayerManager +0x1C index stayed 0 across
all three observed states. This specifically rejects that *receiver* as the
live selected-club index in that session. It does **not** refute the separate
four-state PPC writer found by source triage.

PR #412, separate source audit, identified:
- PlayerManager global hypothesis `0x804BF8D0` from the previously
  source-gated runtime reader, conditionally `r13-0x5AB0`.
- The same source handler passes `r13-0x5A80` as a **different**
  receiver to a bounded [0,3] `+0x1C` writer.
- The conditional static small-data join implies `r13=0x804C5380`
  and candidate distinct global `0x804BF900`. Neither a live r13
  register read nor native receiver ownership has been established.

The original 26-packet multi-club broad-float study had no aim/holdout-valid
discriminator. Do NOT repurpose it for training.

## Protocol

The new `scripts/p0_live_club_pair_private.py` uses #412's
`p0_live_club_selector_global_private.bracketed_index`, retaining the
canonical Rev1 active scene, player, ball, hole, selector pointer/epoch and
double-read validity checks. It verifies that the source-candidate index
distinguishes **Wedge** from **Iron**, then restores Wedge, changes aim
(without changing club), repeats the pair, and produces predictions *before*
two withheld operator labels are revealed. The secondary +0x3C source-selected
record word is direction-correlated, not established native aim semantics.

If the first Iron index equals Wedge, it stops immediately and reports
`ABSTAIN_NO_TWO_CLUB_INDEX_CONTRAST_STOP_EARLY`. That is a useful negative
result, not a reason to retry the same candidate unmodified.

Any failure, missing label, aim confound, source pointer change, ball motion,
or blind misclassification leaves all learning flags false. Two-label
candidate success **does not** validate Driver/Putter or native r13 ownership.

## Operator — copy/paste PowerShell, current Dolphin session only

This preserves the original working tree and does not download scripts
manually; Git checks out the committed isolated branch in a new detached
worktree. No Dolphin launch or button injection is performed. Existing
Felk Dolphin RPC bridge must be active on port 55355 and Hitting the Green
ready to hit with A released.

```powershell
$ErrorActionPreference = 'Stop'
$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
$parent = Split-Path $repo -Parent
$work = Join-Path $parent 'Wii-AI-Golf-P0ClubPair-20261110'
$data = Join-Path $parent 'Wii-AI-Golf-Data\captures'
$branch = 'agent/p0-club-two-label-probe-20261110'
if (-not (Test-Path -LiteralPath $repo)) { throw 'Original repository not found' }
if (-not (Test-Path -LiteralPath $data)) { throw 'Private captures folder missing' }
if (Test-Path -LiteralPath $work) { throw 'Worktree destination exists: refusing overwrite' }
& git -C $repo fetch --no-tags origin "refs/heads/$branch"
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
& git -C $repo worktree add --detach $work FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'Worktree creation failed' }
$script = Join-Path $work 'scripts\p0_live_club_pair_private.py'
& py -3 -I $script --selftest
if ($LASTEXITCODE -ne 0) { throw 'Offline selftest failed' }
& py -3 -I $script --private-root $data --port 55355
Write-Host ('Experiment exit code: '+$LASTEXITCODE)
```

Operator follows the prompts in Dolphin. Do **not** press A or swing.
For the two blind phases, choose Iron and Wedge in any order, reveal the
label only *after* the printed prediction. Share only final sanitized JSON,
not private `*-PRIVATE` captures or original MEM1/MEM2 banks.

## Validation needed before merge

Synthetic Windows and Ubuntu tests, complete offline suite, exact-head
review, source-owner review and the actual operator live test. No remote
Dolphin access available to the agent. No training promotion.
