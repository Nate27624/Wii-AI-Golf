# S002 P0 — Offline guest-step attestation boundary (2026-11-21)

**Owner:** `S002-guest-step-witness-20261121-a` · **Task:** `S002-P0-GUEST-STEP-EVIDENCE-20261121-A`  
**Roster:** [S000 rev48](https://github.com/Nate27624/Wii-AI-Golf/pull/320#issuecomment-7073967068) · **CLAIM:** [issue #472](https://github.com/Nate27624/Wii-AI-Golf/issues/472#issuecomment-7073983875)  
**Evidence state:** offline synthetic validation only; `native_game_parity_verified=false`, `training_approved=false`.

## Why this is a separate evidence gate

The current S003 M1 trajectory producer emits **numerical steps**, not verified
native Golf guest-physics invocations. A Felk host callback, VI FrameAdvance,
FrameDrawn, a read-only selected-Ball sample, or a visually observed shot does
not by itself prove a specific guest physics step occurred. Existing public
S001 investigations [#272](https://github.com/Nate27624/Wii-AI-Golf/pull/272),
[#281](https://github.com/Nate27624/Wii-AI-Golf/pull/281) and
[#297](https://github.com/Nate27624/Wii-AI-Golf/pull/297) retain this NO-GO.
Selected and source-global Ball objects can differ; archived D1 human-airborne
vs START contradiction is unresolved. No hypothetical time scale, constant
host/guest ratio or interpolation is substituted.

## Bounded input contract

`scripts/review_p0_guest_step_attestation.py` exposes pure
`evaluate(document)` and optional **stdin-only** JSON (≤256 KiB; ≤4096 events).
Strict allowlist keys; short symbolic IDs only, no paths, per-boot native
addresses, raw guest memory, ROM, original captures or physical XYZ.

- `schema = "wii-golf-guest-step-attestation-v1"`.
- `trace_kind = "synthetic" | "sanitized"`. A sanitized record is still a
  **claim**: JSON cannot independently authenticate guest execution.
- `source_revision = "RSPE01_01"`.
- `clock_domain = "qualified_guest_physics_step_counter"`; host/VI indices
  are distinct and never used to create a physics counter.
- `qualifiers`: strict Boolean claims of source archive SHA qualification,
  source executed-PC mapping, selected-Ball receiver mapping and post-step
  boundary mapping; absent/false => abstain.
- `identity`: symbolic `boot`, `shot`, `ball_epoch` (same-shot identity).
- `events`: zero or more `vi_frame` / `host_callback` markers, plus
  `guest_step` objects with matching identity, `executed_guest_pc=true`,
  `receiver="selected_ball"`, `phase="post_golf_step"`, `atomic=true`,
  strictly consecutive `guest_step_index` and strictly increasing
  `host_frame`. Duplicate host frame cannot imply another native step
  without separate evidence; abstain rather than assume. Sparse host frames
  are allowed **only** if guest-step counter itself is contiguous.

## Output and M2 consumption boundary

- `SYNTHETIC_CONTRACT_PASS` permits a **synthetic** count only. Positive
  controls test the validator, not the emulator.
- `CANDIDATE_REQUIRES_EXTERNAL_PROOF` means sanitized claims are internally
  consistent; `sanitized_candidate_guest_steps` is **not** a verified native
  count. M2 must still refuse a native comparison.
- `ABSTAIN_*` identifies the missing source, executed-PC, selected receiver,
  same-shot epoch, phase, atomicity or clock evidence.
- In every output `verified_native_guest_step_count=null`,
  `guest_physics_clock_independently_verified=false`,
  `native_game_parity_verified=false`, `training_approved=false`.

**Critical unresolved native proof:** an externally source-qualified **actual
executed Golf physics entry/exit event** tied to the selected Ball receiver
and one uninterrupted boot/shot epoch, atomic post-step ordering, and a
guest-origin monotone invocation counter. Self-asserted metadata, static PPC,
bridge RPC success or host callbacks cannot substitute. S001/S002 must first
establish a permitted producer with independent source and runtime evidence;
any live Dolphin or private archive study needs *new operator authorization*.

## CLI exit status is not native-attestation status

The optional stdin-only JSON CLI uses **exit 0 only for**
`SYNTHETIC_CONTRACT_PASS` (fixture logic, **never** a native witness),
**exit 1** for source/receiver/clock/identity abstentions **and** for
`CANDIDATE_REQUIRES_EXTERNAL_PROOF` (consistent but independently
unverified sanitized claims), and **exit 2** for malformed/rejected input.
Consumers must read the JSON `status` and
`verified_native_guest_step_count`; no process exit code, including 0,
certifies guest timing. This differs intentionally from the independent
coordinate-basis #477 consumer: neither exit-0 success category constitutes
native physics parity. There is no direct M2 adapter or live input.

## Acceptance tests and commands

`python -m unittest discover -s tests -p test_p0_guest_step_attestation.py -v`  
`python -m unittest discover -s tests -v`

Synthetic tests cover missing executed PC, wrong selected receiver, wrong
boot/shot/epoch, duplicate/nonmonotone host frames, absent/gapped guest counter,
discontinuous phase, nonatomic sample, wrong source revision, host-as-guest
cadence, strict types/privacy fields, bounded input and safe stdin errors.
Run full tests on proposed exact head and require configured Windows/Ubuntu CI
before non-draft promotion/merge under root `merging.md`.

No LocalOps Beads task is assumed registered for this new S002 assignment;
the historical `wgp-y7h` was synthetic and unrelated. No LocalOps operation,
Dolphin, private source access, real shot, model fitting or training is
authorized by this document.
