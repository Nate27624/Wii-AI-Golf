# S002-SWING-VARIABLE-TRIAGE-01 — next source-owned, offline-first memory discovery

Status: **research handoff / operational triage only**; no executable changes, no new Dolphin session, no shot or model training. Created to connect the user's 2026-10-27 swing-memory-variable request to the *existing* owners instead of introducing a fourth whole-RAM scanner. Do not merge over active S002 branches without owner review.

## What the actual evidence supports

- S002 #181: preserved same-operator B0 idle, B1 later idle, B2 visibly changed WASD aim, B3 released-and-idle native 24MiB MEM1 + 64MiB MEM2 pairs; all adjacent whole banks differ, so these are not byte-identical captures.
- One selected 0xCC-byte player record has **17** offsets which change with B1→B2 aim and persist B2→B3: `+0x03C,+0x040,+0x044,+0x048,+0x04C,+0x094..+0x0C0` (last range aligned 4B, 12 fields). The separate `+0x090` field is an idle confound, not aim-exclusive. Inactive records and selected ball/start/field objects are stable in the no-shot study.
- The angle-like `+0x03C` and matrix-like `+0x040..+0x04C` have a strong sin/cos relationship (residual ~7e-5) and two unit-length four-float groups `+0x0A0..+0x0AC`, `+0x0B0..+0x0BC`. **Do not call these verified club pose, quaternion C++ class, swing power or actual shot heading.**
- S002 #178 source direct callers at `0x802A293C→0x802A2968` and `0x802A2B00→0x802A2B0C` load selected pointer from PlayerManager-relative `+0x334`, invoke `0x8029ED2C`, and helper `0x802A3894` constructs rotation-like data. Remaining source questions: manager receiver `r29` provenance and independent left/right heading direction validation.
- S002 #183 finds `ball+0xCC,+0xF0,+0xFC` are **initialization/conditional cache** triplets, not three independent moving positions; source FieldManager target-or-pin getter depends on target count. S001 #166's first watched V2 pilot had **no visible ball motion**, only stationary candidate samples and an incomplete initial drain; later code tightens completeness. **No verified contact-time ball XYZ, impact, velocity or internal strength**.
- S000 #154 evidence dictionary owns semantic promotion/privacy. S002 #180 owns future human-approved visibly displaced PRE/POST paired RAM study. S001 #166 owns within-bridge watcher. S003 #125 cannot train from these static controls or reported ~75% gauges.

## First operator task: three EXISTING-data offline checks (no Dolphin)

Use a **new detached worktree per PR**, not a reset or switch inside another agent's working directory. The original captures remain in the sibling ignored Data folder. The two relevant branches are independently stacked and **are not** both merged on main. This block checks worktree SHAs; it does not erase an existing worktree, re-export RAM, upload data or send game input.

```powershell
$ErrorActionPreference = 'Stop'
$root = 'D:\Projects\Wii Golf AI'
$repo = Join-Path $root 'Wii-AI-Golf'
$private = Join-Path $root 'Wii-AI-Golf-Data\ball-study-20261027-212633'
if (-not (Test-Path -LiteralPath (Join-Path $private 'checkpoint-manifest-PRIVATE.json'))) {
    $private = (Read-Host 'Exact existing B0-B3 private checkpoint directory').Trim('"')
}
if (-not (Test-Path -LiteralPath (Join-Path $private 'B3-MEM2.bin'))) {
    throw 'Existing complete B0-B3 snapshots required; do not auto-recapture'
}

function Use-ResearchTree([string]$branch, [string]$target) {
    git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
    if ($LASTEXITCODE -ne 0) { throw 'Branch fetch failed' }
    if (-not (Test-Path -LiteralPath $target)) {
        git -C $repo worktree add --detach $target "origin/$branch"
        if ($LASTEXITCODE -ne 0) { throw 'New research worktree failed' }
    } else {
        git -C $target rev-parse --show-toplevel | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Existing target is not a Git worktree' }
        $dirty = @(git -C $target status --porcelain)
        if ($LASTEXITCODE -ne 0 -or $dirty.Count -ne 0) {
            throw 'Existing research worktree has modifications; preserve it'
        }
        $actual = (git -C $target rev-parse HEAD).Trim()
        $expected = (git -C $repo rev-parse "origin/$branch").Trim()
        if ($actual -ne $expected) {
            throw 'Existing worktree differs from fetched revision; stop, do not overwrite'
        }
    }
}

# Stage 1: independently recheck the 17 aim/pose-like words mathematically.
$atlas = Join-Path $root 'Wii-AI-Golf-Fullbank-Atlas'
Use-ResearchTree 'agent/research/fullbank-fourphase-source-overlay-20261027' $atlas
py -m unittest discover -s "$atlas\tests" -p 'test_golf_aim_pose_math_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Aim-math synthetic tests failed' }
py -I "$atlas\scripts\audit_golf_aim_pose_math_private.py" --private-root $private --aim-visibly-moved --operator-same-session
if ($LASTEXITCODE -ne 0) { throw 'Aim-math real private check failed' }

# Stage 2: source-selected record is passed into the rotation updater.
$source = Join-Path $root 'Wii-AI-Golf-Expanded-Memory'
Use-ResearchTree 'agent/research/golf-source-object-windows-private-20261027' $source
py -m unittest discover -s "$source\tests" -p 'test_golf_selected_aim_callers_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Source-caller synthetic tests failed' }
py -I "$source\scripts\audit_golf_selected_aim_callers_private.py" --private-root $private
if ($LASTEXITCODE -ne 0) { throw 'Source-caller real private check failed' }

# Stage 3: use existing detailed object-window report, if already generated.
$report = Join-Path $private 'golf-object-windows-PRIVATE.json'
if (Test-Path -LiteralPath $report) {
    py -m unittest discover -s "$source\tests" -p 'test_inspect_golf_aim_rotation_private.py' -v
    if ($LASTEXITCODE -ne 0) { throw 'Rotation inspection tests failed' }
    py -I "$source\scripts\inspect_golf_aim_rotation_private.py" --report $report
    if ($LASTEXITCODE -ne 0) { throw 'Rotation inspection failed' }
} else {
    Write-Host 'No prior object-window report; skip stage 3 rather than invent data.'
}
```

Operator may paste **only redacted/offline report summaries** into the research chat. Game numeric angles can be discussed in private chat, but do not commit the source report, screenshots, native MEM1/MEM2, emulator paths, heap addresses or exact ROM bytes to public GitHub. The command above intentionally **does not** execute the already-completed 88MiB atlas again: it verifies two much narrower complementary hypotheses.

## Next novel experiment (proposal only, not a live command)

After S001 confirms clean-Dolphin readiness and S002/S000 review, collect a **no-shot, bidirectional aim dose-response** from the same stable selected player/hole: center idle twice → modest left aim → center recovery → comparable right aim → center recovery, with a timed idle at each state. Use pause-and-export MEM1 and MEM2 **under the same GUI pause** for each state; name/store each privately with source-verified hashes and explicit human WASD-direction labels. Repeat on a second clean boot. Record *both* proposed angle and full 17-word change signature, plus source-selected record identity, camera/HUD controls, and inactive player records. Check sign reversal, monotonicity and center-return hysteresis before typing `+0x03C` as a gameplay heading signal. Do **not** treat each sample from one boot as an independent experiment. Do not reuse B0–B3-only auditors on an incompatible phase manifest without an S002-reviewed adapter.

To identify *swing* rather than aim, require separate negative controls (idle, camera/pointer-only, A-held-no-motion, club animation without contact) and a reproducible contact baseline **before** using #166 frame sampler. Calibrate observer interference (watched vs unwatched; fixed V1 waveform) and require full terminal watch samples, source ownership stable through flight, persistent START control, visible ball displacement, and measured frame provenance. A changed positional cache alone is not verified world XYZ.

For eventual **distance to hole**: independently source-validate the pin translation and the moving ball translation **in the same live phase**, check axis/units and on-screen outcomes, then compute Euclidean distance only after that validation; Hitting-the-Green `100.0 ft` off-green penalty is censored, **not true physical carry**.

## Owner handoff and failure gates

- **S002 #178 / #181:** validate direct-caller `r29` chain and all +0x094..+0x0C0 writer/reader receiver identities; accept/decline left-right no-shot cohort protocol. No additional generic fullbank scanner.
- **S002 #183 / #180:** use conditional ball caches as *candidates* and eventually a GUI-paused PRE/visibly displaced POST paired experiment. No false claim of independent trajectories from cached copies.
- **S001 #166 / #171:** restore a consistent observed-contact V1/V2 baseline and prove bridge-frame watcher noninterference before one authorized live ball-watch attempt; fresh boot via canonical shared launcher, never a bare assumed `--attach-running` recipe.
- **S000 #154:** only approve allowlisted aggregate evidence; keep `training_allowed=false` until real physics meaning independently validated.
- **S003 #125:** define targets only once actual gameplay power, ball motion and result units are independently measured; do not use controller ACK, an angle-like memory float or penalty score as ground truth.

No code execution, Windows tests, new game attempt, raw-data read or successful memory inference is claimed **by this documentation PR**. It is a low-collision operational guide and should receive S002 and S000 review before being advertised as canonical.
