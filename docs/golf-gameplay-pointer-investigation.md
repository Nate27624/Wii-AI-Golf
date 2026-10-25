# S002 / S001: source-anchored golf gameplay pointer investigation

## Source-verified facts

The public [ogws_info](https://github.com/kiwi515/ogws_info) Wii Sports
US Rev1 `RP/RPSports/RPGolScene/RPGolScene.h` contains a
`RPGolMain* mGolMain` at **offset +0x9C within an RPGolScene instance**.
That **does not establish the address of an RPGolScene instance**.
The source also documents the RPGolScene methods
`OnConfigure` (0x8028DFF0), `OnCalculate` (0x8028DFA8),
`OnReset` (0x8028DFB0), and destructor (0x8028E030).
These are executable code addresses, **not object pointers**.

`RPSportsBaseScene.h` defines inherited scene fields through +0x98.
It does not provide a reliable global address of the active scene object.
The expected RPGolMain header is not present at the checked source path.
Neither `golf_field` nor `minimap_ball_effect` is a substitute for
`RPGolScene`.

## Included source-verified symbols (no download necessary)

The repository includes
`research/reference/golf_scene_rev1_symbols.csv`: a **small, attributed
selection of symbol facts** from
[`kiwi515/ogws_info/RSPE_r1.map.csv`](https://github.com/kiwi515/ogws_info/blob/bcf62e22f9e7fc1d75acbb24bd8368b03cba1c81/RSPE_r1.map.csv).
From the PR #122 checkout, run:

```powershell
py scripts/audit_golf_scene_symbols.py
```

That default command is **fully offline**. There is no Dolphin action,
no manual download, and no raw memory output.

## Optional complete upstream maps, cached locally

The upstream project has no license file granting wholesale
redistribution of its symbol maps, so the full maps are **not committed
into this repository**. A version-pinned helper fetches them unchanged
into the *sibling* `Wii-AI-Golf-Data/symbols` directory rather than Git:

```powershell
# Get all three from upstream: Ghidra map, CSV, Dolphin map
py scripts/fetch_golf_symbol_map.py --format all

# Analyze the cached complete CSV
py scripts/audit_golf_scene_symbols.py --map "..\\Wii-AI-Golf-Data\\symbols\\RSPE_r1.map.csv"
```

The optional fetch needs internet access to GitHub and refuses to
overwrite an existing local file. For offline work, use the bundled
source-verified subset above. The three verified upstream filenames
are `RSPE_r1.map`, `RSPE_r1.map.csv`, and `RSPE_r1.dmap`.

The symbol triage reports relative categories and match counts only.
**Function addresses do not equal runtime instance pointers**:
`RPSysSceneMgr::getCurrentScene` has a Rev1 function entry in the
source map, but calling or tracing it to find a live scene instance
still requires independent implementation review.

## Updated verified chain — cross-checked with doldecomp/ogws

The second, independent [doldecomp/ogws](https://github.com/doldecomp/ogws)
source adds the **manager-to-scene** relationship (for its documented
`RSPE01_01` structures):

| Level | Evidence | Offset / status |
| --- | --- | --- |
| `RPSysSceneMgr::spInstance` | Singleton declaration and implementation: `RPSingleton.h`, `RPSysSceneMgr.cpp` | Static **storage address unknown** |
| `EGG::SceneManager::mCurrentScene` | `include/egg/core/eggSceneManager.h` | `+0x0C` from live manager instance |
| `EGG::SceneManager::mCurrentSceneID` | Same header; `RPSysSceneCreator.h` scene enumeration | `+0x18`, golf scene ID `5` |
| `RPGolScene::mGolMain` | `kiwi515/ogws_info/RPGolScene.h` | `+0x9C`; **gameplay type unverified in newer decomp** |

The newer `doldecomp/ogws` `RPGolScene.h` defines
`unk9C[4]` at `+0x9C`, whereas the older kiwi515 header names it
`RPGolMain*`. The offset agrees, but **the pointer type is not yet
independently confirmed**. Do not assume `RPGolMain` is safe to
dereference until the class/instance is validated on Rev1.

The tool now reports the two additional manager offsets and ID. The
machine-readable evidence lives in
`research/reference/golf_scene_layout.json` with all live object
addresses deliberately `null`.

The logical chain we seek is **static manager storage** ->
manager instance -> `mCurrentScene` -> validated golf scene ->
candidate `+0x9C`. We have a valid *layout* but **not** a
verified address of the initial static manager storage. We will not
scan arbitrary memory or hardcode an estimated one.

Useful links:

- [RPSingleton.h](https://github.com/doldecomp/ogws/blob/master/include/Pack/RPSingleton.h)
- [RPSysSceneMgr.cpp](https://github.com/doldecomp/ogws/blob/master/src/Pack/RPSystem/RPSysSceneMgr.cpp)
- [eggSceneManager.h](https://github.com/doldecomp/ogws/blob/master/include/egg/core/eggSceneManager.h)
- [RPSysSceneCreator.h](https://github.com/doldecomp/ogws/blob/master/include/Pack/RPSystem/RPSysSceneCreator.h)
- [Kiwi RPGolScene.h](https://github.com/kiwi515/ogws_info/blob/main/RP/RPSports/RPGolScene/RPGolScene.h)


## Offline follow-up: bounded DOL code-reference triage (no live Dolphin actions)

The upstream `RSPE_r1.map`, `RSPE_r1.dmap`, and CSV files contain
**function addresses, not a named `RPSysSceneMgr::spInstance` storage
symbol**. We checked the map: it does not contain a literal `spInstance`
or `sInstance` entry. Therefore no public map alone currently identifies
the singleton storage address.

To narrow it without guessing game RAM, PR #122 also includes
`scripts/audit_golf_singleton_code.py`. It reads **only** a locally
extracted `main.dol`, maps DOL executable sections, and inspects three
source-anchored function ranges for PowerPC `lwz` instructions using the
`r13` mutable small-data-area base:

- `RPSysSceneCreator::changeSceneAfterFade`, 0x80184BA4, 0x26C bytes
- `RPSysScene::setSceneFadeColor`, 0x80185484, 0x48 bytes
- `RPSysScene::setFadeColor`, 0x801854CC, 0x48 bytes

The starting addresses and sizes are from the public **Rev1**
`kiwi515/ogws_info/RSPE_r1.map`; the newer source
`doldecomp/ogws/src/Pack/RPSystem/RPSysSceneMgr.cpp` shows multiple
`RP_GET_INSTANCE(RPSysSceneMgr)` callsites. The tool reports shared
**signed r13-relative displacements**, never guesses a RAM address.
Multiple callsites could still reference other shared globals. It
does **not** identify the manager singleton without disassembly review.

To extract the executable from the user's own local Wii Sports USA Rev1
image, use Dolphin's game list: right-click Wii Sports, choose
**Properties > Filesystem**, locate and extract `main.dol` (or choose
**Extract System Data** / **Extract Entire Disc** and find
`DATA/sys/main.dol`). Save it somewhere private under
`Wii-AI-Golf-Data`, never in the Git checkout or uploads.

Then from the PR #122 worktree run:

```powershell
py scripts/audit_golf_singleton_code.py --dol "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\symbols\main.dol"
```

This is local, offline, read-only and never controls Dolphin. The DOL
alone has no authoritative disc revision header; the script **cannot**
verify the input is Rev1. If mapped function ranges are missing, it
fails closed instead of searching unknown bytes. Never publish/upload
the extracted executable or its raw bytes. The only useful output for
peer review is the sanitized JSON report with callsite counts and
relative offsets, not absolute object addresses.

**Next gate:** distinguish the candidate `spInstance` loading instruction
from other globals by examining the function's instruction/register
flow and independent anchors. Only then can a separately reviewed
read-only `RPSysSceneMgr` runtime probe be designed.

## Evidence from operator-supplied extracted main.dol (offline)

The operator supplied a private `main.dol` for analysis. **Do not commit,
share, or reupload the executable**. A private, read-only disassembly
check of the selected source-backed Rev1 functions found the same
`lwz ..., -0x5EA8(r13)` reference in all three audited callsites:

- `RPSysSceneCreator::changeSceneAfterFade`
- `RPSysScene::setSceneFadeColor`
- `RPSysScene::setFadeColor`

The `RPSysSceneMgr` constructor at `0x80186108` also reads that
displacement (`lwz r0,-0x5EA8(r13)`) and later stores a constructed
instance (`stw r30,-0x5EA8(r13)`). The executable initializes `r13`
as `0x804C5380` in `__init_registers`; signed arithmetic gives
`0x804C5380 - 0x5EA8 = 0x804BF4D8`.
That static storage address lies within the supplied DOL's declared
BSS range. **This is a strong code-verified static singleton storage
candidate, not the runtime manager pointer value or an active scene.**
Executable identity alone does not prove the game revision.

The new script `scripts/verify_golf_scene_manager_slot.py` reproduces
these checks locally and **fails closed** if the independent callsites,
initializer, constructor read/write or BSS range do not agree:

```powershell
py scripts/verify_golf_scene_manager_slot.py --dol "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\symbols\main.dol"
```

The script returns the derived static-storage address, not the contents
of that memory location. The returned `scene_manager_runtime_pointer`,
`active_golf_scene_pointer`, and `golf_main_pointer` stay `null`.

### Handoff to S001 / S002

Next implement an explicitly approved, **read-only**, revision- and
game-state-gated observation in the canonical RAM capture path:
read just the four-byte word at the derived static storage address;
check non-null/4-byte aligned mapped RAM; read manager `+0x18` and
confirm scene ID 5; read manager `+0x0C` as active scene pointer;
verify pointer identity and scene ID stable across paused/same-game
snapshots; only then inspect candidate scene `+0x9C`, with no assumption
that it definitely is `RPGolMain`. Record aggregate statuses and relative
offsets, never raw RAM or live absolute heap addresses in public
artifacts. Do not infer shot outcome/power from a pointer dereference.

## Next evidence gate — do not skip

1. From independently reviewed Rev1 source/decompilation, establish the
   **active scene-manager pointer source**, how the active scene object
   is selected, its exact type check and lifetime.
2. Separate addresses of **code functions**, **static pointer storage**,
   **live scene object**, and **RPGolMain object**.
3. Only after the pointer source is proved: propose a bounded,
   read-only, opt-in probe gated on `RSPE01` Rev1 and training mode 4,
   null/valid RAM pointers, repeated reads, and emulated-frame span.
4. Contrast static-aim, A-only, backswing, swing, flight, and rest
   with camera-only and failed-shot negative controls; never promote
   inferred club power or XYZ from a single changed word.

Existing 24-capture audit mostly identifies scene/UI transitions and
minimap effects. No verified club power, club pose, ball XYZ or score.
No Dolphin action or pointer dereference is introduced in this PR.
