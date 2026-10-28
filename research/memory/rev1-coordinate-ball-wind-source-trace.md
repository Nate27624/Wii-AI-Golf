# RSPE01 Rev1: source-traced pin/start/ball translation and wind lookup

**Study:** S002-REV1-STATE-PROVENANCE-01. **2026-10-27 / memory-first.**
This document is a *private-executable-derived SOURCE record*, not a new
runtime decoder, memory reader, publisher or training feature.

Input: operator-supplied USA revision-1 `main.dol`, 3,995,168 bytes,
inspected privately. Its mapped .text instruction sequences were decoded
as PowerPC 32-bit big endian and cross-checked against
`doldecomp/ogws/config/RSPE01_01/splits.txt` and the selected
`kiwi515/ogws_info` headers. **No raw DOL bytes, private RAM, game ROM,
pointer values or live float values are in this document.** Relative
object-field addresses and code PCs are source observations.

## Confirmed by executable code (and limits)

### 1. Correct `RPGolMapObjBase` storage

At constructor `0x80290A48`, r3 is retained as the receiver. Stores
initialize three BE-f32 values at receiver offsets `+0x30,+0x34,+0x38`
to zero, three values at `+0x3C,+0x40,+0x44` to one; internal pointer
`+0x48` refers to receiver `+0x0C` (rotation matrix) and `+0x4C`
refers to receiver `+0x30` (translation vector).

This **corrects a contradictory community header**:
`RPGolMapObjBase.h` annotates `mpRotation+0x40` and `mpTrans+0x44`,
which overlap the three scale floats. For this specific Rev1 constructor,
internal pointer stores are `+0x48,+0x4C`.

**Confidence:** strong code-level storage and pointer-provenance proof
for the class base; NOT proof every derived object begins at offset zero
or that three numbers in an arbitrary RAM block represent world XYZ.

### 2. Selected PIN and START accessors directly follow translation

`RPGolFieldManager.cpp`, source-backed selected object pointers:

| Rev1 PPC | Exact pointer follow | Source meaning |
| --- | --- | --- |
| `0x802922A8/AC/B0` | `lwz r3,+0x44(r3)`; `lwz r3,+0x4C(r3)`; `blr` | current Pin object, then its translation VEC3 pointer |
| `0x802922EC/F0/F4` | `lwz r3,+0x50(r3)`; `lwz r3,+0x4C(r3)`; `blr` | current Player START object, then its translation VEC3 pointer |

First is part of a bounded branch path around `0x80292294`,
not independently proven a named public API function. The second is a
tiny standalone getter. `RPGolFieldManager.h` independently labels
`+0x44` `mCurrentPinObj`, `+0x50` `mCurrentStartObj`.

**New fact:** the actual game code *uses* selected Pin/Start `+0x4C`
as a pointer to a three-component translation value. No need to use
the erroneous `+0x40/+0x44` map-object pointer annotations.

**Still unknown:** the human-visible coordinate axes, scale, whether
the selected Ptr points to the first byte of the Base subobject, and
whether present values match visually observed pin/start location
across two verified hole variants.

### 3. Four player slots and SimulateManager's four ball-like objects

`RPGolPlayerManager.cpp` creation at `0x802A344C..0x802A34EC`
allocates a manager (1272 bytes). Its array construction call at
`0x802A34A4` passes `r3 = manager+4`, stride `204 = 0xCC`,
and count **4**. A later loop at `0x802A34D0..E8` dispatches
`0x802A0B9C` once for each `manager+4+0xCC*i`, i=0..3.

Separately, `RPGolSimulateManager.cpp` at
`0x8029BB18..0x8029BB9C` allocates 1724 bytes, constructs
**four** inline objects beginning `SimulateManager+4`, each of
stride `428 = 0x1AC`. Array constructor wrapper at
`0x8029BACC` branches to `0x8029AB78`, a constructor
inside `RPGolMapObjBall.cpp` (`0x80296FD8..0x8029B240`).
This constructor calls `RPGolMapObjBase` at `0x8029AB90`
and stores a data-word/class-table hint at `0x8029ABA4`.

**Most important bridge:** `RPGolPlayer.cpp` at
`0x802A08B4..0x802A08F0` captures its player record receiver
in r30, indexes `i * 428`, loads the SimulateManager singleton
from r13 displacement **-23280** (source static slot
`0x804BF890`), adds `4+428*i`, and stores that pointer
at player record `+0x88`. Since the record begins
`PlayerManager+4+0xCC*i`, its visible memory slot is exactly

`PlayerManager +0x8C +0xCC*i -> SimulateManager +4 +0x1AC*i`.

This is source-backed receiver/index/dataflow, independently
corroborating the four repetitive ball-like pointers observed in
private paired MEM1/MEM2 by S002 PR #160. It is **not** merely
counting immediate `0xCC` values or matching compilation-unit
data ranges.

**A different field:** the per-record constructor
`0x802A0CB8..0x802A0DA0` writes allocated-object pointers
at record `+0x8C` and `+0xC4`; the latter maps to
`PlayerManager+0xC8+0xCC*i`. Do not conflate record
`+0x8C` with **manager** `+0x8C`: the former is
four bytes later because records begin at manager+4.

### 4. Actual three-float ball-related position writer

In `RPGolPlayer.cpp`, `0x802A0388..0x802A03C8`:

1. Reads f32 components from player record `+0x60,+0x64,+0x68`.
2. Copies them into record `+0x54,+0x58,+0x5C`.
3. Loads the indexed ball-like pointer from record `+0x88`.
4. Loads ball object `+0x4C` (base constructor's translation
   pointer).
5. Uses `stfs` to write three BE floats at translation-pointer
   `+0,+4,+8`.

The same class code at `0x8029F300..0x8029F31C` takes
`record+0x88 -> ball+0x4C` and **reads** its three f32
components back into record `+0x60..+0x68`.

Initial start position is source-connected: at
`0x8029F244..0x8029F264`, loads `RPGolFieldManager`
singleton via r13 displacement -23320 (source slot `0x804BF868`),
calls `0x802922EC` selected START translation getter, copies
its f32 triple into player record `+0x60..+0x68`.

**Therefore:** the executable establishes a connected
`start translation -> player-record position -> ball-object
translation` *code path*. The underlying data are first-class
source-backed motion/position candidates, far more specific than
the background-ticking word `RPGolMain+0x074`.

**Still unverified:** live player slot selection; observed player
movement versus ball movement through a shot; in-game coordinate
frame/units; real MEM2 sample coherence; collision/velocity/impact,
and whether the rendered active gameplay ball corresponds to the
indicated ball-like array element. S002's current two-bank dumps
have ~111-second native export timestamp separation; they do not
prove same-emulated-frame or even same-boot capture.

### 5. New source-backed numeric wind lookup (no RAM values yet)

`RPGolConfig::GetWind(int *dirOut,int *spdOut) const`, source
at `0x8029CE74..0x8029CEA4`, reads
`mCurrentHole=*(r3+0x98)` as a 32-bit index and shifts left
two for 4-byte table indexing.

It loads *direction raw integer* from
`0x804A8B54 + 4*holeIndex`, writes to `dirOut`;
loads *speed raw integer* from
`0x804A8B78 + 4*holeIndex`, writes to `spdOut`.
This is supported by register-argument order in the `GetWind`
function header; not guessed from nearby pointer values. Both
tables reside in `RPGolConfig.cpp` BSS range
`0x804A8B48..0x804A8BA0` according to
`RSPE01_01/splits.txt`. They are 0x24 bytes apart
(9 * 4 bytes each, consistent with nine-hole capacity).

**This is a true executable-confirmed field lookup.** Its array
contents are *runtime BSS values*, unavailable from the DOL
itself; no numerical wind direction, wind-speed units, sign
convention or display correspondence is verified yet.
CurrentHole raw index `1` in earlier source-gated captures
is not necessarily the displayed UI hole number.

## Next narrow studies / agent responsibilities (in order)

1. **S002 #160:** add source-reproducible assertion for
   `PlayerManager+0x8C+0xCC*i` to
   `SimulateManager+4+0x1AC*i`; verify exact correct record
   offset and first-word object hints in the existing private
   native pair; compare record+0x54..+0x5C with the ball translation
   pointer's BE-f32 triple *only locally*. Do not print numeric
   floats, addresses, private hashes or raw input. Source evidence
   is stronger but actual active ball/world coordinates remain
   unverified without **frame-aligned** movement and UI correlation.
2. **S002 #159:** augment selected Pin/Start hypothesis with
   source-backed `selectedObj+0x4C` accessor in its boolean-only
   report, test whether pointer equals `selectedObj+0x30`
   and whether the three BE floats are finite/plausible in
   same-snapshot RAM. No shortcut from source to actual world XYZ.
   New private float report must stay local, never GitHub.
3. **S002 #150:** add conservative, bounded **MEM1 runtime
   wind-table** validation with source-known `config+0x98`
   hole raw index `0..8`, checking both direction/speed
   integer tables; initial safe public output should say
   `source_lookup_present` and optional reviewed categorical
   bounds, NOT raw values or unknown unit labels.
4. **S000 #154:** distinguish `source_pointee_and_store_verified`
   from `runtime_frame_and_visual_semantics_verified` in
   canonical evidence ledger; do not mark model-training eligible.
5. **S001/S003:** only after offline source/private gates,
   preregister one true same-shot read-only frame-aligned
   confirmation with multiple time-matched idle/pointer controls,
   and human-observed ball motion. Do not re-run broad 28-child
   idle/aim scans or train on off-green 100ft penalty.

## Confidence / safety

| Target | Source code chain | Observed right-time XYZ | Training allowed |
| --- | --- | --- | --- |
| Pin selected translation accessor | yes, source +0x44 → object+0x4C | no | no |
| Start selected translation accessor | yes, source +0x50 → object+0x4C | no | no |
| Four ball-like simulation records | yes, two independent 4-slot constructors and explicit pointer indexing | only structural paired-bank snapshot | no |
| Ball-related translation writer | yes, 3 `stfs` via internal VEC3 pointer | not causally or visually confirmed | no |
| Wind direction/speed table lookup | yes, two 9-word MEM1 BSS arrays indexed by raw current hole | runtime values/units not inspected | no |
| Swing power, impact, velocity, score | no complete verified decoder | no | no |

**No automatic Dolphin launch, controller input, save edits, raw file
publication, network uploader, or library-byte export was done for
this study.** The native private executable and raw captures remain
private. Owner signoff and all regression/privacy gates are still
required before making any code changes to canonical readers.

## Source pointers

- `doldecomp/ogws/config/RSPE01_01/splits.txt`, Rev1 PPC unit
  boundaries and `RPGolConfig.cpp` BSS source map.
- `kiwi515/ogws_info/RP/RPSports/RPGolScene/RPGolFieldManager.h`,
  current pin/start pointers and member offsets.
- `kiwi515/ogws_info/RP/RPSports/RPGolScene/RPGolMapObjBase.h`,
  contradictory pointer offsets resolved using Rev1 DOL itself.
- `kiwi515/ogws_info/RP/RPSports/RPGolScene/RPGolConfig.h`,
  `GetWind` signature and raw hole index member.
- Existing S002 PRs #150, #159, #160 and S000 #154
  are the canonical owners of the follow-on validation.
