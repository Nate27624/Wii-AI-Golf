# S002 — Wii Sports Rev1: locate club pose, swing power and ball state

## Confirmed source anchors (addresses hold **pointers** to objects)

Source: [kiwi515/ogws_info](https://github.com/kiwi515/ogws_info),
`RP/RPSports/RPGolScene/RPGolConfig.h`,
`RP/RPSports/RPGolScene/RPGolFieldManager.h`,
`RP/RPSports/RPSportsSequenceMgr.h`,
`RP/RPSports/RPGolScene/RPGolScene.h`.

| Static pointer address | Structure | Source-backed fields | Relevance |
| --- | --- | --- | --- |
| `0x804BF8C4` | `RPGolConfig` | scores `+0x04..+0x93`, game mode `+0x94`, hole `+0x98`, undocumented from `+0x9C` | mode gate/control, **not** a known power gauge |
| `0x804BF868` | `RPGolFieldManager` | start obj `+0x50`, pin obj `+0x44`, cup obj `+0x54`, minimap ball effect `+0x9C` | stable control geometry, minimap rendering |
| `0x804BF708` | `RPSportsSequenceMgr` | sport `+0x04`, sequence `+0x08`, training game `+0x0C`, golf scores `+0x14..+0xA3` | scene/score changes, **not** known power |

`RPGolScene` contains an `RPGolMain*` at **scene object** offset
`+0x9C`. This is a promising pointer chain toward live gameplay, but the
scene object address and `RPGolMain` structure are NOT established. Do not
dereference guessed scene addresses. `RPGolMapObjBase` has a rotation matrix
`+0x0C` but belongs to course map objects, **not** the swinging club.

## Findings from October 25 private automated minimap capture

The 25-sample sequence had 5 pre / 20 post rows, the same minimap
visual effect instance, and just one transition across the pre/post
boundary; no within-phase changes. Only rendering-effect relative words
`+0x78` and `+0x7C` changed. The latter looks pointer-like, rather than
an f32 power or pose value. These are hypotheses and not shot-contact
evidence. Absolute runtime pointers and raw byte values remain private.

## No new live test: audit existing outcome captures

From the primary checkout, run offline against **one locally available
`outcome-*-RAW-PRIVATE.jsonl`**, not against a published candidate summary:

```powershell
$root = "D:\Projects\Wii Golf AI"
Set-Location "$root\Wii-AI-Golf"
$raw = Get-ChildItem "$root\Wii-AI-Golf-Data\captures" -Filter "outcome-*-RAW-PRIVATE.jsonl" |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $raw) { throw "No private outcome capture found" }
py scripts/audit_golf_memory_regions.py --input "$($raw.FullName)" --top 60
```

The offline script bins **same-instance** 32-bit word transitions by
`pre/post/settled`, only prints region-relative offsets, documented roles,
change counts and weak pointer/f32-shape hints. It refuses cross-instance
comparison if a window base address moves. It does **not** infer semantics
from a single correlation and uploads no data.

If only a `automated-effect-*-RAW-PRIVATE.jsonl` is available, this
same script can process it, but it will only rank minimap rendering bytes,
not discover a new club/gameplay object. Please do not repeat that scan.

## Next hypotheses, prioritized

1. **Find valid RPGolMain/golfer object chain** from documented scene
   code/symbols; only then add bounded read-only snapshots of the owning
   object. The field manager is not the golfer/player object.
2. **Compare at least two identical at-ball runs**: still pose, A-held
   backswing, downswing/impact, post-flight, landing. These are different
   events, and a slow pre/post read may entirely miss transient angles.
   Capture emulation frame brackets and keep the source/version fixed.
3. Use negative controls: camera-only changes should not rank as club
   power; A press without swing should not rank as shot power; missed
   strokes should not be labeled zero-power hits.
4. Hypothesize only bounded smooth `f32` time series for club angle and
   power, cross-check with visible meter/human labels. An address must
   replicate across sessions and discriminate different observed powers.
5. Keep `score`, `club_pose`, `swing_state`, `power`, and `ball` as
   separate unverified targets. Publish source offsets & statistics only,
   never raw RAM, absolute private capture paths or unvalidated scores.

**Stop rules:** reject unsupported disc revision, wrong mode, invalid
instance pointers, high non-atomic frame spans or stale scene/savestate.
Do not modify Dolphin configurations, overwrite save states, or trigger
unapproved live swings from the memory-audit script.
