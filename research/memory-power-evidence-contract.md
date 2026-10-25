# S002 → S003: Memory-informed swing-power evidence

**DRAFT / read-only / zero live trials.** This is an evidence bridge, not a trained power model, swing controller, Dolphin RAM reader, or second CLI. It stays separate from unmerged S002 phase capture PR #116, S003 evidence PR #119, power-identifiability PR #118, and S000 review PR #105.

## Research finding

Recent human-labeled V1 swings with 45-frame A lead at speed 0.8 / 0.9 or backswing 0.8 all made contact but were visually estimated near 75% power; 100.0 ft was an **off-green penalty**, not ball carry. Separately, the memory team's repeated minimap effect offsets are **unidentified rendering state**, not verified golf trajectory, power or club pose.

The proposed S002 phase capture produces golf-memory-phase-differential records: source-validated US Rev1 structural windows, idle/aim/A-hold/club/shot/settled phase labels, relative 32-bit changed-word counts, and non-atomic snapshot-span metadata. Its present schema lacks a reliable **same-shot join**, per-offset phase-conditioned change counts, and a source-verified gameplay power address. Neither matching timestamps nor float-like word-shape heuristics can repair those omissions.

## Implemented offline API

wii_ai_golf.memory_power_evidence.review_memory_power_evidence(memory_summaries, swing_observations):

- Consumes only sanitized record dictionaries; no I/O, raw bytes, emulation, RPC or network.
- Validates S002 schema, identity, sizes, aligned region-relative offsets, change counts, stage observations and source claim flags.
- Counts candidate offsets once per independent valid capture, detects duplicated IDs and invalid timing spans, and relegates minimap rendering regions to negative controls. Known structural windows remain **non-golfer / exploratory**, not claimed power.
- Can count matched records only after an explicit same-run and same-frame contract is met; missing evidence stays unlinked, never replaced by a timestamp guess.
- Outputs a bounded, allowlisted relative-offset shortlist, missing link reasons, and a concrete next research step.
- Always returns training_ready=false, verified_swing_power_field=false and predicted_swing_power=null. A change-count summary does not contain numerical swing-power values.

### Requested upstream FUTURE S002 publication contract

These fields are **not** present in PR #116 and **must not** be silently added by S003. They require S002's owner approval, S001 clock/controller validation, and S000 public allowlist approval.

| Proposed S002 summary field | Required cross-check |
| --- | --- |
| linked_swing_observation_id | exact unique S003 V1 public record ID |
| scenario_id | identical, source-backed scene ID |
| bridge_sha256, trace_sha256 | exact same bridge and controller waveform |
| a_lead_observed_frame_delta | same observed A lead |
| shot_start_frame_before_controller_trace | equals S003 human/swing start-frame provenance |
| capture_frame_min, capture_frame_max | bracket the start frame; shot_attempt must be a recorded phase |

**A complete join would not establish causal power or physical carry.** It establishes correspondence necessary for investigation, not what a RAM word means.

## Memory-led research plan

1. **Existing captures offline first.** S002 should publish sanitized summaries of already stored private outcome RAM captures, preserving genuine pre/post/settled labels. Never upload raw bytes.
2. **Find actual gameplay ownership.** Source-backed RPGolScene has an mGolMain pointer at scene object offset +0x9C, but neither the live scene instance nor the inner golfer layout is verified. Do not dereference a guessed address. Known RPGolConfig, RPGolFieldManager, RPSportsSequenceMgr, and minimap windows are not power decoders.
3. **Discriminate negative controls.** A future reviewed source-gated capture should compare idle/still, camera-only, A-held/no-motion, club movement without contact, observed impact and settled phases. Request per-offset per-phase change counts with bounded frame brackets from S002 rather than aggregate within/between-phase totals. Excessive non-atomic spans invalidate fast swing timing.
4. **Validate before learning.** A candidate must survive controls and remain source-grounded across independent fresh boots, distinguish objectively verified distinct power levels, and then pass held-out assessment. Never regress the 100ft off-green penalty as physical carry. Any live shot still requires S001's canonical full fresh-boot launcher and explicit one-shot approval.

## Ownership and tests

S002 #3 / PR #116 owns capture and publication. S001 #2 owns timing/input. S003 #4 owns offline model research and PR #119. S000 #94 / PR #105 owns the one CLI / approved loader. **None of those shared paths were edited.**

New paths: src/wii_ai_golf/memory_power_evidence.py, tests/test_model_memory_power_evidence.py and this file. **14/14 targeted offline source-equivalent tests passed** locally. Full canonical Windows suite and Dolphin tests NOT run here. This draft is not self-merge ready until required owner acknowledgment and full tests. No ROM, private RAM, savestate, credentials, local paths or raw captures committed.
