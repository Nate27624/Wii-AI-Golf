# S002-REV1-WIND-MODE4-CALLGRAPH-01 — why training near-pin has zero wind tables

**Evidence status:** offline, source-code control flow from operator's existing private RSPE01 Rev1 MEM1, corroborated by public `kiwi515/ogws_info` `RPGolConfig.h` function names/addresses and `doldecomp/ogws` Rev1 compilation-unit map. One separately exported native MEM1/MEM2 pair has all-zero BSS wind entries. Neither measured in-game wind forces, physics air resistance, nor its visual display is verified. No private executable bytes, native RAM, float values, hashes, runtime heap addresses, paths or emulator state included in this document.

## Question left open by canonical #164

PR #164's **completed operator private offline table study** confirms nine zero words in each of the two MEM1 BSS wind tables during Hitting the Green (config mode 4). Does code explicitly set wind to zero for mode 4, or does this training setup *avoid initializing* the general golf wind tables?

The latter has the **stronger source support** in the observed Rev1 code: mode 4 is assigned by a separate training setup path that does NOT call `RPGolConfig::CreateWindForGamemode`, whereas the standard-game setup has the only discovered direct `bl` call to it.

## Source-backed control flow, real Rev1 executable

All PCs are Rev1 PowerPC code addresses; branch target/operand facts derive from instructions in the existing operator-supplied MEM1 image, decoded as BE PPC32. Public headers identify:
- `RPGolConfig::SetupGame` begins `0x8029D810`
- Mode-specific training setup begins `0x8029D778` (header has an ambiguous duplicate SetupStandardGame label; **do not promote the header's name**; use code path and explicit mode assignment instead)
- Standard setup begins `0x8029D4BC`
- `RPGolConfig::CreateWindForGamemode` begins `0x8029CEA8`
- `RPGolConfig::GetWind` begins `0x8029CE74`
- General `CreateWind` implementation begins `0x8029DCF4` (identified by direct tail branches from `CreateWindForGamemode`, not by a duplicate/mislabelled declaration in public header)

### A. SetupGame dispatches to distinct setup paths

`0x8029D810` sets a default mode, reads a separate global mode-selector word, then dispatches as follows:

| Source PC | Static instruction behavior | Implication |
| --- | --- | --- |
| `0x8029D810..0x8029D824` | source global mode discriminant read, compare, branch | Training/fitness/standard selection is made *before* training hole mode is assigned |
| `0x8029D844..0x8029D84C` | branch into `0x8029D778` | Enters source training setup path |
| `0x8029D850..0x8029D858` | branch into `0x8029D6E0` | Separate fitness setup |
| `0x8029D85C` | branch into `0x8029D4BC` | Separate standard-game setup |

Inside training setup, the path at `0x8029D7D0..0x8029D7E4` executes an explicit `li r0,4` and `stw r0,0x94(r31)` at `0x8029D7D8/0x8029D7E0`. This is the real, source-backed assignment for game mode 4 (= `GAMEMODE_TR_NEARPIN` in public `RPGolConfig.h`). The training setup terminates without a direct call to `0x8029CEA8`.

### B. Only the standard-game setup has a discovered direct CreateWindForGamemode call

Within `0x8029D4BC..0x8029D6E0`, the standard setup assigns modes **9–12** in its branches (not 4). At `0x8029D5E4..0x8029D5EC` it tests an additional global setup word. When that branch takes the initialization path, instructions `0x8029D5F0..0x8029D680` clear the four-player score storage and **`0x8029D684` calls `CreateWindForGamemode` at `0x8029CEA8`**.

I searched BE PPC relative direct calls in the captured `0x80004000..0x80350000` source-code interval and found exactly **one direct BL target** `0x8029CEA8`: `0x8029D684`. This is *not* a proof that no indirect call exists anywhere or that no alternate runtime could call it; the finding is limited to the checked direct-BL region. Nonetheless, the actual mode-4 setup path provides a concrete **direct-call bypass** explanation for untouched zero BSS tables.

### C. Why an incorrect shortcut would be misleading

`CreateWindForGamemode` at `0x8029CEA8` checks `config+0x94` and branches by mode, then **tail-branches to** `CreateWind` `0x8029DCF4`. For the numeric mode-4 case, *if called anyway*, its `<9` branch at `0x8029CED4..0x8029CEE4` supplies integer arguments **(0,8,0,15)** to `CreateWind`. It does **not** set all wind values to zero for mode 4.

The general `CreateWind` at `0x8029DCF4..0x8029DEA4` initializes and writes the two source BSS arrays in a nine-entry loop. In particular `0x8029DD90..0x8029DDA0` writes nonzero fixed defaults for out-of-range holes (the source uses values 8 and 16), while other branches assign computed entries; precise wind units, direction convention and resulting game physics are **unverified**.

Therefore **do not implement** “`CreateWindForGamemode(mode4)` clears the wind tables.” The stronger hypothesis is “normal Hitting-the-Green setup bypasses the wind initialization routine, leaving BSS zero” (supported by the source path and one mode4 all-zero BSS snapshot). This says nothing about whether the physics engine separately enforces a no-wind rule.

### D. GetWind is simply a raw lookup

`RPGolConfig::GetWind` `0x8029CE74..0x8029CEA4` uses `config+0x98` as an index and reads both fixed tables. It has no own mode check in this routine. In the existing mode4 still capture, both arrays happen to contain nine zero words, so lookup of any in-bounds index would return a zero raw integer pair. This is an observed lookup result, **not** measured wind velocity, on-screen indicator semantics or proof of ongoing execution of GetWind.

## Evidence levels / study next step

- **Source verified:** the direct callgraph `SetupGame` training path → mode 4 assignment does not invoke direct wind initialization; standard setup can invoke `CreateWindForGamemode`; `GetWind` simply reads two nine-word tables.
- **Runtime observed once:** both nine-entry BSS arrays zero in an existing mode4 paired-bank still state (the two images are not independently proven same emulated frame or boot).
- **External game rule:** original Wii Sports guides describing no wind in Hitting the Green are independently referenced by existing #164 owner; this is consistent, not an executable physical-world proof.
- **NOT verified:** dynamic call frequencies, any indirect wind-initializer calls, actual engine wind-force usage or meter units, training-gated no-wind physics, movement/score changes, general golf mode wind behavior.

This is **source-only follow-up** on existing S002 #162/#164, not a new runner, memory scanner, ROM disassembler, publisher or model feature. No new Dolphin shot, bridge integration, reset, RAM capture, public numerical data or user action required. S002 #164 can record the callgraph as supporting explanation for the all-zero table and leave training disabled. S000 #154 should preserve code-path-vs-runtime-vs-gameplay semantic evidence categories.

## Independent source anchors

- `kiwi515/ogws_info/RP/RPSports/RPGolScene/RPGolConfig.h` — `EGameMode`, `GetWind`, `CreateWindForGamemode`, `SetupGame`, field offsets.
- `doldecomp/ogws/config/RSPE01_01/splits.txt` — `RPGolConfig.cpp .text 0x8029CA4C..0x8029E62C`, BSS `0x804A8B48..0x804A8BA0`.
- Existing S002 #162 `research/memory/rev1-coordinate-ball-wind-source-trace.md`; S002 #164 `research/studies/S002-REV1-WIND-SOURCE-01.md`.

**No source-derived state here is authorized as a training feature.**
