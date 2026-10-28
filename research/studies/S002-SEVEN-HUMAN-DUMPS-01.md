# S002-SEVEN-HUMAN-DUMPS-01 — seven operator-annotated Wii Golf RAM snapshots

Status: **human observations recorded; RAW files not read by this agent; memory identity/phase continuity unverified**. 2026-10-28, Wii Sports Golf Rev1 project. Operator performed manual Dolphin memory exports and provided one example local filename. Exact file-to-phase mapping, bank identity, hashes, timestamps and capture atomicity are **not yet verified**. Only these sanitized, operator-supplied labels are public; original native RAM MUST remain on the operator's Windows disk.

| Observation | Operator description (human, NOT memory-decoded) | Provisional cohort |
| --- | --- | --- |
| 1 | Driver, post-swing, ball visibly midair. Power indicator about 27 at instant, continuing to rise to roughly 56 (estimate). Shot subsequently off the green with UI showing 100.0 ft. | Driver shot D, airborne |
| 2 | Same driver shot as #1: ball stationary before screen transition. | Driver shot D, later settled/pre-transition |
| 3 | Putter, pre-swing, club fully extended backward, A button NOT pressed. | Independent putter setup P |
| 4 | Driver, pre-swing, club medium backward extension, A button PRESSED. | Independent driver setup A |
| 5 | Wedge, post-swing, ball midair near height maximum, indicated power around 31, camera angle just adjusted. | Wedge shot W, near apex |
| 6 | Same EXACT wedge shot as #5, a few frames later, ball descending. | Wedge shot W, descending |
| 7 | Ball contacts flag; 'Nice on' text appears. Same wedge shot as #5/#6, on-green result shown as 15.2 ft. | Wedge shot W, flag/green-result phase |

## Highest-value within-shot comparisons

1. **Wedge #5→#6**: same hit and short time delta, ascending/near-apex to descending; candidate motion-related differences with camera transition as confound. Distinct banks or tiny raw offsets may nevertheless reflect camera, rendering, frame counter, UI and physics.
2. **Wedge #6→#7** and **#5→#7**: changes at collision/UI state. A 15.2 ft human-read UI label is **not a verified game-score memory field**; 'Nice on' is a visual text state.
3. **Driver #1→#2**: airborne to stopped before transition. The 100.0 ft UI is an off-green penalty/status, **not necessarily an actual ball-to-cup distance**.
4. **Putter #3 vs Driver #4**: *not a single-factor comparison*: different clubs, ball states, club extension and A-button states; DO NOT infer an A bit, power, or swing state from this pair alone.
5. **Driver vs wedge**: between-shot contrast confounded by club, scene camera, power, time, ball state and course environment; only hypothesis-generating.

## Data contract and gates

- Raw native dump basename pattern is UNKNOWN. An example was supplied but no full listing or file sizes. **Do not assume** a label corresponds to MEM1 or MEM2, or that `n.1.raw`/`n.2.raw` exist for all seven.
- Source-pinned prior #223/#224/#225 comparisons found movement among ball candidates but a **pin-coordinate confound**. Reuse existing S002 source-resolved object owners and negative controls; don't copy a second pseudo-decoder.
- Do not equate a human-labeled phase with verified game frame. Dolphin GUI bank exports may span different frames; no paired guest-frame atomicity or same process/hole independently established.
- Require concrete names, exact bank lengths (MEM1=25,165,824 bytes; MEM2=67,108,864 bytes), Rev1 header, hashes and stable bank pairing BEFORE scientific comparison. No interpolation of unobserved frames.
- Never publish source file paths, full bank SHA, runtime addresses, raw words/coordinates, ROMs or game dumps. These are ignored RAW-PRIVATE data. Any public summary only contains phase IDs, boolean gates and conservative changed-page counts.
- Do not label ball XYZ, height, velocity, power percentage, impact, cup distance/score or training as verified from these dumps without independent source and repeated observational controls.

## Work item / handoff

Use independent read-only PowerShell 5.1 inventory and bounded offline bank comparison to generate a private **local** report of file pairing and whole-bank delta-page counts for D1→D2 and W5→W6→W7. On file naming/size ambiguity, stop at inventory; let the operator provide only sanitized name/size mapping (not bytes). S002 #223/#224/#225/#227 use source-gated follow-up and source-selected coordinate controls. S000 #205 track status and P0 blockers. S001 must not alter approved V1 waveform or create a new swing merely to obtain these frames.

## 2026-10-28 operator-run real native file inventory and whole-bank page differences

**Actual operator stdout (not independently accessed by GitHub agent):** Windows PowerShell 5.1 ran exact commit `dda6131e8baee76ea51870a52f9087e29ec9de8d` via `Invoke-P0SevenDumpAudit.ps1 -Mode Analyze` in the local Dolphin User/Dump. All seven phase numbers 1..7 contain exactly one 24 MiB MEM1 `n.1.raw` and one 64 MiB MEM2 `n.2.raw` by actual size. **14 files / 7 complete native bank pairs; unmatched raw filenames 0, wrong-sized matched files 0.** Original input files remained unmodified; operator script reported 4 completed same-shot comparison results and wrote a new RAW-PRIVATE local report. Strict Rev1 header and double-pass SHA checks did not trigger refusal. This is tool-success evidence, not independently demonstrated same-frame atomicity, stable pin/camera, proper image provenance across phases, or source-decoded physics.

| Pair (human labels) | MEM1 changed 4096-byte pages | MEM2 changed 4096-byte pages |
| --- | ---: | ---: |
| D1→D2 airborne→stationary | 385 | 244 |
| W5→W6 near apex→descending | 267 | 208 |
| W6→W7 descending→flag/'Nice on' | 306 | 217 |
| W5→W7 near apex→flag/result | 319 | 225 |

Each page count refers to **pages with >=1 changed byte**, not count of individual changing bytes, motion dimensions or physical variables. MEM1 has 6144 pages; MEM2 has 16384 pages. The 100.0 ft driver and 15.2 ft wedge are human UI readouts, not a decoded RAM score field.

**Next P0:** Preserve all seven pairs as read-only baseline; source-resolve selected ball, start and PIN via existing S002 #223/#224/#225 readers in **each** W5,W6,W7 and D1,D2, requiring consistent selected owner/hole and validated cache alias/self-reference. For the wedge time sequence, the key prediction is candidate ball location changes W5→W6 and W6→W7 while stable start/pin/tee controls stay unchanged. Prior flight study found the PIN also changes, so gate off any physical XYZ/velocity claim until coordinate-rebase/pin camera confounds are resolved. Check temporal overlap of changed pages as coarse triage, not a coordinate decoder.


## Wedge 3-state temporal page-mask follow-up (new code, real data pending)

Extended the **same** standalone PowerShell 5.1 audit to calculate the intersection of 4KiB changed-page masks for W5→W6 (A), W6→W7 (B), and W5→W7 (C), for MEM1/MEM2 separately. Reports pages changed in both adjacent intervals, in all three contrasts, changed twice but with first/last page identical, first-interval-only, and second-interval-only. Enforces `C ⊆ A ∪ B` before writing the report, which must hold for stable immutable three-snapshot byte comparisons. The owner must compare the changed-page masks to **source-gated** selected-ball and PIN object offsets before considering any field. Intersection does not establish motion or field semantics.

**Exact synthetic validation:** [GitHub run 40644726793](https://github.com/Nate27624/Wii-AI-Golf/actions/runs/40644726793) Windows PowerShell 5.1 and Ubuntu PowerShell 7 both **7/7 tests PASS, zero skipped**, including a fabricated three-snapshot wedge control (pages 1,2,3 changed in first adjacent interval; 2,3,4 changed second; 1,3,4 changed long-span; overlap=2, all-three=1, returned-to-original=1). **Real user's W5/W6/W7 temporal intersection counts not obtained yet**; the original 4 pairs remain user-reported source-of-truth until rerun with this reviewed script. No fresh shots required.


## 2026-10-28 real W5→W6→W7 temporal mask findings (operator-run private report)

The operator ran local PowerShell on their previously saved report-RAW-PRIVATE.json containing 4KiB bank-relative changed-page masks from the REAL seven fullbank pair audit. Only the following aggregate counts were shared; private page indices/hashes/bytes stayed local.

| Three-snapshot 4KiB page class | MEM1 | MEM2 |
| --- | ---: | ---: |
| Changed in BOTH adjacent intervals 5→6 and 6→7 | 253 | 200 |
| Changed in ALL THREE contrasts (5→6, 6→7, 5→7) | 252 | 200 |
| Changed in both adjacent intervals BUT first 5 and final 7 pages identical | 1 | 0 |
| Changed ONLY in first adjacent interval | 14 | 8 |
| Changed ONLY in second adjacent interval | 53 | 17 |
| Reconstructed total 5→6 | 267 | 208 |
| Reconstructed total 6→7 | 306 | 217 |
| Reconstructed total 5→7 | 319 | 225 |
| Exact three-snapshot page triangle check | PASS | PASS |

Cross-checks: MEM1 253+14=267, 253+53=306, 252+14+53=319; MEM2 200+8=208, 200+17=217, 200+8+17=225. **94.76%** (253/267) of MEM1's first-interval changed pages and **96.15%** (200/208) of MEM2's first-interval changed pages also changed in the second. Reverse proportions: 82.68% (253/306) MEM1 and 92.17% (200/217) MEM2. One MEM1 4KiB page changed then returned to exactly snapshot 5's entire page contents in snapshot 7; zero MEM2 pages did so.

These are **large recurring activity sets**, not identified ball-position addresses: a 4KiB page can contain rendering/UI, camera, time, player, physics and other fields. Whole-page identity is NOT physical return of a ball. Source bank hashes and masks prove bytewise change, not same-guest-frame atomicity or source-backed object semantics. Same-shot ordering is human observation.

### Next source-gated owner task (do not duplicate readers)

Parallel S002 [PR #230](https://github.com/Nate27624/Wii-AI-Golf/pull/230) and [PR #231](https://github.com/Nate27624/Wii-AI-Golf/pull/231) ALREADY own seven-snapshot source-checked PPC selected-ball/tee/pin/cache/record analysis. Reuse those readers on saved seven local pairs, verifying owner/hole/scene/pin/start for W5,W6,W7 and contrasting candidate current ball+0x30 and caches+0xCC/+0xF0/+0xFC in W5→W6 and W6→W7 (0..3 changed components). Check pin/current-start stable and player record+0x34/+0x38/+0x74, and camera rebase at W5. Driver 1→2 is an independent same-shot control. Putter 3 vs driver 4 is NOT controlled A-state intervention.

UI labels 15.2ft wedge and 100.0ft off-green driver are still human-read screen values, not decoded RAM score. Raw data, memory page indices and private paths never uploaded.

Current gates: same_guest_frame_verified=false, actual_ball_world_xyz_verified=false, ball_velocity_verified=false, power_memory_verified=false, score_memory_verified=false, approved_for_training=false.

## 2026-10-28 REAL source-gated seven-snapshot trajectory — operator #230 run

The operator ran exact **S002 #230 commit b0a5272520d06ea446fe90679690cbc1889a2e3b** in a fresh detached worktree with PowerShell `Invoke-P0SevenSourceTrajectory.ps1`, against the seven original private 24/64MiB bank pairs. The script executed **9/9 synthetic tests PASS**, isolated Python import preflight PASS, and printed `P0_SEVEN_SOURCE_TRAJECTORY=PASS` after the real source-selected read. All **7/7** numbered snapshots passed the existing Rev1 PPC source, scene, golf mode, selected player/ball/start and pin self-reference checks required by the reader. These are *source-gated memory candidates*, not demonstrated game-world physical coordinates or atomic frame timestamps.

| Human-labeled same-shot transition | Selected ball object +0x4C→+0x30 changed components | ball caches +0xCC/+0xF0/+0xFC changed components (each) | source start | source pin | record +0x54/+0x60 (each) | Source ball/pin/field/start pointer identities |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Driver #1 airborne→#2 stopped | 3/3 | 3/3 | 0/3 | 0/3 | 0/3 | identical |
| Wedge #5 near apex→#6 descending | 3/3 | 0/3 | 0/3 | 0/3 | 0/3 | identical |
| Wedge #6 descending→#7 flag/green result | 3/3 | 0/3 | 0/3 | 0/3 | 0/3 | identical |
| Wedge #5 near apex→#7 flag/green result | 3/3 | 0/3 | 0/3 | 0/3 | 0/3 | identical |

Other real fields: **all four same-shot transitions** returned `source_slot_and_hole_stable=true`, `ball_candidate_changed_with_stable_start_and_pin=true`, `ball_candidate_changed_but_pin_or_pointer_confounded=false`, and `ball_motion_proven=false`. There were **three distinct** source-selected ball candidate triplet bit patterns for wedge phases #5,#6,#7, so differences cannot be inferred solely from unrelated page activity. Existing source-selected fixed reference and pointer stability resolves the specific earlier B0→airborne PIN movement confound *for these within-shot comparisons* at the checked fields. It does **not** eliminate unmeasured global camera/world transform, reset/boot, timing, memory bank atomicity or numerical/physical semantics.

**Notable wedge cache split:** current source-selected ball translation changes 3/3 for 5→6 and 6→7 while all three +0xCC/+0xF0/+0xFC copies remain bitwise unchanged across all three wedge phases. Meanwhile they change 3/3 along with the current translation in driver 1→2. These caches are *not* proven independent live position variables or synchronized to the current ball. Test whether they mirror launch/settled endpoints, stored aim/tee or delayed/reference transforms by using the existing cache-coherence owner #225 / seven-source owner #231, without writing a second reader. Explicitly compare **within each snapshot** cache vs current live vector bitwise and references across phase 1,2,5,6,7, then source check writer/callers. A stable cache is not a proof it is wrong; a changing current triplet is not proof its axes/units represent physical XYZ.

**P0 promotion gates remain FALSE:** same-guest-frame MEM1/MEM2 atomicity, independent frame count/time delta, world XYZ axes and scale, velocity, power, contact frame, decoded memory score, full training readiness. The 15.2ft and off-green 100.0ft UI values are human-provided labels, not extracted RAM fields. No raw memory bytes, hashes, runtime pointer values or private file paths were uploaded to GitHub. No new swing needed.

## Cross-agent source confirmation: preserved seven-pair archive and a static wedge cache reaching W7

S002 [PR #231 study](https://github.com/Nate27624/Wii-AI-Golf/pull/231) now documents an **independent completed REAL operator run** on the separately preserved 14-bank SHA-verified private archive: 16/16 local synthetic tests passed, real seven-pair source audit PASS. Reported selected source slot=0/hole=1, stable selected slot/hole and field/pin/start pointers across human-associated pairs. Wedge W5→W6, W6→W7, W5→W7 selected ball+0x30 changed 3/3 each edge, while source PIN/START/cache+0xCC changed 0/3; driver 1→2 selected ball and cache+0xCC both changed 3/3. This matches original #230 run above and validates analysis against the preserved archive rather than only the live Dump.

**Crucial within-snapshot equality (from independently recorded #231 real operator output):** current selected ball equals cached +0xCC in **3/3** u32 words at snapshots #1,#2,#3,#4,#7, but **0/3** at wedge flight snapshots #5,#6. Since +0xCC is invariant across W5,W6,W7, its bitpattern already equals the ball translation at the visually labeled flag/result snapshot #7 as early as W5 and W6. This specifically supports an **endpoint / landing-target cache hypothesis**, not necessarily an independently live trajectory cache. Alternative explanations include stored target, stale reference coordinate, reconstruction/transforms, or UI/camera phase differences. No game-world meaning/axes/units/velocity or mechanistic write proof follows from equality alone.

Source-specificity cross-check: #231's linked #230 operator review reports **selected ball+0x30 3/3 changed while three inactive player slots changed 0/3** during wedge transitions. Source identity was validated; machine guest frame count and exact screen association still unproven. The +0xCC per-snapshot equality result is *not* a statement about +0xF0/+0xFC per-snapshot equality, as those columns were not fully printed in the #231 operator transcript. Do not extrapolate.

Recommended next owned experiment: ask existing #225/#231 source owners to verify source-code writers and whether +0xCC is assigned at shot launch, aim prediction or result propagation; determine what W7's human 15.2ft UI label measures relative to PIN and cached endpoint only after PPC, units and reference frame are established. Preserve raw banks PRIVATE, do not invent collision frame, velocity or training approval.
