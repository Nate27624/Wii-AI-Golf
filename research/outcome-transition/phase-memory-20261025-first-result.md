# S002 result: first offline memory differential + next object chain

## Observation record

[offline-20261025T024447Z-a37ee401](https://github.com/Nate27624/Wii-AI-Golf/blob/research/observations/research/observations/offline-20261025T024447Z-a37ee401.json).

One source-validated 8-row `outcome-*-RAW-PRIVATE.jsonl` capture:
3 `pre`, 2 `post`, 3 `settled`. Mean and max
non-atomic sampling span: **22 game frames**. No window relocation skips.
No aligned 32-bit word changed in the golf config, field manager or
sports sequence structures.

Twenty-one unique *relative words* changed, **only in minimap effects**:
- `minimap_ball_effect`: 9 words,
  `+0x1EC,+0x1F0,+0x1F4,+0x1F8,+0x1FC`
  each changed once within the same phase and twice across boundaries;
  other changed offsets are `+0x78,+0x7C,+0x108,+0x10C`
- `minimap_player_effect`: 6 words at
  `+0x78,+0x7C,+0x108,+0x10C,+0x198,+0x19C`
- `minimap_shot_line_effect`: the same 6 relative offsets as the
  minimap player effect

Shared relative offsets across *different rendering-effect instances*
may represent effect-internal runtime state; treating their changes as
golf-club pose, physical ball XYZ, or power is unjustified. The five
ball-effect trailing words have float-like bit patterns, but they still
belong to a rendered effect. There is no contact / true impact timestamp
in this report. No human labels were added to the offline report, and
the script cannot infer them from memory. This is a useful **negative
result** for the existing source-constrained golf-core windows, not
evidence that game power is absent elsewhere.

## Better pointer chain (source-backed offsets, NOT verified live base)

Reverse-engineering references:

1. `EGG::BaseSystem` owns a static `ConfigurationData *mConfigData`;
   `RPSysConfigData` has virtual `getSceneMgr()` returning its
   `mSceneMgr`. The static instance address and concrete member offset
   have **not** been established in Wii Sports US Rev1. Do not guess them.
2. `EGG::SceneManager + 0x0C` is the
   `Scene *mCurrentScene` member in
   [eggSceneManager.h](https://github.com/doldecomp/ogws/blob/master/include/egg/core/eggSceneManager.h).
3. `RPGolScene + 0x9C` is the
   `RPGolMain *mGolMain` member in
   [RPGolScene.h](https://github.com/kiwi515/ogws_info/blob/main/RP/RPSports/RPGolScene/RPGolScene.h).

Proposed read-only chain *after source-verified scene manager base*:

```
verified EGG::SceneManager instance
  +0x0C → candidate active RPGolScene*
    +0x9C → candidate RPGolMain*
      → bounded yet-undocumented golfer/club object state (future research)
```

Any future live reader **must** validate disc ID/revision, memory ranges,
scene type and stable frame brackets before following pointers. The
`RPGolMain` pointee's layout is unknown. Do not infer a club transform
from a generic course map-object rotation matrix.

## Next evidence experiment

First exhaust existing PRIVATE outcome captures (no new controller input)
and check whether the same 21 visual-effect relative offsets replicate.
Then identify the scene manager instance via source/decompiled code, or
approved bounded, read-only runtime pointer census. Only after a verified
pointer chain may S002 sample its small unknown windows under
`idle / camera-only / A-held / club movement / actual hit` labels.

S001 owns controller/frame synchronization; S003 owns swing waveforms;
S002 owns raw RAM sampling, source grounding and human-label provenance.
Do not alter the existing known-good swing as part of object discovery.

Private snapshots must stay local. This note contains only relative
offsets and already-published aggregate statistics; not actual RAM bytes,
runtime pointers, disc data or local file paths.
