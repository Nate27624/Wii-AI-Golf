# P0 S001/S002 V1 observed-45-frame selected-record watcher — DRAFT

Research only; no live permission. Stacked on V1 source adapter #202, selected record #189, upstream S001 #166.

Real operator Windows result: 14/14 adapter tests plus 7/7 source diagnostics pass, historical V1 SHA verified, structural source preflight pass, separate watched V1 source generated SHA256 465b6b02a9ae3833c65233b0d7a26fca79c613330eedf4eeb1de2a5d89ff886b. Original V1 left intact; no Dolphin/RAM interaction occurred. This establishes source compatibility, not real watched contact, native 5ms callback performance, game physics or training.

## Additive change

- New scripts/record_selected_ball_swing_v1_private.py specifically rejects any bridge but the exact separately generated watched V1 source hash and dedicated V1 provenance RPC. Existing V2 recorder is NOT changed.
- Only explicit human SWING approval allows controller input, after trusted canonical first-ball boot. No GUI or extra savestate load.
- One watch: 24 **observed no-input idle Dolphin frames**; A-only exactly one A button RPC and **>=45 observed Dolphin frames** via existing wii_ai_golf.shared.controller_timing.hold_a_for_observed_frames; frozen 89-frame SwingTraceClient waveform; A-release/posttrace. 45 button RPC requests without measured frames are explicitly rejected.
- Existing 51-u32 source-selected player window + selected ball/start vectors sampled in bounded Felk loop for 280 bridge ticks / interval4 (70 max), 5ms fail closed. No new RAM interface. Separate watcher input stages idle_control, a_prime, trace, posttrace. Callback tick not proven same guest physics frame.
- PRIVATE output only under ignored Wii-AI-Golf-Data/captures, compatible with existing local selected-player change-ranker. Printed report strips raw pointer/RAM values. No automatic public upload, model training or verified physics.
- Small shared S001 post_boot.py allowlist extension allows canonical runner to inject trusted --attach-running for this new specific script. Requires S001 owner signoff.

## PowerShell-only offline preview (no Dolphin)

    $ErrorActionPreference = 'Stop'
    $root = 'D:\Projects\Wii Golf AI'
    $repo = Join-Path $root 'Wii-AI-Golf'
    $work = Join-Path $root 'Wii-AI-Golf-P0-V1-Timed-Watch-Review'
    $branch = 'agent/review/s001-v1-watched-observed-45frame-collector-20261028'
    if (Test-Path $work) { throw 'Review folder already exists' }
    git -C $repo fetch origin $branch
    if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
    git -C $repo worktree add --detach $work FETCH_HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Worktree failed' }
    $oldPythonPath = $env:PYTHONPATH
    try {
      $env:PYTHONPATH = Join-Path $work 'src'
      py -m unittest discover -s (Join-Path $work 'tests') -p test_s001_v1_observed_45_watched_collector.py -v
      if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
    }
    finally { $env:PYTHONPATH = $oldPythonPath }
    py -I (Join-Path $work 'scripts\record_selected_ball_swing_v1_private.py')
    if ($LASTEXITCODE -ne 0) { throw 'Dry run failed' }

Do not launch Dolphin with the prepared watched source until S001/S002/S000 approve.

## Mandatory review before live use

1. S001 native clean Felk watch <=5000us/callback; unchanged original V1 neutral swing calls, 89-sample dispatch and successful contact parity. Owner review #166/#202.
2. S001/S002 independent phase negative controls #191 and trace-link #193. Bridge frameadvance tick not proven guest CPU physics frame.
3. S000 privacy of pointer-containing 51-word record; raw RAM never GitHub/stdout; only approved allowlisted summaries may eventually publish automatically.
4. S002 source-writer ownership for selected record +0x024 untyped state enum, +0x088 child, ball Base+0x030 and +0x0CC/+0x0F0/+0x0FC caches. No repeated B0-B3 static aim scans.
5. Multiple independent real hit/miss controls before physical field promotion; 100.0 ft off-green may be censored and visual 75% power unverified. Training remains false.

This is an additive private script plus a one-name post-boot allowlist change. No original bridge/savestate/window or game profile modified. No self-merge until owner review and full Windows suite.
