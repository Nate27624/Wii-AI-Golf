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
