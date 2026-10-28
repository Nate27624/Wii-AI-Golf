# S002 P0 — Source-store candidates for changing player-record words

Draft, offline, source-only. Different from #235 runtime seven-phase masks and #219 branch callgraph. Focus is Rev1 PPC store-instruction candidates for the distinct selected-player record, NOT ball-object +0x30.

## Evidence motivating this check

#235 exact original fourteen-bank SHA/source-gated operator study found record D1→D2 changed +0x030,+0x034,+0x090; W5→W6 and W6→W7 changed +0x030,+0x090. A two-word role test found bounded BE-f32 interpretations, not proof of type or meaning. +0x054/+0x060 are source writer input/mirror controls from #162/#236; +0x038 is an unchanged control.

## Method and limits

- Reuse #219 original B0 native MEM1 SHA256/manifest and published RSPE01 Rev1 Golf code unit boundaries. Check header and SHA again after bounded source read. No Dolphin, RAM writes, new shots, new captures, raw uploads or private path leaks.
- Scan ONLY RPGolPlayer and RPGolPlayerManager .text for D-form stw/stwu/stfs/stfsu and other D-form stfd/stfdu/sth/sthu/stb/stbu whose signed displacement exactly matches +0x030,+0x034,+0x038,+0x054,+0x060,+0x090. Output source-unit-relative site offsets, names of registers/opcodes, capped candidate counts and explicit false gates. For each site, perform a **64-byte maximum backward straight-line hint** for the base register: nearby source GPR load, immediate arithmetic, register copy, update-form or unknown writer. **Any branch/call within the window stops the trace with a control-flow barrier**. This intentionally does not prove pointer ownership, frame execution, or complete def-use.
- A store +0x090(rA) does NOT establish rA as the selected record base. This could be a different object or adjusted base. Indexed/indirect, other object-file and 8-byte overlapping stores remain unresolved. Zero candidates does NOT disprove a runtime writer.
- Source displacement matches cannot be causally joined to #235's changing runtime record until register provenance and actual receiver identity are established.

For approved operator use on EXISTING B0 only, after upstream #219 review. A guarded PowerShell 5.1 runner is also provided at `scripts/Invoke-P0PlayerStoreProvenance.ps1` and **requires an externally verified exact pinned detached-worktree commit** and existing private Data root. The runner requires synthetic PASS, repeats B0 source/manifest SHA gates and prints sanitized only:

    python scripts/audit_p0_player_record_store_candidates_private.py --data-root "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data" --private-session "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\ball-study-20261027-212633"

## Testing and release gates

Thirteen fully fabricated unit tests cover endian/opcode widths, signed negative displacement, source-unit attribution, direct load, branch barrier, GPR zero base, unknown writers, float loads versus update-form base mutation, no-match and malformed gates, sanitized output and failed private path. Windows/Ubuntu synthetic CI and Windows PowerShell parser-only CI; no native data in GitHub.

No real original B0 was analyzed as part of this PR. Actual field semantics, shot power, velocity, physical XYZ, frame sync, impact, score and training all UNVERIFIED; approved_for_training=false, allowed_to_publish=false. Draft stacked on #219; require S002/S000 owners and full Windows suite before merge.


## New real B0 candidate-count evidence and strictly bounded r31 follow-up

Owner ran the exact previous PR #244 source commit `65c510ea73a483389b6baaf2a07ef773f4d190c7` on its original SHA-verified private B0 and obtained **13/13 local fabricated tests PASS**, source manifest SHA PASS and 6 displacement groups. The `RPGolPlayer` unit has one known exact 4-byte D-form `stfs` site using displacement `+0x090` and base register `r31` at source-unit relative `+0x1C18`; other four +0x090 D-form sites use `stfd` (8-byte) or `sth` (2-byte) and cannot be treated as identical full-word stores. Because offset is relative to r31 rather than proven player-record origin, it is a **source instruction candidate, NOT an established record+0x090 writer**. Overlapping stores, adjusted bases, other units and indirect/indexed writes remain unsearched/unexcluded. Full scan found 13 matched D-form sites at +0x030 (12 4-byte), and many at controls; matching counts do not prove receiver ownership or dynamic execution.

Added a **second**, read-only source study `scripts/audit_p0_r31_store_slice_private.py` plus 8 fabricated tests and exact-source PowerShell wrapper `scripts/Invoke-P0R31StoreSlice.ps1`. It reads only the original B0 source text in the 0x180-byte region immediately preceding the candidate, validates instruction `stfs f?, +0x90(r31)`, and reports a **capped, sanitized** list of r31-related source-unit-relative syntax candidates and control-flow hazards. PPC register copy `mr`, source load, immediate arithmetic, update-form and unknown writes are classified conservatively, with separate `branch_aware_cfg_dominance_verified=false` and `r31_is_selected_player_record_verified=false`. It does NOT inspect another captured phase or output instruction words, dynamic addresses, bank SHA, floats or paths. Do not infer that a source-nearby assignment dominates a real call path.

This r31 follow-up requires **its own exact approved pinned SHA and local operator run** before any new real source claim. Both synthetic platforms and full suite/S002/S000 review must pass; model use is unapproved.

## Operator B0 r31 slice result and bounded branch-aware refinement

Owner ran exact pinned #244 head b4636bd625db92bb6c306dd0533d8d4ac5976ca9 on the original B0: 8/8 synthetic tests PASS, source/manifest SHA PASS, Rev1 instruction at RPGolPlayer +0x1C18 = stfs f0,+0x90(r31). Earlier source scanner also found mr r31,r3 at source-unit +0x1BE8; reported +0x1C04 as a broad control-flow hazard. These two instructions are 0x30 bytes apart. The 28 earlier control-flow hazards across a 0x180-byte backward scan do NOT mean 28 branches on a reachable path.

New independent source-only local CFG support script: scripts/audit_p0_r31_local_cfg_private.py, 11 mock PPC tests and exact-source pinned Windows 5.1 wrapper scripts/Invoke-P0R31LocalCfg.ps1. After exact B0 SHA/revision validation it checks both source instructions, models branch and register-write possibilities only within 13 instructions from +0x1BE8 to +0x1C18, and reports source-relative edges, unknown exits, and whether any possible local path reaches the store preserving the r3->r31 copy. Original PPC opcode19 CR logic is NOT automatically counted as branch; conditional branch tests consider both arms. Unknown writes, linked calls, indirect control-flow and external edges keep interpretation conservative.

IMPORTANT: this is NOT full function CFG, branch dominance, selected-record receiver identity or runtime execution. An external incoming edge may bypass the copy; an external exit might return. Every report retains full_function_cfg_dominance_proven=false, runtime_receiver_is_selected_player_record_verified=false, dynamic_store_execution_verified=false, approved_for_training=false and allowed_to_publish=false. A found local path does not prove r3 is the source-selected player record. Human wedge phase labels/actual shot state remain independent and unjoined.
