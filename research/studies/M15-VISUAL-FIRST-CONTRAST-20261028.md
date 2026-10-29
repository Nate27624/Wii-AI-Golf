# M1.5 — human-visible action/outcome contrast (review only)

**NO LIVE GO until S001/S002/S000 review, CI, Clean Dolphin provenance, and merged main.**

## Design and maximum budget

Seven historical V1 human-contact-positive shots showed only the game's
fixed 100-ft off-green penalty. Those are not measured physical miss distances.

- B1: A lead 45 observed bridge frames, speed 1.0, backswing 1.0.
- B2: exact baseline replay under independently fresh, matched setup.
- X1: only backswing travel scaled 1.2 (15 backward requested samples
  0.25 to 0.30m); speed, forward phase, trace length 89, A lead unchanged.
- Maximum 3 shots, each individually consented. **Only B1 first** to prove
  runtime startup and screen/result observability. Stop if no visible
  terminal screen, no contact, mismatched setup or launcher error.
- Do NOT use the distinct 10-trial S003 POWER_MAP study ID/trial-index.
- Predeclare outcome before shots: HUMAN contact, HUMAN result class and
  displayed number/unit, observed terminal before transition yes/no/unknown,
  and optional coarse visual power. The 100-ft miss is a censored penalty,
  NEVER physical shot distance. No training, verified score, verified XYZ
  or physics-frame claim.

## Operator-owned setup comparability

For every shot independently check canonical single fresh boot and registered
green-pre-start, exact approved Clean EXE + User, game US Rev1/mode4,
scene/hole/course/tee/pin, wind if known, selected player and club, camera,
aim and initial club pose. Record unknown confounds as unknown rather than
asserting matching. Trace equality is necessary but not sufficient.

Re-use S001 existing canonical launcher. Prior PR #195 already proposes the
Clean EXE/User/config/catalog pass-through; **review/adopt it instead of
building a competing launcher**. Running research_cli v1 from an unmerged
review worktree is disallowed by the trusted-main sync gate.

## Result-first protocol and privacy

The opt-in --visual-first action asks ONE terminal-screen note immediately
after the 89-frame swing trace completes, without post/settled memory RPC
sampling. Enter G:15.2ft (human on-green result), M:100ft (human off-green
penalty), G or M without a legible number, U for unknown, T if the screen
already transitioned, or q to abort labeling. This is not automatic visual
recognition. Human contact and optional coarse power are asked afterward.

Child writes a local private categorical summary under ignored Data/captures,
with an exclusive run-token path. Parent matches exact run token, bridge
trace settings and 89/89 completion, A45 observed bridge ticks, strict human
types and censored result class; no mtime-only guessed source. If not joined,
cancelled, unapproved or failed, save local status but NEVER publish an
eligible trial to research/observations. No raw RAM is generated in
visual-first mode; screenshot/photo is optional private-only, never uploaded.
The published result, if owner-approved, remains HUMAN-UNVERIFIED.

## GO gates and halt

1. S001: exact Clean startup/Qt state, original bridge revision, no duplicate
   process, canonical menu and ready-state checks. Dispatch ACK is not hit.
2. S002: result-first screen note truly before transition or T/UNKNOWN;
   no late-settled RAM scoring and no 100-ft true-distance interpretation.
3. S000: unique run-token/source/trace join, failed/cancelled suppression,
   strictly categorical public allowlist and exact negative tests.
4. Focused + full Windows/Linux synthetic tests and owner review. Merge to
   clean main before the operator uses the normal CLI.
5. Request just B1 with --no-upload initially; inspect human outcome
   quality and setup conditions before considering B2 then X1.

If all three produce the same off-green penalty without a distinct visible
landing/region or meter, conclude **uninformative / saturated**, STOP.
Do not fit, optimize or claim physical null effects from three observations.
