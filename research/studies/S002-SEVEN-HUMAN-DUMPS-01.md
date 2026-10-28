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

