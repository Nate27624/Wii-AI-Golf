# S002-SELECTED-BALL-START-LINK-01 — source-gated selected record ↔ ball/start triplets

**Status:** source-first, single still-state candidate validation, NO dynamic ball XYZ claim. Owner S002 #160, coordination #3; downstream S000 #154, S001 #2, S003 #125. This is an intentionally **stacked draft PR** on `agent/research/golf-crossbank-player-ball-roster-20261027` (PR #160), not a standalone reimplementation of roster source/type gates.

## Why this is a narrow high-value study

S002's real Rev1 code disassembly has verified:
- Source manager has **four inline 0xCC-byte records** starting at manager+0x04, and manager+0x334 stores the selected record pointer derived from index. In ONE source-gated still snapshot it selected index0.
- RPGolPlayer record+0x88 loads a ball-related object; source accesses its +0x4C translation pointer and writes three f32 components through it (PPC `stfs` at 0x802A03B8, C0, C8).
- Record+0x54/+0x58/+0x5C is a separate three-word candidate position, one of four records matches its nested ball-related triplet in the old private snapshot.
- Independent FieldManager Rev1 getters obtain the **current start** translation using manager field+0x50 → selected map object +0x4C. Base object constructor initializes translation storage +0x30/+34/+38 and pointer self-ref +0x4C to +0x30.
- Other agent's single raw paired B0 result: selected record0 +0x54 source words, selected nested ball translation, and current start translation are **bitwise equal for all three components**. This is a plausible *ball starts at tee marker* state, NOT proof of physics ball, movement, units, or independent frame timing.
- Separately #159 operator showed pin backing-map candidate x/y/z agreement and start only x/z agreement; current-start **game-accessor vector** is stronger than unverified PMP-in-memory +0x08 interpretation.

## This PR: reuse #160 as the gate

Only **NEW files**: `scripts/audit_selected_ball_start_link_private.py`, `tests/test_selected_ball_start_link_private.py`, `.github/workflows/s002-selected-ball-start-offline.yml`, this study note. The executable imports #160's `audit_golf_two_bank_roster_private` and calls its source/rev/scene/sport/mode/member/selector/PPC `triage` unchanged. It **fails closed** unless selected record is unique in the 4-slot source-defined array and source code actually supports record+0x88 and nested 3-float writer.

It reads **only source identified** selected record+0x54 triplet, selected record+0x88 → ball candidate +0x4C → 3-word destination, and current start (FieldManager+0x50) → object+0x4C → 3-word source getter. No whole RAM scan or new pointer candidate search. Output contains exact component **equality counts 0..3**, bitwise all-three agreement, float finiteness/boundedness, constructor compatible start selfref, and selected slot index 0..3. No runtime heap pointers, numerical coordinates or raw words. All actual ball-world XYZ, ball movement, ball velocity, same boot/frame, active human and training semantics remain **FALSE**.

With two preserved memory pairs, compares entire pair bytes privately via SHA256 **equality only**, plus whether the selected record triplet, nested ball triplet and start translation differ. Different dumps cannot prove a temporal sequence, same boot, an actual shot or ball motion. One pair can be source-gated individually; if second fails, DO NOT cherry-pick a variant to claim movement. A matching pair is a duplicate, not replication.

No Dolphin start/pause/dump, no game controller, no RPC, no network writes, no publication, no private file outputs. Inputs are exact 24MiB and 64MiB binaries located under the ignored sibling `Wii-AI-Golf-Data`; it rejects bad sizes/symlinks and prints generic errors without paths.

## The only useful existing operator action

After S002 accepts the stacked review, on the operator's Windows workstation, from a CLEAN isolated worktree:

```powershell
$root = "D:\Projects\Wii Golf AI"
$repo = "$root\Wii-AI-Golf"
$work = "$root\Wii-AI-Golf-Selected-Ball-Link-Offline"
$branch = "agent/research/selected-ball-start-link-20261027"
$base = "$root\Wii-AI-Golf-Data\mem-checkpoints"
$first = "$base\roster-existing"
$second = "$base\unclassified-20261027-203338"
if (Test-Path -LiteralPath $work) { throw "Worktree already exists; preserve it" }
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
git -C $repo worktree add --detach $work "origin/$branch"
if ($LASTEXITCODE -ne 0) { throw "Worktree creation failed" }
Set-Location $work
py -m unittest discover -s tests -p "test_selected_ball_start_link_private.py" -v
if ($LASTEXITCODE -ne 0) { throw "Focused synthetic tests failed" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Full Windows suite failed" }
py scripts/audit_selected_ball_start_link_private.py --first-dir $first
if ($LASTEXITCODE -ne 0) { throw "First preserved source-gate failed" }
py scripts/audit_selected_ball_start_link_private.py --first-dir $first --second-dir $second
if ($LASTEXITCODE -ne 0) { throw "Second pair failed source gates or comparison; STOP" }
```

If both preserved pairs are not from same boot/phase that is **not a bug**; the tool explicitly records that provenance is unverified and stops short of any motion claim. Never substitute the current Dolphin Dump files without manually checking timestamps and input origins. **Share only sanitized printed JSON, not native binaries, local file hashes or memory words.** This output does not itself grant permission for training.

## Stop / next promotion gates

Only promote to a game-state observation after S002/S001 can prove a controlled same-boot/timestamped pair from an opt-in live session with stationary ball and then clearly moved ball, source-backed selected slot, correct word writer, visual agreement, consistent change direction and units. First control should be no game action/idle and a distinct captured condition; only then causal physics/motion label. No user asked to run such a session yet. Unknown ≠ zero, and static start marker is NOT the dynamic ball.
