# S000 P0 memory integration — non-atomic flight-read guard (rev37)

**Scope:** offline scientific evidence checking, not a new decoder for coordinates, input, contact, results, or learning. Manager roster rev37 reserves the code/test paths for S000. S002 owns the 46-packet control-phase retrospective (#391), S001 the corrected live A/swing capture (#390), and S003 swing-power discriminators (#4).

## Observed discrepancy

A previously operator-supervised SHA-verified 46-packet aborted A/motion run contains 40 complete no-contact control packets and six contact-associated M1 packets. Source-selected ball +0x30 changed repeatedly during M1, but each host packet was non-atomic (roughly 0.62 seconds). Direct selected ball +0x30 and nested +0x4C -> +0x30 can resolve to the SAME source-qualified address while sequential reads differ. This does NOT imply two different ball objects or simultaneous coordinates.

Candidate cache +0xCC matched a later selected-current word triple in the same flight. One-shot forward equality cannot establish a predictive landing position, game-terminal outcome, or world units.

## Offline guard

The pure library at src/wii_ai_golf/audit/p0_flight_read_coherence.py accepts 2–80 already source-qualified same-run, same-shot, same-scene/hole, same-owner-epoch records. All timestamps are HOST packet brackets, not game physics frames. It accepts only direct/nested/CC allowlisted BE32 triplets plus opaque source and shot tokens. It never accesses the filesystem, RAM, Dolphin, or controller.

- Same-address aliased reads that differ are classified as non-atomic mismatch possibilities, not proof of separate actors.
- Cache CC equality with a future current value counts only if cache differs from current in its own packet; it is a timing pattern, not a landing prediction.
- Mixed shots, changed epochs, missing alias evidence, malformed words, reordered packets, invalid clocks, and extra fields fail closed.
- Output never exposes raw words or run identifiers and always has training_approved=false, no verified physics step, and no verified velocity/prediction.

Ten synthetic tests in tests/test_p0_flight_read_coherence.py verify the behaviors, including privacy. Full Windows/Ubuntu and exact-head full-suite runs remain required by merging.md.

## Integration dependencies

S002 #391 must verify the original exact private manifest schema before marking a real retrospective complete; quarantine M1 for no-contact statistics but preserve separate flight research evidence. S001 #390 must separate contact-possible swings from no-contact controls, record human observed contact, and seek atomic guest-frame read source. S003 #4 must not promote apparent normalized player-record +0x30 to swing power without typed source writer and graded calibration. Repeated CC matches across independently identified shots plus source/terminal evidence are needed before even considering a predictive interpretation. 100-ft off-green penalties remain censored and real training stays disabled.

Do not merge this contribution until current exact-head focused/full offline checks and required GitHub Windows/Ubuntu CI all pass under the canonical merge policy.
