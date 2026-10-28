# S002 P0 — Seven-phase source-selected RPGolPlayer+0x024 equality audit

**Status:** draft, synthetic validation only. **No operator real seven-bank execution or state-semantic claim.**

## Disjoint question and prior work

- PR #162 documented a Rev1 PPC player-record receiver writer assigning literals 1,2,3,4,5 to +0x024. This is **not** an exhaustive or decoded enum.
- PRs #174 and #176 examine only the original B0–B3 no-shot series.
- PR #231 already source-gates the DIFFERENT seven numbered bank pairs and reads the complete 51-u32 selected record, including +0x024; its published comparisons focus on +0x034/+0x038/+0x074. PRs #230/#232–#234 own ball/cache/axis comparisons.
- This new-only script provides a limited equality/membership crosswalk for +0x024 using exactly #231's source reader. It changes no existing readers or registries.

## Falsifiable comparison

For the seven human-labeled snapshots, print only first-appearance opaque equality groups, whether each unknown word is zero, whether it belongs to the known five writer literals, and whether a nonzero value falls outside that set. **Never print the original uint32 or its hash.** Compare driver 1→2, wedge 5→6, 6→7, 5→7 as same-shot HUMAN notes, not machine-proven phase IDs. Include 3→4 only with explicit different-club/input confound and no A-button causal claim. No state name (flight/contact/landing/shot) is inferred from a changed or unchanged integer.

## Existing source/geometry gates

Use #231 _check_archive and _get: archive confinement, original 14 bank SHA, Rev1 scene and source-selected record/ball/slot/hole. For every compared edge, additionally require stable selected player/hole, record+0x88 ball-object pointer, FieldManager, source pin/start object pointers, pin/start vectors and GolfConfig BC/C0/C4. On any failed gate **ABSTAIN**. There is no new dump, Dolphin launch, controller input, arbitrary RAM scanner, ROM upload or automatic result publishing.

The five source writer opcode instructions were investigated by PR #162/#176, **not revalidated here**. Explicitly keep source_writer_instructions_reverified_in_this_study=false and all model-training, state, power, XYZ, velocity, contact and publication flags false.

## Validation and reproducibility

Run only the fabricated focused tests:
- Windows: py -m unittest discover -s tests -p 'test_p0_seven_state24_private.py' -v
- Ubuntu: python -m unittest discover -s tests -p 'test_p0_seven_state24_private.py' -v

There are 16 synthetic tests covering equal/different/zero/unknown states, club confound, phase set, owner/ball/pin/start/config instability, privacy and false training flags.

**After owner review and pinned checkout only**, the operator may run this existing-bank read-only analysis with one command: py -I scripts/audit_p0_seven_state24_private.py --archive <private seven numbered capture archive>. This is not authorization for any new shot, raw upload, training or merge. Source semantics, boot/frame identity and physical meaning remain unverified.
