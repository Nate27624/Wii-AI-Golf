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
