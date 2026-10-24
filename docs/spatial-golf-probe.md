# Read-only candidate pin / start / cup coordinates for US Rev 1

**Status:** source-guided field hypotheses, not yet confirmed visually in a running game. This supplements [S002 data capture](game-data-capture.md).

Independent [kiwi515/ogws_info RPGolMapObjBase.h](https://github.com/kiwi515/ogws_info/blob/main/RP/RPSports/RPGolScene/RPGolMapObjBase.h) documents a translation vector `mTrans` at `+0x30` (three PowerPC big-endian floats) and `mpTrans` pointer at `+0x44`. [RPGolFieldManager.h](https://github.com/kiwi515/ogws_info/blob/main/RP/RPSports/RPGolScene/RPGolFieldManager.h) includes current pin/start/cup/course/minimap object pointers. Treat layout inheritance and units as research assumptions until verified on screen. Candidate values can be static offsets or values in a different coordinate frame.

User-operated **live** `scripts/probe_golf_symbols.py` run on 2026-10-24 found `RSPE01`, revision `1`, `RPGolConfig.mGameMode = 0x4` (**GAMEMODE_TR_NEARPIN**), `mCurrentHole = 0x1`, and plausible nonzero scene object pointers. This validates version selection and supports the expected training mode, but it does NOT yet verify coordinates or score units.

### Run on local Windows Dolphin machine

```powershell
py scripts/probe_golf_spatial.py --label green01-spatial-before
```

With the game still in Hitting the Green, optionally make a **manual visible change** and capture again with a fresh label:

```powershell
py scripts/probe_golf_spatial.py --label green01-spatial-after
```

The command is read-only, only attempts structure reads for `RSPE01` disc revision `1` **and game mode 4**, checks instance and object pointers against plausible MEM1/MEM2 ranges, and reads `+0x30` vectors as big-endian float32. A second potential vector can be read by dereferencing a validated `mpTrans` pointer. Unreasonable or non-finite values are flagged. Other region/revision/modes safely skip object reads.

### How to interpret

- A candidate vector can look reasonable but remain unrelated to the physical ball/hole. Do not claim any particular distance or map coordinate without repeated independent visual checks.
- Compare start and pin/cup candidate vectors, repeat from the same savestate, then advance to a different training shot. A valid dynamic pin position should change with the visible pin while other fields may stay fixed.
- The raw `hole` field may be a zero-based or one-based course index; it has not been calibrated to the ten-shot training challenge.
- Preserve the local ignored JSON only; no ROMs, raw game screenshots or memory dumps in Git.
- No game-controlled shot or actual scoring evidence was obtained in this software-only implementation.

### Testing

`PYTHONPATH=src python -m unittest discover -s tests -p 'test_spatial_probe.py' -v` — 5/5 targeted offline mock tests passed in an isolated dependency-compatible local harness. Run the complete suite on the Windows checkout before merging.