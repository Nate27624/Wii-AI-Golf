# Hitting the Green: inferred shot labels and motion discovery

## 417-sample evidence

Real [user-uploaded run](https://github.com/Nate27624/Wii-AI-Golf/blob/data/hitting-green-20261024T073347Z-f47fba1c/research/results/hitting-green/20261024T073347Z-f47fba1c.json): 417 successful samples, 41 significant scene changes, 10 distinct tee positions recurring in the same sequence across nearly three rounds, and 3 pin positions. The raw golf current-hole field remained 1 throughout: **it is not the ten-shot training index**.

Source-gated US Rev1 coordinate fingerprints live in the evaluation scenario inference module. Match known tee XYZ with tolerance 0.25 units; unknown points have unknown indices. Pin and cup must agree in horizontal XYZ (XZ <=0.2 game units, Y <=0.5). The normal automatic monitor now requires three consecutive aligned samples before publishing a **stable empirical tee/pin candidate**. This is not an authoritative internal game counter and not evidence that the ball was struck. Tee and pin may update several seconds apart.

## Searching candidate moving-ball and score data

Public [ogws_info reverse-engineering headers](https://github.com/kiwi515/ogws_info) identify golf config/field/sequence struct pointers and field manager minimap effect pointers. They do **not** establish the actual physics ball XYZ or the final score location. The new read-only motion sampler probes fixed US Rev1 golf config and modest windows around field, sequence and three minimap effects. It ranks big-endian f32 XYZ triples that change at stable addresses over the recording; a moving UI effect is not necessarily the ball.

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