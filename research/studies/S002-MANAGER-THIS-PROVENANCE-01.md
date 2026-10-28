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

## Actual operator result — source manager-this register chain found

The operator ran the prior offline `audit_golf_manager_r29_private.py` on B0; its three synthetic tests passed and its real output listed 17 source-unit r29-def candidates. **Both** selected-player call chains report the closest predecessor **`0x802A28F0 mr r29,r3`**. The new observed method prologue at `0x802A28DC` is `stwu r1,-0x20(r1)`, followed by `0x802A28F0 mr r29,r3`, `0x802A28F4 lwz r3,+0x334(r3)`, and `0x802A28F8 bl 0x802A0CA8`. The earlier two callsites `0x802A293C→2968` and `0x802A2B00→2B0C` then reload the selected pointer using `+0x334(r29)` and call `0x8029ED2C`, which retains its input r3 in r29 and updates the +0x3C angle / +0x40..+0x4C trig-like fields. This resolves the **static manager-this register link** substantially beyond the former register-offset coincidence.

Earlier r29 candidates at `0x802A2448`, `0x802A24A4`, and `0x802A25AC` occur in different, preceding source routines; they must **not** be treated as overwrites of the later function's r29. Source-PC proximity alone across function boundaries is not causal dataflow.

I upgraded the **existing repository** analyzer `scripts/audit_golf_manager_r29_private.py` to require the actual method-prologue and `r29←incoming r3` / first selected-pointer read PPC instruction words; it fails closed if any *recognized* intervening r29 write is found between the verified assignment and the later call, and continues to require the two exact selected-pointer-to-angle-updater callsite signatures. Its new reports carry `manager_this_register_proven=true` and `manager_r29_saved_from_entry_r3_source_verified=true` only at the source level, alongside `r29_reassignment_detector_exhaustive=false` and `manager_r29_runtime_identity_independently_verified=false`. The latter flags preserve the missing full CFG/ABI and independent runtime execution evidence. The actual heading and golf physics remain unverified; training and publication stay false.

The source-chain analyzer's synthetic tests now include corrupt prologue, corrupt r29 assignment, corrupt source-selected load and an injected r29 overwrite after the method entry. **These are tests of evidence gates, not a live movement calibration.**

**Operator next step:** rerun the identical standalone PowerShell block above after fetching latest branch. New output should include the source-level verification flags and any actual function-provenance links; share the compact `manager_this_register_proven` and `caller_chains` result. All existing B0–B3 checkpoint files remain unchanged.

## Actual operator rerun of exact source-chain verifier

On the preserved RSPE01 Rev1 B0 snapshot, the operator fetched commit `ccf5f0634`, ran `test_golf_manager_r29_private.py` (**3 tests, OK**), and ran `audit_golf_manager_r29_private.py --private-root` successfully. The tool's actual results, not CI fixtures:

| Exact output field | Observed |
| --- | --- |
| `checked_direct_calls` | `2` |
| `manager_this_register_proven` | `true` |
| `manager_r29_saved_from_entry_r3_source_verified` | `true` |
| `source_selected_pointer_read_from_manager_r29_verified` | `true` |
| `no_recognized_r29_reassignment_before_both_calls` | `true` |
| `r29_reassignment_detector_exhaustive` | `false` |
| `manager_r29_runtime_identity_independently_verified` | `false` |
| `dynamic_execution_proven` | `false` |
| `absolute_shot_heading_verified` | `false` |
| `ball_motion_verified` | `false` |
| `training_allowed` | `false` |

In the operator source context, three r29 candidates at `0x802A2448`, `0x802A24A4`, and `0x802A25AC` belong to earlier independent source blocks. The relevant method begins at `0x802A28DC`; `0x802A28F0` preserves the method argument `r3` in `r29`; both callsites subsequently load `+0x334(r29)` into `r3` before calling the angle/rotation updater. This is now **operator-confirmed static pointer provenance**, not hypothetical inferred code.

**Research handoff priority:** stop repeating B0–B3 no-shot aim verification. #186's cross-agent guidance explicitly prioritizes S001-controlled A-hold/backswing/forward swing/contact/no-contact temporal sampling under reviewer and operator gates. #166's proposed per-frame selected-ball watch, #180/#184 private PRE/POST/RESULT staging, and #154's nontraining evidence ledger should coordinate that first genuine swing cohort. #181's dense MEM2 aim-associated blocks and `golf_main+0x1DC` transient B1→B2→B3 reversion remain **untyped**; do not conflate them with swing or ball motion.

Do not commit raw memory banks, runtime heap pointers, user-specific paths, or full private reports. No field is promoted to verified ball velocity, golf physics, GUI aim heading, swing power, or training eligibility.
