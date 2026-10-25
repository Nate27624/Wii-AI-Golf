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
