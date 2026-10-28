# S002 manager receiver register provenance (source-only follow-up)

The operator's **real** B0 source-gated run of `audit_golf_selected_aim_callers_private.py` passed, finding two Rev1 `RPGolPlayerManager.cpp` call chains:

- `0x802A293C lwz r3,+0x334(r29)` → `0x802A2968 bl 0x8029ED2C`;
- `0x802A2B00 lwz r3,+0x334(r29)` → `0x802A2B0C bl 0x8029ED2C`.

The callee saves its incoming `r3` as `r29` and computes the angle / two-dimensional rotation fields around `+0x3C..+0x4C`. The source +0x334 is the same previously validated source-selected player-record pointer at runtime. The operator's actual report had `selected_player_pointer_source_contract_verified=true`, `source_direct_calls_verified=2`, and `manager_r29_runtime_identity_independently_verified=false`. That last flag is the outstanding source provenance question: **what exactly supplies r29 in the caller?**

`scripts/audit_golf_manager_r29_private.py` is a conservative static aid for answering that question using only the preserved B0 Rev1 PPC code. It rejects incorrect native bank hashes and source-selected pointer gates, verifies both exact caller instruction signatures, scans only the public `RPGolPlayerManager.cpp` linked source text, and prints up to four PPC r29-assignment candidates before each selected-player call plus short instruction neighborhoods. It deliberately does not claim control-flow completeness, actual execution, a game heading, shot physics, or training approval. Static r29 candidate proximity alone is **not proof** that the selected Manager instance is in r29.

## Self-contained operator PowerShell invocation

```powershell
$ErrorActionPreference = 'Stop'
$root = 'D:\Projects\Wii Golf AI'
$repo = Join-Path $root 'Wii-AI-Golf'
$work = Join-Path $root 'Wii-AI-Golf-Expanded-Memory'
$branch = 'agent/research/golf-source-object-windows-private-20261027'
$private = Join-Path $root 'Wii-AI-Golf-Data\ball-study-20261027-212633'
if (-not (Test-Path -LiteralPath (Join-Path $private 'checkpoint-manifest-PRIVATE.json') -PathType Leaf)) { throw 'Missing existing manifest' }
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed' }
if (Test-Path -LiteralPath $work) {
  git -C $work rev-parse --show-toplevel | Out-Null
  if ($LASTEXITCODE -ne 0) { throw 'Invalid worktree' }
  $dirty = @(git -C $work status --porcelain)
  if ($LASTEXITCODE -ne 0 -or $dirty.Count -gt 0) { throw 'Uncommitted edits; abort' }
  git -C $work switch --detach "origin/$branch"
} else {
  git -C $repo worktree add --detach $work "origin/$branch"
}
if ($LASTEXITCODE -ne 0) { throw 'Worktree update failed' }
py -m unittest discover -s "$work\tests" -p 'test_golf_manager_r29_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
py -I "$work\scripts\audit_golf_manager_r29_private.py" --private-root "$private"
if ($LASTEXITCODE -ne 0) { throw 'Source scan failed' }
```

The agent should focus on whether the corresponding function's incoming `r3` is saved into `r29`, whether r29 is overwritten on either path, and whether those functions belong to the game-selected manager instance; do not infer caller identity just from a numeric `+0x334` match.

The separate S001 WASD workflow may fail on upstream/stacked branch history; the targeted S002 suite is the relevant focused CI. Keep publication and model eligibility false.
