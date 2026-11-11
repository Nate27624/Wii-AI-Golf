# S002-BALL-DYNAMIC-02 — selected ball position: static equality vs actual movement

**Owner:** S002 #160/#163 ball/selected-record source chain; S001 #2/#147 is sole live Dolphin/controller capture owner; S000 #154 privacy and verified field ledger; S003 #125 model gating. THIS PR (#151) owns only the offline capture-preservation helper and training-readiness protocol; it does NOT add a duplicate roster parser, memory scan, new input controller, debugger hook or publisher.

## Why a moving ball is the essential discriminator

One existing operator provided MEM1 24MiB and MEM2 64MiB pair (non-atomic GUI exports). In this B0, source-gated PlayerManager selector at manager+0x334 identifies relative record index 0 in a four-record +0xCC stride; that record +0x054,+0x058,+0x05C matches its +0x060,+0x064,+0x068 triplet, matches the child-of-ball-like object's +0x04C translation destination, and matches the selected source-named start transform. This is exactly **12 equal word comparisons = four triplets of three components**, not 12 independent position measurements. This is consistent with initializing a ball at the tee. It can equally be a rendering transform or stale copied position. No actual change, velocity, landing/impact or power has been observed.

Independent static source evidence in PR #160: a manager four-record (+0xCC) loop; source selector store at +0x334; record +0x088 ball-related member; three PPC stfs to nested ball child +0x04C translation. PR #162 adds a simulator array constructor (four per-player +0x1AC objects) and reverse-sync Player code; these source links outweigh generic source-unit .data interval hits. PR #163 owns selected-ball/current-start equality from one or two existing pairs. None alone proves world-space ball XYZ.

## Falsifiable minimal tests and stop rules

| Phase | Human-visible required state | What is sampled | Expected relation if field is physical ball position |
|---|---|---|---|
| B0 | First-ball tee, controls still, Dolphin paused | Native MEM1+MEM2 | selected ball-like vector equals source start |
| B1 | Resume 1–3 s idle, never touch controls, then pause | Both banks | ball-like selected vector remains bitwise (or approximately floating-point) unchanged; clock-like words may change |
| B2 | Resume, move WASD aiming/camera ONLY (no A/shot), then pause | Both banks | ball-like position remains unchanged while UI aim state changes |
| B3 | Release WASD, let animation settle with no shot, pause | Both banks | ball-like position remains unchanged; negative control for UI lingering |
| B4 | ONE explicit operator-approved real shot, after ball physically stops and UI indicates landed, pause | Both banks | selected vector moves by a nonzero plausible displacement relative to B3; source start/pin/cup are stable |
| B5 | Resume 1–3 s idle after landing, pause | Both banks | ball vector remains stable at new position (if same hole, no automatic reset) |

Treat B4/B5 as OPTIONAL until S001/S002 owners approve a harmless real shot and the game is known to remain in the same hole/mode for the chosen training. If the game leaves the Golf scene, changes to another hole, or destroys/replaces objects, STOP and retain private data; do not interpret relocation as motion. If B4 fails because the training challenge immediately resets the ball, postpone shot study and use the S001 bridge's source-gated frame callback to capture during known valid shot frames. Do not reinterpret final score penalty as carry.

### Acceptance criteria (all required before field promoted from UNKNOWN to motion candidate)

1. Every source-gated pair passes `RSPE01 Rev1`, current Golf scene ID5, sport2, manager backlink, mode4, selected player-manager 4x0xCC record and exact selector source witness. Explicitly re-resolve every allocation per pair; never retain raw heap addresses across states or boots.
2. Source-reviewed PlayerManager record+0x88 and child+0x4C decode to three IEEE-754 f32 components; all finite and comparable across B0-B5. If candidate first word, selector, or child pointer changes, separate legitimate reallocation from semantics; no automatic equality on arbitrary addresses.
3. B0/B1/B2/B3 no-shot negative controls show selected ball-like vector stays approximately stationary while frame counters/UI/aim vary; if not, investigate render interpolation or coupled camera coordinates rather than call world XYZ.
4. At B4 actual independently observed ball motion has landed away from start while selected vector differs from B3 and the source-named course pin/cup/start remain unchanged. At B5 returned-to-idle vector agrees with B4 if same hole. A single shot is *a plausibility check*, not independent validation.
5. Repeat with at least two physically different shot outcomes and independent boots, and independently corroborate trajectory axes against the screenshot/game display. Only after these controls and source PPC write-PC dataflow can the field be called candidate ball world XYZ. Velocity requires synchronized frame sampling of actual changing coordinates; GUI-paused dumps never prove a flight trajectory.
6. Class and actor selection: bounded source writers and runtime write-PC / construction must prove we're following the actual active simulated ball rather than a proxy; PR #160+PR #162 should own this. `ball_xyz_verified` remains FALSE before that.
7. Swing power, club rotation, impact event and in-game distance remain UNKNOWN. Do not train any power or trajectory model from the above without S001 same-frame input+memory+contact evidence and >=3 independently observed power bins plus held-out trial.

## Implemented helper: fail-closed, local-only MRAM+ExRAM preservation

New `scripts/preserve_golf_checkpoint_pair.py` is a pure offline file-preservation utility. When the operator has physically paused Dolphin, clicked Memory → Export → Dump MRAM and Dump ExRAM, and the native files exist in the Dolphin Dump directory, ONE invocation with `--checkpoint B0...B5 --paused-confirmed` copies them to *fresh unique* `<private session>/Bx-MEM1.bin` and `Bx-MEM2.bin`. B4 additionally requires `--shot-observed`. The helper never starts/controls Dolphin, never accesses a network, and never writes RAM. It checks size (24MiB+64MiB), `RSPE01` Rev1 and Golf scene/mode/backlink via existing source-gated paired-bank module, source mtime ordering and <=5min gap, both files newer than previous phase and newly different in at least one bank. It **refuses overwrites**, out-of-order phases and unexpected session-root outside sibling `Wii-AI-Golf-Data`. It creates a local-only `checkpoint-manifest-PRIVATE.json` with phase labels, source mtimes, SHA256 hashes and operator pause assertion; console prints only a redacted acknowledgment. It cannot independently establish one boot, exact paused frame, or operator input correctness.

### Operator steps after S001 owner signs off (NOT an instruction to run shots now)

1. Start ONE known-good canonical Felk Dolphin session at Hitting the Green first ball; do not revive old B0 from a DIFFERENT boot. In Windows PowerShell create a fresh session folder under the sibling ignored private directory:

```powershell
$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
$work = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-MEM1-Offline'
$branch = 'agent/research/offline-mem1-checkpoint-diff'
$private = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\ball-validation-session-01'
New-Item -ItemType Directory -Path $private -ErrorAction Stop | Out-Null
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
if (-not (Test-Path $work)) { git -C $repo worktree add --detach $work "origin/$branch" }
if ($LASTEXITCODE -ne 0) { throw 'Worktree failed' }
py -m unittest discover -s "$work\tests" -p 'test_preserve_golf_checkpoint_pair.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Preservation tests failed; STOP' }
```

2. At each phase **BEFORE running helper**, use Dolphin GUI to `Emulation → Pause`, `View → Memory → Export → Dump MRAM`, then `Export → Dump ExRAM`. Do NOT use frame-polled `emulation.pause` RPC. Run only the one stage applicable to the current visibly verified state:

```powershell
py "$work\scripts\preserve_golf_checkpoint_pair.py" --private-root $private --checkpoint B0 --paused-confirmed
# AFTER you resume, wait idle, pause again and re-export both banks:
py "$work\scripts\preserve_golf_checkpoint_pair.py" --private-root $private --checkpoint B1 --paused-confirmed
# AFTER source-approved WASD-only aim and new paused exports:
py "$work\scripts\preserve_golf_checkpoint_pair.py" --private-root $private --checkpoint B2 --paused-confirmed
# AFTER no-shot idle and new paused exports:
py "$work\scripts\preserve_golf_checkpoint_pair.py" --private-root $private --checkpoint B3 --paused-confirmed
# B4 & B5 require distinct future S001 owner approval of one known-good shot.
```

3. Review only sanitized summaries; NEVER upload native memory files or local checkpoint manifest to public GitHub. The manifest contains local file SHA256 and operator provenance; it is not an approved typed public schema. S002 #160/#163 should add *selected vector across phases* comparison to its canonical roster implementation; do not add another competing parser to #151.

## Handoff

- S002 #160/#162: code identity + write PC confirmation for actual ball simulation, treat current nested vector as candidate.
- S002 #163: extend source-gated position-equality checks from first/second pair to B0...B5 with per-phase selected record, map/start control, candidate reversion/persistence. No raw floats in stdout. Time labels are manual, never same-frame truth.
- S001 #2/#147: design a sub-two-frame in-emulator passive watcher after getting proof of ball address+field lifetime; no second controller writer and no full-MEM RPC.
- S000 #154: canonical field ledger maintains `ball.xyz_verified=false`, `power_verified=false`, training disallowed until independent evidence.
- S003 #125: no regression before different real power bins, event-matched input and verified ball trajectory.

**Status:** No B1–B5 results exist in provided uploads. The two MEM2 submissions were identical. Both prior B0 files were GUI exported minutes apart, so no same-frame claim. This protocol is proposed, not an executed shot study.