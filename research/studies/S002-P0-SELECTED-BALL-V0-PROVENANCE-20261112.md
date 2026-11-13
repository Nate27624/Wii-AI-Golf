# S002: selected Ball initial-velocity source provenance

Assignment: [S000 roster rev46](https://github.com/Nate27624/Wii-AI-Golf/pull/320#issuecomment-6842921942), task S002-P0-SELECTED-BALL-V0-PROVENANCE-20261112. Canonical source findings [#415](https://github.com/Nate27624/Wii-AI-Golf/issues/415). No additional private original-source execution is claimed by this document.

## Falsifiable conditional call chronology

| Site | Existing source-qualified candidate | Remaining gate |
| --- | --- | --- |
| 0x80299B38 | fn_8029A0E0 initializer on third/prep | receiver identity through CFG |
| 0x80299B48 | fn_8029A5EC copy third/prep to global | destination/source must-definition |
| 0x80299B64 | fn_80299C70 intermediate processing | effects on global vector, return path |
| 0x80299BC4 | fn_8029A5EC copy incoming to global | branch reachability/receiver lineage |
| 0x80299CCC | fn_80299890 conditional processing | receiver and return/side effects |

The new offline reader verifies only five exact native PowerPC direct-BL callsite encodings, original seven-pair archive manifest and all 14 bank SHA values both before/after, and identity of source words across original phases 1/5/7. Failures ABSTAIN without exporting private path, bytes or vector values. No generic callgraph scan, launch coefficient refit, or false runtime witness.

The order includes an intermediate processing call *before* a possible later incoming-to-global copy. Thus an overwrite hypothesis cannot exclude an earlier global consumption. It equally cannot prove that the selected Ball ever received the prep velocity.

Published state3 (state+0x1A4==3) and optional state+0x1BC flag branches govern late operations; +0x8C scalar is separate from velocity +0x78/+0x7C/+0x80. A conditional +0x138 state-pointer clear does not prove native selected integration. Source-selected, global and third/prep must be distinct labels, not silently aliased.

## S003 interface recommendation

Pass a typed record with start_xyz, nullable v0_xyz, source_case, source_role (selected/global/prep/UNKNOWN), selected_identity_verified, branch_conditions_verified, source_archive_verified, guest_execution_verified and provenance_status. Until a selected receiver and actual source execution are demonstrated, return UNKNOWN for native v0; S003 may simulate a clearly marked illustrative v0 but must not label it source-verified.

## Remaining source studies

1. Original SHA-gated bounded control-flow/must-def audit of 0x80299ACC and callee 0x80299C70, including 0x80299890; track caller-saved registers across BL and both copy return paths.
2. Original Ball +0x78/+0x7C/+0x80 writer target must be proven to be source-selected rather than the third/global scratch.
3. Check selected integrator fn_8029B554 gating against Ball+0x138 (non-null skip) and demonstrate source update order. A static source edge is never a shot-time guest tick.

The previously tried LocalOps checkout failed original archive qualification. Before LocalOps request, verify the dedicated operator-approved source-audit project, reviewed tracked script/checkout, original archive identity and all SHA/phase gates. Operator Y/N per bounded request, no bypass. The script now supports no-argument fail-closed lookup of exactly one candidate in its existing sibling private `Wii-AI-Golf-Data/captures` root (maximum 32 immediate child entries, manifest metadata inspected only). It still requires complete original 14-bank SHA verification before and after reading; unknown, ambiguous or mismatched archives ABSTAIN. The dedicated LocalOps source-audit checkout's actual private archive location is **not yet proven** compatible with this root. Do not bypass it using raw absolute path arguments, checkout changes or arbitrary fallback discovery. A separate source-audit study is pending and must finish before any shared checkout switch. No new original-bank result or runtime verification is claimed.

selected_ball_v0_verified=false; runtime_execution_verified=false; training_approved=false. No Dolphin, private assets or training.


## Decompilation-first receiver investigation (next bounded native run)

Matching public `doldecomp/ogws` RSPE01_01 symbols establish exact code owners, not a decompiled Ball function body:

| Function | Public text interval | Focus |
| --- | --- | --- |
| `fn_80299890` | `[0x80299890,0x80299ACC)` | shared integration dispatch / receiver handling |
| `fn_80299C70` | `[0x80299C70,0x8029A038)` | global Ball route into shared integrator |
| `fn_8029B554` | `[0x8029B554,0x8029B57C)` | selected SimManager +0x6B4 route |

The script's default `--study integrator` now reports *only* original SHA-gated symbolic PPC instruction windows `[0x80299890,0x802998D0)`, `[0x80299C9C,0x80299CDC)`, and `[0x8029B554,0x8029B57C)`. Exact opcode/register/branch summaries in phase1/5/7 are compared before publishing; unsupported opcodes are labeled unresolved, not interpreted. This intentionally does NOT infer the physical vector from a matching `+0x78` immediate.

**Source-backed relationship already published on #415:** operator's original-Ball/SimManager identity check found `SimManager+0x6B4 == selected Ball`, while `r13-23304` identified a distinct global Ball and `r13-23300` a third preparation Ball in one no-shot source-gated epoch. The SimManager route `fn_8029B554` conditionally branches to `fn_80299890`; `fn_80299C70` conditionally calls `fn_80299890` with the global Ball. Source equivalence of *callee* does not imply equivalence of receiver, actual invocation, numerical input or output.

**Candidate state-lifecycle hypothesis, NOT verified:** entry to the outer `fn_8029B43C` source-selected launch route tests selected `+0x5C` and `+0x138` before `fn_80299ACC`; in the `state+0x1A4==3` path, `fn_80299ACC` clears incoming `+0x138` at `0x80299BCC` after the second global copy. Separately `fn_8029B554` may skip when selected `+0x138` is non-null. This is compatible with an **arming/processing -> active integration** transition (a pointer-clearing handoff), but is also compatible with independent gameplay state changes. To falsify, decode actual branch polarity and reaching paths in `fn_8029B554` and `fn_80299890`, then establish selected `+0x78/+0x7C/+0x80` values are defined *before* an eligible selected call. Never infer a guest tick just from this state machine hypothesis.

Concrete positive/negative checks: verify `0x8029B554` source `lwz r3,+0x6B4(r3)` and `0x8029B574` tail `b fn_80299890`; verify `0x80299CAC` source global load and `0x80299CCC` `bl fn_80299890`. Distinguish `+0x138==NULL` vs non-NULL, eligible/ineligible return edges, global vs selected receiver, and overlapping writes from `fn_80298E70` / `fn_80297A00`. Output should be a conditional receiver/definition map, **not** a guessed native trajectory or shot execution claim.

No local execution of the new `integrator` study has been observed yet. Tests are synthetic pending exact-head CI; private source SHA and original-game witness remain required.


## V0-3: two integrator callers, possible distinct r4 mode (bounded audit code ready)

Existing source-qualified call evidence identifies the selected SimManager entry `fn_8029B554` sending literal `r4=0` into `fn_80299890`, while the global call from `fn_80299C70` supplies an independently constructed `r4`. The integrator prefix at `0x802998AC` reportedly stores incoming `r4` in nonvolatile `r30`, which makes a source use/definition census worthwhile. **Mode semantics remain UNKNOWN**: differences could be preview behavior, collision switches, iteration counts, or simply metadata; avoid naming it without source reads.

The new `--study mode` (now zero-argument default) performs an immutable fourteen-bank SHA pre/post audit and exact equality of the complete published `fn_80299890 [0x80299890,0x80299ACC)` code body across original phases 1,5,7. It demands a valid **PowerPC OR/MR alias** at `0x802998AC` (specifically `r30 <- r4`) and exact direct-call targets at `0x802998B4 -> fn_80298E70` and `0x80299A18 -> fn_80297A00`. It reports bounded possible r30 operands (register/base/offset/PC only) and explicitly declines semantic verification. Unrecognized X-form instructions are classified as **possible operands**, not provable dependencies. A >12 reference count or >2200-character output causes an ABSTAIN rather than a cut-off JSON receipt.

**Critical tooling evidence:** dedicated LocalOps source-audit #54 original B0 caller run returned exit-zero and B0 SHA success, but its JSON output was truncated at 2750 characters. Its full target census is unavailable; do not promote any missing target count to fact. Private LocalOps issue #63 requests an explicit truncated-output error. S002 source checkout #58/#61 safely refused a dirty worktree; a separate `git_status` check can misleadingly report `tracked_changes=(clean)` because the bridge *excludes untracked files* there but *includes them in checkout_reviewed*. This is a verified predicate mismatch in the bridge source; no private directory names, bytes, files or cleanup actions requested. Future source run only after S000/operator reconciles preserving untracked archives.

**Not proven by this study:** whether r30 is subsequently modified, mode controls the update, selected Ball receives prep velocity, live update frequency, or first terrain contact. Keep every native-v0 claim UNKNOWN until receiver must-def and actual execution are established. No script or model executable was newly run in the original source audit environment during this update.


## V0-4: alternative initializer path and audit correctness correction

**New implementation discovery:** the inherited `original._check_archive(archive)` returns a dictionary mapping capture numbers 1..7 to the already manifest-qualified **phase-specific directory**. The original three S002 source readers incorrectly attempted to pass the outer archive directory to `original.src._file`. That would fail despite a legitimate source archive. All three readers now use `folders = original._check_archive(archive)` and open `folders[phase]` with the numbered bank filename, then repeat `_check_archive` after inspection. Added a static regression guard checking this contract. This is a real correctness fix; no executed original research result is yet claimed.

**New hypothesis to test:** selected v0 might be initialized through one of the smaller alternative callsite functions rather than through the main `fn_80299ACC` preparation/global-copy path. Existing public matching RSPE01_01 symbols delimit `fn_8029A1D0 [0x8029A1D0,0x8029A204)` and `fn_8029A204 [0x8029A204,0x8029A2D0)`. Previously identified source candidate calls `0x8029A1E4 -> fn_8029A0E0`, `0x8029A220 -> fn_8029A0E0`, `0x8029A2B4 -> fn_8029A5EC`. **No receiver register identity is yet proven**, and a previous generic lexical lookback crossed function boundaries.

New `--study alternative` uses exactly these whole function slices; it SHA-gates all 14 original banks pre/post, requires the whole slices to match original phases 1/5/7, validates three direct BL targets, reports bounded candidate r3/r4 D-form operands from the correct function entry and a number of intervening control transfers. This deliberately **does not call any lexical preceding assignment a must-definition**: control paths, ABI clobbers, and xform instructions could still invalidate an apparent receiver. The expected result is a compact falsifiable candidate map indicating the next exact PPC register-flow instruction subset, not a verified selected launch vector.

Research queue, prioritized once the user-approved source checkout issue is resolved: (1) V0-3 `--study mode` inspect saved `r30` use in shared integrator, (2) V0-4 `--study alternative` distinguish alternate prep/selected writer receiver, (3) if both abstain, a scoped whole-function CFG must-def proof for a selected `+0x78/+0x7C/+0x80` store; no generic RAM scans. Every native study requires a separate LocalOps Y/N. Both new modes cap output to 2200 characters and refuse uncertain provenance. No per-shot game execution or training claims.


## V0-5: state-pointer gate handoff across launch and selected integration (new bounded study)

**Hypothesis H1:** for the source-selected Ball, the path into `fn_80299ACC` is eligible while an attached state pointer at `+0x138` is non-null, and the state-3 conditional block clears that pointer; `fn_8029B554` then allows integration when `+0x138` becomes null. **Null hypothesis H0:** two branches are unrelated gating or may never execute on the same selected receiver/shot. A static compatibility result is NOT an executed pointer transition, initial v0, guest time, or rendered shot.

**Source audit built:** the new `--study gates` reads only three public OGWS RSPE01_01-bounded PPC code slices:
- `fn_8029B43C` selected outer launcher `[0x8029B450,0x8029B478)`, including exact load of `SimManager+0x6B4` and `0x8029B474 BL fn_80299ACC`.
- `fn_8029B554` selected integration gate `[0x8029B554,0x8029B57C)`, including exact Ball+0x5C and +0x138 loads, `r4=0` and tail `b fn_80299890`.
- `fn_80299ACC` state3 tail `[0x80299B68,0x80299BD0)`, including state+0x1A4 compare to 3, `0x80299B74` conditional skip, and `0x80299BCC stw 0,+0x138(r31)` after matching literal-zero instruction.

It verifies exact D-form opcode/register/base/displacement gates and required call/branch targets, but reports the five conditional branch BO/BI/targets **without silently claiming complete CR-state polarity**; proving the conditional branch outcomes and same-guest-frame receiver identity remains future work. Original seven-phase manifest + all 14 banks SHA pre/post and phase1/5/7 native PPC identity required. The report is capped at 2,200 characters and keeps original data private. Missing/altered gates ABSTAIN, never guessed.

**Falsifiers:** a branch target or polarity inconsistent with hypothesized active-vs-prepared transition; the two calls receive different Ball objects; the pointer clear is bypassed by a return/non-state3 branch; or the first eligible integration lacks defined selected +0x78/+0x7C/+0x80 state. Source code verifying branch shape alone supports at most *conditional source compatibility*, never true temporal transition.

## V0-6: selected pre-step v0 must-definition (proposal, not yet implemented)

Build a def-use/CFG proof for selected `+0x78/+0x7C/+0x80` *before* its first eligible `fn_8029B554 -> fn_80299890` invocation, not merely the first integration's `v += a`. Qualify candidate receiver lineage through `fn_80299ACC`, the two V0-4 alternative initializer entry functions, exact `fn_8029A5EC -> fn_8029A3FC` destination/source order, and separately classify selected writes vs third/global writes. Gate every original native source window and call clobber, branch reachability and source identity. Outcomes: `PRESTEP_SELECTED_WRITER_PATH` (source-only conditional), `NO_DIRECT_PRESTEP_SELECTED_WRITER_IN_SCOPED_WINDOWS`, or `ABSTAIN`. Do not conclude no velocity exists from lack of direct call/writer in the bounded windows: indirect dispatch and external constructors remain possible. If H1 is supported, S003 may accept a source-conditional v0 provenance record; otherwise keep initial velocity EXTERNAL_UNVERIFIED.

**Execution sequencing:** V0-3 mode, V0-4 alternative and V0-5 gates are separate choices and must each receive independent LocalOps Y/N only after a *clean, exact-SHA, operator-reviewed* source-audit worktree is available. Two earlier checkouts rejected untracked worktree; do not retry without LocalOps maintainer diagnosis. Never report source success from code written but not executed. S003 source/model ownership remains exclusive.


## V0-7: force-before-speed-refresh source PCs vs carried `Ball+0x84` (ready for review, unexecuted)

**Unique research question, separate from V0-3 mode and V0-5 pointer gates:** is `Ball+0x84` a carried *previous-step* speed-like input to the force routines, rather than a scalar recomputed from the current updated velocity before force application?

Original-source-ledger callsite hypotheses within shared integrator `fn_80299890 [0x80299890,0x80299ACC)`:
- `0x802998B4 BL fn_80298E70` — force-like/update callee `[0x80298E70,0x80299528)`.
- `0x802998C0 BL fn_80298C98` — postprocessing/collision candidate.
- `0x80299A18 BL fn_80297A00` — position/vector adjustment candidate.
- `0x80299A20 BL fn_80299528` — speed-like `+0x84` writer candidate in `[0x80299528,0x80299890)`.

**V0-7 implementation** `--study speed` does exact SHA-gated, phases1/5/7 whole-code equality of all three bounded source function bodies. It requires all four exact direct-BL targets AND the integrator `r4->r30` PPC MR alias. For each of the two bounded callees, it counts and samples only direct D-form `lfs/stfs` using literal displacement `+0x84` (including base GPR and PC, never native words or private values). It returns `same_path_and_receiver_verified=false`, `speed_scalar_freshness_verified=false`, and `selected_pre_step_v0_verified=false` even if static lexical call order and candidate offset occurrences are found. Output is capped to 2,200 characters; original archive SHA rechecked after source reads.

**Falsifiers / decision tree:**
1. Any original 14-bank SHA, phase code, callsite, or `r4->r30` gate fails: `ABSTAIN`, no inferred lag.
2. Direct source +0x84 occurrences absent from one callee: identify **no direct D-form match in the bounded slice**, not absence of indexed/paired-single or deeper callees.
3. Both callees show candidate reads/writes: request follow-on register must-def, `r3` aliasing, branch CFG and caller mode=0 reachability; same code lexical order alone does **not** imply same selected Ball or one executed step.
4. Only after a selected-receiver, same-path proof would an explicit synthetic `speed_prev` versus `speed_current` differential be meaningful. Source `+0x84` and native mode/f32 order stay independent until qualified.

**Archive-discovery reliability update:** the earlier script aborted if over 32 immediate capture-directory entries existed, though the approved other original-source preflight #81 now successfully handles a populated archive with a bounded 512 metadata entry cap. S002 discovery now tolerates up to 512 *immediate* entries under its **existing** trusted `original.src.selected.DATA_ROOT/captures` only, while still requiring exactly one metadata-qualified 7-pair manifest; `original._check_archive` enforces full 14-bank SHA and strict signed metadata pre/post. Added fabricated test with 60 unrelated capture directories and one reviewed cohort, plus over-cap rejection. **Important source helper nuance:** `original._check_archive` returns `{phase: qualified_capture_directory}` and entries can point to the *same* archive root, not seven distinct directories. Using `folders[phase]` is a correct helper contract and SHA-qualified path binding, but is NOT evidence the earlier direct `archive` argument would necessarily fail in a valid flat archive.

**Execution state:** no S002 PR #455 original native script has been run. Branch source/test updates require exact-head Windows/Ubuntu CI and original source-audit checkout. The protected source-audit checkout remains blocked pending an operator-installed diagnostic from private LocalOps PR #82; do not submit further checkout retries or source runs before that dependency. V0-7 is distinct from already executed synthetic #75/#76 and original nonlinear #83, and does not modify S003 model or accepted-power owner files.
