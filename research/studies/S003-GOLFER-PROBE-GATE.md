# S003-GOLFER-PROBE-GATE — Candidate gameplay RAM decision study

**Owner:** S003 (draft PR #125). Downstream of S002 live candidate recorder PR #129. This is OFFLINE-ONLY analysis of previously sanitized reports. No Dolphin, controller, raw RAM, extra launcher, uploader or shared-schema change.

## Hypothesis and budget

**H0:** Words changing during IDLE/AIM negative controls are not evidence of swing-power or club-angle state. **H1 (exploratory):** a uniquely source-gated RPGolMain candidate may contain relative words worth following up with a future synchronized swing study, but current report does not prove field semantics.

Budget: 0 new game attempts and at most 32 preexisting sanitized S002 reports. No model fitting, held-out claims, physical carry or change to V1 A45 control. Source-verified candidate is not verified actual golfer, nor a decoded power sensor.

## Pure analysis API

The new wii_ai_golf.modeling.golfer_probe_review.review_golfer_probe_summaries(reports) parses S002 local-golfer-memory-audit summaries (or no_unique_golfer_pointer_chain diagnostics) and returns only safe counts, relative offsets, frame-span advisories and next action.

Validation requires exact RSPE01 US Rev1 / mode4, singleton-candidate status, creator-scene diagnostic presence (true OR false), two or more idle/aim control snapshots, 4-byte aligned 0x100-window offsets, bounded counts, no duplicate IDs. It always emits estimated_power_percent=null, memory_power_model_ready=false and observed_real_swing_sample_count=0. It NEVER emits raw bytes, absolute RAM addresses, local paths, or caller free-text.

Data present during idle/aim is a NEGATIVE CONTROL even if a bit pattern resembles finite f32. The analysis cannot establish a distinct physical power response. Max non-atomic read span >12 frames is advisory for timing invalidity; it cannot support precise swing timing.

## Live S002 safety review and owner blockers

SOURCE CORRECTION: doldecomp/ogws RPSysScene.h says mCreatorSceneID at +0x40 is the PREVIOUS/PARENT scene, not the current scene. It can legitimately differ from current Golf scene ID 5; S002 PR #129 is correct to use it diagnostically and must NOT require creator ID==5. The remaining concern: initial RSPE01 revision + RPGolConfig mode4 gate should be checked again after operator prompts before every candidate memory read; please review and patch that with S002 ownership. S003 cannot mutate S002-owned live code.

The known source links are EGG::SceneManager current scene +0x0C and ID +0x18, RPSportsBaseScene sport +0x54, RPGolScene's RPGolMain* member +0x9C. Map symbol locations are not live instance pointers; RPGolScene+0x9C must NEVER be confused with golf_field+0x9C minimap effect pointer. Source-gated candidate search is not an established gameplay decoder.

## Result→action preregistration

| Result | S003 conclusion |
| --- | --- |
| No unique candidate / ambiguous static census | Stop. S002 source-investigates singleton, no gameplay power. |
| Previous/creator scene differs from Golf | Expected/possible: diagnostic only; do NOT reject because of that difference. |
| Unique gated candidate with zero relative word changes | Negative for sampled 0x100-byte window in idle/aim only; source-inspect inner gameplay member pointers offline. |
| Unique gated candidate with word changes | Camera/idle confounding, not power. Follow source data ownership and design true same-shot frame capture with negatives. |
| Slow non-atomic snapshot or no per-stage counts | No fast temporal effect can be inferred. |

## S002 / S001 / S000 / S003 responsibilities

S002 #129 source-validates pointer census and safe read of candidate game RAM; S001 owns one canonical fresh boot and exact controller/frame clock; S000 #126 must approve any new sanitized public kind before publication; S003 #123 prospective same-shot link stays blocked until real run/scene/frame provenance and ≥3 genuinely distinct objective power levels exist. The present S003 reviewer adds NO competing live interface; its prospective experimental preregistration is separate from historical study S003-MEM-01.

**Privacy:** only inspect S002 golfer-*-summary.json, never golfer-*-RAW-PRIVATE.jsonl. Locally generated review summaries are not automatically publishable. This contribution was code-authored in GitHub; full canonical Windows tests/Dolphin verification remain pending.