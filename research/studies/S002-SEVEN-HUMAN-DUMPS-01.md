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
