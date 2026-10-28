# S002-PLAYER-MEMBER24-01 — source-writer candidate in four no-shot phases

**Offline ONLY, from already-preserved B0/B1/B2/B3 native MEM1+MEM2 pairs.** Stacked on S002's existing #163 private selected-ball/start B0-B3 audit, which itself imports #160 source-backed roster. No new Dolphin, savestate, controller, RPC, bridge, camera, game start, shot or file output. Do not upload raw memory, checkpoint manifest or script output without S000 review.

## New specific source finding and limits

The real operator's previously uploaded RSPE01 Rev1 MEM1 code contains a candidate `RPGolPlayer.cpp` routine in which:
- At 0x8029F0C0, `mr r29,r3` saves an apparent receiver.
- Five literal loads/store sequences write to the **+0x24 offset** in a player-like record:
  - PC 0x8029F0C8: `li r0,5` → PC 0x8029F0CC: `stw r0,0x24(r3)`
  - PC 0x8029F0D4: `li r0,1` → PC 0x8029F0DC: `stw r0,0x24(r3)`
  - PC 0x8029F0F4: `li r0,2` → PC 0x8029F0F8: `stw r0,0x24(r29)`
  - PC 0x8029F134: `li r0,3` → PC 0x8029F138: `stw r0,0x24(r29)`
  - PC 0x8029F1BC: `li r0,4` → PC 0x8029F1C0: `stw r0,0x24(r29)`

**IMPORTANT source correction:** First two stores use `r3` as base and latter three use `r29`. Some preliminary handoff notes described all five as `r29` stores; that shorthand is *incorrect*. Exact load and store opcode/operand pairs above were checked against the real original MEM1 code, not just generated test fixtures. This verifies literal writer instruction shapes. It does NOT prove that all branch-specific r3 values are always the same receiver, that these five literals exhaust all values, or that the member is a typed gameplay enum.

In the one uploaded private still-state MEM1/MEM2 pair, the code-selected player manager record pointer at manager+0x334 resolves to **slot 0**, and its +0x24 word is **zero** (not one of those five source-written literals). Only this B0-like still pair was inspected for this new scalar in ChatGPT. We do **not** yet know this word's B1/B2/B3 values, nor its meaning in aim/hit/motion.

## New contribution without another scanner

`scripts/audit_selected_player_member24_four_phase_private.py` uses **existing** S002 #163 manifest verification and B0-B3 private checkpoint names (`B0-MEM1.bin`, `B0-MEM2.bin`, ... `B3-MEM2.bin`, `checkpoint-manifest-PRIVATE.json`) and #160/#163 source selector/ball/start gates. It hashes original banks only to match private original manifest, uses read-only mmap on the eight native existing files, checks exactly the five real PPC writer sequences, then reads **one source-selected u32 at selected player record+0x24 per phase**.

Output is strictly sanitized: boolean membership in the set of code-written literals {1,2,3,4,5}, three per-transition **changed/not-changed** booleans, distinct 32-bit word-class count 1..4, selected index and hole stable/known source status, and reused ball/start no-shot control result. **No integer values, heap pointers, private paths, hashes, ROM/code bytes, signed values, float guesses or per-slot raw words** are printed. In every case: gameplay state, flight/contact/landing, actual physical ball XYZ, power, guest frame verification, publication and training remain **false/unverified**.

## Optional read-only operator run (ONLY already-preserved files)

No additional capture is needed. Use an isolated, unmodified worktree of this stacked research PR:

~~~powershell
$repo = "D:\Projects\Wii Golf AI\Wii-AI-Golf"
$work = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Player24-Audit"
if (Test-Path $work) { throw "Preserve existing checkout" }
git -C $repo fetch origin pull/174/head
if ($LASTEXITCODE -ne 0) { throw "PR fetch failed" }
git -C $repo worktree add --detach $work FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw "Worktree creation failed" }
Set-Location $work
py -m unittest discover -s tests -p "test_selected_player_member24_four_phase_private.py" -v
if ($LASTEXITCODE -ne 0) { throw "Source gate tests failed" }
$private = Read-Host "Existing B0–B3 PRIVATE session folder under Wii-AI-Golf-Data"
py scripts/audit_selected_player_member24_four_phase_private.py --private-root $private --aim-visibly-moved --operator-same-session
if ($LASTEXITCODE -ne 0) { throw "Do not infer +0x24 values; source audit refused" }
~~~

The `--aim-visibly-moved` and `--operator-same-session` arguments are explicitly operator attestations of the existing four-phase experiment, not independent time/boot proof. Never invent a manifest or capture to satisfy this gate.

## Falsifiable interpretation and next decision

- If word remains constant through idle/aim/return while ball/start remain stable, it is only a **no-shot-stationary member** candidate, not a power or motion sensor.
- If word changes during no-shot aim with stable selected roster/field, note candidate AIM/control relationship for a later S002 interpretation; still do NOT label it as aiming.
- If word changes with idle/no action, possible scheduler/animation/state lifecycle confounds require more independent source/negative controls. Do not promote.
- If source writer code differs, +0x24 word is outside bank, selected identity changes, manifest invalid, or input lacks all eight verified images, abort.
- Only a later **visibly observed moving ball/contact study** with independent timing/boot provenance can test hit/flight phase semantics. The clean restarted Felk installation responds to RPC but is not currently a validated game-state contact session. S001 still owns any live input; don't restart/reset it merely to test this offline scalar.

S002 source/owner review and S000 evidence ledger privacy approval required before merge. S003 training remains blocked.
