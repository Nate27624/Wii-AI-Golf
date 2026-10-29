# P0 SHOT-TRANSIENT-MEMORY-01 — recover POST-only candidates from the ORIGINAL V1 hit

**Status:** DRAFT S002/S000 review, 2026-10-28. This is an **offline, read-only** analysis of the already-recorded, **human-observed YES** V1 strike (45 **observed-frame** A lead, original 89-sample forward trace). It is not a request to launch Dolphin or reproduce the swing. No physics, ball XYZ, swing power, velocity, or training eligibility has been established.

## Concrete gap in existing research

Existing S002 `rank_outcome_candidates()` on `main` and audited #197/#199 require **stable PRE != stable SETTLED** to rank a persistent word. The original hit has eight such changed words, **all duplicated within overlapping minimap/visual-effect windows**; source register provenance in #178 does not make them ball physics. These tools intentionally do **not** list a field that **temporarily changes in POST and returns to PRE by SETTLED**. That transient state is exactly where a shot-phase flag, effect-active bit, timer, state machine word or short-lived gameplay marker **might** reside. This study tests that narrower hypothesis; candidates may all be visual artifacts, pointers or timing confounds.

## Source and controls

- Input: the original ignored `Wii-AI-Golf-Data/captures/outcome-20261028T033948Z-5cd47f00-candidates.json` and matching `-RAW-PRIVATE.jsonl`. Both stay local. The Python analyzer refuses any mismatched source stems, symlinks, path outside private captures, oversize files, wrong RSPE01 Rev1 mode4, wrong profile (V1 45 observed lead / 89-sample trace), unknown human contact, short phases, inconsistent prior persistent ranking, changing window source addresses, or missing static negative control regions.
- Sampling: 3 PRE + 2 POST + 3 SETTLED from the original session. Samples are **multi-frame reads**, not atomic snapshots or proved scene/ball timestamps. No one is allowed to relabel a specific B0/B1/B2/B3 as in-flight or settled based on the operator's separate recollection.
- Test: group **unique absolute in-RAM word addresses internally** across overlapping windows (but do **not** print them); require stable identical PRE, stable SETTLED exactly equal PRE, at least one changed POST. Report whether BOTH POST changed or only one. Exclude unstable PRE or SETTLED, malformed pointer/word bounds, and **non-atomic contradictory alias reads** instead of inventing physical meanings.
- Provenance: only source-window-relative offsets are visible. Rank `golf_config`, `golf_field`, `sports_sequence` **before** `minimap_*` visual effects, and mark pointer-shaped raw words and finite/float-compatible patterns as confounds/bit patterns, not typed fields. The historical eight PERSISTENT changes are cross-checked against the stored rank count and never misreported as new transient physics.
- Output: one exclusive-created local `*-POST-TRANSIENTS-SANITIZED.json` under ignored private captures. Contains bounded candidate IDs, offsets, source hints, phase counts and caveats. **Never prints private absolute addresses, raw bytes, raw numeric word values, full JSONL, ROM, savestates, or user paths.** Candidate listing capped at 40; `candidate_list_truncated` flags if more remain.
- IMPORTANT publishing boundary: `research_cli.py` currently auto-publishes only trusted `test` and `v1` sanitized schemas. This unmerged special analyzer has **no approved S000 publisher adapter** and therefore **does not auto-upload to GitHub**. Human/user may share its redacted PowerShell summary, after which S002 should post findings to the owning issue and link an owner-reviewed registry update. Do not silently upload PRIVATE JSON or invent a new separate publisher.

## One copy-paste PowerShell operation (offline; does NOT start Dolphin)

Only execute after reviewing the PR and exact head SHA. This block fetches the **specific PR branch into an isolated detached worktree** without switching or resetting the operator's main checkout. If the worktree already exists at a different SHA, stop rather than overwriting another agent's changes. The script runs synthetic tests before inspecting the original private pair.

```powershell
$ErrorActionPreference = 'Stop'
$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
$work = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-P0-Shot-Transient-Review'
$branch = 'agent/research/p0-shot-transients-existing-capture-20261028'
$expected = '<EXACT_REVIEWED_HEAD_SHA>'
Set-Location -LiteralPath $repo
git -C $repo fetch origin $branch
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
$received = (git -C $repo rev-parse FETCH_HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $received -ne $expected) { throw 'Unreviewed changed branch head; STOP' }
if (-not (Test-Path -LiteralPath $work)) {
    git -C $repo worktree add --detach $work $expected
    if ($LASTEXITCODE -ne 0) { throw 'Detached review worktree failed' }
}
$present = (git -C $work rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $present -ne $expected) { throw 'Existing worktree is not the reviewed head; preserve it and STOP' }
$changes = @(git -C $work status --porcelain)
if ($LASTEXITCODE -ne 0 -or $changes.Count -ne 0) { throw 'Review worktree dirty; preserve existing changes and STOP' }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $work 'scripts\Invoke-P0ShotTransientAudit.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Private audit failed' }
Set-Location -LiteralPath $repo
```

**Do not run the literal placeholder**; use exact reviewed PR HEAD after owner approval. This script is intentionally available for code review first; no user action is required now. At the end it shows only `TransientUniqueWords`, `PersistentCrosscheck`, unstable-control exclusions, `MaxNonAtomicFrameSpan`, and at most 12 redacted relative-offset rows. If missing data or a prior output file exists, it fails closed without overwrite.

## Test, handoff and next discrimination

Targeted GitHub CI runs synthetic Python classification/private-path tests and PowerShell syntax on Windows+Ubuntu without Dolphin. A passing test is only code validation, **not a real-hit analysis**. Full Windows repository suite and S002/S000 review remain separate merge gates.

After the real private run, report only the sanitized counts/offsets and mark source hypotheses as **new P0 candidates**, not true ball-state variables. The owner should take any surviving **non-effect** transient offset and trace its specific **PPC read/write receiver** on Rev1 with S002 source proofs and independent still/no-shot negative controls. A static config/timer flag or a minimap effect bit must not be promoted to ball motion or internal power. Cross-reference proposed stable field IDs with #205's still-draft registry and #154's 33-field evidence ledger; do not independently edit their concurrently owned files.
