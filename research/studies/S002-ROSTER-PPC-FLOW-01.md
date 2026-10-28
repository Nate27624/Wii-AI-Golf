# S002-ROSTER-PPC-FLOW-01 — bounded, static register-shape triage

**S002 support / draft / source-syntax hypothesis only.** Stacked directly on PR #160 (source-gated four candidate player/ball roster pairs at 0xCC stride). This adds **only** an offline PPC code-flow helper, tests and study; no changes to PR #160, S001 live controller, S002 captured game memory, S000 uploader, or S003 models.

## Operator evidence before this study

Real private 24MiB MEM1 + 64MiB MEM2 (RSPE01 rev1, mode4) passed source-gated chain: manager scene ID5, scene own ID/backlink, sport2, main object pointer, player manager plausible first-word data interval. PR #160's real run found four distinct candidate ball-like/player-like references in four 0xCC-separated records; 4 manager-source-unit PPC mulli instructions and 7 addi instructions use immediate 0xCC out of 1,236 instructions. This is **not yet a verified real player/ball object, complete member layout, nor power, pose, ball XYZ or shot state**. The two bank files have an approximate 111.41-second modification-time gap, so no same-frame or same-boot correlation is asserted.

## Distinguishing hypothesis

H0: The repeated 0xCC in code is unrelated to snapshot-derived roster records at +0x8C and +0xC8; 4+7 immediate matches alone have no receiver provenance.

H1 (weak syntactic): At least one PPC mulli slot*0xCC result feeds an add with another register and then a bounded D-form memory load/store at +0x8C or +0xC8 without an intervening branch or recognized register clobber. This is *still not register receiver identity*, a proven execution path, the full PPC CFG, an exact vtable, or C++ layout. Current tracker stops rather than guessing across unknown PPC families; zero chains is inconclusive, not H0 proof.

Source interval: doldecomp/ogws config/RSPE01_01/splits.txt, RPGolPlayerManager.cpp .text 0x802A2210..0x802A3560 (end exclusive), 1,236 32-bit big-endian PPC instruction words.

## Offline tool and safety

New scripts/audit_golf_roster_ppc_flow_private.py uses existing **native MEM1 only**; does not require another shot, dump, MEM2 read, main.dol, Dolphin or RPC. It refuses wrong game header/revision, incorrect 24MiB size, a symlink or path outside sibling Wii-AI-Golf-Data. Reads only the exact source compilation-unit code interval using read-only mmap. Examines mulli/addi immediate 0xCC, candidate D-form member +0x8C/+0xC8 and conservative bounded instruction chains. No arbitrary heap scanning. Prints ONLY bounded aggregate counts and false identity/physics/provenance flags, never executable opcodes, code addresses, RAM values, heap pointers, private file paths or binary code. Explicit allowed_to_publish:false; not yet a S000 approved public observation.

Tests in tests/test_audit_golf_roster_ppc_flow_private.py: 9 synthetic cases for positive indexed-address chains, unmatched register, branch barrier, unknown PPC opcode barrier, explicit GPR overwrite, multi-register lmw clobber, addi-vs-mulli, offset-only false positives, output redaction and bounds. Python compileall PASS and all 9 synthetic tests PASS in isolated Linux workdir. A full-size 24MiB generated **synthetic** MEM1 CLI smoke passed (1 generated code candidate chain). User's actual MEM1 has NOT been run on this branch and full canonical Windows suite has NOT been run.

## Operator offline-only reproduction

In PowerShell with your existing private native MEM1 copied in the Data sibling directory:

~~~powershell
$root = "D:\Projects\Wii Golf AI"
$repo = "$root\Wii-AI-Golf"
$work = "$root\Wii-AI-Golf-Roster-PPC-Flow"
$privateMem1 = "$root\Wii-AI-Golf-Data\mem-checkpoints\roster-existing\mem1.raw"
$branch = "origin/agent/research/roster-ppc-bounded-flow-20261027"

git -C $repo fetch origin
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
if (Test-Path -LiteralPath $work) { throw "Research worktree exists; preserve it" }
git -C $repo worktree add --detach $work $branch
if ($LASTEXITCODE -ne 0) { throw "Worktree creation failed" }
Set-Location $work
py -m unittest discover -s tests -p "test_audit_golf_roster_ppc_flow_private.py" -v
if ($LASTEXITCODE -ne 0) { throw "Targeted study tests failed" }
py -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Full regression failed" }
py scripts/audit_golf_roster_ppc_flow_private.py --mem1 $privateMem1
if ($LASTEXITCODE -ne 0) { throw "Offline PPC analysis failed" }
~~~

Paste only the JSON stdout, not any raw dump. If the private file is stored in a different Data-subdirectory, change only $privateMem1. There is no need to recapture MEM1 or MEM2.

## Follow-up, regardless of findings

If any bounded syntactic candidates match, S002 should review *named PPC function boundaries, register origin, and the object receiver* at those sites using the source-reviewed PPC/DOL extraction from PR #122/#144/#146. Do not promote to actual ball/player until receiver and write/access semantics are independently proven; do not treat the number of slots as active players. If the bounded scan yields zero chains, inspect unsupported instruction families or a source callsite/decomp, not arbitrary RAM.

This branch must stay DRAFT until the S002 owner confirms coexistence with PR #160, Windows focused/full suite passes, and S000 reviews privacy; no automatic merge, new native dumps, additional swing trials or S003 training.


## Operator evidence — first real bounded code study (2026-10-27)

User ran the earlier #161 analyzer against their preserved real native MEM1:
- code_unit_instructions_checked=1236; mulli 0xCC=4, addi 0xCC=7.
- mulli_sites_with_bounded_index_plus_base_add=4.
- direct_candidate_member_memory_opcode_counts: exactly 3 +0x08C_load, zero +0x08C_store, zero +0x0C8_load/store.
- mulli_sites_with_bounded_index_add_then_member_access=0; all direct strict chain counts 0.
- register_receiver_dataflow_proven=false; no ball XYZ, club pose or swing power verified.

**Interpretation:** Four syntactic scaled-index+base additions are present, but none pass the very restrictive same-register, D-form +0x8C/+0xC8 member access pattern within 20 recognized instructions. This does not refute the 4x paired roster layout. Candidate explanations include D-form memory +0 offset from the derived record address; indexed PPC X-form loads; an intervening addi +0x8C/+0xC8; a branch, unhandled opcode, or intervening helper call. Code immediates with 0x8C elsewhere are NOT guaranteed related to the same derived base.

## Follow-up instrumentation (same PR; no new game capture)

The updated analyzer separately counts how many of the four joined sites exhibit:
- D-form 0-offset load/store or other small relative offsets from the joined register.
- Indexed PPC X-form lwzx/stwx and selected byte/halfword/FPR indexed loads/stores.
- addi immediate +0x8C/+0xC8 applied to the joined address and then D-form 0-offset memory.
- Conservative stop reasons: branch, multi-register GPR load, unknown PPC opcode, or bounded-window end.

These are **site counts**, not exhaustive dynamic dataflow or inferred class members. The updated test suite adds four synthetic tests (13 total expected): joined zero-offset load, addi-member then zero-load, PPC indexed load, unknown-opcode fail-closed. Run the focused/full Windows suites and same saved input from the existing worktree after refreshing the clean branch. Do NOT interpret any positive shape as source-level object class identity; after this, assign S002 a source-backed receiver and constructor/xref review using PRs #144/#146.


## Operator evidence: second real run and decision on next gate

The user reran the updated #161 source-unit audit against existing MEM1 (no new Dolphin data):
- Four of four mulli 0xCC sites reached a syntactic index-plus-base add.
- Three of four continued into a different addi displacement (not +0x8C or +0xC8); one reached a different small-offset load.
- None reached a zero-offset load/store, indexed X-form memory access, addi +0x8C/+0xC8, or direct +0x8C/+0xC8 memory access.
- **Two** joined traces stopped at a PPC branch; **two** stopped at an unsupported PPC opcode. No 20-instruction window ended normally.
- Static source code unit had three +0x8C loads at unspecified unrelated base registers and zero +0xC8 loads/stores; these are independent totals, not evidence of roster membership.
- All receiver/provenance/class/physics flags remain unverified.

Interpretation: the original 20-instruction bounded straight-line tracker is the bottleneck in half of the sites due to control-flow boundaries, and in the other half due to unhandled instruction families. Do not broaden the full memory scan or run shots yet. One bounded final diagnostic per site was added to **the same #161 helper**:
- ordinal 1–4, boolean join/member flags;
- early termination class and *primary opcode family or opcode31 XO family* (not raw instruction word);
- observed post-join shapes and a small capped list of source-code signed addi immediates in hex (not raw memory).
These fields enable S002 to prioritize 2 unknown-family decoders vs source-level branch CFG review. The scan still does NOT prove the other input register points to a player-manager base or that class construction uses the candidate slot layout. The richer per-site report requires Windows targeted/full tests and an operator real-data rerun before interpreting the categories. The current helper adds two additional synthetic tests, bringing the intended total to 15.

Success decision: nominate one or two exact unsupported opcode families for S002 manual PPC dataflow review, then prove constructor base-register ownership with a bounded cross-reference. Positive syntactic matches never authorize field promotion; no new training or live capture is justified solely by this result.
