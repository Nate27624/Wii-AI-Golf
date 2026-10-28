# P0: golf-specific Near Pin sequence roots and active phase — archive test

**Stage:** unexecuted on real private banks; native source field types are
NOT established. This is one strictly bounded candidate relationship study,
not a result-variable map and not a request for any new gameplay or capture.

## Distinguish two different singleton managers

- The user actually tested `RPSportsSequenceMgr` singleton
  `0x804BF708` in #245. Its independent 36-word score table showed
  **0/36 changes** on four existing edges. This does not represent the
  Golf-specific sequence controller or Near Pin outcome producer.
- The public [Kokeshi `RPGolSequenceManager.h`](https://github.com/PackProject/Kokeshi/blob/main/include/Pack/RPSports/RPGolScene/RPGolSequenceManager.h)
  declares a separate `RPGolSequenceManager` singleton, with
  `mpSequenceTraining1` at +0x0C, `Training2` at +0x10,
  `Training3` at +0x14, and an active `mpPhase` at +0x18.
  Its public [symbol list](https://github.com/PackProject/Kokeshi/blob/main/base/symbols_sports.txt)
  identifies static `spInstance` at `0x804BF920`.
- The mode4 `GAMEMODE_TR_NEARPIN` ordinal is documented in public
  [Golf Config header](https://github.com/PackProject/Kokeshi/blob/main/include/Pack/RPSports/RPGolScene/RPGolConfig.h)
  and is already source-gated by original #231 reader on active Golf
  scene 5 and selected player/hole/pin/start.

**Critical caveat:** Kokeshi headers are independent public C++ layout
hypotheses, not themselves execution proof in user's RSPE01 Rev1 build.
Do not infer which TrainingN corresponds to NearPin. `mpPhase` can point
to an **embedded phase subobject** inside a sequence, so a non-alias to
the three training root pointers is NOT proof none is active. No
`RPGolPhase::WaitFrame` or main loop counter is a verified machine
physics-step event.

## Distinct narrow experiment

`scripts/audit_p0_golf_nearpin_sequence_roots_private.py` inherits
#231's original *all fourteen* MEM1/MEM2 bank SHA provenance checks
before and after reading, Rev1 mode4 selected object source gates,
private ignored capture-root boundaries, and read-only mmap. It only
reads four header-proposed words in a **single source static singleton
instance**, with native-bank range tests. It returns:
- **per numbered capture**: singleton presence, training/active pointer
  range classes, active pointer direct equality to training root indices
  (if any), nonnull training root distinctness.
- **five pre-registered numbered edges**: manager pointer equal,
  each training/active pointer word equal, active pointer change flag.
  No inferred temporal order, physical impact, training-state type,
  displayed result, or cross-boot/guest-frame relationship.
- **No private bytes**: never print pointer values, addresses of runtime
  objects, hashes, raw words, paths, score, float triplets, or human phase
  labels. No arbitrary pointer graph traversal or memory search.

Native source validation is still needed for each proposed struct
member offset; this script does NOT promote header labels to Rev1 class
fields. All result, physics, training, publication flags remain FALSE.

## Decision / stop gate

After S002 source-owner verifies exact Rev1 PPC instructions that read
`RPGolSequenceManager+0x0C/+0x10/+0x14/+0x18` and receives independent
S000 approval, **at most one** new local read-only run on the SAME
already-preserved seven pairs is warranted.

- If singleton is absent/unstable or all pointers are null/out-of-range,
  **stop**; no further pointer carving.
- If active phase changes on numbered edges and training roots are
  stable, source owner may trace only mode-specific active phase dispatcher
  and direct Near Pin outcome producer after the real mode4 type is proved.
- If active phase does not change, do not infer no result; the caller
  could retain one phase while an internal state counter changes.
- Source/C++ role remains unverified until native Rev1 code supports it,
  and visible result needs separately attested guest-frame evidence.
- Neither source-global nor selected ball is called rendered or physics
  XYZ. Separate S001 #215/#248/#272 runtime watchers/frames own that P0.

This does not duplicate prior #245 generic score table, #256 concluded
unproductive UI text xrefs, #240 global-ball or #263 receiver analyses.
No user commands or Dolphin shots requested merely to review this PR.


## Stronger typed outcome edge: `RPGolPhase::CommitResult`

Independent public [Kokeshi NTSC-U Rev1 `RPGolPhase.h`](https://github.com/PackProject/Kokeshi/blob/dfbdda61aadad423911d5345f67f8793aa92cd5f/include/Pack/RPSports/RPGolScene/RPGolPhase.h)
declares the instance method:

```cpp
void CommitResult(u32 ftScore, u32 trScore, u32 trSubScore);
```

The same header declares `Calculate()`, `Finish()`,
`Check()`, `WaitFrame()`, and `Enter()` on `RPGolPhase`.
`RPGolSequenceManager::mpPhase` is typed as `RPGolPhase*` in
that separately published header. This is a **named C++ interface
linking active Golf phases to a result commit**, a better lead than
generic formatted-text sinks or whole score-table scans.

**Crucial limits:** The upstream pinned source provides the
**declaration only**. Independent searches of current public
`doldecomp/ogws`, `kiwi515/ogws_info` and this repo did not
locate the function's body or its exact Rev1 machine-code entry.
The names `ftScore`, `trScore` and `trSubScore` are argument
identifiers, **not evidence of Near Pin distance, feet, meters,
single-hit proximity, the 100-ft miss penalty, persistent storage,
game-frame event or UI text.** Neither does the declaration prove
that training mode 4 executes this method.

**Pre-registered source-only decision:**
1. Source owner #219/#231 should verify the Golf-specific singleton
   and phase-pointer instruction accesses in original Rev1 code,
   then locate the exact `CommitResult` method body/callsite
   **without making up an address from adjacent named functions**.
2. A positive source chain must show a mode4 training phase
   invoking `CommitResult`, followed by the exact result
   receiver/write path. Identify which of the three arguments
   is used for the displayed outcome, if any; all three are
   untrusted until proven.
3. If no exact Rev1 entry/caller can be identified in ONE
   bounded review, report ABSTAIN, leave the result variable
   unverified and preserve the source-only STOP gate. Do not
   turn this into generic GPR/printf/score-table scan families.

This finding raises the expected value of **typed outcome tracing**
over running the current unconfirmed +0x0C..+0x18 pointer reader.
No new native run, Dolphin, shot, frame or training data is authorized.


## Additional independent source discrepancy: singleton symbol class-length

The pinned Kokeshi `base/symbols_sports.txt` entry is literally
`spInstance__16RPGolSequenceManager=0x804bf920`, but the pinned
C++ header declares `class RPGolSequenceManager`, whose identifier
has **20 characters**; `RPGolSequenceMgr` has 16. The
`RP_SINGLETON_DECL(T)` macro in pinned `RPTypes.h` really
declares `static T* spInstance` so this difference is not a
benign macro-rewritten field name. The source symbol file may have
a stale/manual typo or may refer to a differently named binary
class; this discrepancy **does not establish** which interpretation
is true.

Therefore the pair `0x804BF920` + `RPGolSequenceManager`
has **only candidate confidence**. No operator execution of the
#277 private pointer reader is warranted based on this header/symbol
join alone. Require exact Rev1 PPC code xrefs/load/store or a
second independently mapped symbol with full object provenance.
A global static pointer-looking word or a successful test against
fabricated RAM would not resolve the class ownership.

The named `RPGolPhase::CommitResult` API is a distinct source
declaration; the singleton symbol typo does not establish
its machine-code address or whether mode 4 invokes it.


## P0 typed result-presentation object and saved-record distinction

Another **independent public-source *type*** in pinned Kokeshi Rev1:

- [`RPSportsBaseScene.h`](https://github.com/PackProject/Kokeshi/blob/dfbdda61aadad423911d5345f67f8793aa92cd5f/include/Pack/RPSports/RPSportsBaseScene.h):
  inherited scene `RPSportsTrainingResult* mTrainingResultLyt` at
  **scene +0x84**; scene `mTrainingGame` at +0x48.
- [`RPSportsTrainingResult.h`](https://github.com/PackProject/Kokeshi/blob/dfbdda61aadad423911d5345f67f8793aa92cd5f/include/Pack/RPSports/RPSportsTrainingResult.h):
  `LoadResource`, `Reset`, `Calculate`, `UserDraw`;
  `mFlags` at result-layout object +0x6C, **not identified numeric distance**.
- Pinned [`base/symbols_sports.txt`](https://github.com/PackProject/Kokeshi/blob/dfbdda61aadad423911d5345f67f8793aa92cd5f/base/symbols_sports.txt)
  independently labels `RPSportsTrainingResult::Calculate`
  **0x80200600**, `Reset` 0x80200A88, `UserDraw` 0x801FFEE0,
  `LoadResource` 0x80200D38.
  These are source annotations, **not a confirmed Golf Near Pin
  result-screen instance or its dataflow**.
- [`RPSportsSequenceMgr.h`](https://github.com/PackProject/Kokeshi/blob/dfbdda61aadad423911d5345f67f8793aa92cd5f/include/Pack/RPSports/RPSportsSequenceMgr.h):
  generic `ETrainingGame mTrainingGame` at **+0x0C** (0..2); this
  field is categorically DISTINCT from the standard Golf scoring
  `mGolfScores[9][4]` at +0x14. The previous 0/36 result says
  nothing about active training-game selection.
- [`RPSportsPlayerData.h`](https://github.com/PackProject/Kokeshi/blob/dfbdda61aadad423911d5345f67f8793aa92cd5f/include/Pack/RPSports/RPSportsPlayerData.h):
  `u16 mGolTrainingRecords[3]` at **player-save object +0x296**,
  accessed via `getGolTrainingBest(EGameID)`. This is
  explicitly a **persistent best-record** category, NOT a current
  shot-distance variable, current ten-shot total, result-layout
  numeric field, or physics position.

### Better constrained S002 source chain (no native scan authorization)

1. Use the existing source-typed Golf scene identity and **only verify**
   its inherited `mTrainingResultLyt+0x84` membership via Rev1
   opcode-level caller/layout source, rather than another generic
   `findTextBox` scan. The published class types support this as a
   candidate pointer; no new Dolphin action or private pointer
   dereference is authorized merely by a header.
2. Follow only an actual `RPSportsTrainingResult::Calculate` /
   `UserDraw` caller and its **typed score arguments**. A persistent
   `mGolTrainingRecords` value must be rejected as the live per-hit
   metric unless a separately proven result path links the quantities.
3. Cross-check source `mTrainingGame` enums only if mode-4-to-training
   sequence number really needs disambiguation, and require same-shot
   frame/visual witness before claiming Hitting-the-Green result.
4. A direct caller yielding NO typed score dataflow is **ABSTAIN**.
   Do NOT reopen generic 60-lookups/19-zero-argc, static sprintf,
   score-table deltas or arbitrary heap scans.

**All addresses above are *public static field/code annotations*, not
validated runtime values.** The current #277 Kokeshi singleton
mangling mismatch is still unresolved and its local pointer reader
remains blocked from operator execution. Training/publication remain
FALSE.


## P0 alternative Near Pin outcome discriminator: typed ground collision attribute

**Source-only typed lead; not an observed runtime value.** The independent,
immutable Kokeshi Rev1 header
[\`RPGolCollisionModel.h\`](https://github.com/PackProject/Kokeshi/blob/dfbdda61aadad423911d5345f67f8793aa92cd5f/include/Pack/RPSports/RPGolScene/RPGolCollisionModel.h)
defines:

- \`EGndAttr_Green=6\`, \`EGndAttr_GreenEdge=9\`, \`EGndAttr_Cup=11\`,
  and \`EGndAttr_Target=14\` (separate named values, all **public enum
  hypotheses** until native Rev1 comparisons/producer are checked).
  It also distinguishes rough, bunker, water, OB, fairway and tee.
  Do **NOT** silently count green edge, target or cup as green, or infer
  any training pass/fail policy from the enum alone.
- \`RPGolCollisionTriangle\` has a \`u16 attr\` member at
  **triangle-relative +0x0E** and \`mPosIdx/mDirIdx/mNrm{A,B,C}Idx\`
  members plus length; its declaration implies a **0x10-byte
  triangle-record stride** (candidate, compiler layout not
  independently matched to original PPC).
- \`RPGolCollisionModel\` has
  \`RPGolCollisionTriangle* mTriangles\` at **model +0x0C**,
  \`u32 mNumRPTris\` at **model +0x5C**, and \`GetTris/ GetNumTris\`
  accessors; these are **type/memory-layout claims in a public
  header**, not a verified instance or an invitation to index RAM.
- The independently pinned public
  [\`base/symbols_sports.txt\`](https://github.com/PackProject/Kokeshi/blob/dfbdda61aadad423911d5345f67f8793aa92cd5f/base/symbols_sports.txt)
  lists \`spInstance__19RPGolCollisionModel=0x804BF908\`.
  The class name \`RPGolCollisionModel\` has 19 characters, so
  this symbol's encoded class-name length is **internally
  consistent**, unlike the still-disputed Golf sequence singleton
  \`spInstance__16RPGolSequenceManager\` vs its 20-character
  class. A consistent symbol name **still does not prove the
  actual native pointee identity**.

**Why this is promising:** one missing Hitting-the-Green outcome
predicate is *whether the stopped ball is on the green*. A typed
surface enum could in principle discriminate **a ball's current
contact triangle surface** independently of an operator-entered
100-foot off-green penalty or a cumulative 10-shot total. It is
potentially a better causal feature than unnamed player-record
+0x30/+0x90 float words. But the stored \`attr\` belongs to
**static collision geometry**, not a live selected-ball collision
contact. Neither a triangle's \`attr=Green\` nor the existence of
the triangle table shows the moving ball touched/rested on it,
or that the training result scorer tests this enum.

**One narrow, owner-disjoint source decision (S002 #219/#240 and
Near Pin #277/#184):**

1. Locate an already identified **source-typed ball collision
   consumer/contact result** and determine whether its final
   grounded-state triangle index resolves into the published
   \`RPGolCollisionTriangle::attr\` or an equivalent enum. Require
   exact native Rev1 PPC member and range checks; do not search
   arbitrary RAM for byte/halfword value 6.
2. Determine whether training mode4's result producer compares
   \`Green\`, \`GreenEdge\`, \`Target\`, or something else to
   assign accepted/penalty outcome. Do not assume green membership
   alone equals success or that it updates \`CommitResult\`.
3. Only after S001 establishes a genuinely executed post-update
   clock, distinguish **contact**, **final settled contact** and
   **result acknowledgment** in the *same confirmed shot/actor*.
   Without ball→collision→score chain, emit
   \`NEARPIN_GROUND_ATTR_CONTACT_ABSTAIN\` and STOP. No
   score calibration or training-data promotion.

No static table dump, source-code xref family, new memory scan,
user PowerShell, Dolphin boot, swing, private bank upload or
new runtime-variable claim is justified by this public declaration
alone. Existing game-step, rendered actor, power, result and training
gates remain false.


## New bounded Rev1 mode-4 setup dispatch source experiment

**Stage:** synthetic tests only until source-owner review and exact native
report. Named public function entries and independent same-Rev1
\`doldecomp/ogws\` symbol-map bounds now permit a **61-word fixed
window**, not a generic program-wide xref pass:

| Public source-annotated function | Exact Rev1 public entry | Published byte extent | PPC words |
| --- | --- | --- | --- |
| \`RPGolConfig::SetupTrainingGame()\` | \`0x8029D778\` | \`[0x8029D778,0x8029D810)\` | 38 |
| \`RPGolConfig::SetupGame()\` | \`0x8029D810\` | \`[0x8029D810,0x8029D86C)\` | 23 |

Source citations: [Kokeshi \`RPGolConfig.h\` pinned revision](https://github.com/PackProject/Kokeshi/blob/dfbdda61aadad423911d5345f67f8793aa92cd5f/include/Pack/RPSports/RPGolScene/RPGolConfig.h),
independent [doldecomp/ogws \`RSPE01_01/symbols.txt\`](https://github.com/doldecomp/ogws/blob/main/config/RSPE01_01/symbols.txt).
The two aligned source map entries are annotations, not proof of a compiled
runtime call into the TrainingN classes.

The new
\`scripts/audit_p0_nearpin_training_setup_dispatch_private.py\`
inherits the **original #231 14-bank SHA pre/post**, exact
game revision, scene5/mode4/selected roster/geometry/source qualification,
and read-only mmap of the same original seven numbered pairs; refuses
wrong function extents or code drift across pairs. Reads **only 61 guest
source instruction words per capture** and reports (without raw PPC words,
runtime pointer values, guest heap addresses, bank hashes or paths):
- direct PPC unconditional \`BL\` call locations classified into
  *current function*, *same published Config source unit*, or
  *outside known Config unit (untyped)*;
- conditional and nonlinked branch counts, ordinary \`blr\`
  count, and explicitly recorded indirect branch/system-call hints;
- literal-immediate comparison sites for modes 3, 4 and 5 as
  **syntax-only**. A \`cmpwi ...,4\` site is not a proven test on
  current \`mGameMode\`, and even a following branch is NOT proven
  mode4-reachable without full receiver/control provenance.

**Single useful decision rule:** A source instruction directly
comparing an integer to literal 4 plus a typed Config mode-value load
and a branch selecting a source-owned training sequence would be a
positive *source-mode-dispatch* lead. The classifier alone **cannot
make that claim**. If no such direct typed link can be proven after
this one bounded window, label
\`NEARPIN_SETUP_DISPATCH_ABSTAIN\`, do not open more generic
R13/source xref microstudies or dereference disputed sequence-manager
\`0x804BF920\`.

All returned flags remain false for actual phase identification,
\`RPGolPhase::CommitResult\`, current ball contact/green status,
Near Pin single-hit score/distance, guest physics time, rendered ball,
impact/power, training and publication. This test asks the game
*which setup routine's code it could use*, not the contents of a
RAM score table. No new Dolphin session, control input, shot or
native memory export is required.
