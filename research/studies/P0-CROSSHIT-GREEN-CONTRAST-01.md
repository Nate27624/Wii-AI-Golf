# P0 CROSSHIT-GREEN-CONTRAST-01 — Compare the original 11 positive-hit captures by original human label

**Research owner:** S000 #205 (cross-run stratifier), S002 #199 (strict single-shot source audit). This contribution is an additive, offline PowerShell wrapper + CI, **stacked** on S000 #205 and changing none of its existing files.

## Research baseline

The operator already ran the S002 #199 reader over ELEVEN human-contact-positive raw/summary private capture pairs, with **11/11 validated, 0 rejected**. Persistent candidate counts per run: **8, 13, 13, 19, 45, 13, 9, 13, 45, 45, 45**. Every source snapshot spans up to 22 guest frames; the capture is **not frame-atomic**. Prior recurrence already identified 13 canonical alias signatures present in 10/11 shots. Many are minimap/effect memory aliases; golf_field offsets +0x44/+0x50 and golf_config +0xBC/+0xC0 are other untyped candidates.

Crucial unresolved ambiguity: S002 #199 reports human_green_yes=false for both original human NO and UNKNOWN, so do NOT claim all ten non-YES were confirmed off-green. S000 #205 now has the existing source-validated Python analyzer scripts/contrast_p0_hit_signatures_private.py, which stratifies original human_green labels into YES, NO and UNKNOWN. Its synthetic CI was already green; its real stratification has not yet been reported. One human YES is insufficient to prove outcome specificity.

## What this separate wrapper actually does

The new scripts/Invoke-P0CrossHitGreenContrast.ps1:

- Confirms it is derived from the reviewed S000 #205 base and runs the existing 12 source stratifier tests BEFORE inspecting private captures.
- Requires a separate clean S002 #199 reader worktree pinned to commit **4f9deea39be8511f1b68907164623d98bdb2f3dc**, at the same parent as the ignored Wii-AI-Golf-Data folder. This prevents using an unrelated or modified per-shot validator.
- Calls the EXISTING #205 cross-hit code with that EXISTING #199 auditor to validate each private paired shot. It refuses mismatched 11-pair counts, wrong sorted candidate counts, incomplete signature output or unsupported training/physics claims. The YES/NO/UNKNOWN counts must add to 11.
- Saves only an allowlisted, source-relative aggregated JSON inside ignored captures as p0-human-green-outcome-11hit-contrast-SANITIZED.json, never overwriting an existing different file. Prints only capped signature support counts, pointer-shape and rendering-only warnings (not raw numeric memory, file names, runtime heap pointers or per-shot IDs). No GitHub auto-upload.
- Never runs Dolphin, a bridge, controller, savestate, capture or memory write.

## Interpretation and owner decision

A recurring source-relative alias proves **recurrent sampled field change**, not movement, velocity, height, distance, score, or owner/allocation identity. A few GREEN YES observations are not a basis for discriminative probability claims without more confirmed independent outcomes and no-contact/no-hit controls. This run will tell us which candidate signatures vary between true literal NO and unknown outcomes and which are mostly effect/pointer lifecycle confounds.

S002 should then prioritize source-selected ball object translation pointer +0x4C to +0x30, with record +0x54/+0x60 and caches +0xCC/+0xF0/+0xFC in a reproducible same-shot source/trace watch, but **ONLY after** the documented S001 native Dolphin Qt6Widgets crash is addressed and the live owner allows a shot. No new live trial is part of this study.

## Integration gates

S000 #205 owns the registry and stratifier. S002 #199 owns per-pair source validation. S001 owns live Dolphin, startup and controller. This wrapper edits none of their files and is **stacked draft**, not main. Hosted Windows/Ubuntu CI runs only existing stratifier synthetic tests, PowerShell syntax and a safe TestsOnly mode. It is not a real 11-pair execution. Raw private JSON/ROM/RAM remain solely in the local ignored data directory.

Automatic research/observations publication for this special study is **NOT IMPLEMENTED**; successful human-run output will be recorded by an owner-reviewed sanitized GitHub FINDING comment only, never as a fabricated successful publisher action.
