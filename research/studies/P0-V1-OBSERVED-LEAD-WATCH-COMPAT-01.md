# P0 V1 selected-player watcher compatibility — OFFLINE source review

Status: DRAFT. NOT APPROVED FOR LIVE DOLPHIN. Stacked on S001/S002 #189 and upstream #166. This proposal makes no edits to their existing source. No live shot, bridge-port access, controller RPC or RAM access.

## Why this is necessary

The operator confirmed real visible ball contact in clean Felk Dolphin with the historical V1 bridge, 45 OBSERVED Dolphin frames holding A, zero extra A-prime RPC requests, and the frozen 89-sample forward waveform. S001 #189 currently requires a V2-only watched bridge and issues 45 BUTTON RPC requests before the trace: request count is NOT elapsed/observed Dolphin frames. The existing #189 recorder therefore does NOT implement the contact-positive controller program.

## What is implemented (offline only)

- New src/wii_ai_golf/integration/v1_ball_watch_compat.py reuses the 51-word read-only watcher from #189 but surgically injects into a separate copy of the historical V1 bridge. Exact original source SHA256 required: fe04cb0ba312c559d5cb7edb8d0ac2185aca72046839a903160929ee7c58ca19. Reject V2 neutral suppression, autoload startup, existing watcher or unknown tick/handler anchors.
- New scripts/prepare_v1_selected_watch_bridge_private.py reads original local tools/mcp_bridge_swing_legacy_eval.py and creates separate tools/mcp_bridge_swing_legacy_watch_eval.py exclusively. Never overwrite, no download, no GUI, no game execution.
- V1 trace.submit_swing and _wii_ai_tick original source remain preserved by reversible insertions; add read-only provenance endpoint. Provenance does not claim A lead happened, contact, score or training.
- Synthetic tests/test_s001_v1_selected_watch_compat.py covers compilation, source preservation, wrong hashes, V2/autoload, existing watch, duplicates and 51-word selected record access.
- This code DOES NOT adapt or enable a live recorder. S001 must implement correct observed-frame A hold and approve actual runtime native parity first.

## PowerShell-only offline source check

Run these lines from PowerShell, not a GUI:

    $ErrorActionPreference = 'Stop'
    $root = 'D:\Projects\Wii Golf AI'
    $repo = Join-Path $root 'Wii-AI-Golf'
    $work = Join-Path $root 'Wii-AI-Golf-P0-V1-Watch-Review'
    $branch = 'agent/review/s001-v1-selected-record-watch-compat-20261028'
    if (Test-Path $work) { throw 'Review worktree already exists' }
    git -C $repo fetch origin "refs/heads/$branch:refs/remotes/origin/$branch"
    if ($LASTEXITCODE -ne 0) { throw 'GitHub fetch failed' }
    git -C $repo worktree add --detach $work "origin/$branch"
    if ($LASTEXITCODE -ne 0) { throw 'Worktree failed' }
    $env:PYTHONPATH = Join-Path $work 'src'
    py -m unittest discover -s (Join-Path $work 'tests') -p 'test_s001_v1_selected_watch_compat.py' -v
    if ($LASTEXITCODE -ne 0) { throw 'Offline V1 tests failed' }
    $src = Join-Path $root 'tools\mcp_bridge_swing_legacy_eval.py'
    $dst = Join-Path $root 'tools\mcp_bridge_swing_legacy_watch_eval.py'
    if (Test-Path $dst) { throw 'Refuse overwrite' }
    py -I (Join-Path $work 'scripts\prepare_v1_selected_watch_bridge_private.py') --source $src --output $dst
    if ($LASTEXITCODE -ne 0) { throw 'Bridge prep refused; no game changed' }

Do not launch the resulting watched source in Dolphin yet. Generated output is NOT evidence of a safe contact/hit.

## S001/S002/S000 review and next experiments

1. Correct 45 *observed-frame* A lead for any future V1 recorded shot using existing wii_ai_golf.shared.controller_timing.hold_a_for_observed_frames; do not substitute prime_a_button requests=45. Keep unchanged 89-sample waveform and source bridge semantics.
2. Verify source read overhead <=5000us in CLEAN real Dolphin, unchanged V1 controller dispatch and actual repeatable contact versus unwatched baseline. Synthetic equality is not game-side proof.
3. Review #191 neutral/A-only confounds and #193 independent trace-link; V1 trace metadata may lack V2-only kind/protocol2 attributes.
4. S002 source target candidates: selected player +0x024 untyped lifecycle, +0x088 ball-like object, Base +0x030 translation and +0x0CC/+0x0F0/+0x0FC cached vectors. Existing eight persistent successful-shot words are overlapping minimap visual effects, NOT verified dynamics.
5. Require S000 private sample privacy review, full Windows regressions, explicit one-shot operator consent, and no training/publication of memory words before further live action.

No ball-world XYZ, velocity, contact flag, swing power or score verified.
