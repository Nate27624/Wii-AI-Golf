# S001 + S002 + S003: link memory changes to golf swing timing

Issue #121. Research-only, **offline** proposal, 2026-10-25 UTC. No Dolphin operation, no ROM/savestate, no private RAM, no automatic score or club-power decoder.

## Repository situation

- S001 [PR #112](https://github.com/Nate27624/Wii-AI-Golf/pull/112) records OUTGOING button requests and trace status. It does **not** prove game-recognized A hold or per-frame applied controller state.
- S002 [PR #116](https://github.com/Nate27624/Wii-AI-Golf/pull/116) records phase-labeled non-atomic RAM windows and publicly summarizes relative-offset changes. Its current summary aggregates per-offset changes across phases and lacks a same-shot V1 ID and stage-specific frame brackets. S002 [PR #109](https://github.com/Nate27624/Wii-AI-Golf/pull/109) and [PR #120](https://github.com/Nate27624/Wii-AI-Golf/pull/120) additionally rank source-anchored windows; S002 should decide which of the overlapping analyzers becomes canonical.
- S003 [PR #119](https://github.com/Nate27624/Wii-AI-Golf/pull/119) analyzes 10-shot human power observations. The off-green 100.0-ft display is a **penalty**, not physical carry. Human ~75% meter observations are approximate.

**The present experiments cannot be joined as one shot.** Matching bridge hashes, trace lengths or timestamps are insufficient; RAM sampling across several RPC calls can miss the 89-frame swing transient.

## Delivered independent module

Pure Python function `wii_ai_golf.research_memory_swing_link.assess_memory_swing_link(memory, swing)` accepts already SANITIZED in-memory S002 phase summaries and S001/S002 public V1 shot summaries. It requires *mutual* shot IDs, exact boot session/scene/waveform/bridge equality, revision/mode checks, frame-start anchor, sample non-atomic span and motion-window overlap before ranking any relative offset. It demotes camera/idle/A-hold-sensitive, pointer, score and minimap rendering effects. Reports blockers without echoing RAM, private names or numerical human-distance values. All results remain **exploratory**; `game_power_calibrated=False`, never a game score.

### Proposed future fields (not published or merged today)

This is a suggestion to owners, NOT a unilateral public schema change:

| Canonical owner | Proposed fields | Meaning |
| --- | --- | --- |
| S001/S002 V1 | reciprocal `linkage.memory_id`, `session_id`, `scene_fingerprint`, bridge/trace SHA, `shot_start_frame` | Same-run association, NOT A accepted or physical contact |
| S002 memory | reciprocal `linkage.swing_id`, same session/scene/bridge/trace/start, `game_id`, `disc_revision`, `game_mode_raw`, `phase_frame_brackets` | Validated scene and *bounded non-atomic* snapshots |
| S002 per-offset rank | `phase_change_counts` keyed by `idle`, `aim_only`, `a_hold`, `club_motion`, `shot_attempt`, `settled` | Sanitized relative changes only; no absolute addresses or raw values |
| S001 optional private A log | emulator-frame dispatch events ONLY if actually instrumented | Client-issued requests are not evidence of game input |

Do not derive scene identity from a global frame count alone. Use an opaque per-boot ID, grounded checkpoint/shot metadata, and owner-reviewed allowlisting. Never publish RAW-PRIVATE captures or A-command raw logs.

## Concrete next experiment: discriminate power from UI changes

1. Under the existing one-shot consented canonical fresh Dolphin startup, preserve the known V1 45 observed A-lead and original 89-frame waveform. Record shot-start frame, scene, bridge SHA, contact and starting pose. Include misses and incomplete attempts.
2. S002 should target valid source-backed **gameplay** object pointers (documented `RPGolScene` -> `RPGolMain` candidate) rather than the minimap visual effect. Validate live scene instance and pointer chain first; never guess/dereference unsupported absolute addresses.
3. In the **same emulator session**, bracket limited read-only RAM samples around the event. Use negative controls **idle**, **aim/camera only**, **A-held/no swing**, **motion/no observed ball contact**, versus independent contact-positive repeats. Detect per-offset phase specificity. Discard values that change equally in idle/aim, animation or mode transitions.
4. If the current external 9KB snapshots span too many emulated frames, **stop**. Ask S001 whether an approved bounded, in-bridge, read-only sampling scheduler can capture a few validated words at predefined frame intervals while executing its current swing. Do not attach a second live launcher, alter A timing or inject additional motions without shared owner and operator consent.
5. Correlate only across verified same-scene repetitions with differing independently measured or visibly differentiated power. The 100-ft off-green penalty is not continuous distance. Freeze held-out repetitions and no-contact negative cases before optimizing.

**No live test authorized by this document.**

## Validation and ownership

Command used in an isolated source-only runtime:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p test_research_memory_swing_link.py -v
```

**18/18 synthetic tests passed locally.** Python compile check also passed. No Windows/Felk test and **no full canonical checkout suite** were run because this environment cannot retrieve a checkout by git; do NOT self-merge until full test suite and S001/S002/S000 owner acknowledgment.

Ownership and next steps: S001 owns command/frame instrumentation; S002 owns memory capture, score/power provenance and sanitized publication; S003 owns power hypothesis testing; S000 owns shared CLI/public schemas. This PR edits only independent S003 research files. Next owner: S001 + S002 agree exact per-shot linkage and fast read feasibility on GitHub, S003 designs balanced contacts/misses and response sensitivity afterward.
