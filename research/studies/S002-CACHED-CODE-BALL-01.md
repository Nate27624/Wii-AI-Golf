# S002-CACHED-CODE-BALL-01 — source-first PPC and candidate ball state before training

**Status:** real B0 static instruction and paired RAM evidence analyzed; 0 new live runs; no swing-physics labels or model training. S002 PR #160 owns authoritative 4x0xCC player/ball roster register dataflow; this document and PR #151 supply ONLY general offline cached PPC atlas and cross-check. Do not merge duplicate source ledgers; PR #154 S000 evidence ledger is canonical.

## Important unblock: missing main.dol does not block offline PPC instruction analysis

The already uploaded raw 24MiB MEM1 (`RSPE01` Rev1) includes cached executable PPC instructions at published doldecomp/ogws `config/RSPE01_01/splits.txt` source-unit ranges. Source gate and 32-bit big-endian opcode decode confirm nonzero instructions and D-form memory operations at all three exact source compilation units:

| Code unit | Instructions | D-form memory ops | Candidate r3/r30/r31 float stores |
|---|---:|---:|---:|
| RPGolMain | 538 | 210 | 12 |
| RPGolPlayer | 3,833 | 1,350 | 52 |
| RPGolPlayerManager | 1,236 | 397 | 20 |

These are not scoped to methods or proven live receiver types; code may access temporary transforms, helper classes or stack copies. The new `golf_cached_ppc_access.py` and CLI produce a locally capped private atlas of code-unit, register, D-form relative offset, mnemonic, operation counts and source code PC references, NEVER code bytes, RAM values, runtime pointers or paths. `main.dol` extraction should not be requested solely for these basic code-unit accesses.

Highest frequency PPC operand hints within Player source unit (NOT player class member proof): `r30+0x03C` (6 static stfs), `r30+0x048` (4), `r30+0x04C` (4), `r31+0x030` (3), `r3+0x050` (3), `r30+0x058` (3), `r31+0x074` (3). All numbers are static *instruction occurrences*, not observed values/writes. The source from PR #160 includes actual register flow for specific ball-related callsites and outranks these general heuristics.

## Stronger direct witness already in PR #160

Read-only paired private B0 cross-check: Source-gated player-manager `+0x334` selected pointer equals inline record at `manager+0x004 + index*0xCC` for candidate **index 0**. Record +0x54/+0x58/+0x5C 3 f32 components **match byte-for-byte** both the nested ball-like object's `+0x04C` destination's first three f32 components and source-named `RPGolFieldManager.currentStartObj +0x030` translation. Three other indexed records have position components that do not equal their nested destinations; source code does show four records. This is a strong BALL START TRANSFORM hypothesis, **NOT ball world XYZ verified, no velocity, no collision/contact, no dynamics.** Only one paused B0; `MEM1` and `MEM2` GUI dumps not guaranteed same-frame. Do not commit actual coordinate values or runtime pointers.

Runtime player-like object via `GolfScene+0x9C → RPGolMain+0x030`: candidate first word lies in Player `.data` compilation range, first **20/24** table entries point into Player `.text` unit; not verified exact class vtable. In one Player source function near public code PC `0x802A0320`, a PPC `mr r30,r3` is followed by float loads at `r30+0x060/+0x064/+0x068` and writes to `r30+0x054/+0x058/+0x05C` on a conditionally reached branch. This proves a bounded static same-register copy pattern and honors PPC r30 nonvolatile behavior; it does NOT prove r3 was the actual Player object at runtime or that it describes the physics ball. PR #160 independently traces record `+0x88`, nested `+0x4C` and three `stfs` writes, so S002 SHOULD inspect that tighter object-owning path first.

## Next priority: S002-BALL-DYNAMIC-01 (opt-in only, after owner review)

Primary question: Does selected-record+0x54 and nested ball-like+0x4C vector leave the initial source-matched start coordinate during a real shot, follow a stable frame-time trajectory, and settle at a different final position? Require per-stage revalidation of manager selection pointer and source .data/table anchors; an allocator relocation must not be interpreted as movement. Screen-observed ball motion is a separate human/vision label, not inferred from the numerical changes alone.

**Phase A (preferred BEFORE an actual shot):** Run the existing 4-pair B0 still / B1 later still / B2 WASD aim only / B3 idle after aim experiment and privately inspect 0x0C bytes of *selected-record and its nested destination* to establish timer and aim null controls. Use one canonical Felk Dolphin session; GUI pause, `Dump MRAM` + `Dump ExRAM` and preserve UNIQUE private B0/B1/B2/B3 pairs. Do not combine today's previous B0 with a new boot. No bridge pause or double socket writer. Existing S002 phase comparator PR #151 only targets `RPGolMain+0x030` first 0x80: S002 #160 should add the narrowly selected record/nested-vector contrast to its own source-gated analyzer to avoid duplicate ownership.

**Phase B (ONLY after source-gate + Phase A):** ONE operator-approved known-good 45-A canonical swing with a small, bounded passive selected-record/nested-vector watcher inside the SAME S001 frame callback. Include independent frame markers, source-PPC writer sites and paired no-swing control; avoid paused full-RAM dumps during a contact window. Compare before contact, near impact, in flight and after landing without inventing timestamps or physical yards. Numeric ball velocity requires actual frame interval and consistent in-game units. No model before this passes.

**Priority source evidence request to S002:** Review source writer path from PR #160 (manager four-record init, selector source PC, record+0x88 ball-like member, child+0x4C vector); tie actual in-game memory object to those instructions with register provenance or debugger write watch, and identify chosen-record lifetime after tee vs shot. Verify exactly which vector represents ball world position rather than render proxy. Determine what in-game swing meter/power implementation and contact state write, independently from graphics.

## Training gate — all false as of B0

- Selected ball-like vector: static equality to start, runtime dynamic motion **NOT VERIFIED**.
- Velocity: **NOT VERIFIED**; no frame-aligned time series.
- Swing power: **NOT VERIFIED**; no same-shot game-written power field or three independent power levels.
- Club head pose: **NOT VERIFIED**.
- Same frame-thread input → actual game contact observation: **NOT VERIFIED**.
- Course start/pin/cup geometry: source-anchored and one B0 invariant, unit calibration and independent-hole replication **PENDING**.
- Training: **BLOCKED**. Model code PR #125 and frame-hook study #147 remain gated; don't interpret training score penalty (100 feet) as physical carry.

CI and privacy: new static PPC tool has seven fully synthetic tests, Linux and Windows focused workflow; full repo failures still tracked separately. All outputs LOCAL only and are not S000-approved publication records. Actual bytes, private pointers, main.dol, ROMs, user files and complete disassembly never enter GitHub.