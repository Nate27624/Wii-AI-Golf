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

## Real 14-sprintf argument study, operator 2026-10-28

The user ran the exact source `a3f93ad882a56a637659adb773da772463a0ef6c`
with 12/12 local synthetic tests and original B0 source SHA passed.
All fourteen sites were within `RPGolScene_unsplit.o`, clustered:
`+0x07B98,+0x07BBC`;
`+0x1779C,+0x177C0,+0x177E4,+0x17808,+0x1782C,+0x17850`;
`+0x18EC0,+0x18EF0,+0x18F20`;
`+0x19A50,+0x19B50,+0x19B74`.
Each output-buffer r3 came from `addi r3,r1,...` syntax (stack).
Each format pointer r4 came from `addi r4,r31,...` syntax.
No FPR load/op was seen in the **post-barrier bounded window** at any
of the fourteen direct BL sites. This does NOT rule out values computed
earlier or integers/GPR/floats prepared outside the bounded window.
No format literals, types, UI linkage, runtime execution, backing memory
or result values were identified.

### Next disjoint code-only slice, without a new memory scan
`scripts/audit_p0_golf_sprintf_r31_variadics_private.py` scans a
bounded **0xC00-byte syntactic predecessor** for a recognized r31 register
definition and tentative `lis r31,...; addi r31,r31,...` construction,
plus within the last 0x80 bytes following the nearest branch/call, last
recognized r5/r6/r7 assignment classes (integer varargs candidates).
The scan may cross unknown function entries and report unexecuted
branches: **no CFG reaching-definition, pointer, format literal or true
UI distance value can be inferred even when syntax matches**. An absent
r31 definition is an unresolved source region, not proof no string.
Keep all format bytes and native values private. The code explicitly
refuses any direct sprintf call count other than the original 14 and
revalidates original B0 SHA after reading.

Use this to decide whether the best *next source trace* is value-side
integer arguments to a specific formatting call, a typed static format
string origin, or else the indirect NW4R/RPSys layout/message dispatch
path. Separate S001/#248 guest-frame and visual result link remains P0.

## Real second-stage r31/variadic register result, operator 2026-10-28

The owner ran #256 exact pinned source `bd3335a50c78e85896b75329a4b9fed9755059b8`
locally with original B0 SHA/source gate PASS and 15/15 focused synthetic
tests PASS. All 14 `bl sprintf` sites reconfirmed. The source-syntax
analysis found **11 possible r31 high/low constant pairs**, three
`addi r31,r6,imm` categories, and **12/14 sites with a control-flow
barrier after the candidate r31 definition**. Thus the existing
constant-construction classifications are **not trusted format-string
pointers or runtime paths**. r5 was syntactically prepared at all fourteen
sites from r26/r27/r28/r29; none of those underlying source values were
read or typed. No source-proven distance, score, layout/render, pointer,
function CFG, output format or training variable established.

## Third-stage disjoint strict format-category probe

`scripts/audit_p0_golf_sprintf_format_types_private.py` is a
**more conservative** local offline, original-B0 source-gated study.
For precisely the same fourteen exact direct `sprintf` sites, it inspects
at most 0xC00 preceding bytes and accepts a possible format pointer only
when a **single bounded branch-free suffix** contains either:

- `lis r31,hi; addi r31,r31,lo; addi r4,r31,disp`, or
- `lis r6,hi; addi r31,r6,lo; addi r4,r31,disp`,

with no recognized or ambiguous intervening tracked register writes.
An unknown source, wrong target, branch/call barrier, unsupported
register clobber or pointer outside original MEM1 yields `NOT_QUALIFIED`,
not an invented result. For qualifying candidates, **private local only**,
it reads at most 96 bytes at a bounded candidate address and emits ONLY
coarse types: NUL-terminated printable ASCII candidate, count of
recognized printf conversions, integer/float/string/pointer conversion
presence. It NEVER emits the literal text, candidate address, source
instruction words, runtime pointers, gameplay numeric values, full paths,
hashes or ROM bytes.

A constant construction **even within a branch-free linear suffix**
is still syntactic evidence, not complete function CFG reaching-def
or guarantee that this path executed or the source address is a true
literal pool. Presence of `%f` or `%d` alone does not identify the
Hitting-the-Green result, units or a typed backing memory field.
Unqualified sites remain `unknown`, not `not numeric`.

Source correctness review #259 independently hardens original
`_reg_def_class` for rA/write-update/multiword clobbers, and is NOT
overwritten by this new-only extension. Integrate only with S002
owner approval. The independent S001 guest frame+visual result contract
in #248 is unchanged. All training/publication claims remain FALSE.


## New real strict format-category result, operator 2026-10-28

Exact reviewed branch source: \`21ad5c9303e32d78ee704af13273abe97bad3ef2\`.
Original B0 source/manifest SHA PASS; 17/17 real-local focused
synthetic tests PASS. Of 14 exact \`bl sprintf\` sites, only two had
strict branch-free source-constant candidates and local NUL-terminated
ASCII strings with one recognized **integer** conversion:
\`RPGolScene_unsplit.o+0x18EC0\` and \`+0x19B50\`.
The other 12 all abstained \`r31_definition_outside_safe_segment\`.
They are UNKNOWN, not evidence of nonnumeric output.
Nothing so far ties either result to the Golf Hitting-the-Green
display, distance units, backing source state or actual execution.

### Follow-up with unique value of information: two literal context flags

\`scripts/audit_p0_golf_two_sprintf_literal_roles_private.py\` reuses
the same exact 14 direct BL source and original B0 SHA gate, insists
that only the *two* previously qualified file-relative code positions
have accepted constant reconstruction, then classifies the two local
96-byte candidate NUL-terminated ASCII strings into **coarse categories
only**: explicit distance unit (feet/ft/yard/yd/meters/cm/inches),
distance/target terms, result words, score/stroke, timer, debug/counter
or no recognized role token. No text, numeric literal/address, source
code, raw memory contents, SHA or path is printed.

Even a positive distance-unit flag is an *unverified heuristic* of
static format-string content, not proof the call executes on the
actual result screen, its displayed number is a true distance, or
any source memory field is typed. A negative flag could be an
abbreviated or localization-specific format; it does not disprove the
GUI label. If both are unhelpful, stop the sprintf family and
prioritize NW4R/RPSys layout/message dispatch or independent
operator-attested result screen evidence with S001/#248.

The dedicated new suite has 17 fabricated tests and runs with the
four earlier #256 suites on both Windows and Ubuntu. Changes are
new-only; #259's unrelated GPR-clobber correction remains in a
separate owner-review PR. Keep private archive unmodified and
publication/training false.


## Operator literal-role audit negative and source direction change (2026-10-28)

The operator verified exact pinned #256 \`c46833a4c418a949f77498d5cc71e6c7e7ba04d7\`
using 17/17 focused synthetics and original B0 source/SHA gates.
Both previously qualified one-integer static format candidates,
\`RPGolScene_unsplit.o+0x18EC0\` and \`+0x19B50\`,
had **no recognized distance-unit, distance/target, result-screen,
score/stroke, timer, debug or counter keywords** in the bounded
printable string context. The output returned
\`NO_KNOWN_ROLE=True\` for both. This is a genuine negative on the
allowed English token list; it cannot rule out numeric-only,
resource-based or translated UI text. Deprioritize further generic
\`sprintf\`/r31 scans unless a verified UI dataflow emerges.

### Better source-defined formatting wrapper

Public \`kiwi515/ogws_info/RP/RPKernel/RPSysLytTextBox.h\` declares the
Golf-compatible \`RPSysLytTextBox\` interface. Concrete RSPE Rev1
function addresses:

- \`RPSysLytTextBox::setMessage\` 0x80198FD0 (va_list overload);
- \`RPSysLytTextBox::setMessage\` 0x80199148 (variadic overload);
- \`RPSysLytTextBox::setText\` 0x8019931C (formatted text);
- \`RPSysLayout::findTextBox\` 0x80196280;
- \`RPSysLayout::create\` 0x80196A38.

The public header duplicates 0x80198E24 for both \`setScaleX\` and
\`setMessage(text)\`; this ambiguous code address is intentionally not
claimed as a sink. The documented \`RPSysLytTextBox\` API can render a
formatted text message via a BMG resource without any direct
\`TextBox::SetString\` BL from Golf. The original #256 first-hop scanner
did not include these exact wrapper methods; zero direct base-NW4R
setter hits was therefore not evidence of absent text UI.

### Distinct read-only test

\`scripts/audit_p0_golf_layout_text_wrapper_xrefs_private.py\`
reuses unchanged #219 original B0 SHA/Rev1 gate and #256 public 25
Golf source object units. It counts direct PPC b/bl sites for the five
exact wrapper calls above, and returns only public *source-unit-relative*
code offsets and sorted co-occurrence windows. It never emits native
instruction words, private RAM/ROM bytes, static/heap addresses, message
text, guest code contents, SHA, local file paths or game values.

A direct BL into \`setMessage\` plus nearby \`findTextBox\` would prioritize
the **code location** for typed value provenance, but *window
co-occurrence is NOT same function/CFG/dataflow/runtime proof*.
A zero direct hit may reflect indirect \`bctrl\`/vtable calls or other
text interfaces. If direct wrapper calls are absent, investigate the
indirect dispatch path conservatively rather than promoting a
negative no-UI conclusion.

No live Dolphin, new capture, human-provisional phase promotion or
training. All rendered/result/backing-physics semantics remain
UNVERIFIED; S001/#248 independently owns same guest-frame association.


## Actual local Golf formatted layout wrapper xrefs (operator 2026-10-28)

The operator used SHA-pinned source \`68c7d804be45e099a9de8b34d10b16514090e1a3\`
with 13/13 focused synthetic tests passing and canonical original B0
source/manifest SHA passing. In the 25 Golf public code units there are
**60** direct \`RPSysLayout::findTextBox\` BL, **49** direct
\`RPSysLytTextBox::setMessage(...)\` BL, **11** direct
\`RPSysLytTextBox::setText(...)\` BL, **12** direct
\`RPSysLayout::create\` BL, and **zero** direct calls to the
\`setMessage(va_list)\` exact anchor. All returned UI wrapper BLs were
within \`RPGolScene_unsplit.o\`. This proves Golf's source directly uses
the formatted text layer; it does **NOT** establish that any candidate
belongs to the Hitting-the-Green result or carries the actual result
value. Notably a \`findTextBox\` at +0x07C28 and \`setMessage\` at
+0x07C40 are only 0x18 bytes apart; nearby presence alone is not
control-flow/receiver identity or same-message semantics.

### Constrained next source-only test and stopping condition

\`scripts/audit_p0_golf_message_arg_pairs_private.py\` reuses the
exact B0 SHA and public Golf source unit trust gates. Only direct
\`findTextBox\` followed by a direct formatted-message/text wrapper
call **within 0x40 bytes**, with NO intervening branch/call, can be
reported. For each such source-code pair, it records a possible
intervening r3 clobber (the prior call may return the pane in r3),
plus the *last syntactic* post-lookup \`argc\` definition: \`r7\`
for \`setMessage(...)\` or \`r5\` for \`setText(...)\`. The first
variadic value register candidate is \`r8\` for \`setMessage(...)\`
or \`r6\` for \`setText(...)\`; only source classes (register move,
memory load, unknown, etc.) are emitted.

The code does not recover BMG group IDs, message IDs, pane names,
numeric argument contents, actual function CFG or incoming branch
edges, and it cannot identify a displayed result number just from
\`argc>0\`. The group/idx arguments are excluded from the output,
to avoid unauthenticated game semantic promotion and private values.
Unknown/zero argc also cannot prove no number, because the analysis
is limited to definitions AFTER the last lookup and the UI setter
may access a stored value via indirect dispatch.

**Stop rule:** If the operator run produces no source-local paired
formatted call with an explicit nonzero argument count and plausible
value-side source, do NOT request another static UI xref iteration;
next step requires S001 independently attested result screen and
guest-frame linkage. If promising pairs appear, only trace those
specific source-code locations and ask the S002 owner to connect
pane/message and typed value producer, without promoting training.
Source owner and downstream S000/S001 review remain required.


## Terminal source-only P0 UI audit: STOP RULE MET (operator October 28, 2026)

Operator ran exact pinned commit `9c3438a2326655ecf643e6bd506975117274465d`
and its 16/16 focused fabricated tests on Windows, then successfully
revalidated original private B0 manifest/SHA, RSPE01 Rev1 and public
Golf source ownership. No new emulation session or RAM capture.

Observed direct Golf source anchors:
- 60 `RPSysLayout::findTextBox` BL.
- 49 formatted `RPSysLytTextBox::setMessage(...)` BL.
- 11 formatted `RPSysLytTextBox::setText(...)` BL.
- 19 pairs with lookup→formatted call separation <=0x40 bytes, NO
  intervening direct branch/call and no recognized r3 overwrite.
- **19/19** pairs have post-lookup `argc` classification `zero`.
  **0/19** have known nonzero argc; first variadic source is
  `not_resolved`. These can be ordinary static label/message
  initialization, but displayed result/UI ownership is still UNKNOWN.
- Pair-site clusters in `RPGolScene_unsplit.o` include +0x07C28...,
  +0x17A1C..., +0x17F8C..., +0x19C0C..., all *public unit-relative*.

**Evidence boundary:** This is a scoped negative for one *local,
linear direct-call pattern*, not proof all Golf UI setters use zero
arguments. The source analyzer does not prove same runtime function,
incoming CFG edges, resource IDs, live execution, pane identity or a
numerical result field. A result screen may update text later through
indirect virtual calls, different code, or a separate resource.

**Hard compute stop** for this S002 owner branch: NO additional
unanchored static UI xrefs, sprintf, score-table scans, or new native B0
runs without externally attested on-screen result/guest-frame evidence.
Draft PR #256 is research-complete for first-hop structural call-path
triage, **not** ready to merge as a verified RAM variable.

**Required next disjoint stage:**
1. S001 #215 live owner must first qualify stationary, noninterfering
   read-only watcher and a genuine game *guest-physics-frame* clock.
   Existing bridge ticks are NOT game guest frames.
2. S001 #248 dual-object contract (synthetic only) requires source
   selected and source-global balls, cache CC, stable pin/start/config
   and same-frame identity; it cannot authenticate a frame by itself.
3. With informed operator permission, a controlled Hitting-the-Green
   PRE/POST/RESULT visual event may use #184's private capture plan,
   but that manual workflow alone does **not** guarantee that the UI
   screenshot and MEM1/MEM2 were sampled in one guest frame.
4. S002 should then trace only a concrete visually linked result
   setter and source-typed numeric producer; keep unknowns as abstain.
   S000 #205 must independently review before any training.
   
All UI outcome, physics XYZ/velocity/contact/power, frame
synchronization, training and publication remain UNVERIFIED/FALSE.
