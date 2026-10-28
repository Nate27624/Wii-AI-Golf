# S000 P0 PowerShell documentation report

**DRAFT / stacked on S000 registry PR #205.** Claim: issue #121. Current script is offline metadata-only and does not run Dolphin, use a bridge, inspect private JSON or native RAM, upload private data, or validate physical P0 quantities.

## Reused source of truth

The input is research/memory-variables/registry.json from #205, with 17 seeded candidates and 0 training-approved fields. The more detailed behavior ledger is PR #154. This is a status projection, not a competing registry. The script checks IDs, RSPE01 Rev1 and big-endian provenance, candidate versus verified status, phase evidence, and training input/label gates. It emits sanitized columns without native addresses or locator expressions. It records one review action per P0 field from the current status and phase provenance, without falsely claiming that any listed control was performed.

## Outputs

- Private, append-only CSV variable table with stable logical IDs, priority, status, owner, locator class, phase class and counts of source references, capture groups, listed controls, training flags.
- Private Markdown P0 review matrix and next validation gates.
- Private JSON summary with source registry hash, counts, explicit FALSE game/physics proof and FALSE automatic publication.

Output path: ignored sibling Wii-AI-Golf-Data/p0-documentation/unique-report-id/. No overwrite, no raw RAM, private capture data, or pointer expressions printed or written by this tool.

## Operator one-block Windows PowerShell invocation (offline)

~~~powershell
& {
    $ErrorActionPreference = 'Stop'
    $repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
    Set-Location -LiteralPath $repo
    $root = Split-Path -Parent $repo
    $branch = 'agent/coordinator/p0-powershell-doc-report-20261028'
    $work = Join-Path $root 'Wii-AI-Golf-P0-Docs-Review'
    $data = Join-Path $root 'Wii-AI-Golf-Data'
    git -C $repo fetch origin "refs/heads/$($branch):refs/remotes/origin/$($branch)"
    if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
    $expected = (git -C $repo rev-parse "origin/$branch").Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve docs branch' }
    if (-not (Test-Path -LiteralPath $work)) {
        git -C $repo worktree add --detach $work "origin/$branch"
        if ($LASTEXITCODE -ne 0) { throw 'Worktree failed' }
    } else {
        $dirty = @(git -C $work status --porcelain)
        if ($LASTEXITCODE -ne 0 -or $dirty.Count -gt 0) { throw 'Worktree is dirty' }
        $have = (git -C $work rev-parse HEAD).Trim()
        if ($LASTEXITCODE -ne 0 -or $have -ne $expected) {
            throw 'Existing worktree differs; preserve it'
        }
    }
    py -I "$work\scripts\validate_memory_registry.py" --registry "$work\research\memory-variables\registry.json"
    if ($LASTEXITCODE -ne 0) { throw 'Registry invalid' }
    & "$work\tests\Test-P0MemoryDocs.ps1"
    if (-not $?) { throw 'Synthetic tests failed' }
    & "$work\scripts\Export-P0MemoryDocs.ps1" -DataRoot $data
    if (-not $?) { throw 'P0 report failed' }
}
~~~

Expected sanitized stdout: VALID registry, SYNTHETIC_P0_DOC_TESTS=PASS, P0_REPORT_ID, REGISTRY_VARIABLES, P0_VARIABLES, TRAINING_APPROVED, MODE=OFFLINE_DOCUMENTATION_ONLY, GITHUB_OBSERVATION=NOT_UPLOADED. Do not paste private files or raw capture bytes.

## Scientific caution and publication

The four effect-handle candidate pairs from the successful V1 shot are render/effect-linked (PRs #197 and #208), not demonstrated ball physics; human 100 ft off-green may be censored. Another JSON-associated ball may have been falling but its file/frame identity and physical velocity are unverified. Current documented fields are NOT authorized as a trained state/action/outcome dataset.

The code + test evidence are available in this GitHub PR, but **the actual operator-generated documentation output is kept local** until S000/S002 approve a typed allowlisted summary through the existing research_cli.py publisher. This standalone script deliberately does not create a competing Git uploader or falsely claim to publish. Significant findings are recorded through the existing owning issue/PR and reviewed ledger process.

## Review prerequisites

S000 owns registry and operator-facing code; S002 owns evidence semantics; S001 launch unchanged. Targeted Windows/Ubuntu synthetic tests and complete Windows unit suite, dependency/merge review and full PR merge checklist required. Draft must not be self-merged without those gates.
