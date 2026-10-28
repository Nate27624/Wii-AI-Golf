# S001 P0: one-factor V1 NO-A pretrace comparison (review only)

## Why the control is needed

One real watched V1 attempt was recorded by the operator with a visible nearly successful club swing but **no actual contact or ball movement**. The controller/bridge execution was complete: 25 idle advancing bridge ticks (24 minimum), exactly ONE separate A button request followed by 45 observed ticks, original 89/89 V1 waveform SHA256 `b63a1818ba5086c64b0fe7338236a498240e4be97bbd111809a772d783699891`, 70/70 source-selected 51-word observations at max 64us, no candidate ball movement. That input series is a preserved no-contact negative control and MUST NOT be edited.

Historical human-observed 2.1ft on-green and 100ft off-green shots in `docs/outcome-transition-protocol.md` and `docs/outcome-cross-run-comparison.md` did **not** add separate A button pre-prime. They were taken under other imperfectly controlled conditions and do NOT prove that A preholding caused the new miss.

## The one variable changed

Opt-in CLI `--pretrace-mode neutral-45` replaces the 45-observed-bridge-tick **A-requested** pretrace window with a same-duration **NO new A request** control. The 24-tick idle negative control, watcher arm 280 ticks / interval 4, selected-record source checks, source-pinned V1 bridge, checkpoint/menu input program, 89-frame original waveform and trace fingerprint remain unchanged. **This is a comparison of requested input; there is no game-side A latch readback.**

Old default `--pretrace-mode hold-a-45` remains unchanged. Bridge watcher stage name `a_prime` stays intact because altering that generated V1 source would invalidate its SHA; for the neutral control, the **collector and analyzer explicitly label this legacy stage as no-A neutral pretrace** in the private and sanitized reports. The analyzer sets `a_only_stable_and_equal_to_idle=null` for no-A pretrace rather than pretending A was pressed.

One no-A trial is only a hypothesis test; not an automatic hit fix, verified physics or training approval. Do not tune amplitude, speed, follow-through or starting pose concurrently.

## Exact bounded fresh-boot action

1. S001 input owner, S002 source/memory owner and S000 privacy owner review this stacked DRAFT PR (#222) and document live-shot authorization. Review focused Windows/Linux tests and preserved legacy 89-frame SHA.
2. Close Dolphin before the next full experiment. Use the isolated review worktree, not the main repo. Run full canonical `scripts/run_golf_experiment.py --send-live` with trusted `--dolphin`, `--dolphin-user`, `--bridge`, saved `--config` and `--catalog`, and `--script record_selected_ball_swing_v1_private.py -- --pretrace-mode neutral-45 --send-live-swing`.
3. Visually verify first stationary ball before typing `SWING`. Do NOT send any second shot automatically.
4. Record separate operator-visible contact and ball movement `yes/no/unknown`. Private `selected-ball-frame-watch-v1-*-PRIVATE.json` stays solely in sibling ignored Data. Review `pretrace_control_mode=neutral-45`, `pretrace_control_A_requested=false`, `pretrace_control_A_requests=0`, `pretrace_control_observed_frames>=45`, `a_lead_observed_frames=0`, `watch_complete=true`, `trace_sha256` unchanged, stable source & read cap.
5. Analyze privately with existing `scripts/analyze_selected_player_swing_words_private.py --private-report <exact-file>`; compare against the frozen 45-A no-contact control, then decide if source-relative candidate changes are merely generic swing animation or correlate with real independently observed contact.

## Stop rules

- Wrong bridge SHA, game source, player/ball pointer identity, incomplete 70 sample watcher, >5000us per-sample, fewer than 45 advancing neutral ticks, unexpected A request, wrong trace SHA, incomplete 89-frame trace: stop and do NOT mark shot as successful.
- No visible contact/movement: keep as another labeled negative; do not infer score or physical coordinates.
- If contact occurs: record operator observation and seek independent memory/object-source validation; not a training authorization.
- Never upload private RAM words, pointers, ROM images, UI photos or savestates.

**See also:** draft [#215](https://github.com/Nate27624/Wii-AI-Golf/pull/215) for real stationary watcher pass, [#220](https://github.com/Nate27624/Wii-AI-Golf/pull/220) for preserved near-contact baseline and Qt GUI recovery.
