# S002-NATIVE-STAGING-RECOVERY-01 — PRIVATE native capture retry guard

2026-10-28. Additive helper for S002 paused full-bank reader PR #201 (stacked on native keeper #184). It changes neither the reader nor keeper, launch sequence, controller, V1 waveform, nor any publishing schema.

## Original failure
Current #201 save_pair() stages to a fixed STAGING-PRE/POST folder. If the MEM2 read or keeper fails, partial bytes remain and the same-session retry fails because the stage already exists. Users must not manually delete private evidence to recover.

## New reviewed helper API
src/wii_ai_golf/audit/private_capture_staging.py exports staged_native_bank_phase(session: pathlib.Path, phase: str). The context manager yields two exclusive paths (mem1.raw, mem2.raw). Only the existing S002 reader/keeper should write and validate those banks. The helper never touches Dolphin, Wii Remote, ROM, savestates, GUI, network, trained model or GitHub observations.

- Session must be an existing, non-symlinked ignored Wii-AI-Golf-Data/captures/SHOT-*-PRIVATE directory; phase PRE/POST/RESULT.
- Create a new unpredictable STAGING-PHASE-nonce directory; never reuse old partial files.
- On reader/keeper exception (including interruption), rename to FAILED-PHASE-nonce and rethrow; do not label the phase successful.
- Only once the keeper has returned normally, delete the two files created in this new stage. Preserve unexpected contents as FAILED rather than discard them.
- Leave older STAGING/FAILED directories untouched. No automatic multi-process lock; caller still needs the canonical single-live-session guard.
- A successful staging cleanup does NOT prove Dolphin was paused, an atomic guest-frame pair, visible contact, ball XYZ/velocity, a verified score, or permission to train/publish.

## Proposed owner-only integration (not wired in this PR)
Inside the existing #201 save_pair(), replace fixed tmp-directory allocation with:

    with staged_native_bank_phase(session, phase) as (mem1, mem2):
        read_bank(reader, 0x80000000, 24 * 1024**2, mem1)
        read_bank(reader, 0x90000000, 64 * 1024**2, mem2)
        # Keep the existing header and source/phase checks.
        result = keeper.preserve(private_root=session,
            mem1_source=mem1, mem2_source=mem2, checkpoint=phase,
            paused_confirmed=True, ...existing flags...)

Do not change the historical V1 45 observed-frame A lead or the 89-sample swing. Preserve the existing keeper's phase/hash/shot attestations. S002 and S000 owners must approve any integration into their capture contract.

## Offline PowerShell test

    cd "D:\Projects\Wii Golf AI\Wii-AI-Golf"
    py -m unittest discover -s tests -p "test_s002_private_capture_staging.py" -v

Local synthetic tests: 10/10 passed in an isolated Linux/Python environment. Exact-branch GitHub Windows/Linux CI and full-suite checks are tracked on the PR. No live Felk Dolphin, actual Wii RAM, pause freeze or hit trial performed.

RAW-PRIVATE: FAILED/STAGING folders, original MEM1/MEM2, source addresses and local manifests never go to GitHub. This PR contains only source, fake-byte tests and documentation.

Next: S002 #201 owner may adopt after reviewing this API; S001 #206 handles source-pinned V1 watched input; S000 owns the final PowerShell-only operator route. This helper alone does not repair an existing installed capture command.
