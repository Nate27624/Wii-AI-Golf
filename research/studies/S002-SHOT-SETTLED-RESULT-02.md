# S002-SHOT-SETTLED-RESULT-02 — optional post-hit follow-up

**Draft / research only. No Dolphin action, shot, save/load, capture,
memory write, public data upload or model training authorized.**

## Motivation

PR #180's **PRE** and **POST** capture answers a narrowly scoped
question: did the source-selected ball translation change between
a stationary ready-to-hit ball and a visually observed displaced ball?
It doesn't identify landing/settled state or the **result-screen
distance to the hole** that the operator wants to capture eventually.

The target state has THREE DIFFERENT post-impact concepts:

| Phase | Operator-visible condition | Memory semantics |
| --- | --- | --- |
| `POST` (#180) | One shot has visibly displaced the ball before reset | Source-selected ball/record/start, required canonical comparator |
| `SETTLED` (optional new) | Ball visibly **stopped** and has not reset or advanced to new hole | Same source-selected active ball/record/start and selected pin must persist, else ABSTAIN |
| `RESULT` (optional new) | Results screen visibly displays the outcome / distance | Save full native banks and an operator-read UI value, **do not reuse moving-ball pointer assumptions** |

A single actual shot may not afford enough time for the operator to
capture both moving and settled phases. We do NOT require SETTLED and
RESULT to exist. Failed/not-captured phases remain absent, not invented.

## Additive, source-gated data plan

File `scripts/audit_golf_postshot_followup_private.py` is stacked on
#180, leaving the original PRE/POST manifest and comparator untouched.

1. Requires #180's original four preserved, SHA-verified banks and
   `shot-checkpoint-manifest-PRIVATE.json`. Re-runs the original
   `prepost.run_local()` source gates, checks and output flags.
2. Takes a separate **optional** `shot-followup-manifest-PRIVATE.json`
   with `schema_version=1`, kind
   `local-private-golf-shot-followup`, operator attestation that the
   same live Dolphin process and one shot were used, and a `checkpoints`
   object with `SETTLED` and/or `RESULT`. Each present checkpoint
   requires 24MiB MEM1, 64MiB MEM2 and 64-char SHA256 entries in a
   private manifest, plus the operator's same-GUI-pause attestation.
3. For `SETTLED` only, reads selected actor source-backed nested ball
   translation, player record translation and START, and uses the
   FieldManager selected pin getter `field+0x44 -> pin_obj+0x4C` to
   locate the three-word **candidate pin**. Requires stable owner,
   selected slot, hole, start and pin across PRE/POST/SETTLED.
4. Reports only a **categorical** comparison of candidate
   first/third-component squared separation between selected ball and
   selected pin: `closer_candidate`, `farther_candidate`,
   `indistinguishable_candidate` or `unavailable`. The first/third
   components are a *hypothetical plane*, not verified physical XZ,
   yards, feet or the final shot distance. No raw coordinate value
   or ratio is released. A motion-to-RESET state invalidates this
   comparison.
5. For `RESULT`, validates and preserves the two native banks.
   It records only whether the bank contents differ from POST and
   whether a HUMAN reported a displayed numeric distance. It **never**
   asserts that the selected actor/ball exists at this phase, as the
   game may already have reset it.
6. Optional `human_displayed_result_distance` stores only **in the
   ignored local private manifest**, e.g. `{"value":12.5,"unit":"feet"}`
   if the UI *actually* displayed that exact number and unit. Allowed
   units: `feet`, `yards`, `meters`. No guessed or automatically
   converted number. Console outputs only a boolean and the human unit,
   not the private numerical distance. Subsequent calibration needs
   multiple independent visually verified shots and source-unit proof.

The `RESULT` source fields are NOT parsed as a ball position or score.
The eventual memory outcome decoder and a calibrated game-unit-to-UI
conversion are explicitly open research problems.

## Private file layout (same session; do not overwrite prior files)

```text
Wii-AI-Golf-Data/captures/SHOT-<private-id>-PRIVATE/
  PRE-MEM1.bin; PRE-MEM2.bin            # canonical #180
  POST-MEM1.bin; POST-MEM2.bin          # canonical #180
  shot-checkpoint-manifest-PRIVATE.json
  SETTLED-MEM1.bin; SETTLED-MEM2.bin    # optional, before reset
  RESULT-MEM1.bin; RESULT-MEM2.bin      # optional, after result shown
  shot-followup-manifest-PRIVATE.json  # separate human annotations/hashes
```

Only after explicit S001/S002/S000 review and operator approval, the
existing `preserve_golf_paused_pair_private.ps1` may be extended or a
separately owner-reviewed helper may be written for these two optional
new phase labels. It presently accepts PRE/POST ONLY. Do not manually
mislabel a RESULT bank as POST or claim that the game remains in mode4
at the results screen.

**No copy/paste live shot command is released here.** The operator must
see the actual screen and intentionally decide when to pause/export.
Do not invoke `--attach-running --send-live` as a passive status check:
that code loads a savestate and sends inputs. If the UI resets before a
valid SETTLED capture, simply omit SETTLED. If numeric results are not
visible, do not fabricate them.

## Private manifest example (illustrative ONLY)

```json
{
  "kind": "local-private-golf-shot-followup",
  "schema_version": 1,
  "operator_reports_same_dolphin_process": true,
  "operator_reports_same_one_shot": true,
  "checkpoints": {
    "SETTLED": {
      "phase_operator_label": "settled_before_reset",
      "operator_reports_gui_paused": true,
      "operator_reports_both_exports_same_pause": true,
      "operator_reports_ball_visibly_stopped": true,
      "operator_reports_no_hole_or_reset_transition": true,
      "sha256": {"MEM1": "<locally computed SHA256>",
                 "MEM2": "<locally computed SHA256>"}
    },
    "RESULT": {
      "phase_operator_label": "visible_results_screen",
      "operator_reports_gui_paused": true,
      "operator_reports_both_exports_same_pause": true,
      "operator_reports_result_screen_visible": true,
      "sha256": {"MEM1": "<locally computed SHA256>",
                 "MEM2": "<locally computed SHA256>"}
    }
  },
  "human_displayed_result_distance": {
    "value": 12.5,
    "unit": "feet"
  }
}
```

Do not paste this example as real evidence. Only attest what happened.
The human distance object may be `null` if the UI did not show a
numeric distance. Omit a phase entirely if no true paused-pair capture
exists. The script verifies all hashes and native sizes before reading,
and reports `approved_for_model_training=false`,
`physical_distance_to_hole_verified=false` regardless of outcome.

## Offline runner after captured files and approval

```powershell
# Use a reviewed branch checked out into a separate worktree and
# the exact pre-existing, ignored PRIVATE shot session directory.
py scripts/audit_golf_postshot_followup_private.py `
  --private-root "<exact ignored local shot session folder>"
if ($LASTEXITCODE -ne 0) { throw "Post-shot audit failed closed" }
```

No Dolphin commands, no automatic screenshot/OCR, no bare result
number or game addresses printed. S000 must review any proposed
publication of even sanitized JSON; raw native banks stay local.
