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
