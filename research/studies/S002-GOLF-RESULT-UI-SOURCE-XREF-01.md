# S002 P0: Golf result/distance UI code producer — bounded first-hop source xrefs

## Hypothesis, scope, and source provenance
We seek the source routine **that renders the Hitting-the-Green on-screen
distance/result**, then the value producer and source-owned backing object
needed before training on a measured outcome. This PR does **not** claim to
have identified that producer or decoded the value.

Public, US Rev1-specific references:
- `kiwi515/ogws_info/RSPE_r1.map.csv`: `TextBox::SetString`
  0x8007C00C / 0x8007C074, `snprintf` 0x800B7500,
  `sprintf` 0x800B75D8, `swprintf` 0x800BCE24,
  `RPSysMessage::GetMessage` 0x80190D90,
  `PSVECSquareDistance` 0x800E86D0,
  `Golf::CalcRealScore` 0x8029CCBC,
  `Golf::UpdatePlayerScores` 0x8029CF24,
  `Golf::IsTrainingGame` 0x8029D3AC, and the two
  `Golf::GetPlayer[Score|Strokes]OnRelativeHole` entries.
- `doldecomp/ogws/config/RSPE01_01/splits.txt`: published Golf object units,
  including **RPGolScene_unsplit.o** at 0x802A79F8–0x802C7924.
  Reused existing trusted public split index and Rev1 decoder from #219.
- `kiwi515/ogws_info/RP/RPSports/RPGolScene/RPGolConfig.h`:
  the Config score table is a standard-mode score field, with **no known
  direct Hitting-the-Green result UI mapping**.
- #239 and #245 operator experiments: Config 9x4 and SequenceMgr 9x4 score
  entries changed 0/36 on four **human-provisionally-labeled** edges; do not
  treat those negatives as proof a game UI distance is absent.
- #250: seven numbered capture labels/order not independently verified.

## Distinct new source investigation
`scripts/audit_p0_golf_result_ui_xrefs_private.py` reuses #219's
`checked_private_b0` original manifest/SHA, RSPE01 Rev1 and pinned 832-unit
source split index. It visits ONLY the published Golf code units and extracts
PPC **direct b/bl** destinations equal to the exact public symbols above.
Each source-site report gives *public file-relative code offsets only* and a
bounded count (never private/native instruction values). Groups nearby direct
BLs in purely geometric 0x200-byte source-code windows to prioritize manual
analysis; co-occurrence is **not function identity, callgraph connectivity,
execution or causal dataflow**.

No hit at a sink **cannot exclude** indirect bctrl / vtable dispatch, message
resources, intermediate RPSystem layout wrappers, inline formatting or other
geometry helpers. Formatting sinks may be shared by ordinary golf HUD/round
scores/wind and are **not known to be the Hitting-the-Green final result**.

## Next verification gates and handoff
1. Run existing source-gated original B0 audit locally, *once*, with strict
   exact pinned head and synthetic tests, no new emulator action or download.
2. Inspect any exact direct formatting + nearby score/geometry source-site
   candidates. Use PPC function boundary/control-flow reconstruction and
   backward trace caller input registers to typed source objects. An
   `sprintf` BL by itself proves neither numerical value nor units.
3. Distinguish on-screen **final distance-to-pin** from UI aiming distance,
   target graphics, stroke score, persistent best, and fallback 100.0 ft
   off-green penalty. Find the actual producer + typed store (if any), or
   report *computed on demand without persistent field*.
4. S001/#248 needs independently attested guest-physics-frame sample + visual
   output event to tie candidate state to a screenshot/score; old snapshot
   phase/shot labels are not machine verified. No training until S002 score
   semantics and S000 gates independently approve.

## Safety and handoff
S002 source unit owner #219/score owners #239/#245, S000 registry #205,
S001 guest-frame #248. New-only files, no edits to another agent's analyzer
or production CLI. Code PR stays DRAFT pending owner and complete suite.

Fabricated-only focused tests verify direct BL, b tailcalls, indirect bctrl
abstention, exact symbol matching, source unit scoping, and privacy. GitHub
Actions synthetic outcomes do not imply native B0 or live Dolphin validation.
No ROM, raw memory, snapshots, paths, hashes, controller input or private
reports uploaded; all physical XYZ, velocity, impact, power, training and
publication false.

## Operator local B0 direct xref result (2026-10-28)

The original locally-preserved B0 code (US RSPE01 Rev1) was inspected by
the operator at precisely pinned #256 head `7494bbe39d02116303b26bcec060977e9459ab35`.
The 10 focused synthetic tests, native source, SHA and 25 Golf public units
passed. Observed direct `bl` counts: `sprintf=14`,
`PSVECSquareDistance=18`, `Golf::CalcRealScore=2`,
`Golf::UpdatePlayerScores=1`, `Golf::GetNthHoleScore=1`,
`Golf::GetNthHoleStrokes=3`, `Golf::IsTrainingGame=4`.
Exact `TextBox::SetString=0`, `snprintf=0`, `swprintf=0`,
`RPSysMessage::GetMessage=0`, but indirect/virtual layout calls remain
uninspected. No 0x200-byte source window contained both a known formatter
and the tracked math/score category. The xref supports REAL source-call
existence, not a Hitting-the-Green result producer or memory state.

### Focused #256 extension: bounded sprintf argument syntax

`scripts/audit_p0_golf_sprintf_arg_origins_private.py` reuses original
#219 SHA and public Golf code boundaries, checks exactly 14 `bl sprintf`
sites, and classifies only <=0x80 preceding code bytes in each **same source
unit**. It emits the source-relative code offset, last recognized GPR r3/r4
definition syntax after the nearest control-flow barrier, and nearby
PowerPC FPR load/op/store counts. Branch/call instructions are hard
barriers; earlier register writes do not count as reliable origins. Even
the post-barrier syntax is **not CFG reaching-definition proof**, and FPR
activity is not necessarily a `sprintf` float argument.

This stage does NOT read literal format strings or attempt to decode numeric
precision/units, destination buffer contents, UI layout dispatch or actual
score state. A direct `sprintf` call may format ordinary HUD values or
logging unrelated to the user's visible result. A further owner-reviewed
exact caller/input and format string provenance study is required after
the sanitized per-site metadata is examined. Source/owner review and
independently attested guest frame+visual output event are still required.
No new Dolphin, capture, controller action, raw private files or upload.
