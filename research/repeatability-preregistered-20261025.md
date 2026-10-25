# S000/S001/S002: evidence-gated Wii Golf repeatability study

Date: 2026-10-25 UTC. **Preregistered future experiments; no automatic live runs authorized.**

## Audited already-public observations

Source: https://github.com/Nate27624/Wii-AI-Golf/tree/research/observations/research/observations

- `20261025T014552Z-db2d3d790b`: one human-labeled historical V1 attempt. Bridge SHA `fe04cb0ba312c559d5cb7edb8d0ac2185aca72046839a903160929ee7c58ca19`, original 89-frame waveform SHA `b63a1818ba5086c64b0fe7338236a498240e4be97bbd111809a772d783699891`, observed A-lead **45 emulated frames**, visually reported initial club pose **back**, **ball hit yes**, not on green, **game displayed 100.0 ft**. The displayed distance is NOT validated ball travel, physics XYZ or score.
- `20261025T015004Z-17e136d09e`: an additional matched 45-frame V1 human-labeled attempt, **contact yes**, **100.0 ft**, **not green**, pose **back**, same historical V1 bridge SHA and original 89-sample trace SHA. It started from a different Dolphin frame count. Thus there are **2/2 completed human-labeled contacts for this one configuration**; no score, power or distance is game-memory verified.
- `20261025T013459Z-b6de90e7b2`: 0 A-lead, exit 0, **no unambiguous collector summary**, so contact is **UNKNOWN**, not a miss and not a paired controlled observation. `20261025T012919Z-65b1289dfa` exited 1, also no outcome.
- `20261025T014015Z-idle-automated-minimap`: 5 pre/20 post, NO swing/button RPC, **zero** adjacent changes across 128-byte visual-effect snapshot.
- `20261025T020222Z-idle-automated-minimap`: another separately published idle trial, also **zero** changes. Thus idle n=2 and swing n=1, not yet enough to identify physics.
- `20261025T014057Z-swing-automated-minimap`: 5 pre/20 post, swing dispatch reported, **one** adjacent change at offsets **123,126,127**. This is minimap VISUAL effect memory, not verified physics ball state.
- Earlier full regression suites failed; the later `20261025T013445Z-0493c7f688` full suite passed. A unit-test pass does not establish an actual golf hit.

**None of the results proves** that lead 45 outperforms lead 0, V1 beats V2 under identical input, the displayed 100 ft is flight distance, changed effect bytes are ball XYZ, or input-motion scale equals on-screen power. Minimap conditions currently n=1 each.

## Next operator-approved experiments (individual fresh boots, never unattended)

### R1: Fixed successful V1 control — first priority

**Hypothesis:** Same V1 bridge + original waveform + 45 observed A frames + starting pose back can repeatedly produce human-visible contact.

Collect **one additional individually consented** attempt at **45 observed A-lead frames**, to bring the matched-condition sample count to 3 including the **two** existing published trials, ONLY if historical bridge SHA, waveform trace SHA, exact scenario/starting pose, menu sequence and checkpoint match.

Fix: original 89 generated samples; 30-frame follow-through; no separate request-count A primer; no motion-scale change; existing green-pre-start named savestate and canonical A/A+B/A intro. The operator visually records initial pose, tee/pin, ball contact yes/no/unknown, on-green yes/no/unknown, displayed value **and unit**, and power gauge only if shown. Save all no-hits, timeouts and partial captures. A process exit 0 or bridge ACK without a human label does NOT count as a hit.

**Stop if** Dolphin/bridge fails, scene differs, starting club pose changes materially, trace SHA changes, or the collection cannot save evidence. Three matched labeled trials only justify an exploratory replication claim, never calibrated power or a reliable hit-rate assertion.

### R2: Matched 0-frame A lead — second priority

After R1, collect **three** consented 0-lead trials, holding same exact V1 bridge, waveform SHA, savestate, initial pose, menu timing and motion amplitude. Outcome: human-visible contact, with explicit unknown/missing count. The existing 0-lead process-exit-zero record lacking a collector summary is NOT a no-hit.

Do not vary lead and motion scale, bridge version, or checkpoint in one study. No causal superiority claim on small samples.

### R3: Replicate minimap effect with genuine no-swing controls

Get **one more independent idle and two more swing** studies (target n=3 each), maintaining 5 pre/20 post reads, same view, interval and matching scenario. Idle does not send any button/motion RPC after game intro. Record pointer and frame-span consistency PRIVATELY. Effects at 123/126/127 are unverified visual-effect data. Reject "ball position" until separate human contact/no-contact, camera-only, and idle controls disagree with animation-only explanations.

### R4: Scale swing motion AFTER R1 repeatability is established

- `20261025T020329Z--baseline`: S002 single-variable power-study `baseline`, 89-frame trace SHA `b63a...`, controller ACK present, human reported **contact=no**, power unavailable. **Crucial confound:** public record has NO bridge SHA, NO starting club pose and NO observed A-lead frames. This cannot be used as a matched V1 45-frame negative control; it is a distinct protocol awaiting provenance validation.

Merged S002 PR #92 **supersedes treating simultaneously scaled speed/distance/return-speed as physical power**. Its separate, canonical postboot `trial_swing_power.py` study exposes one-variable, explicitly labeled input variants `baseline`, `shorter`, `slower`, `faster`, `longer-backswing` and requests human-observed gauge power/contact; the starting-pose field is being reviewed in PR #96. These are candidate controller-input modifications, NOT calibrated game power or club angle.

Do not start variant sweeps until R1 is matched/repeated and S002/S003 certify identical bridge/start-pose/trace provenance and publication allowlists. The first future variant must be **baseline**, one separately approved full startup and annotated shot, then pause for analysis. Never upload RAW-PRIVATE RAM or invent power values to fill missing labels.

## Canonical read-only research review

After merging the S000 evidence reviewer, run:

```powershell
py scripts/research_cli.py review
```

It safely syncs trusted main, clones ONLY the approved public `research/observations` branch into a temporary folder, and prints counts grouped by **bridge SHA + trace SHA + observed A-lead**. It reports incomplete/failed V1 trials, test execution status, idle/swing condition effects and whether replication gates are met. It does NOT execute downloaded observation code, start Dolphin, infer any official game score, or upload results.

Ownership: S000 public evidence synthesis/CLI; S001 bridge/waveform/run preconditions; S002 outcome capture/human labels and minimap interpretation; S003 modeling after matched repeatability. Respect SPOCOC Single Point of Control Over Change.
