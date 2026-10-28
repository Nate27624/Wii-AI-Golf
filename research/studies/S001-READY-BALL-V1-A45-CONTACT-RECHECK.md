# S001: Recheck missed contact from an ALREADY-ready first ball

**Motivation:** The previous operator received a successful initial A/A+B/A menu intro with an isolated no-autoload V1 bridge. The subsequent attached collector was incorrectly instructed to use `--a-lead-frames 0`; the operator visually reported the ball was **not** struck. Repository issue #94 documents one V1 trial that visibly contacted with a **45-observed-frame A-button-only lead and the original 89-sample forward trace** (human hit=yes, off-green 100 ft). That single trial is **not proof of reliable repeatability or causality**.

**Canonical existing process:** NEVER relaunch Dolphin, load `green-pre-start`, change savestate slots, or use `scripts/probe_swing.py` on the V1 bridge. The last script requires V2 capabilities and may reject the legacy bridge. `scripts/collect_outcome_transition.py` connects to the already running RPC and already implements the frame-measured 45 A lead via `hold_a_for_observed_frames`, without modifying the 89-sample waveform.

## Quick recovery for operator with current MAIN checkout

Only if the golfer is STILL at the stationary first ball AND the original clean Dolphin game is advancing (not paused), paste as ONE PowerShell block:

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
    Set-Location -LiteralPath $repo
    & py "$repo\scripts\collect_outcome_transition.py" --send-live-swing --a-prime-requests 0 --a-lead-frames 45 --observe-start-pose --ask-power
    if ($LASTEXITCODE -ne 0) { throw 'A45 recheck command failed; no contact inferred' }
    Write-Host 'Collection process returned; manually verify contact label in saved output'
}
```

At the prompt, confirm first-ball visible, report initial club pose, then **only press Enter to authorize ONE swing**. When ball stops (before game transition), press Enter; if transition already occurred use `t`, not a fabricated landed snapshot. Label actual contact `yes/no/unknown`. This collector preserves bounded **source RAM observation windows** locally, not full 24 MiB MRAM+64 MiB ExRAM.

## Proposed guarded reusable wrapper (this PR)

Once merged, use `py scripts/recheck_ready_ball_v1_a45.py` for a dry-run inspection, followed by `py scripts/recheck_ready_ball_v1_a45.py --send-live-swing` only when ready. This is **attached-only**; it verifies the local isolated no-autoload V1 source file, expects a running responsive bridge with advancing frames, rejects an explicitly reported V2 capability, and calls the current collector with `--a-prime-requests 0 --a-lead-frames 45` and operator labels. It does **not** prove active process loaded the same V1 source based on ping, nor prove contact. No new controller calls, waveform implementation, fresh Dolphin process, GUI, savestate write, memory dump, or training.

**Safety / evidence gates:** Missing contact or unclear labels are negatives/unknown; do not promote ball XYZ, swing power, 100ft penalty as physical distance, or resume training from a completed RPC trace. No full native PRE/POST pair exists unless independently paused/exported before/after the shot. Compare the next A45 trial to the zero-A-lead miss as an exploratory timing difference with confounds, not an isolated proof of effect.

**Validation:** New 7 synthetic offline tests and Python compile checks passed in author container. Real Windows/Dolphin bridge and actual repeatable hit remain untested; this branch is DRAFT pending S001/S002/S000 review.
