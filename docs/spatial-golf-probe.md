# Read-only candidate pin / start / cup coordinates for US Rev 1

**Status:** source-guided field hypotheses, not yet confirmed visually in a running game. This supplements [S002 data capture](game-data-capture.md).

Independent [kiwi515/ogws_info RPGolMapObjBase.h](https://github.com/kiwi515/ogws_info/blob/main/RP/RPSports/RPGolScene/RPGolMapObjBase.h) documents a translation vector `mTrans` at `+0x30` (three PowerPC big-endian floats) and a scale vector `mScale` at `+0x3C`. The same published header calls `+0x44` a pointer, which **overlaps the scale vector**; that pointer annotation is inconsistent and must not be trusted. The live result `0x3F800000` at `+0x44` is the float `1.0`, supporting scale Z rather than a valid pointer. [RPGolFieldManager.h](https://github.com/kiwi515/ogws_info/blob/main/RP/RPSports/RPGolScene/RPGolFieldManager.h) includes current pin/start/cup/course/minimap object pointers. Treat layout inheritance and units as research assumptions until verified on screen. Candidate values can be static offsets or values in a different coordinate frame.

User-operated **live** `scripts/probe_golf_symbols.py` run on 2026-10-24 found `RSPE01`, revision `1`, `RPGolConfig.mGameMode = 0x4` (**GAMEMODE_TR_NEARPIN**), `mCurrentHole = 0x1`, and plausible nonzero scene object pointers. This validates version selection and supports the expected training mode, but it does NOT yet verify coordinates or score units.

### Run on local Windows Dolphin machine

```powershell
py scripts/probe_golf_spatial.py --label green01-spatial-before
```

With the game still in Hitting the Green, optionally make a **manual visible change** and capture again with a fresh label:

```powershell
py scripts/probe_golf_spatial.py --label green01-spatial-after
```

The command is read-only, only attempts structure reads for `RSPE01` disc revision `1` **and game mode 4**, checks instance and object pointers against plausible MEM1/MEM2 ranges, and reads `+0x30` vectors as big-endian float32. The scale vector at `+0x3C` is now read, but no translation-pointer dereference is attempted until its layout is separately verified. The report also computes pin-to-cup and start-to-pin separations in **unverified game coordinate units**. Unreasonable or non-finite values are flagged. Other region/revision/modes safely skip object reads.

### How to interpret

- A candidate vector can look reasonable but remain unrelated to the physical ball/hole. Do not claim any particular distance or map coordinate without repeated independent visual checks.
- Compare start and pin/cup candidate vectors, repeat from the same savestate, then advance to a different training shot. A valid dynamic pin position should change with the visible pin while other fields may stay fixed.
- The raw `hole` field may be a zero-based or one-based course index; it has not been calibrated to the ten-shot training challenge.
- Preserve the local ignored JSON only; no ROMs, raw game screenshots or memory dumps in Git.
- No game-controlled shot or actual scoring evidence was obtained in this software-only implementation.

### Testing

`PYTHONPATH=src python -m unittest discover -s tests -p 'test_spatial_probe.py' -v` — 5/5 targeted offline mock tests passed in an isolated dependency-compatible local harness. Run the complete suite on the Windows checkout before merging.
### Live user evidence — 2026-10-24

The user ran the first spatial probe on a live `RSPE01` Rev 1 Hitting the Green screen and ran the entire repository unit suite: **56 tests, all passing (before this correction)**. Raw reported translations were pin (210.100006, -7.0, -350.5), cup (210.100006, -7.04664135, -350.5), and start (2.20000005, -5.5, -318.0). Pin and cup exactly matched X/Z and differed only ~0.04664 in Y; start-to-pin X/Z separation ~210.43 **game coordinates, not verified meters**. All 5 objects had `0x3F800000` at `+0x44` (float 1.0), exposing a bad pointer interpretation in the prior probe.

This evidence substantially increases confidence in the inline translation fields; it does NOT establish ball coordinates, map scale or shot-result distance. The revised probe reads `+0x3C` scale instead of dereferencing `+0x44`.

**Recommended independent check:** capture the same visible first-shot state again with a new label, then manually advance to a different Hitting the Green shot and capture another fresh label. Check whether the pin/cup translations change coherently with the on-screen target. The `research/game-data.local` outputs must remain local and are never overwritten.

Local updated focused mock tests: **6/6 pass** (five legacy spatial mocks plus one regression fixture representing the reported live values). Run the complete repository suite on the updated worktree before merging.
