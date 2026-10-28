# S001 reference: near-contact V1 input baseline, NO ball strike (2026-10-28)

**Evidence type:** Actual Windows operator run, successfully completed RPC trace and selected-player source watcher; operator visual outcome **NO CONTACT / NO MOVEMENT**. The operator described the swing as **"almost worked"** and requested preserving this exact input set for later memory analysis. This is a valuable *near-contact / no-contact negative control*, **NOT a positive-hit record, game score or verified ball XYZ**.

**Do not discard or tune this baseline.** Reuse the frozen input schedule, player-record phase alignment, and private local recording as a comparison for any later successful V1 contact. Do not copy untyped RAM words or raw private capture data into GitHub, issues, logs or training.

## Exact action provenance / input schedule

| Component | Preserved value / qualification |
| --- | --- |
| Platform | `D:\Projects\Wii Golf AI\tools\FelkDolphin-Clean\Dolphin.exe`, portable `User` retained after Qt GUI reset |
| Game scenario | RSPE01 Wii Sports Rev1, **Hitting the Green**, `green-pre-start` named checkpoint, slot **2** |
| Wii Remote | Emulated Wii Remote **1**, Extension `None`, remote index **0** |
| Scripted controller bridge | Historical **Swing V1**, not V2; separately generated watched bridge `tools/mcp_bridge_swing_legacy_watch_eval.py`; SHA-256 **`465b6b02a9ae3833c65233b0d7a26fca79c613330eedf4eeb1de2a5d89ff886b`** |
| Canonical launch route | `scripts/run_golf_experiment.py --send-live --script record_selected_ball_swing_v1_private.py -- --send-live-swing`, with explicit `--dolphin`, `--dolphin-user`, `--bridge`, `--config`, `--catalog` from existing private local paths |
| Checkpoint/menu sequence | **State settle 120** neutral; **first A 30**; **wait 315** neutral; **A+B 60**; **release 135** neutral; **final A 45**; **game transition 300** neutral. These are **requested menu input frames**, not proved guest-game-applied frame counts. |
| Operator authorization | At visibly first stationary ball, typed `SWING` exactly once; no unapproved automation |
| Watcher | Arm for **280 bridge ticks**, interval **4**, complete **70** source-selected samples, **51 u32 words** per selected player record |
| Idle negative control | **24** requested bridge ticks, **25** actually observed before A lead; private watch sampled **7** idle-control rows |
| Pre-swing A prime | Exactly **one** A-button-only RPC and **45 observed advancing bridge frames** (not 45 RPC calls); **12** A-prime watched samples |
| Frozen forward trace | **89** original source-defined samples: **12 neutral A / 15 backswing / 20 forward / 30 follow-through / 12 A-release**; trace sample digest SHA-256 **`b63a1818ba5086c64b0fe7338236a498240e4be97bbd111809a772d783699891`** |
| Trace result | `state=complete`, `total_frames=89`, `applied_frames=89`, stable non-null trace ID. This means dispatch complete, **not** ball contact. |
| Posttrace | **28** watched samples. Other watch stage samples: 23 trace, 12 A-prime, 7 idle; source player, hole and slot stable. |
| Runtime overhead | Full shot watcher maximum **64 microseconds**, comfortably below **5,000 microsecond** cutoff. A distinct stationary-only run before this yielded **32/32** samples and **49 microseconds** maximum. |
| Operator visual outcome | `contact_human=no` and `movement_human=no`; the ball was **not struck**. No distance/score, ball velocity or world XYZ can be inferred. |

## Private evidence and offline analysis (do NOT upload)

The real capture was saved locally in the ignored sibling `Wii-AI-Golf-Data/captures` with filename pattern `selected-ball-frame-watch-v1-*-PRIVATE.json`. No unique filename or file checksum is exposed by the pasted logs, so **do not pick the newest capture as this baseline if more runs exist**: identify by human no/no labels, 70 samples, 64 us overhead, 45-frame observed A prime and trace SHA above. Retain original raw JSON unchanged. The offline analyzer is `scripts/analyze_selected_player_swing_words_private.py --private-report <exact local private file>`.

Observed sanitized private summary:

- Watch `complete` and trace `complete`; **70 distinct bridge ticks**, with **23 trace-active** samples and **47 without active trace**.
- Selected player slot, source hole, owner identity, and current-start vector stayed stable, and all read-budget checks passed.
- The candidate ball translation **did not change anywhere in the recording**, including after the forward trace. `candidate_record_triplet_equal_ball_triplet_count=70` — an alias/equality observation, not physical ball-motion semantics.
- Analyzer found **10 unverified motion-specific record offsets**, stable during idle and A-only: `+0x074`, `+0x094`, `+0x098`, `+0x09C`, `+0x0A0`, `+0x0A8`, `+0x0B0`, `+0x0B4`, `+0x0B8`, `+0x0C0`. Nine overlap the prior known-aim/control-confound region, so **do not label them club speed, power or contact**. A further `+0x034` changed on release/posttrace only, not motion-specific.
- Stage-resolved sample counts: idle 7; A prime 12; trace neutral 3; backswing 4; forward 5; follow-through 8; A release 3; posttrace 28. The bridge tick is not a proven game-applied physics frame.
- The CLI concludes `allowed_to_publish=false`, `approved_for_training=false`, `contact_or_ball_world_xyz_verified=false`, `swing_velocity_verified=false`, `swing_power_verified=false`.

## Use in follow-on experiments

1. **KEEP this input set unchanged as the negative control**: same green-pre-start slot, seven menu phases, original historical V1 watched source hash, 25 actually observed idle ticks (24 minimum), 45 actually observed A-held ticks and identical 89-sample digest. Never replace observed A ticks with 45 button RPC requests.
2. Compare later successful contact with this baseline **on separately verified source ownership and bridge timing**. Keep operator contact and visible movement as independent labels. Don't call an animation, trace response or completion code a hit.
3. When trying an input adjustment to achieve contact, change **one controlled factor** and record the new provenance and trace digest under a different trial ID. Retain this baseline as-is; do not retroactively call it successful.
4. Do not auto-retry or train on untyped private data. Obtain reviewed S001/S002/S000 input/bridge/privacy approval for further live shots. Source semantics and actual impact must be independently verified.

**References:** [#215 stationary V1 read qualification](https://github.com/Nate27624/Wii-AI-Golf/pull/215), [#211 51-word RPC + separate contact/movement labels](https://github.com/Nate27624/Wii-AI-Golf/pull/211), [#206 observed A45 V1 collector](https://github.com/Nate27624/Wii-AI-Golf/pull/206), [#220 Qt recovery](https://github.com/Nate27624/Wii-AI-Golf/pull/220).
