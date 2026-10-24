# US Rev 1 symbol-guided read-only golf probe

**Purpose:** Replace blind RAM guesses with research-grounded, read-only pointer hints. This probe is a *hypothesis generator*, not a verified real-game state extractor.

Reference: [kiwi515/ogws_info](https://github.com/kiwi515/ogws_info), public US Rev 1 Wii Sports reverse-engineered golf structs. Confirmed fields documented in its header files RPGolConfig.h, RPGolFieldManager.h, RPSportsSequenceMgr.h. The repository also provides a region/revision-specific Dolphin symbol map (RSPE_r1.dmap) and CSV, useful for further offline study.

We **strictly require RSPE01 and disc revision byte 1** in the emulated header at 0x80000000 before trying these static pointers. If your copy is a different revision/region, the tool refuses all subsequent reads and prints why. Do not override that gate without independent symbol mapping for the right build.

### Local read-only probe

~~~powershell
python -m pip install -e .
py scripts/probe_golf_symbols.py
~~~

It saves research/game-data.local/symbol-probe.json (refuses overwrite) and prints raw results. Run while Wii Sports is on the Hitting the Green screen, unpaused, with the loopback bridge responding. No ROM/savestate/memory writing or controller commands occur. No live validation has occurred yet.

### Candidate static pointers in decomp documentation, US Rev1 ONLY

| Static address | Class | Example fields (offset relative to the pointed object) |
| --- | --- | --- |
| 0x804BF8C4 | RPGolConfig | game mode +0x94; current hole +0x98 |
| 0x804BF868 | RPGolFieldManager | map data +0x18; current pin object +0x44; current start object +0x50; minimap course object +0x74; ball minimap effect +0x9C |
| 0x804BF708 | RPSportsSequenceMgr | current training game +0x0C; golf mode +0xAC |

Only raw 32-bit big-endian pointers/integers are returned. These are **not** pin world coordinates, score distances or minimap geometry. A valid-looking pointer is not proof the corresponding class is instantiated, and a raw hole field may not correspond to a Hitting the Green shot number. Some decompiled names may change; all must be visually verified across multiple resets, shots, and other games.

### What to verify on screen

- First compare outputs while on the golf menu and actual Hitting the Green first-shot screen; does the object pointer become plausible only while playing?
- Repeat reset without changing settings. Which raw integers/pointers are stable?
- Advance manually to a different shot, compare changes to a visually confirmed shot index; check gamemode against the observed training mode.
- For map data, future work must follow pointers into understood class layouts, preserve coordinate systems, and independently verify against screenshots. **This probe does not render or decode a map.**
- Actual scored distance remains unknown; evaluate 30 double-annotated scored shots only after Worker 1 proves valid input and resets.

Other details: [game-data-capture.md](game-data-capture.md). Do not commit output JSON, raw memory, game resources or screenshots.
