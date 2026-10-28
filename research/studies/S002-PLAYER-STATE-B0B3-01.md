# S002-PLAYER-STATE-B0B3-01 — selected golfer state-word negative control

**Status:** new additive, PRIVATE offline-only candidate check; synthetic tests
authored, real operator data / full Windows run PENDING. Does not touch
working FelkDolphin-Clean, old crash-prone install, S001 controllers, memory
bridge, active savestates, or game mode. Reuses the four already-preserved
B0/B1/B2/B3 source-gated native paired-bank images and checkpoint manifest;
do NOT capture/re-export memory, launch Dolphin, swing, reset or upload bytes.

## Hypothesis and evidence

The user's US RSPE01 Revision 1 `main.dol` was privately inspected.
In `RPGolPlayer.cpp`, this function has receiver r3 -> r29
at `0x8029F0C0` and **five literal-to-`record+0x24` writes**:

| Code PC pair | Exact PPC opcodes | Candidate literal |
| --- | --- | --- |
| `0x8029F0C8` / `0x8029F0CC` | `li r0,5`; `stw r0,+0x24(r3)` | 5 |
| `0x8029F0D4` / `0x8029F0DC` | `li r0,1`; `stw r0,+0x24(r3)` | 1 |
| `0x8029F0F4` / `0x8029F0F8` | `li r0,2`; `stw r0,+0x24(r29)` | 2 |
| `0x8029F134` / `0x8029F138` | `li r0,3`; `stw r0,+0x24(r29)` | 3 |
| `0x8029F1BC` / `0x8029F1C0` | `li r0,4`; `stw r0,+0x24(r29)` | 4 |

This is *source code writer identity*, not proof of execution during our
snapshot, a complete enumeration, active shot/contact, landing, power or
a public enum mapping. Prior S002 source analysis links the selected
player record to a nested ball-like VEC3. Previous real B0–B3 null
controls passed: ball/start/record vectors 0/3 changed components
through idle, visible WASD aim, idle; the **state word has NOT YET been
examined**.

## Implementation and guardrails

`scripts/audit_selected_player_state_four_phase_private.py` is a
new-only addition stacked on #163 and **reuses**:

- #163 manifest labels/order/sha checks and exact native sizes (24MiB
  MEM1 / 64MiB MEM2) for all eight already-saved B0–B3 private files.
- #160 source-gated revision, mode4/scene5, selected source player
  manager/record pointer chain and PPC writer checks through
  `selected.analyze_one`.
- Exact *ten* PPC US Rev1 instruction-word witnesses for the five
  literal stores (match against already captured MEM1 code bytes),
  before reading exactly **one additional source selected-record u32
  at receiver-relative `+0x24` per checkpoint**.

The script uses native read-only mmap, not a new RAM scanner. It
prints **only** per-phase candidate zero flags, candidate membership
in the five source-written literals (1..5), distinct count,
three transition change booleans, selected record identity
stability and all uncertainty flags FALSE. It emits **no raw state
integer**, native pointers, private paths, executable/game bytes,
file hashes, or numeric game coordinates. Public GitHub publication
explicitly blocked (`allowed_to_publish=false`).

A state match or change cannot establish the game semantics of the
numeric value. A state word can be zero or outside the five literals
without contradicting the source code; no class/physics value is
automatically inferred. An aim-only change would disprove
stationarity for that candidate but *not* prove it indicates aiming.

`tests/test_selected_player_state_four_phase_private.py` includes
twelve synthetic checks (no game ROM/RAM): source instruction
corruption, wrong revision/selected actor, stable and varying no-shot
candidate words, zero/unknown values, source record relocation,
hole/slot mismatch, redaction and CLI private path error.

## Operator command — offline AFTER owner review + focused CI

Only when user wants this bounded study; no urgency while
FelkDolphin-Clean is restored and responding, and no need to change
or reboot its current session.

```powershell
$repo = "D:\Projects\Wii Golf AI\Wii-AI-Golf"
$root = "D:\Projects\Wii Golf AI"
$work = "$root\Wii-AI-Golf-State-Offline"
$branch = "agent/research/selected-player-state-b0b3-20261027"
if (Test-Path $work) { throw "Preserve existing worktree; do not overwrite" }
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
git -C $repo worktree add --detach $work "origin/$branch"
if ($LASTEXITCODE -ne 0) { throw "Checkout failed" }
Set-Location $work
py -m unittest discover -s tests -p "test_selected_player_state_four_phase_private.py" -v
if ($LASTEXITCODE -ne 0) { throw "Focused test failure; no real data read" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Full suite failure; no real data read" }

# Use the EXACT, already-preserved B0-B3 session folder with
# checkpoint-manifest-PRIVATE.json and B0..B3-MEM1/MEM2.bin files.
# Do NOT guess a path, copy raw memory to GitHub, or trigger GUI export.
$session = Read-Host "Existing B0-B3 private folder"
if (-not (Test-Path (Join-Path $session 'checkpoint-manifest-PRIVATE.json'))) {
    throw "Manifest missing; stop"
}
py scripts/audit_selected_player_state_four_phase_private.py `
  --private-root $session --aim-visibly-moved --operator-same-session
if ($LASTEXITCODE -ne 0) { throw "State audit failed closed" }
```

The two operator report flags are appropriate ONLY for the already
confirmed original same-session B0–B3 context. They are not
independent boot proof. Send only sanitized console flags (and only
after S000 owner permits that schema); NEVER post actual private
native files or the unapproved report to the public repository.

## Scientific next step

If the candidate state word is unchanged in no-shot controls, it is a
plausible piece of the golfer state machine but **NOT a verified shot
phase**. If it changes with WASD-only aiming, it needs a different
state explanation. Later S001 may consider a single additional
read-only source-selected u32 alongside the existing opt-in ball
watch, but ONLY after S001/S002/S000 approval, no contact baseline
issues, instrument overhead and real guest-frame limitations resolved.
No swing-power calibration or training from these four files.
