# S002-BALL-XYZ-SOURCE-CALLERS-01 — which code can update the selected ball translation?

**2026-10-28, draft source-only hypothesis and offline read-only audit.** Claim/handoff: [issue #121](https://github.com/Nate27624/Wii-AI-Golf/issues/121). No new Dolphin launch, swing, savestate edit, native read from running emulator or raw publication. This is additive to the prior S002 #162 + #183 actual Rev1 PPC reverse-engineering, not a competing live watcher.

## Why this is the next P0 question

The operator's actual SHA-gated B0–B3 no-shot RAM check of #217 showed 0/3 matches between historical v1.00 cheat-address coordinates and Rev1's source-selected ball translation in each phase. Rev1's selected ball position at object+0x4C -> +0x30 equals start/tee 3/3 and remains fixed across idle/aim, which is normal at rest but cannot establish in-flight motion. Source trace #162 proves a Player routine copying record+0x60/+64/+68 into record+0x54/+58/+5C and the selected ball object's +0x4C pointee as three floats, and another Player path reading that translation back. Source #183 proves a Ball-unit routine that copies a source-global current position into receiver+0xCC and conditionally refreshes +0xF0/+0xFC, but whether its receiver is the same selected ball object remains unproven. Thus the most valuable OFFLINE question is which direct executable callsites feed these routines and how to direct the existing S001 frame watcher.

## Implementation and evidence

New `scripts/audit_ball_xyz_source_callers_private.py`: using only original B0 24MiB MEM1 under ignored Wii-AI-Golf-Data, verifies saved manifest schema/idle phase and SHA256, exact RSPE01 Rev1 executable header, bounded nonzero PPC source code at three documented Rev1 routine neighborhoods. Scans only published Rev1 Golf object-file .text units from [doldecomp/ogws RSPE01_01 splits](https://github.com/doldecomp/ogws/blob/master/config/RSPE01_01/splits.txt) (MapObjBall, SimulateManager, Player, PlayerManager, FieldManager, Main), decodes unconditional PPC `b` and `bl` (opcode 18), and groups static direct calls **into bounded neighborhoods** around the known dataflow routines. Output is source-unit labels and source-relative callsite/target offsets and bounded branch counts; it never prints instruction words, raw memory, live heap addresses, floats, private hashes or local paths. Does not touch shared source registry or other S002 worktrees.

**IMPORTANT**: source neighborhoods are *not* proven function entries or boundaries. A direct `bl` to a neighborhood may be a helper, thunk, or interior block. A zero caller count does **NOT** prove the function is unused: conditional branch, function-pointer/vtable/indirect calls, or calls outside scanned units remain uncounted. The original B0 is idle, so discovering a callsite is **not proof it executes in-flight**. The source routine's owner, dynamic physics state, physical XYZ, units, timing and training approval remain FALSE.

Target contexts:
- Player→Ball candidate translation stores (code `0x802A0388..0x802A03C8`, scanned around a broader neighborhood).
- Ball→Player reverse position read (code `0x8029F300..0x8029F31C`, broader).
- Ball-unit current-position refresh and conditional caches (code `0x80299C70..0x8029A030`).
- FieldManager target/pin and start translation getters (existing stationary controls).

Output is an allowlist-limited JSON object (source relative code offsets, hit counts, all scientific proof flags false) to terminal only, with `github_observation=NOT_UPLOADED_S000_S002_ADAPTER_MISSING`. No new uploader; the existing `research_cli.py` publisher still needs S000/S002 typed adapter review. The source PR and dated GitHub FINDING can store public sanitized callsite interpretations, not ROM/private memory bytes.

## Reproduction and one-block PowerShell requirements

The operator should use the exact tested PR head in a separate immutable offline worktree, never manually copy source or touch another agent's worktree. Run all targeted synthetic tests before the real existing B0 native scan. The final copy/paste-ready PowerShell is supplied by the agent after the exact tested head is confirmed and should print only sanitizer-safe JSON. This study does not authorize a live emulator shot and does not rely on Dolphin runtime startup, which #215 presently reported crashing before bridge preflight with Windows code 0xC0000005.

## Scientific interpretation and next owner

S002: interpret resulting direct callsite counts/relative offsets against the *real Rev1* PPC source and inspect receiver/argument chains only where actual calls exist. S001: once the separate Dolphin startup fault is resolved and S001/S002/S000 reviews/owner gate pass, reuse the original V1 45 **observed Dolphin A frames** and frozen 89-sample trace to instrument the selected source-owned ball object's current position, player copy and candidate caches during **human-observed contact plus actual flight**, with unchanged start/pin negative controls and sample-tick vs guest-frame distinctions. No implicit live opt-in. S000: no training and no private numeric vector publication until frame/axes/units/independent-boot controls pass.

Focused Windows/Ubuntu synthetic CI covers signed relative PPC branches, direct/nonlink distinction, source unit classification, false promotion, output privacy, original native hash, wrong game/phase and invalid private roots. Full repository Windows suite and owner review remain merge gates. All new-only files:
`scripts/audit_ball_xyz_source_callers_private.py`, `tests/test_ball_xyz_source_callers_private.py`, this study and `.github/workflows/s002-ball-xyz-callers.yml`.


## 2026-10-28 actual operator run: corrections after exact public symbol map

**Operator-confirmed**, exact original auditor SHA \`ff997b0cd6a599203c2bb30dd73456a49ed3bf31\`: all 11/11 local Windows synthetic tests PASS; B0 hash/revision/idle code gates PASS; source scanned 13,934 words. No additional Dolphin session or native data was captured. Sanitized result stored in GitHub #219 FINDING; original native words remain private.

Original output:
- PlayerManager +0x09F4 and +0x0F2C issue direct BL to **0x802A0318 / 0x802A0320**, not to the three \`stfs\` instructions themselves. Public \`doldecomp/ogws\` RSPE01_01 \`symbols.txt\` identifies \`fn_802A0318\` as an 8-byte function, \`fn_802A0320\` as 0x354-byte function that CONTAINS the previously source-proven Player→Ball \`stfs\` at 0x802A0388..0x802A03C8. The earlier target-window label implied callers of the three stores directly, which is inaccurate. The revised auditor uses symbol-level function bounds and explicitly distinguishes entrypoint calls from interior jumps; it **also checks whether the 8-byte stub actually branches to the longer function from ORIGINAL B0 PPC**. A symbol name alone does not prove a thunk redirects.
- MapObjBall +0x2B8C and +0x2C80 issue direct BL to **0x80299C70**. Public symbol map gives \`fn_80299ACC\` (0x118 size), \`fn_80299C20\` (0x50 size) as the caller functions, and \`fn_80299C70\` (0x3C8) as the callee. The callee contains the source-identified current-position refresh +0xCC and conditional +0xF0/+0xFC cache-copy logic. This is stronger static *owner-local function-entry* evidence, still not dynamic flight execution, exact receiver identity, or physical axes.
- The inverse Ball→Player read block 0x8029F300..0x8029F31C is **within** \`fn_8029F0A0\` of size 0x37C. The six nonlink branches observed in the old narrow block were internal PPC control flow, NOT six distinct caller functions. The revised source audit reports function-level calls into \`fn_8029F0A0\` separately from branches within its body.
- The target/pin and start accessors are independent tiny public symbols \`fn_80292294\` size 0x20 and \`fn_802922EC\` size 0x0C. These source-getter callsites are controls, not a ball-flight locator.

**Follow-up priority:** S002 determine from surrounding PPC the role and input conditions of \`fn_80299ACC\`, \`fn_80299C20\`, \`fn_802A28DC\`, \`fn_802A30F8\`, including whether the cache updater's receiver is the currently selected ball or a copied recording/cache instance. S001 capture only AFTER native Dolphin pre-bridge access violation and reviewed 51-word watcher permit safely observed same-shot A45/89 sample input. A source-confirmed function containing conditional position-copy code is not a verified current moving XYZ coordinate.
