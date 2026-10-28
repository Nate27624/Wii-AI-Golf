# P0 — Source-gated receiver-chain application to original seven captures

**Owner-review-only, pending real private-run.** This extends draft #255 with an integration **runner** and PowerShell 5.1 entrypoint. The existing #231 canonical archive owner, #254 inner CFG owner, and #255 outer syntax helper remain separately owned; no changes to their source files. The user acknowledged that some capture phase descriptions may be mislabeled; none are used here.

## Known source evidence (separate from this new run)
- #240 operator previously confirmed seven original-source snapshots: source-global ball pointer **outside all four roster balls** 7/7. Source-global position matches source-selected +0xCC for IDs 5/6/7, while selected current+0x30 differs in 5/6 and equals CC in 7. This is not the displayed ball's proven location.
- #240 separate operator r13 slot xref scanned 13,934 PPC words in six Golf source units: 15 exact r13 global pointer loads, one exact direct `stw` at RPGolMapObjBall source unit +0x3084, source register `r3`. Its nearest bounded def is `addi`, but intervening control-flow remains unresolved. The owner is pursuing that micro-window, NOT this PR.
- #219 provided two static outer-to-inner calls: SimulateManager `fn_8029B43C→fn_80299ACC`; MapObjBall `fn_8029A204→fn_80299C20`. #254 independently evaluates branch-sensitive inner function reaching definitions; #255 evaluates outer immediate `r3` source syntax.

## What the new integration does
`scripts/audit_p0_authenticated_receiver_chain_private.py` has only a private-source offline CLI. It imports the EXACT reviewed #231 canonical source reader (not its human phase-labeled summary) and the exact reviewed #254 pure CFG helper, alongside #255 own source-only script. It verifies the original #231 14-bank capture archive by SHA *before and after*, RSPE01 Rev1 scene/selected player/ball/field/pin/start chain for **every one** of seven original captures and verifies source-r13 FieldManager anchor/load/translation pattern, checks all FOUR roster record+0x88 ball pointers plus fifth global-ball translation self-reference in all seven.

Then it SHA-digests source-code *windows* from both outer function entries, both inner entry→cache BL ranges, plus exact anchor/slot-follow sites and requires those code windows **bitwise unchanged across all seven independent captures**. Only then does it join:
- #255 `inspect_upstream(read_u32)`: strict `bl` per bounded 0x100-byte outer SEARCH window, nearest 0x40-byte `r3` source syntax and control-flow hazard.
- #254 `inspect_known_callers(read_u32)`: conservative bounded inner CFG all-reachable-path entry `r3→r31→r3` must flow or explicit abstention.
- A strict matching of the exact two source caller names so source pairings cannot silently swap.
- **New categorical discriminator:** whether an outer-callsite nearest syntactic `r3` def is an EXACT direct `lwz r3,global-slot-displacement(r13)`, with source-global slot authenticated by independent Golf FieldManager anchor. A `lwz r3,+0x88(rX)` receives ONLY an *unowned player-ball offset* candidate classification since identity of the base register is not proven.

Report fields are categorical/booleans/counts/public source symbol names only. Actual **runtime** global vs player-roster object receiver, executed cache writer, ball renderer, physical XYZ, power/velocity/impact/score and training/pub permission remain FALSE regardless of apparently matching source syntax or all-path inner CFG.

## Original Windows operator run (after owner review)

Use your existing repo and a **detached worktree** at an explicitly reviewed integration PR SHA. Then:

```powershell
& .\scripts\Invoke-P0ReceiverSourceChain.ps1 -ReviewedHead '<EXACT_REVIEWED_PR_255_SHA>'
```

The wrapper finds exactly ONE existing canonical original private `p0-new-cohort-*-PRIVATE` folder (or accept `-Archive '<exact path>'`), verifies original manifest type, checks current integration HEAD, fetches **EXACT** pinned #231 SHA `89aa3a2bd3e82532c4051168a466498e7195f596` and #254 SHA `8696a46a315499f220ee7c87580a21dc99f21462`, places each in separate detached clean worktrees, runs the three fabricated local test groups, canonical source SHA before the new read, the receiver join, canonical SHA after the new read and confirms manifest unchanged. Temp worktrees are cleaned up; original game data untouched.

No automatic uploads, no new Dolphin, controller, ROM, snapshots or guest writes. Any provenance/shape mismatch fails CLOSED; do NOT edit private manifest to bypass it. If owner PR heads drift, STOP and review their new revisions.

## Meaning of returned results

- `STATIC_ENTRY_R3_MUST_FLOW` by #254 would establish a **syntactic inner register-preservation chain under its conservative bounded control-flow model**. It is not a proof of class of object passed from an outer call.
- `DIRECT_GLOBAL_R13_LOAD_SYNTAX_CANDIDATE` from the new join is the strongest narrow hint: an exact `lwz` from the verified source-global pointer slot appears as nearest source `r3` def. Outer *all-path reaching definition* still unproved, so runtime receiver remains UNKNOWN. Missing/ambiguous callsite or a different code pattern is likewise UNKNOWN, **not proof the receiver is player-owned**.
- `BALL_CHILD_OFFSET_0x88_UNOWNED_BASE_CANDIDATE` is a hint of a ball child access only. Without proving `rX` points to an RPGolPlayer record it CANNOT establish selected/inactive player-ball ownership.
- If the independent native data have the source-global pointer outside all four roster balls, that proves two kinds of stored ball objects existed in those snapshots, not which one is passed at either static callsite.

No phase ordering, same physical shot, exact guest-frame, live receiver object or physical motion conclusion. Draft/hold all training.
