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
