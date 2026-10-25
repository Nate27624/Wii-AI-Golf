# S002 outcome comparison across independent scored shots

**Read-only/offline.** Compare two or more already collected sanitized outcome-...-candidates.json files to avoid treating graphical transforms/counters as game score. This tool never launches Dolphin, reads raw game RAM or uploads results. New live captures must still start Felk Dolphin through the canonical run_golf_experiment.py wrapper and its registered pre-start savestate/menu intro.

## First two user-observed runs (2026-10-24)

- First outcome: manual label **2.1 ft, green=yes**, swing trace dispatch **122 frames**.
- Second outcome: manual label **100 ft, green=no**, dispatch **89 frames**.
- Both summaries contain the same **45 memory addresses** and identical **before u32 values** at each address.
- At the settled stage, **16/45** memory words have identical raw u32 bit patterns even though the outcomes differ; **29/45** differ.
- Only **24 distinct two-run before/settled bit signatures** across all 45 addresses: seven identical-pattern groups contain four distinct starting addresses each. Such repeated patterns may be aliases or repeated model matrices, not independent outcome features.
- The two golf-config words 0x91BF176C and 0x91BF1770 transition 3→5 and 10→1 **identically in both shots**, so they cannot be a *direct, unchanged-unit* representation of the displayed 2.1 ft versus 100 ft. They may be game phases or counters; NOT confirmed.
- The minimap_ball_effect 0x91BF4AA8..0x91BF4AB8 values differ between outcomes; the first three settled f32 values have approximately **unit vector norms in BOTH runs**, suggesting an orientation/rotation hypothesis, not a verified ball location.
- **Major confound:** The swing traces were different lengths (122 versus 89 frames). The experimental program has changed as the integration agent introduced a separate A-button-only prehold, so outcomes cannot be attributed solely to landing variance and neither memory address has a causal/validated game-score interpretation.
- **Collector consistency fix:** The outcome collector now calls the same `prime_a_button` (60 button-only A requests) before the existing `build_probe("forward", follow_through_frames=30)` trace and always calls `release_buttons` afterward, matching the standalone successful S001 probe. It also records the exact waveform SHA256, generated frame count, and A-prime metadata. The previous two captures did NOT have this documented prime protocol; both remain exploratory and unchanged. The cross-run tool requires matching waveform hashes AND matching documented prime parameters before marking full controller programs comparable.

## Regression control: controller priming is not yet a proven improvement

The S002 collector temporarily adopted the S001 integrator's **60 separate button-only A requests** before the trace. A user subsequently reported no ball strike from that updated collector. The earlier **2.1 ft GREEN** and **100 ft MISS** reports both involved visibly successful strikes without this additional priming. We therefore restored **no separate A prime** as the S002 default. Opt-in `--a-prime-requests 60` is diagnostic and MUST be treated as a distinct controller program, not a harmless startup convention. This does **not** change the swing waveform, canonical fresh Dolphin intro, or independently evolving local swing-bridge V2; any V2 change remains a separate possible confound.

## Usage on existing local summaries

~~~powershell
cd "D:\Projects\Wii Golf AI\Wii-AI-Golf"
git pull --ff-only

py scripts/compare_outcome_runs.py --input "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\outcome-FIRST-candidates.json" "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\outcome-SECOND-candidates.json" --out "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures\comparison-FIRST-SECOND.json"
~~~

Use the actual two filenames; FIRST/SECOND here are placeholders. The tool validates the 32-bit word addresses and includes no raw memory contents or GUI images. Output file uses exclusive create, refusing overwrite. Supplying N summaries compares intersection of observed candidate address sets (not missing/unpublished words), and groups identical bit patterns to prevent overcounting.

~~~powershell
py -m unittest discover -s tests -p "test_outcome_compare.py" -v
py -I scripts/compare_outcome_runs.py --help
~~~

Eight focused mock tests are provided but have NOT been executed on the user's Windows checkout by this connector-only agent. The algorithm's important safety rule is simple: a different final RAM word is only a *candidate* for further inspection, never proof of official score.

## What to do before training

Collect *repeated same-waveform* shots using a confirmed first-shot setup and exactly one fully recorded waveform per run. Confirm same savestate, pin/tee scene and controller phase. Preserve human observation labels and their displayed units. Record a waveform fingerprint (sha256) **and button-only A prime request count**, because 89 samples alone doesn't establish that two controller programs were identical. Add no speculative score calculations or forced zero rewards for misses. Independently confirm a candidate's numeric relationship with distance/score on at least one held-out scenario. If the game displays 100 ft as a limit/sentinel or a different metric, verify that visually.

This comparison work is independent of S002 evaluation PR #14. [Issue #3](https://github.com/Nate27624/Wii-AI-Golf/issues/3).
