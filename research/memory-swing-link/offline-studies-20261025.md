# 2026-10-25 S001–S003 retrospective and offline stress-study results

Study owner: supporting S003 / [Issue #121](https://github.com/Nate27624/Wii-AI-Golf/issues/121) / [PR #123](https://github.com/Nate27624/Wii-AI-Golf/pull/123). **No live Dolphin or new game trials were performed.** Sources are previously published sanitized research/observations summaries, not private raw RAM. Generated test fixtures below are synthetic and are NOT Wii Sports performance results.

## Study A — repeated memory-change specificity (real sanitized cohort)

Predeclared question: do the repeatedly changed relative words implicate validated golf power/gameplay state rather than minimap visual effects?

Actual source: [cohort-20261025T025308Z-fbda2d0e.json](https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/cohort-20261025T025308Z-fbda2d0e.json), S002 `golf-memory-cohort-relative-words` report.

- **24** independently counted capture files; **84** distinct recurring changed region-relative 32-bit words (changed in 2+ captures); **16** words changed across all 24 captures.
- **78/84** recurring words are in `minimap_ball_effect` (23), `minimap_player_effect` (28), `minimap_shot_line_effect` (27). All **16/16** words shared by every capture belong to the minimap effect regions.
- Only **6/84** recurring changed words are outside minimap effects: `golf_config` +0xBC, +0xC0 (7 runs each), `golf_field` +0x44, +0x50 (7 each), +0x6C, +0x88 (5 each). The field +0x44 and +0x50 offsets are already source-documented map object pointers, not swing power.
- Only **7/24** capture files contain changed words in either `golf_config` or `golf_field`; all 24 have visual-effect changes.
- The recent single [offline S002 audit](https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/offline-20261025T024447Z-a37ee401.json) had **21 changed words, all rendering effects**, with **22 emulated frames per non-atomic snapshot**.

Finding: repeated difference is **not** a validated power/club/ball measurement. Repeated rendering changes are plausible UI/animation effects. Six other words are investigation candidates only; no causal frame anchors or power truth labels accompany this cohort. An apparently predictive feature must beat camera-only, A-only, idle and no-contact controls on the *same scene* before interpretation.

## Study B — observed power response identifiability (real sanitized human labels)

Audited five individual published V1 `kind=v1` records: `20261025T021350Z-5c73da554a`, `20261025T021501Z-ec585ddab4`, `20261025T022242Z-4154dea732`, `20261025T023456Z-15d1c97c12` and `20261025T023739Z-eb86e4661c` from the same public branch.

These records cover nominal speed 0.8, 0.9, 1.0 and backswing distance 0.8 or 1.0 (some settings were omitted in earlier records). **All five** are human-labeled contact=yes, approximate meter reading **75%**, off-green, displayed **100.0 ft** penalty, starting pose back, observed A-lead 45. Individual trials are not proven identical scene/reset conditions and the meter reading is not memory-verified.

Finding: the selected observations have **zero variation in the reported approximate meter reading** and zero physically measured carry. No continuous power regression, causal speed effect, controller-to-game gain estimate or game score validation is supported. Do not treat 100-ft penalty as carry distance or report 5/5 as a population contact-success rate.

## Study C — false positive from unsampled negative controls (synthetic offline)

The earlier S003 link checker could rank a zero-idle-change candidate even when the supplied memory report had **no counted idle/aim-only/A-only observations**. This creates a confounding false positive: zero changes when unobserved is not specificity.

Correction in PR #123:
- Require **at least two actual snapshots each** for idle, aim-only, A-only, club-motion and shot-attempt phases, before treating any phase as a control.
- Require matching per-phase emulation-frame brackets, chronological sampling and **negative-control brackets that end before the swing starts**.
- Require the observed trace-completion frame, not start + 89 requested waveform samples.
- Leave score/power/ball verification gates `false`, even for a perfectly linked synthetic pair.

Actual local execution: `PYTHONPATH=src python -m unittest discover -s tests -p test_research_memory_swing_link.py -v`, **27/27 pass**, Python 3.13.5, isolated source-equivalent worktree. These tests are synthetic only, not a clone of the full current repository. Complete canonical `python -m unittest discover -s tests -v` and Windows Dolphin validation remain **unrun**.

## Study D — adversarial pairing mutation stress (synthetic offline)

Deterministic random seed `1212026`. **256 synthetic pairs**, each derived from a good future-schema fixture, then exactly one of 14 provenance/time/control gates deliberately corrupted (scene, session, shot ID, waveform hash, start/end frame, revision, mode, read span, control coverage, missing sample brackets, process completion). Outcome: **0/256** invalid pairs accepted by the same-shot gate. There is no estimate here of real-world sensitivity, false-rejection rate, or actual physics: the stress set tests only known invalid combinations.

## Next experimental decision and stop rules

1. **S002**: first settle duplicate memory scanners (#109/#116/#120); use source-anchored gameplay-object rather than minimap-effect capture. A valid `RPGolScene.mGolMain` member at scene +0x9C is source documentation, NOT the live scene instance or a known power value. Keep all raw values local.
2. **S001**: examine current V1 A-command journal #112 and determine whether a same-session, frame-indexed trace-end and *actual bridge-dispatched* button sequence can be obtained without altering the successful motion profile.
3. **S002 + S001 + S000**: specify **one canonical** public-safe per-shot ID, sampled frame brackets and per-offset phase counts, with effect-size and read-latency checks. A late 22-frame snapshot must not be aligned to instantaneous impact. No automated live shots or unsanctioned RPC writes.
4. **S003**: only after above contract lands, preregister fixed-scene independent idle/camera/A-held/no-hit negative controls, repeated contact positives and a varied actual-power condition. Hold out independent fresh resets before judging predictivity.
5. **Stop** a study when field provenance is unknown, the scene/shot IDs mismatch, controller ACK is substituted for game input, snapshot span misses the event, or power still has no independently observed variation. Never fit a numeric power model to five identical 75% estimates or 100.0-ft penalty values.

Privacy: this note uses already-public sanitized totals, relative object offsets and human labels, no private game evidence, paths, pointers, ROMs or local bridge files. Do not merge PR #123 until S001/S002 review and the complete source checkout tests pass.
