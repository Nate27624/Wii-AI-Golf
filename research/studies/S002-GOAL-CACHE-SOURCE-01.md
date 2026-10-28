# S002-GOAL-CACHE-SOURCE-01 — pin fallback and conditional position caches

**Status:** private, offline source-and-still-state investigation. Source PPC inspected in the *already supplied* operator-native RSPE01 Rev1 24MiB MEM1. No game launch, Dolphin bridge, controller, new shot, RAM capture or public binary upload. Source-backed register paths are static code evidence, not proof that the same routine executed on the selected ball during any shot.

## New source finding: source goal getter chooses target objects or current pin

The Rev1 function **0x80292294..0x802922B0** within the FieldManager compilation unit reads `FieldManager+0x30` (public header: `mNumTargetObjs`). If this count is strictly positive, it loads the `mTargetObjs` pointer at FieldManager`+0x34` and branches to a helper at `0x802B6F24`. If the count is not positive, it loads `FieldManager+0x44` (`mCurrentPinObj`) then that object's `+0x4C` translation pointer and returns it.

In the current operator-provided MEM2 snapshot, the target-object count is **zero**. Its current-pin object has the already corroborated `obj+0x4C == obj+0x30` translation self-reference and a finite bounded 3-word candidate. Thus, **for this still state**, the source getter's PIN fallback is selected if this function is called. This is stronger than assuming the function always returns the pin: other modes/holes may have target objects.

The helper's target-object branch has not been independently decoded here. The selected target/pin coordinate axes, units and physical object identity remain unverified.

## New source finding: two conditional ball-unit position caches

Real Rev1 `RPGolMapObjBall.cpp` code `0x80299C70..0x8029A030`:

- **0x80299C90** saves receiver r3 to r27; **0x80299CD0..0x80299CEC** reads a *different source-global ball pointer* and its `+0x4C` translation, then copies 3 f32 words to receiver `+0xCC/+0xD0/+0xD4`. This is a **current-position refresh** in ball-unit source. **Do not automatically equate r27 receiver with the player-manager-selected ball object**: caller-to-instance ownership requires separate proof.
- At **0x80299EE4..0x80299EE8**, the routine uses the FieldManager singleton and calls `0x80292294`, the target-vs-pin getter above.
- At **0x80299EEC..0x80299F38**, it loads receiver current candidate components 0 and 2 from +0xCC/+0xD4, cached ones from +0xF0/+0xF8, and target components 0/2; executes subtract/multiply-add comparing **two planar squared differences**. When the branch predicate allows it, **0x80299F3C..0x80299F50** copies all 3 current candidate floats into `+0xF0/+0xF4/+0xF8`, along with a 32-bit tag `+0x118`.
- Independently **0x80299F60..0x80299F90** compares the current candidate middle float `+0xD0` with the cached middle `+0x100`, and conditionally copies the 3 current floats into **+0xFC/+0x100/+0x104**, with another 32-bit tag `+0x11C`.
- The copy routine at **0x8029A5EC..0x8029A720** additionally copies both sets of cached triples and accompanying metadata from one object to another, so seeing matching snapshots can reflect initialization or replication. Earlier source **0x8029A724..0x8029A7F4** initially seeds all three `+0xCC/+0xF0/+0xFC` triples from `obj+0x4C`. See S002's broader PR #181.

**Interpretation:** these are two distinct code-controlled *candidate extremum/position caches*, **not three independently observed real-time ball XYZ locations**. One comparison operates on the first and third components relative to target/pin; the other compares a middle-component scalar. Without verified receiver identity, runtime write execution or known axis conventions, do not label these “closest approach to pin,” “minimum ball height,” “lie/landing,” or “final score.” Even if the comparison predicates suggest such behavior, their physics meaning is unknown.

## Real one-snapshot control (no temporal claims)

The operator's existing one MEM2 snapshot passes source selected record/start/ball triage. In its Hitting-the-Green configuration (`mode=4`), `FieldManager+0x30 == 0`, so the source getter's fallback is current pin rather than a target list. The operator's source-selected ball-like object has `+0xCC`, `+0xF0` and `+0xFC` triplets each **3/3 equal** to the current-start 3-word translation in this one still. That is *expected following source initialization*. It is **not** proof the cache-update routine ran, nor that pin-distance or ball height changed after impact.

## Code and tests

New bounded `scripts/audit_golf_ball_goal_cache_private.py` piggybacks #160/#163 source and selected-owner checks, exact PPC register/opcode/branch-target gate for the target-vs-pin getter, receiver position copy, first/third arithmetic path and two conditional f32 cache copies. It reads only the source-current pin and source-selected candidate's 3×3 buffer words, from an already-preserved private native pair. Its stdout is only source booleans, 0..3 matching-component counts and explicit false physics/score/training flags; no heap pointers, raw floats, source instruction words, file paths, native memory, hashes or diagrams of private layout output. A mismatch aborts.

15 fabricated-memory source and negative control tests include target fallback vs nonzero target, wrong getter branch and field offset, wrong position-refresh member, wrong F0/FC store/call/math path, missing pin selfref, NaN candidate, mismatched cache, wrong game/selector, output privacy and CLI error redaction. No real uploaded Wii banks are needed by CI. A second human owner can run the tool locally against a preserved private `mem1.raw` + `mem2.raw` pair under ignored sibling Data; **do not recapture** if missing.

## Owner requests

S002 #162 source reviewer: validate caller and receiver r27 provenance for `0x80299C70`, including whether `source-global ball +0x4C` is the currently active ball while receiver is a recorder/clone. Independently review which comparison direction selects cached +F0 vs +FC and the meaning of tag fields +0x118/+0x11C. S002 #181 atlas: compare these 3 cached triplets and their two tag fields across B0–B3 no-shot controls; rank changing time/aim vs static cache, without claiming live motion. S000 #154 ledger: preserve *source code cache update predicates* as distinct from *runtime buffer motion/physics*.

Later, **only after reviewed single-owner live instrumentation and explicit operator consent**, capture one shot with independently observed ball movement and check that source start/pin remain fixed while selected ball state and caches update according to source-controlled paths. No training on speculative cache semantics.

Existing references: #160 roster, #163 selected ball/start, #162 source PPC, #181 source-linked wholebank atlas, #182 pin/cup still alignment.

**No independent same-guest-frame guarantee, dynamic ball world XYZ, velocity, contact, score semantics or power calibration is established.**
