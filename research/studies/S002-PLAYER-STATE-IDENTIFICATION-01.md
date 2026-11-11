# S002-PLAYER-STATE-IDENTIFICATION-01 — source-first golf state, then causal shot labels

**Status:** offline B0 evidence analyzed; phase-control protocol PRE-REGISTERED, zero additional authorized shots or captures executed by this PR. Memory-first prioritization per operator. Owner S002 source and runtime memory, S001 canonical Dolphin and wave input, S000 privacy/typed publication, S003 identifiability and modeling. Do not train until proof gates below.

## Actual paired B0 findings: not a speculative scan

Operator supplied one paired native 24 MiB MEM1/64 MiB MEM2 captured with Felk Dolphin debugger at first-ball training scene. Both exact sizes pass. Original MEM1 and two submitted MEM2 files checked; the latter two MEM2 images were identical by whole-file SHA256 (hash retained PRIVATE, not committed). The pair is source-gated: RSPE01 Rev1, scene 5, manager+0x0C active scene and scene+0x20 backlink, sport2, RPGolConfig+0x94 mode4, config+0x98 hole raw index1. There is **no independent same-frame or same-boot proof** for sequential GUI export. The root Golf scene/golf-main and current field manager are in MEM2, so MEM1-only comparisons cannot identify game state.

**New SOURCE-NAMED GEOMETRY DISCOVERY:** From `kiwi515/ogws_info` headers `RPGolFieldManager.h`, `RPGolMapObjBase.h` and `RPGolConfig.h`, we read five typed map-object transforms (current start field+0x50, current pin +0x44, cup +0x54, course +0x70, tee marker +0x2C). `RPGolMapObjBase` declares 3x3 rotation at object+0x0C, 3-vector translation at +0x30, scale at +0x3C. On actual private B0 all five translation vectors are finite, rotations orthonormal and scale components positive. Pin and cup horizontal positions agree exactly in B0; current-start-to-pin horizontal separation is **216.551 game coordinate units**, pin minus start height +3.000 game units, absolute pin/cup height difference 0.092. This is NOT verified yards, feet, ball position, or golfer pose. Config score matrix 4x9 (`+0x004`) has 36/36 zero entries in B0; no real shot outcome yet. **Header integrity warning:** upstream annotations for two transform pointers at +0x40/+0x44 overlap the declared 3-float scale +0x3C..+0x47. The new code DOES NOT dereference these contradictory pointer annotations; source translation is independently plausible.

**New PLAYER-OBJECT SOURCE WITNESS:** `RPGolScene+0x9C` → source-gated main object; within its first 0x100 bytes, **only main+0x030** points to a MEM2 object whose first word lies in `RPGolPlayer` `.data` interval 0x803C7CC8–0x803C7DD0 from `doldecomp/ogws config/RSPE01_01/splits.txt`. Reading twelve aligned words at that static table shows eight code-pointer entries into RPGolPlayer `.text` 0x8029E62C–0x802A2210. Source-gated main first word maps RPGolMain `.data`, and player-manager static first word maps RPGolPlayerManager `.data` with one of twelve pointers into its `.text`. This is **strong L2 type evidence but not verified C++ dynamic type, ownership, individual member offsets, swing power or ball**. No raw pointers or function absolute runtime values are published.

## Training-state field priorities

| Priority | Variable family | Status after B0 | Proof needed for training |
|---|---|---|---|
| P0 | Disc/revision, scene, sport, mode, hole | Source-backed one-pair | Replicate in every checkpoint and independent boot |
| P0 | Start/pin/cup/course geometry | Five source-named transforms with sanity invariants | Independent-boot stability, hole changes, distance unit calibration |
| P1 | Player/club transform, aim | Single L2 RPGolPlayer-like main+0x030 source witness | Show source/PPC store owner, distinct aim-only response, actual player pose not just camera |
| P1 | Impact, swing meter power | UNKNOWN | Same-shot observed impact frame, write PC/field semantic, 3+ distinct human-measured powers |
| P1 | Ball world XYZ, velocity, motion/contact state | UNKNOWN | Source identity, pre/post impact changes, derivative consistent with game frames |
| P2 | Wind direction and speed | `RPGolConfig::GetWind` source routine exists; field wind obj pointer only | Validate source fields and independent read vs visible wind |
| P2 | Scores, penalty, rest state, landing/carry | Zeroed source score matrix only | Real post-shot score and clean outcome, separate 100ft challenge penalty vs carry |

Evidence tiers in `research/claims/golf-state-field-register-v1.json`: L0 unknown, L1 source-defined single-pair field, L2 type witness in `.data`+`.text`, L3 write-site/source/independent-boot, L4 independently measured physical/gameplay effect. Unobserved labels stay UNKNOWN.

## S002-PLAYER-NULL-01 — one new consented NO-SHOT four-checkpoint controlled session

**Why not more 28-child idle sweeps?** Those were already completed and mostly frame counters. Focus the SOURCE-PLAYER-like object `RPGolMain+0x030` and compare only first `0x80` bytes. This reduces confounding and preserves object-relative field provenance when heap addresses relocate.

Study four source-gated pairs in ONE existing canonically launched first-ball session, all without pressing A or swinging:

- B0: paused first-ball tee with all controls still.
- B1: resume to advance time with hands off controls, then pause; timed idle negative control.
- B2: resume, manually move WASD pointer/aim ONLY and confirm visually, then pause while target is at new setting.
- B3: release all controls, resume for comparable idle, pause again. Aim may remain at new setting; `persistence` is NOT failure of an effect.

At EACH paused checkpoint, record `Export → Dump MRAM` and `Export → Dump ExRAM` and copy `Dump/mem1.raw` and `Dump/mem2.raw` to unique ignored folder `Wii-AI-Golf-Data/mem1-checkpoints/B0-MEM1.bin/B0-MEM2.bin` etc BEFORE another export (Felk `DumpArray` uses `wb` overwriting defaults). Write a private local provenance note recording checkpoint label, human visual input observation, whether Dolphin pause actually froze a frame, mode/hole, whether Dolphin restarted, any GUI errors. No frame count asserted from UI alone. **Do not resume until both images are copied.** Never use Felk bridge emulation.pause, no second Dolphin instance or per-byte RPC whole-bank reads. If the old B0 pair came from a terminated earlier session, acquire a NEW B0 in this same boot; do not pretend old B0 and new B1 are a controlled series.

**Offline code now ready in PR #151**:

- `src/wii_ai_golf/audit/golf_cross_bank_state.py`: source-gate scene/mode/fields in each bank pair.
- `src/wii_ai_golf/audit/golf_environment_geometry.py`: five source-named transforms and geometric sanity.
- `src/wii_ai_golf/audit/golf_player_owner_evidence.py`: main+0x030 candidate `.data` + PPC `.text` region checks.
- `src/wii_ai_golf/audit/golf_player_four_phase.py`: gate all four bank pairs; compares ONLY candidate player's first 0x80 bytes at 32-bit word resolution; classifies B0→B1 idle change, B1→B2 aim change, B2→B3 persistence/reversion. B1→B2 unique candidate requires B0/B1 stability. Up to 24 relative offsets, never exports raw bytes/values/runtime pointers or source DOL. One idle-control interval is insufficient to establish causality.
- `scripts/audit_golf_player_four_phase_private.py`: explicit opt-in local 8-file comparator. No automatic publication. CI targets Windows and Linux synthetic tests for all new code.

**Research decision tree:** (a) Candidate owner vtable/data/code check breaks at any stage → STOP and debug object lifetime; (b) no stable-idle+aim change → no evidence from first 0x80, not proof that pose doesn't exist; source atlas and debugger write-site next; (c) 1+ aim-contrasted offset → keep UNKNOWN field candidates and request tiny targeted write-PC trace from S001/S002 only after verifying input source, do not call power; (d) if all 32 change with idle, classify as timing/global/allocator nuisance and do not expand generic scanning.

## S002-PLAYER-SWING-02 — eventual source- and frame-validated real-shot labels (NOT YET AUTHORIZED)

Only after source verified the player/club fields and in-bridge frame-timed sampler, have S001 opt-in ONE canonical known-good A-lead45 V1 trace preserving exact 89 sample identity and no second socket writer. Pre/post club/power and ball state must be sampled from SAME bridge frame thread in a known shot, not slow 6–18 frame polling. Separate requested vs dispatched vs game-applied input. All event records should include opaque session+shot+trace IDs, actual emulator frame or explicit unavailable, synchronized input and memory observation. First do stationary/no-A, WASD, A-held-without-swing negative controls; then real human-approved swings.

**Calibration gate:** at least 3 *genuinely different* human-observed in-game power readings (not three identical ~75% shots), multiple independent boots, and held-out contacts. Prefer 3 × 3 clean powers per condition; no optimization/regression until the memory power field varies appropriately and source write-PC matches intended gameplay event. `100ft off-green` remains a challenge penalty, never ball carry. Independent source-backed ball XYZ/velocity required for flight/reward models. If player source has no value, park training rather than fabricate labels.

## Coordination + privacy + requests

Owner S002 #3/PR #129: inspect player source `.text` and `.data` xrefs, use #144/#146 code audits; verify what is actually written during aim; prefer exact PPC function write sites over blind 4KB scans. S001 #2: vet paused MRAM/ExRAM repeatability, write-watch feasibility, frame-thread hook; do not alter known controller. S000 PR #148: update full-state study to paired **MEM1 AND MEM2**, review typed public allowlist; this report is *LOCAL ONLY*. S003 #125: follow identifiability gate, no early power regression. Existing tool targeted tests prove software invariants, not gameplay correctness.

All original RAW RAM, runtime pointers, DOLs and savestates remain PRIVATE. No automatic upload to GitHub; reports contain only source-relative offsets, counts, geometry-derived values and explicit unverified flags. Only the operator can consent to next capture. Two previous files named mem2.raw and mem2(1).raw were byte-for-byte duplicates; no independent second MEM2 state exists from those uploads.