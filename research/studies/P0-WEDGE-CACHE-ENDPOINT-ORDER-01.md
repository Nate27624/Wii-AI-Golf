# P0 wedge: stable cache +0xCC candidate endpoint ordering (offline)

This is a **new complementary S002-support experiment** using the already preserved seven paired, privately archived 24MiB+64MiB banks. It extends the strict Rev1 source-gated #231 archive/ball/pin/selected-player reader, and does **not** repeat the #230 S002 selected-only wedge motion proof, #228 page-intersection maps, S000 registry edits, source-writer disassembly, or S001 live shots.

## Motivating operator evidence

- Actual source selected **ball+0x30 changed 3/3 components** during human-labeled same wedge 5→6 and 6→7; 3 inactive ball objects, source PIN/START and GolfConfig BC/C0 remained stable. Source-selected ball components increment/decrement/decrement on both steps, but no physical axes or frame intervals are certified.
- Cache **+0xCC remains bitwise identical across W5, W6, W7** while ball W5/W6 differs from it 3/3 and ball W7 matches it 3/3. Caches +0xF0 and +0xFC also stable. Do NOT call this 'cache catching up' because cache does not change.
- Separate driver D1→D2 showed **ball+0x30 and cache+0xCC both change 3/3**, so endpoint semantics can be shot/phase-specific.

## Next falsifiable questions

The new script `scripts/audit_p0_wedge_cache_endpoint_order_private.py` computes **private finite bounded IEEE-754 binary32 candidate vectors** in its own process, after every original #231 archive SHA, Rev1 source, selected slot/hole, PIN/START, and Config check. It requires wedge source selected player/ball, FieldManager, pin and start object pointer identity, all GolfConfig BC/C0/C4, pin and tee triplets to be stable across W5/W6/W7. Driver D1→D2 has independent gates; no cross-shot compares.

Only BOOLEANS and discrete changed-component counts leave the process:

1. Is candidate squared Euclidean distance `current ball+0x30→fixed +0xCC` **strictly decreasing** from W5→W6→W7? This supports approach-to-endpoint behavior, not necessarily a predicted endpoint.
2. Is W7 current ball exactly equal to W7 cache+0xCC, and is that cache distinct from PIN, START, +0xF0 and +0xFC? Are other candidate cache distances also decreasing? Report phase-specific relative closeness of CC vs PIN/START/F0/FC, never private distances.
3. Do selected ball component step signs remain consistent from W5→W6→W7? No timing or speed inference.
4. Driver D1→D2 as separate **negative context**: did its CC update together with current, and was it equal to current both phases?

If vectors are nonfinite/out of conservative interpretation range or source geometry differs, ABSTAIN. Strict source-object ownership and bank SHA are inherited and no raw vectors or absolute pointers/addresses/paths/hashes appear on stdout, saved files or GitHub. `+0xCC` may be a predicted target, historical interpolant, transformed endpoint, or something else; **source writer/use tracing is owned by #225/#219**.

No physics world XYZ, velocity, power, exact frame spacing, collision or 15.2ft accuracy established. Human phase filename mapping is still independent metadata and not machine-verified. Zero variables approved for training; no live emulator, controller input, new dump or modified original. Offline script will be marked real-operator PASS only after user executes pinned worktree on existing ignored Data archive. Draft CI only uses synthetic native-free data.

## Dependency/ownership

Stacked on [#231](https://github.com/Nate27624/Wii-AI-Golf/pull/231) as distinct additive script+tests+CI+study. Coordinate with [#230](https://github.com/Nate27624/Wii-AI-Golf/pull/230) trajectory proof, [#225](https://github.com/Nate27624/Wii-AI-Golf/pull/225) cache provenance, S000 [#205](https://github.com/Nate27624/Wii-AI-Golf/pull/205) registry and S001 #215 same-frame bridge. Do not self-merge, do not train on claims.
