# P0 — directly measure selected-player rotation; world axis still unverified

**Operator request (2026-11-10):** Four-club mapping and integration are
working; replace an inspector's relative "delta from initial aim" that can
desynchronize with exact player global position/angle from game RAM.

**Scope:** This is a read-only *candidate validator*, not a change to the
working club ID or inspector. Source/angle identity and world-axis calibration
are separate proof obligations. No A, no swing, no savestate, no controller
automation, no writes and no game launches. `training_approved=false`.

## Previous research preserved; no repeat broad scan

Operator's original SHA-gated B0/B1/B2/B3 US Rev1 paired game memory (S002
PRs #178 and #181) identified a single selected player record with:
- +0x03C angle-like f32, unchanged in both idle controls and changed by
  approximately -25.127 degrees during visual WASD aim;
- +0x040..+0x04C rotation-like f32 values consistent within ~0.00007
  with `[sin(a), cos(a); -cos(a), sin(a)]`, a two-dimensional proper
  rotation (determinant approximately one);
- +0x0A0..+0x0AC and +0x0B0..+0x0BC quaternion-like groups with near-unit norm,
  but not source-proven as actual world orientation;
- +0x094..+0x09C position-like triples, source-untyped. **Do not** present
  them as player XYZ or actual model location.

Original PPC source trace in #178:
`RPGolPlayerManager.cpp` prologue `0x802A28DC`,
`0x802A28F0 mr r29,r3`; manager +0x334 selected-record pointer into
`RPGolPlayer.cpp::fn_8029ED2C` at two direct callsites
`0x802A2968`, `0x802A2B0C`. Callee preserves r3 in r29,
updates +0x3C and calls `RPGolMath.cpp::fn_802A3894` with
record+0x40; writes the paired transform tail at +0x48/+0x4C.
Static source pointer trace is strong but neither native r13 nor physical
world yaw/sign, transformed forward axis or actual shot direction were
independently established.

Inspector main `gui.py` currently uses source tee→pin reference
plus `Δselected_record+0x3C` measured relative to a manually asserted
baseline. That graphical model can drift or be wrong when baseline
assumptions fail. The live game fields are more direct; **a non-drifting
memory scalar does not by itself imply an absolute world-bearing calibration.**

## Proposed direct test

`scripts/p0_live_player_rotation_candidate_private.py` reuses the
canonical `p0_live_no_contact_compare.take_snapshot` for source
revision/scene/mode/hole/selected player and ball/tee/pin pointers.
It then reads a contiguous 5-word block +0x3C..+0x4C,
verifies scalar exact equality before/after, and rechecks the original
source pointer epoch. It also reads the two 4-word quaternion-like groups
without assigning semantic meaning. Stops if selected player, hole,
ball position candidate or source pointer changes.

The script derives two independent *numerical representations of the
same source record* on **each sample**, without integrating any controller
input:
- `candidate_record_angle_degrees = degrees(record+0x3C)` wrapped;
- `candidate_rotation_matrix_angle_degrees =
   degrees(atan2(record+0x48, record+0x40))` wrapped;
- Expected relation: `matrix_angle ≈ record_angle − 90°` (a matrix
  algebra fact; does NOT prove +X or +Z is the golfer's physical forward
  vector).
- `tee_pin_xz_bearing_candidate_degrees =
  atan2(pin_z-tee_z, pin_x-tee_x)`, independently read from source
  tee/pin candidate vectors. The coordinate basis and exact player
  facing relation remain unverified.

It requires manual B0/IDLE/LEFT/RIGHT/RETURN phases with all aiming
movement *stopped* before each bounded read. Verifies idle, signed
opposite controls, within-sample sin/cos consistency, and maintains
**`actual_player_world_yaw_verified=false`** regardless of apparent fit.

## Operator — full copy-paste PowerShell, no Dolphin restart

Use only while **the existing Felk bridge at 55355** is ready-to-hit
Rev1 Hitting the Green with A released and no swing. It does not
send D-pad/WASD inputs, reload savestates or launch Dolphin.

```powershell
$ErrorActionPreference = 'Stop'
$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
$parent = Split-Path $repo -Parent
$work = Join-Path $parent 'Wii-AI-Golf-P0Rotation-20261110'
$data = Join-Path $parent 'Wii-AI-Golf-Data\captures'
$branch = 'agent/s002-live-player-rotation-candidate-20261110'

if (-not (Test-Path -LiteralPath $repo)) { throw 'Original repository missing' }
if (-not (Test-Path -LiteralPath $data)) { throw 'Private captures directory missing' }
if (Test-Path -LiteralPath $work) { throw 'Isolated worktree exists: stop; do not overwrite' }
& git -C $repo fetch --no-tags origin "refs/heads/$branch"
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
& git -C $repo worktree add --detach $work FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'Worktree setup failed' }

$script = Join-Path $work 'scripts\p0_live_player_rotation_candidate_private.py'
& py -3 -I $script --selftest
if ($LASTEXITCODE -ne 0) { throw 'Offline selftest failed' }
& py -3 -I $script --private-root $data --port 55355
Write-Host ("Rotation probe exit code: $LASTEXITCODE")
```

In Dolphin, set a known baseline at B0 (prefer the visible pin direction);
remain idle for IDLE; aim visibly *left of B0* then release motion;
aim visibly *right of B0* then release; manually return near initial.
Do not try to hit exactly the same angle: RETURN is measured as a residual,
not silently forced equal to B0. No A or swing.

Share **only the final sanitized JSON** (and per-stage scalar/matrix/bearing
numbers if helpful). Private `*-PRIVATE` source data never leave local disk.
On source/identity/matrix failure report the exact abstention, not invented
yaw or a generic delta correction.

## World-frame calibration not completed by one hole

After the first live result passes, compare an *operator-confirmed*
"pointed at flag" state on at least two holes/different tee→pin bearings
without changing program semantics. For each, compare the absolute matrix
axis angle and the source tee→pin XZ bearing, testing both sign and fixed
axis offsets; the same offset with correct left/right signs across holes
is necessary evidence for world orientation, not sufficient for exact
rendered avatar forward/shot heading. Independent boot repeat and
source model-to-world matrix multiplication/shot aim consumer linkage
remain needed. Do not train or label actual world yaw prematurely.

Only after verifying the axis, side and cross-session invariance should
S002 owner replace the GUI flag-reference + Δ0x3C heuristic, preserving
the existing club integration and showing UNKNOWN if source gates fail.
