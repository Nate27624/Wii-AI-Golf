# P0-SWING-TRACE-LINK-01 — offline controller-to-memory integrity audit

**DRAFT / no live authorization.** Supporting S001 #166, S002 #189, reviewer #191, S000 #154, cross-agent issue #121. This adds only independent new files; no bridge, producer, controller, CLI or publisher changes.

## P0 false-association risk

The existing S002 swing-field ranker validates trace IDs *among sampled memory rows* but does not compare them against the separately recorded completed controller trace. The new independent offline verifier requires a completed 89/89 sample swing status and matching active IDs, 51 bounded record words per sample, source owner/slot/hole/start stability, less-than-or-equal-to-5ms read overhead, chronological stage/index controls, and independent recomputation of stationary/motion flags. Missing neutral, back, forward, followthrough, release, idle, A-prime or posttrace phases preclude a positive correlation.

Human observed movement and candidate vector motion are independent inputs. A valid no-hit report remains negative evidence rather than a failure. Even a positive result means only *candidate association*, not confirmed guest frame, game-applied motion, impact, physical XYZ, power, distance, score, or training readiness. Raw numeric/pointer arrays remain local private data; stdout contains counts/booleans only.

## Offline Windows synthetic preflight (safe now)

~~~powershell
$ErrorActionPreference = 'Stop'
$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
$work = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-P0-Trace-Link'
$branch = 'agent/review/p0-same-shot-trace-integrity-20261027'
Set-Location -LiteralPath $repo
git -C $repo fetch origin $branch
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
if (-not (Test-Path -LiteralPath $work)) {
    git -C $repo worktree add --detach $work FETCH_HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Worktree failed' }
}
if ((git -C $work rev-parse HEAD).Trim() -ne
    (git -C $repo rev-parse FETCH_HEAD).Trim()) {
    throw 'Existing worktree differs from fetched branch; preserve'
}
Set-Location -LiteralPath $work
py -m unittest discover -s tests -p 'test_p0_swing_trace_link_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Focused tests failed' }
Set-Location -LiteralPath $repo
~~~

## Future offline capture inspection — NOT a request for a live shot

Only after S001 proves an uninstrumented moving-ball baseline, S001/S002/S000 review #166/#189/#191, full Windows regression and separately consented watched trial, investigate the resulting private watched report:

~~~powershell
Set-Location -LiteralPath 'D:\Projects\Wii Golf AI\Wii-AI-Golf-P0-Trace-Link'
$report = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\EXACT-CAPTURE-PRIVATE.json'
py scripts/audit_p0_swing_trace_link_private.py --private-report $report
~~~

EXACT-CAPTURE is a placeholder; B0-B3 native banks do not contain a watched shot report.

## Evidence and handoff

Local Python: **15 synthetic tests PASS**, compileall PASS. No game launched; no real user capture tested; full Windows repository suite **not run**. S001 reviews producer schema, real controller compatibility, source gates and 5ms overhead. S002 determines whether to integrate this before #191 field ranking. S000 reviews private output; S003 awaits independently verified non-censored same-shot outcome. Keep review PR draft; no training/publishing or user live command implied.
