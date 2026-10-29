# S002-LEGACY-BALL-XYZ-ANCHOR-01: actual moving-ball XYZ investigation

Date: 2026-10-28. Claim: issue #121. Owner: S002. Source-only hypothesis plus offline read-only comparator. No new Dolphin, bridge, controller, raw upload, dataset promotion, or live shot.

## New independent public lead: Wii Sports USA v1.00 only

Sharkbyte's public cheat code [P1 controls golf ball (nunchuk movement)](https://gamehacking.org/game/55842?hacker=Sharkbyte) writes the contiguous candidate 32-bit words 0x91BF3E94 and 0x91BF3E9C; the separate 'Moon Jump golf ball P1' writes the middle word 0x91BF3E98. This gives a potential X/Y-height/Z-style float triplet. **These are not asserted to work on the operator's RSPE01 US Revision 1 (v1.01).** The older v1.00 address may be heap/session-specific or entirely relocated; using cheat patches to change RAM is strictly forbidden for this study.

## New source-gated offline falsification

The new-only script scripts/audit_legacy_ball_xyz_anchor_private.py reads original local B0–B3 full paired MEM1/MEM2 banks under ignored Wii-AI-Golf-Data. It checks the frozen SHA256 from the existing checkpoint manifest, native sizes, RSPE01 Rev1 header, scene5/sport2/mode4, source-selected player record, record+0x88 selected ball object, object+0x4C translation self-reference to +0x30, current start/pin transforms, and owner stability. It compares the OLD version's absolute address to the Rev1 source-selected ball vector by exact address identity, per-component bit equality and changes across B0–B3. Output is safe booleans, counts and P0 scientific gates. B0–B3 are IDLE/AIM controls, NOT contact/flight/landing. No native pointers/words/coordinates/bytes/hash strings or private paths ever printed or published.

Exact source-reference code paths originate in draft PRs #160 and #162; existing field matrix PR #213 is independent and unaffected. The script reads no RAM outside bounded known pointer chains and the three-word historical candidate. Current source-selected ball translation may merely be an initial tee copy. Matching 3/3 components at rest does not prove dynamic ball XYZ; a changed float cannot be named a physical axis without true flight frames and game observation. The existing V1 successful-shot small-window samples mapped eight changed effect-handle words to four render pairs, not ball physics (#197/#208). The prior JSON-associated ball possibly moving downward has no identified shot/file link.

S001's reviewed V1 45 **observed** Dolphin A-held frames + exact 89-sample waveform, and source-selected ball observer #166 / selected-record collector #211 are upstream for a future independently consented positive-flight validation. Do NOT substitute 45 RPC commands, start a new Dolphin instance, or collect a live trial from this offline script.

## Result meanings

- legacy_equals_resolved_ball_vector_all true: the historic memory location matches the source-selected translation address in idle/aim B0–B3. NOT proof of flight, coordinate units, or stable future sessions.
- component equality count 3 without alias: at-rest equal numeric words only, much weaker.
- all false: historic Rev0 address is probably not a portable Rev1 locator; it does not refute the source-selected ball pointer path.
- changed components B0–B3: aim/idle changes, NOT a shot.
- TRUE physical XYZ would require same-shot frame-aligned 3D motion, unchanged tee/pin, stable owner, independent actual ball-contact observation, separately captured idle/no-shot control, different boot repeat, coordinate-axis proof, and S002 acceptance. NEVER approve training from this script.

## Approval, provenance, privacy

New-only files: scripts/audit_legacy_ball_xyz_anchor_private.py, tests/test_legacy_ball_xyz_anchor_private.py, this study and .github/workflows/s002-legacy-ball-xyz-anchor.yml. Does not edit S001 controller/bridge/watch code, #213 field matrix, #214 native phase, S000 catalog/publisher or any other agent-owned files. Report emitted to console only, local source under ignored Data, no second uploader; stdout explicitly NOT_UPLOADED. A typed S000/S002 allowlisted adapter to existing scripts/research_cli.py is needed before user requests automatic GitHub publication of this study. The GitHub source PR is not a published private measurement. Windows/Ubuntu CI tests synthetic fabricated banks only, not a live Dolphin execution; full Windows suite and owner reviews still required.

## Operator one-block PowerShell

After the reviewed exact head is confirmed by S002/S000, a source-pinned isolated-worktree block can run the single read-only compare with:

py -I <isolated-worktree>\scripts\audit_legacy_ball_xyz_anchor_private.py --data-root D:\Projects\Wii Golf AI\Wii-AI-Golf-Data --phases B0 B1 B2 B3

This shorthand is **NOT an operator-ready command**; the assistant must supply the complete approved one-block PowerShell including exact SHA, safe preflight and synthetic test checks. Never invoke unmerged branch files from main as if merged.
