# P0 four-slot receiver extension: fail-closed cross-phase consistency review

## Focused ownership

Only the *second* new script introduced in #240 (`audit_p0_global_ball_roster_receiver_private.py`) and its fabricated tests are modified here, not the primary global-source/cache PPC analyzer or other agents' work. This branch is stacked on #240 and requires its source owner's approval.

## Why these controls are necessary

Independent real seven-bank results show the r13 source-global ball object differs from the player-selected ball and has position words equal to selected cache CC at W5/W6/W7, but no active runtime cache writer or rendered-projectile identity is verified. The new four-slot membership probe can compare each phase correctly while accidentally implying the same four objects remained in every phase. The initial implementation previously compared only the selected ball pointer, and its static r31 classification could call an entry-r3 origin an *unambiguous linear candidate* when a branch came after the first r31 assignment.

The source-selected roster's three inactive ball object identities, selected pin/start **vector contents**, source Config BC/C0/C4, and exact r13 global-source slot now stay private and must match across the provisional D1/D2 and W5/W6/W7 groups. The bounded PPC r31 caller probe is also compared for all seven phases, with any change forcing ABSTAIN. Branches after an r31 assignment no longer qualify as an unambiguous linear-origin candidate. Raw guest pointers and source data never appear in the JSON report.

## Explicit known limitation

This extension's pre/post bank hashes alone still do **not** establish the original #231 canonical 14-bank manifest identity. A separate integrity gate is implemented by #241 and for the primary #240 script by #247; integrating one agreed shared manifest gate into both #240 readers must precede any fresh operator real-data interpretation. This review purposely does not build another duplicate archive reader.

All numbered shot labels and shot ordering are operator annotations and may be mislabeled. A stable source pointer or an exact cache equality does not prove a rendered-world position, landing predictor, runtime writer execution, impact, score, power, velocity or guest-frame interval. Keep all training/publication flags false.

## Fabricated regression suite

`python -I tests/test_p0_global_ball_roster_receiver_private.py`

The existing tests plus new checks reject inactive roster replacement, pin/start coordinate drift behind unchanged pointers, Config changes, source-global r13 slot drift, incomplete private comparison information and an r31 branch hazard after its first apparent assignment. The dedicated Windows and Ubuntu Actions jobs run only synthetic cases. No Dolphin launch, extra shot, RAM write, binary upload or model-training action.