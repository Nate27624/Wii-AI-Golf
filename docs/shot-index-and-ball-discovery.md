# Hitting the Green: inferred shot labels and motion discovery

## 417-sample evidence

Real [user-uploaded run](https://github.com/Nate27624/Wii-AI-Golf/blob/data/hitting-green-20261024T073347Z-f47fba1c/research/results/hitting-green/20261024T073347Z-f47fba1c.json): 417 successful samples, 41 significant scene changes, 10 distinct tee positions recurring in the same sequence across nearly three rounds, and 3 pin positions. The raw golf current-hole field remained 1 throughout: **it is not the ten-shot training index**.

Source-gated US Rev1 coordinate fingerprints live in the evaluation scenario inference module. Match known tee XYZ with tolerance 0.25 units; unknown points have unknown indices. Pin and cup must agree in horizontal XYZ (XZ <=0.2 game units, Y <=0.5). The normal automatic monitor now requires three consecutive aligned samples before publishing a **stable empirical tee/pin candidate**. This is not an authoritative internal game counter and not evidence that the ball was struck. Tee and pin may update several seconds apart.

## Searching candidate moving-ball and score data

Public [ogws_info reverse-engineering headers](https://github.com/kiwi515/ogws_info) identify golf config/field/sequence struct pointers and field manager minimap effect pointers. They do **not** establish the actual physics ball XYZ or the final score location. The new read-only motion sampler probes fixed US Rev1 golf config and modest windows around field, sequence and three minimap effects. It ranks both big-endian f32 XYZ triples that change at stable addresses and big-endian u32 values (0..100000) that change over the recording. A moving UI effect is not necessarily the ball; a changing integer is not necessarily a shot counter or score.

From a clean updated evaluation checkout with Felk Dolphin bridge active, manually navigate to Hitting the Green, then run:

```powershell
py -m unittest discover -s tests -v
py scripts/discover_golf_motion.py --seconds 45 --interval 0.6
```

**Swing once or twice normally while it runs.** No Enter prompts; Ctrl+C stops sooner. A 15-second upload-free test is:

```powershell
py scripts/discover_golf_motion.py --seconds 15 --no-upload
```

The script never injects Wii Remote input, loads savestates, or writes game RAM. It checks game ID RSPE01, revision 1 and mode 4 before source-guided structure dereferences; guards pointer ranges to MEM1/MEM2, reads <=1024 bytes per RPC and <=12KiB sampled per sweep. Some effect object lengths are exploratory, not known layouts.

Raw memory hex and full time series stay **local only** in the sibling Wii-AI-Golf-Data/captures folder. The existing Git upload path publishes a compact report of ranked candidate addresses, change counts and representative numerical vectors on a separate data branch, not raw RAM/screenshots/ROMs/savestates. Public numerical candidates remain unverified.

### Limits

- Ten tee indices are empirical matches from actual observed geometry, not the authoritative in-game shot counter.
- The updated monitor labels tentative stable tee/pin configurations, **not** completed swings or scores.
- This probe generates rank-ordered numeric *hypotheses*. Physical ball motion requires independent multi-frame and on-screen correspondence. A score decoder requires validated landing position or actual game result variable and its units.
- The earlier 417-sample run did not capture any actual ball position or score. New tests are offline mocks only; real Dolphin scan and upload remain to be checked.

## 2026-10-24 variable recording upgrade

The motion sampler now has two bounded read-only profiles:

- **Fast** (default): reads the first 192 bytes of the golf configuration, golf field manager, sports sequence, and three minimap effect windows (~2.1 KiB of candidate windows). Fewer memory RPC calls gives more opportunities to catch short-duration motion.
- **Broad**: scans the full source-documented golf configuration (~7.3 KiB), plus the same other windows (~9.2 KiB total). This is useful for finding possible result/counter state, but takes more RPC frames and may miss fast flight.

Every successful sample records its emulator frame count before/after the reads, exact frame span, raw candidate windows (PRIVATE local JSONL only), matched empirical tee/pin and pin/cup alignment status. Candidate ranking distinguishes changes *within* a matching tee/pin from scene transitions. A short-lived pointer value, transition, or a missing sample is not counted as repeated ball motion.

**Source-grounded typed decoder:** `decoded_golf_fields.py` also extracts US Rev1 fields at published offsets: raw golf mode, current course-hole, sport/sequence/training-game IDs, pin/start/target object counts and two standard golf score arrays (36 entries each). The documented score arrays are **not confirmed** to represent the Hitting the Green training metric. These raw values appear in each local sample and their compact change statistics appear in the GitHub report. No guessed units or score conversion is applied.

### Suggested short experiments

For dynamic motion, stand at the same shot, start recording, swing once normally, and let the ball settle:

~~~powershell
py scripts/discover_golf_motion.py --seconds 30 --profile fast
~~~

For possibly slower-changing scores, counters and wind-related state, try a separate run that includes a displayed result and the transition to the next shot:

~~~powershell
py scripts/discover_golf_motion.py --seconds 25 --profile broad
~~~

Both commands support Ctrl+C to stop and upload early. No need to collect another entire 10-shot round. The full raw game bytes remain local under `Wii-AI-Golf-Data/captures` and **are not** part of the auto-published data branch. Only a numerical candidate ranking, counts, documented raw-field change summaries, and frame-span statistics are uploaded.

**Research limitation:** even a high-ranking in-scene coordinate is only a hypothesis until its trajectory matches the ball on screen and its final position predicts an independently visible result. These scans use sequential non-atomic read RPCs; actual ball physics and authoritative displayed distance-to-pin are not decoded.

## Mandatory standard startup before new full-session captures

For a fresh/attached end-to-end game run, prefer **`py scripts/start_golf_recording.py --attach-running --seconds 30 --scan-profile fast`** from the evaluation worktree. This invokes canonical `scripts/launch_hitting_green.py` for **the existing `green-pre-start` named savestate + A → wait → A+B → release → A menu sequence**, then runs the read-only scanner. **Never** call `launch_golf.py` as a substitute for intro navigation; it only restores the savestate. The wrapper never emits its own menu buttons or swing. See [boot-and-capture.md](boot-and-capture.md) for fresh-launch usage and environment isolation. The direct `discover_golf_motion.py` command below remains appropriate when Dolphin is **already verified** at a ready-to-swing screen and a reset is unwanted.
