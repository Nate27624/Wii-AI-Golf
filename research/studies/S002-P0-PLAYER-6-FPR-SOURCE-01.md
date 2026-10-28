# P0 six player-store floating value-side producer clues (source-only)

## Grounding from actual operator original B0 study

User's original SHA-pinned PR #244 local source candidate scan at `41032840e553bd3f99e2dc3fa5139d76274d07a8` passed **11/11 synthetic tests and original B0 source SHA**. For W5→W6→W7 the selected **RPGolPlayer record** +0x030/+0x090 changed both times but no physical semantics were proven. Source PPC store observations:

- `RPGolPlayer` source-relative `+0x0FAC,+0x0FE4,+0x0FF8`: `stfs f0,+0x030(r31)`
- `+0x1FFC`: `stfs f3,+0x030(r30)`; `+0x2008`: `stfs f0,+0x030(r30)`
- `+0x1C18`: `stfs f0,+0x090(r31)`

These are **six source syntax matches only**, not known runtime selected-player writes. 3 other `sth` +0x90 candidates could modify halfwords of a different object; `stfd f30,+0x90(r1)` is stack and not the direct 32-bit float candidate. Original +0x30 has 13 D-form matches, including multiple stack-only sites. Do not equate `player_record+0x030` with `ball_object+0x030`.

## Distinct contribution from S002 owner #244

New-only `scripts/audit_p0_player_float_local_producers_private.py` *reuses* #244 original B0 SHA+manifest/RSPE01 Rev1 source code and #219 published Player source-unit boundaries. Before doing anything new it invokes #244's original source-gated audit; requires **all six exact `stfs` PPC words**, reads ONLY RPGolPlayer .text and revalidates the original B0 source SHA after reading. Returns for each known store only: source-unit-relative site, registered member displacement, stored FPR, unverified base register; the nearest possible floating-point register producer in previous 96 bytes, **abstaining on a branch/control barrier**, and 8 before / 2 after *mnemonic-class* context rows. Some PPC fp/control variants do not actually define fD; these are conservatively labeled `possible_writer` and NEVER asserted as executed reaching definitions. No native code words, raw numeric coordinates, dynamic pointers, full instruction disassembly, source memory pages, private SHA values, paths or files in report.

This study traces the **value side (f0/f3) only**. Source-owner #244/#219 retains the base-register `r31/r30` typed receiver/function/caller identity and execution gating. It does not merge or modify their source decoder, workflow or test. No Dolphin, shot, controller, new dump, upload or training. Candidate meanings (phase scalar, animation, timer, force, physics, speed or power) remain ALL hypotheses. `approved_for_training=false` universally.

## Suggested owner operation

Use a fresh exact-SHA detached review worktree of this draft branch after Win/Ubuntu synthetic tests. Invoke:

`py -I scripts/audit_p0_player_float_local_producers_private.py --data-root "<ignored root>/Wii-AI-Golf-Data" --private-session "<ignored root>/Wii-AI-Golf-Data/ball-study-20261027-212633"`

Only sanitized `site_evidence` rows may be posted. If any code/hash/owner fails, the CLI returns ABSTAIN. Do not treat `f0` origin as a physical variable until S002 proves actual selected-player record receiver, writers and different gameplay phase behavior.
