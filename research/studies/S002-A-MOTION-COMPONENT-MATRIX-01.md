# S002 — Exact-run A/motion component retrospective

**Scope:** Offline only. No emulator, bridge, controller input, RAM writes, raw upload or training.

The operator's original `manual-a-miss-v1` stream had 46 SHA-verified packets and an `ABORTED` manifest. There are five complete 8-packet, human-labeled no-contact controls (`I0` idle, `AH` A held, `AR` A released, `M0` motion without A, `I1` idle after motion), followed by six `M1` packets associated with **operator-observed ball HIT**. The contact instant within M1 is unknown: **M1 is quarantined and excluded from control calculations**.

## Reproducible exact-run read

From the checked-out repository, read the existing *sibling* private capture folder:

```powershell
py -3 -I scripts/audit_p0_a_motion_components_private.py --captures-root "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures" --expected-sha256 "<exact original stream SHA-256>"
```

The SHA must be supplied explicitly; selection matches **one and only one** stream, never the latest timestamp or a guessed run. Also gates the adjacent original `manifest-PRIVATE.json` (ABORTED, protocol, 46 samples, full stream digest, training false), timestamps, source owner digest, ordered phases, sample indices and typed BE32 words. It refuses invalid or ambiguous input, does not create/modify files, and prints only component-level equality, transitions, and relative candidate floats.

## Falsifiable comparisons

- **Selected player record** `+0x30/+0x34/+0x38`: prior report showed one 32-bit component different only during M0 and persisted into I1. Test exact onset and phase-stability; this is **not** selected ball-object position `+0x30`, A latch or swing power.
- **Record** `+0x90`: one component has 7/7 transitions during each phase, even I0 idle; not a unique button signal. Check drift and phase-boundary changes separately.
- **Record** `+0x94/+0x98`: check whether each changes between I0/AH/AR/M0/I1 while `+0x3C` aim is equal. Earlier cosine relation from a **different directional capture** cannot be assumed universal without these controls.
- **M1**: known human HIT but **not** a clean no-contact or machine-timestamped flight sample. No posthoc control labels or trajectory.

No independent game-owned A pressed bit, rendered projectile, guest physics tick, accepted stroke, power, or uncensored score has been verified. Do not train from this stream.

## Follow-up, separate S001/S003 scopes

S001 owns the corrected live capture with independently authorized A-only hold/release and motion-only trials; contact-possible swings require a separate human confirmation and shot-epoch seal. S003 ranks power-specific discriminators separately. A proposed blind operator A-button monitor must first validate an independent input-state memory witness or a high-accuracy, held-out A-only vs idle vs motion-only discriminator; until then its output must permit `UNKNOWN` rather than confidently guessing `PRESSED`/`RELEASED`.
