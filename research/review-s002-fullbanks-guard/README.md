# S002 full-bank exporter — independent synthetic failure review (2026-10-28)

Scope: independent tests only, stacked on draft [#201](https://github.com/Nate27624/Wii-AI-Golf/pull/201), which depends on [#184](https://github.com/Nate27624/Wii-AI-Golf/pull/184). Owner still controls the canonical reader `scripts/capture_golf_fullbanks_private.py`, PowerShell wrapper and keeper. This branch adds **no** new Dolphin boot, waveform, snapshot runner, user-facing command or publication schema.

## Findings

- A synthetic valid paused-attestation PRE flow calls the DME hook, writes both full binary *shapes* through the existing keeper API, and cleans staging. This tests code control flow; it is **not** a real 88 MiB game capture or proof that Felk Dolphin is paused.
- Missing pause attestation, invalid POST/RESULT evidence, wrong game revision, failed DME hook, untrusted session root, truncated RAM reads, and preexisting staging fail without a success report.
- On truncated bank reads or preservation failure, **`STAGING-PRE` remains** in the private session. This preserves forensic evidence but prevents a same-phase retry and may confuse operators. The S002 owner should decide whether to isolate failed staging with a unique attempt ID or clean only a provably new, incomplete attempt; never overwrite/delete earlier evidence.
- The reader does **not independently verify the Dolphin pause state or same-guest-frame MEM1/MEM2 atomicity**. Any POST taken after reset must be rejected, even when the operating system confirms that the process is the right Dolphin instance.
- Do **not** infer motion velocity, ball XYZ, power or score from synthetic acceptance.

## Validation and handoff

Run after checking out this *stacked* branch, no game:
`py -m unittest discover -s tests -p "test_s002_fullbanks_guard_review.py" -v`

The 12 tests passed locally against a manually mirrored copy of #201's reader source (Python 3, Linux). The exact GitHub branch full test suite and hosted Windows behavior were **not** run in that local experiment; GitHub CI is intended to validate the actual stacked branch. No installed `dolphin-memory-engine` or Windows emulator process was exercised. No raw RAM, ROM, savestate, configuration or private hash belongs in this PR.

Next owner: S002 #201 should review the staging retry semantics and native DME hook feasibility, then S001 should pair the keeper with the historically observed V1 45-observed-frame A lead. S000 should ensure any final operator-facing workflow is PowerShell-only and uses the existing canonical launcher, not a competing GUI or startup sequence.
