# P0-CLI-CLEAN-V1: maintained research CLI clean-launch guard

STATUS: DRAFT, OFFLINE REVIEW ONLY. The operator uses scripts/research_cli.py, not the retired Lab GUI. Canonical interface owner S000 and Dolphin owner S001 must review before merge. No Dolphin, ROM, controller or RAM was accessed by this change.

## Concrete P0 bug

The main-branch research_cli.py V1 live subprocess previously passed only the isolated V1 bridge to run_golf_experiment.py. Without explicit Dolphin executable and User paths, the delegated launch_golf.py could fall back to the previously faulting old tools/FelkDolphin installation, invalidating the no-watcher contact baseline. The separate S001 draft PR #194 changes only Lab core planning and does not address this maintained CLI path. No overlap with its files.

The new v1_clean_boot_args helper requires the CLEAN Dolphin.exe and isolated User directory, local launch.local.json and savestates.local.json. Absence causes a no-input, no-fallback error. Existing canonical single fresh boot and human opt-in are preserved; child A-prime requests are explicitly zero, no swing waveform/phase is modified, no extra launcher or UI is created. File presence does not establish that the named savestate actually exists under the clean User or that contact works.

## Windows PowerShell offline-only worktree preflight

    $ErrorActionPreference = 'Stop'
    $repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
    $work = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-P0-CLI-Clean'
    $branch = 'agent/review/p0-cli-clean-v1-baseline-20261027'
    Set-Location -LiteralPath $repo
    git -C $repo fetch origin $branch
    if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
    if (-not (Test-Path -LiteralPath $work)) {
        git -C $repo worktree add --detach $work FETCH_HEAD
        if ($LASTEXITCODE -ne 0) { throw 'Worktree failed' }
    }
    if ((git -C $work rev-parse HEAD).Trim() -ne
        (git -C $repo rev-parse FETCH_HEAD).Trim()) {
        throw 'Existing worktree differs; preserve it'
    }
    Set-Location -LiteralPath $work
    py -m unittest discover -s tests -p test_research_cli_clean_dolphin.py -v
    if ($LASTEXITCODE -ne 0) { throw 'P0 safety test failed' }
    py -m unittest discover -s tests -p test_research_cli.py -v
    if ($LASTEXITCODE -ne 0) { throw 'Existing CLI regression failed' }
    Set-Location -LiteralPath $repo

Tests use only fake file fixtures and mocked live subprocess; no Dolphin or game action. Run full suite and require S001/S000 signoff before integration. Do not run v1 --live in this draft worktree.

## Handoff

S001 owns actual V1 baseline contact and clean executable/User/savestate validation; S000 owns CLI/public result compatibility. The same-shot selected player and ball study #166/#189/#191/#193 remains separately draft and downstream. No physical contact, power, velocity, XYZ, distance or training readiness has been demonstrated by this work.
