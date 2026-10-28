# S002-PLAYER-BALL-ROSTER-01 — two-bank structural hypothesis

Status: one existing operator MEM1/MEM2 snapshot pair. NOT same-frame verified, NOT class-type proven, and NOT game power, club pose or physics ball.

## Observations grounded in the operator's privately uploaded raw dumps

The MEM1 image is 24 MiB with RSPE01 Revision 1 header. The MEM2 image is 64 MiB. Source scene-manager storage leads to a MEM1 manager and a MEM2 Golf scene. Scene own ID 5, manager backlink, sport ID 2, candidate vtable interval and RPGolConfig source mode 4 agree. Source-derived scene +0x9C points to a MEM2 object with its first word inside RPGolMain code-unit .data. PlayerManager singleton candidate storage points to MEM2 with a first word inside the RPGolPlayerManager .data range.

**New candidate pattern:** in the player-manager candidate object, exactly four distinct pairs have child first words lying in two source compilation-unit .data intervals, spaced at 0xCC-byte stride. The ball-like side is member +0x8C and the player-like side is +0xC8, each plus slot-index times 0xCC. A separate child of the main candidate at +0x30 has a first word within Player .data.

This is NOT evidence that these are verified C++ player-manager member offsets, that there are 4 active players, that each first word is the exact class vtable, or that a candidate is the actual gameplay/physics ball. A single snapshot cannot establish motion, slot activity or any float semantics.

## Public source references

- doldecomp/ogws config/RSPE01_01/splits.txt: RPGolMapObjBall.cpp .data 0x803C7918..0x803C7A50; RPGolPlayer.cpp .data 0x803C7CC8..0x803C7DD0; RPGolPlayerManager.cpp .data 0x803C7DD0..0x803C7DE0; RPGolMain.cpp .data 0x803C7798..0x803C77C0.
- kiwi515/ogws_info RP/RPSports/RPGolScene/RPGolScene.h: candidate RPGolMain* scene member at +0x9C.
- Compiler-unit ranges are NOT exact vtable locations or verified runtime object types.

## Implemented tool, security and validation

scripts/audit_golf_two_bank_roster_private.py uses native local 24MiB MEM1 and 64MiB MEM2, gated on rev, source manager backlink, scene identity, sport, golf mode, vtable data region plausibility, and the bounded four-pair pattern. Inputs are confined to ignored sibling Wii-AI-Golf-Data; it does not launch Dolphin, connect RPC, send controller input, write any memory, scan a whole RAM bank, publish anything or print private pointer values. Console reports only aggregated booleans/counts and all unverified claims remain false. No training.

tests/test_golf_two_bank_roster_private.py uses 11 synthetic cases, including negative controls and privacy redaction. Windows/Linux targeted CI configured; complete canonical Windows suite and review required before merging.

## Optional reproduction with already-preserved private images; NO new dump

Use a clean worktree of this PR and, if your native copies are already under ignored Wii-AI-Golf-Data, run:

    py scripts/audit_golf_two_bank_roster_private.py --mem1 "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\mem1.raw" --mem2 "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\mem2.raw"

Adjust only the private filenames. Never copy raw dumps into a Git worktree or public channel. The original operator upload has already been inspected, so additional captures are not needed.

## S002 next source-level gate

Review the actual PowerPC object-constructor/init/access callsites in RPGolPlayerManager.cpp .text 0x802A2210..0x802A3560, RPGolPlayer.cpp .text 0x8029E62C..0x802A2210, and RPGolMapObjBall.cpp .text 0x80296FD8..0x8029B240. Independently verify register receiver provenance and the repeated 0xCC layout before calling these real player/ball members. Existing PR #144 D-form atlas provides operand hypotheses but not receiver identity. Use only the locally extracted Rev1 main.dol, no ROM or raw bytes on GitHub.

Stop if class/constructor linkage cannot be supported. Only after source proof propose narrowly bounded same-shot read-only player/ball field sampling; no power model, repeated broad RAM sweep or new shot yet.


## New independent static-code corroboration from this same MEM1 image

The live game's CPU-code bank also contains the public RSPE01_01 RPGolPlayerManager.cpp compilation-unit .text 0x802A2210..0x802A3560. A bounded PPC D-form immediate-only scan of precisely 1,236 4-byte words found:

- 4 PowerPC mulli (primary opcode 7) instructions with immediate 0xCC.
- 7 PowerPC addi (primary opcode 14) instructions with immediate 0xCC.

That repeated immediate agrees with the 0xCC interval in the speculative RAM records. The tool now checks both code-immediate families separately from the four candidate pairs, and reports only counts. **Crucial:** this STILL DOES NOT establish which base register points to the actual manager record, that the same instructions index these candidate object fields, or the C++ meanings of members +0x8C/+0xC8. Verification now requires a bounded register/dataflow review of those PPC callsites. Source-code unit boundaries from splits.txt are not named function boundaries. No full code dump, assembler instructions or private binary bytes are published.



## Follow-on S002-ROSTER-PPC-02 — bounded cross-unit instruction/dataflow evidence

I disassembled the *existing, privately captured MEM1 code* with PowerPC32 decoding, restricted to documented Rev1 compilation units from ogws splits.txt. This is **source code already present in the operator's one uploaded MEM1 dump**, not an extracted ROM published to Git and not a new game action. The same code checks are now included in the single existing offline analyzer; no competing scanner was created.

**Four inline records, confirmed source-code pattern:**
- In PlayerManager code at PC 0x802A3194, manager receiver r3 is saved to r29. PC 0x802A3200 computes r31 = r29 + 4.
- PCs 0x802A3214 / 0x802A3218 pass r31 and loop index r30 into a direct branch-with-link from 0x802A321C to the Player-code function 0x802A08A0.
- PC 0x802A3224 advances r31 by 0xCC; 0x802A3228 compares index r30 with 4; 0x802A322C branches back to the per-record call loop. Constructor code independently allocates manager and initializes four elements, each 0xCC bytes long, via PC 0x802A3490 and 0x802A349C..0x802A34A4. This is stronger than independent counting of mulli/addi immediates.
- This establishes a source-supported **record array shape** for the candidate manager: four inline 0xCC-byte records starting at manager+0x4. It does **not** prove four active players, dynamic class selection or accepted controller input.

**Ball-related member and nested three-component write (source corroboration):**
- The called Player-code function preserves record r3 in r30 (0x802A08B4) and stores a pointer to record+0x88 (0x802A08F0).
- Other Player code reads record+0x88 (0x8029F0E4) and branches to function 0x80297124, within the documented RPGolMapObjBall code compilation unit (ball method/class semantics still need manual proof).
- Player code 0x802A03A0 reads record+0x88, 0x802A03B4 reads that child's +0x4C pointer, then 0x802A03B8/0x802A03C0/0x802A03C8 store three successive 4-byte f32 words at child-of-child +0/+4/+8. The stored values are taken from source-labelled **record component triplets**, but **world space vs local space, coordinates vs render transform and units remain unknown**.
- Real paired bank snapshots: exactly 4/4 ball-like children have a mapped MEM2 pointer at child+0x4C, and 4/4 have three readable native words at its destination. In this one stationary snapshot **1 of 4** destinations equals its record+0x54 three-word triplet bit-for-bit. This is an equality observation, not an active-player or physics position proof.

**Player-related attached subobject, not necessarily the player instance:**
- Player code 0x802A0CB8..0x802A0DB4 constructs an allocated object. At 0x802A0D74/0x802A0D7C a data address is formed, 0x802A0D88 stores it as the object's first word, and 0x802A0D94 stores its pointer to record+0xC4.
- In privately held MEM2, all **4/4** candidate +0xC4 attached objects have a first word equal to that exact code-initialized data address. This verifies an explicit **constructor-compatible subtype/vtable-shaped word**, not generic Player class, 4 independently allocated players, or physics ball.

The offline analyzer now verifies **these exact PCs' opcode/register/immediate/branch-target patterns** with fail-safe booleans. It does not publish instruction words, RAM bytes, heap addresses or raw float values. Changed instruction or pointer gates fail individual provenance claims, never promote semantics. Fabricated-memory synthetic tests distinguish structural shapes from code-backed paths. None of the three-word values is labeled actual XYZ.

### Next falsifiable study (no new whole-memory scan)

S002/S000 can now review the reduced candidate list:
1. Pointer-owned record+0x88 -> ball-related object -> +0x4C -> three float-word destination.
2. Record+0x54/+0x58/+0x5C triplet: one plausible source of the three copied values in a branch.
3. Record+0xC4: allocated player-related subobject; not ball position or an independent active golfer.
4. The manager's selected record pointer at +0x334 (source writes at 0x802A2494..0x802A24B4 and 0x802A31EC..0x802A31F8), subject to register/dataflow proof and evidence of actual live selection.

Only after an explicitly owned, single Dolphin session can a **small paired-bank before/after control** distinguish render/simulation position, active vs non-active slot and actual swing phases. This dataset alone cannot prove ball/club velocity, impact time, game recognized power, or causal changes. S003 training remains BLOCKED.

