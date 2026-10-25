# Hitting the Green: observation validity audit (2026-10-24)

This audit distinguishes **verified data transport/consistency** from **unverified game semantics**. It does not establish successful ball tracking or automatic scoring.

## Evidence

- [Broad motion](https://github.com/Nate27624/Wii-AI-Golf/blob/data/hitting-green-20261024T231251Z-f7f6507e/research/results/hitting-green/20261024T231251Z-f7f6507e.json): 50 snapshots, 25 deduplicated candidate vectors. Leading movement often represented minimap/scene rotations, **not verified ball motion**.
- [Targeted minimap effect](https://github.com/Nate27624/Wii-AI-Golf/blob/data/hitting-green-20261024T231935Z-dab0bca3/research/results/hitting-green/20261024T231935Z-dab0bca3.json): 124 samples, 4 frame span, nine moving triplets, each with only two transitions; largely duplicated placement transforms.
- [One-hop pointer census](https://github.com/Nate27624/Wii-AI-Golf/blob/data/hitting-green-20261024T232725Z-b034328d/research/results/hitting-green/20261024T232725Z-b034328d.json): 125 snapshots, 17 frame read spans. The field-manager +0x04 pointer yielded dynamic object at 0x92583488, XYZ +0x50 (0x925834D8), 62 moving steps (overlapping candidate triplets are **not** independent observations).
- [Uncontrolled swing](https://github.com/Nate27624/Wii-AI-Golf/blob/data/hitting-green-20261024T234942Z-118c5542/research/results/hitting-green/20261024T234942Z-118c5542.json): 304 snapshots; 286 valid XYZ observations; 18 absent; 86 changing steps; maximum adjacent-sample displacement 176.3398. **An old summary bug incorrectly reported zero present; actual 286 XYZ rows are valid.** Menu/tee transition timing was not independently marked.
- [Menu-advanced idle label](https://github.com/Nate27624/Wii-AI-Golf/blob/data/hitting-green-20261024T235342Z-a4638d6c/research/results/hitting-green/20261024T235342Z-a4638d6c.json): 183 snapshots, 171 valid XYZ, 12 absent, five moving steps, maximum adjacent displacement 0.9548. Operator pressed A and progressed scene setup. **Not a controlled idle measurement** despite phase label.
- [Manual-ready quiet control](https://github.com/Nate27624/Wii-AI-Golf/blob/data/hitting-green-20261024T235737Z-90460728/research/results/hitting-green/20261024T235737Z-90460728.json): 180/180 valid XYZ, 0 absent, 0 steps >=0.1 units, frame span 4. First [-4.811729,-0.544240,-324.531769] and last [-4.811733,-0.544260,-324.531769]. Demonstrates reproducible stability **once golfer is ready**, not ball identity.

## Validity and availability by signal

| Signal | Can collect today? | Confidence in measured bytes / event | Confidence in *semantic meaning* | Notes |
|---|---|---|---|---|
| Dolphin emulated frame counter + read bracket | Yes | High (bridge and recorded spans) | High for frame sequencing, not instantaneous state | 3–4 frame spans for narrow reads; not frame-perfect physics |
| Wii Sports disc ID / revision / game mode | Yes | High when source gate passes | Moderate-high for mode = Hitting the Green | Mode activation may precede golfer-ready scene |
| Game memory pointers, zero/present indicator | Yes | High within validated address bounds | Medium for object lifecycle; low for ball identity | One-hop field +0x04 sometimes null during transitions |
| Candidate XYZ float triplet | Yes | High that three numbers are read consistently | **Low-to-moderate** for actual ball coordinates | Quiet control stable and swing moving; still could be camera/player/follow target |
| XYZ change count, first-last, displacement | Yes | High *as metrics of sampled candidate* | Low-to-moderate as ball flight metrics | Velocity, path length and launch mechanics not validated; peak step may be teleport/camera shift |
| Timing of actual physical swing/contact | Not automatically confirmed | Low | Low | Operator-reported only; need synchronized phase stamps or bridge/game event |
| Actual ball launch/flight/bounce/landing | Not yet confirmed | Low | Low | Requires visual synchronization and candidate-vs-camera discrimination |
| Stroke power, shot direction/spin | Partially controllable, not reliably decoded | Low | Low | Bridge can drive scripted strokes in emulated mode; physical controller path has no verified telemetry |
| Green outcome / official score / shot count | Exploratory memory candidates only | Low | Low | Prior outcome census had 45 persistent RAM changes but no independently verified official score |

**Interpretation:** The data acquisition mechanism is reliable, and the XYZ signal is repeatable under a quiet control. The claim that XYZ +0x50 is the actual ball remains **unproven**. These confidence categories reflect the present evidence, not calibrated probabilities.

## Next controlled test

Use a **fresh** physical Dolphin session, `--manual-ready --phase swing`, and **press Enter only once the golfer is fully at the first tee**. Swing during the 25s capture, allow the ball to finish, record the visible landing/result. Then compare with the 180-sample quiet control. Never infer ball physics from a first-vs-last displacement alone. To distinguish ball from camera, add an independent aim/camera-only control with no shot and align to visible frames or game event markers.

**Data handling:** Only publish numerical summary. Raw hex/individual time-series remains on user's Windows machine under `captures/`; do not upload them. No verified scoring labels are available for supervised training yet.
