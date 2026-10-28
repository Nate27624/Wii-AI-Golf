# Agent codebase tour — source-backed, current-main entrypoints

**Purpose:** help a brand-new S000–S005 context understand **where existing behavior lives**, without making another launcher, controller bridge, data publisher, game-state reader, or user-facing UI. This is a navigation guide, **not** an approved LIVE experiment runbook. Verified against current `main` source on 2026-10-28; its API anchor checks run in CI. Always re-check the actual branch/HEAD and owning PR because independent agents are changing code simultaneously.

**Read first:** [AGENTS.md](../AGENTS.md), [operator PowerShell rules](https://github.com/Nate27624/Wii-AI-Golf/blob/agent/coordinator/powershell-only-repo-contract-20261027/docs/operator-powershell-contract.md), [agent context/re-baseline protocol](https://github.com/Nate27624/Wii-AI-Golf/blob/agent/coordinator/powershell-only-repo-contract-20261027/docs/agent-session-protocol.md), [repository/owner map](https://github.com/Nate27624/Wii-AI-Golf/blob/agent/coordinator/powershell-only-repo-contract-20261027/docs/repository-map.md), [research coordination](../research/coordination.md), and relevant live issues [S001 #2](https://github.com/Nate27624/Wii-AI-Golf/issues/2), [S002 #3](https://github.com/Nate27624/Wii-AI-Golf/issues/3), [cross-agent P0 #121](https://github.com/Nate27624/Wii-AI-Golf/issues/121). **Important:** Policy links above intentionally target the PR #196 branch because these documents are not on main yet; S000 should replace them with relative links after its policy PR merges. At creation, the improved rules/docs in [draft #196](https://github.com/Nate27624/Wii-AI-Golf/pull/196) are **not merged into main**. Current-main README/AGENTS still contain conflicting retired GUI/Git Bash instructions; **the user's direct instruction prevails: CLI-only, give one complete PowerShell code block, no manual Dolphin.**

## How to understand the repository in ten minutes

| Your question | Read this **existing** implementation first | Owned by | Important boundary |
| --- | --- | --- | --- |
| Which operator CLI command exists? | [scripts/golf.py](../scripts/golf.py) → [wii_ai_golf.cli](../src/wii_ai_golf/cli.py), `build_parser()` and `execute()` | S000 shared CLI | Wrapper delegates; do not reimplement Dolphin |
| How are research `test` / `v1` results published? | [scripts/research_cli.py](../scripts/research_cli.py), `main()` and `publish_summary()` | S000 publication | Only `test` / `v1` allowlisted, branch `research/observations` |
| How does a LIVE experiment get its fresh boot? | [scripts/run_golf_experiment.py](../scripts/run_golf_experiment.py), `resolve_target()`, `build_commands()`, `main()` | S001 startup | Required profile `green-pre-start`, one launch |
| Who selects Dolphin, User, bridge and game? | [scripts/launch_golf.py](../scripts/launch_golf.py), `resolve_game()`, `make_start_command()`, `main()` | S001 launcher | Existing local config and one Dolphin process |
| What dispatches the menu intro? | [scripts/launch_hitting_green.py](../scripts/launch_hitting_green.py), `main()`; [menu_sequence.py](../src/wii_ai_golf/menu_sequence.py), `planned_menu_phases()` and `execute_menu_phases()` | S001 menu | Source-frozen A → wait → A+B → release → final A |
| Is a named savestate's file actually present? | [integration/savestates.py](../src/wii_ai_golf/integration/savestates.py), `StateCatalog.get()`, `StateManager.request_load()` | S001 state | Catalog has **name and slot**, not physical save bytes |
| Who implements controller swing dispatch? | [scripts/probe_swing.py](../scripts/probe_swing.py), `build_probe()`; [integration/atomic_client.py](../src/wii_ai_golf/integration/atomic_client.py), `AtomicTraceClient.run()`; [integration/swing_patch.py](../src/wii_ai_golf/integration/swing_patch.py), `extend_atomic_bridge_with_swing()` | S001 input | Frozen trace and bridge protocol; not a new physics truth |
| Who owns before/after shot samples and human labeling? | [scripts/collect_outcome_transition.py](../scripts/collect_outcome_transition.py), `run_session()`, `main()` | S002 observations | RAW-PRIVATE JSONL local; human confirmation ≠ measured physics |
| Where are typed Lab helpers and sync? | [lab/core.py](../src/wii_ai_golf/lab/core.py); [lab/github_sync.py](../src/wii_ai_golf/lab/github_sync.py), `sync_merged_main()` | S000 underlying helpers | Retired GUI is not the operator's workflow |
| Where do negative findings and ownership go? | [research/ledger.md](../research/ledger.md), [research/coordination.md](../research/coordination.md), issue/PR FINDING and HANDOFF comments | Domain owner + S000 | GitHub issue comments are the living coordination layer |

**Don't use this table as evidence that a script is merged on main** without checking it. In particular, [#195](https://github.com/Nate27624/Wii-AI-Golf/pull/195) proposes the missing clean-Dolphin-path guard in `research_cli.py` but is **draft** as of this map; [#198](https://github.com/Nate27624/Wii-AI-Golf/pull/198) investigates the historic **45 observed-frame A-lead** contact reproduction and is also draft. Do not silently apply their behavior to current main.

## Canonical call graphs — reuse the links, not parallel code

**Broad CLI (routing only):**

```text
operator PowerShell -> scripts/golf.py
  -> src/wii_ai_golf/cli.py : main() -> execute()
     -> read-only doctor/state/research helpers OR
     -> scripts/launch_golf.py OR scripts/run_golf_experiment.py
        (which delegates; it does not generate a second emulator stack)
```

**Research result + live shot path (the code currently on main; NOT an instruction to run it now):**

```text
operator PowerShell -> scripts/research_cli.py : main()
  -> lab.github_sync.sync_merged_main(ROOT) [safe main sync gate]
  -> if test: python unittest discover
  -> if v1: verify isolated bridge revision, then
       scripts/run_golf_experiment.py : main()
         -> build_commands() -> scripts/launch_golf.py
           -> scripts/launch_hitting_green.py
             -> integration.savestates.StateCatalog.get()
             -> integration.savestates.StateManager.request_load()
             -> menu_sequence.planned_menu_phases()
             -> menu_sequence.execute_menu_phases()
         -> scripts/collect_outcome_transition.py : main()
           -> run_session() -> source-gated PRIVATE snapshots + human labels
  -> local sanitized result in ignored Wii-AI-Golf-Data/research-cli
  -> unless --no-upload: publish_summary() -> GitHub research/observations
```

The outer coordinator may invoke the inner action with `--attach-running` **internally** after a successful fresh boot. That is **not** a license to tell the operator to launch a separate bridge and manually attach. No duplicate Dolphin, no unreviewed waveform, no manual savestate.

**Important verified source detail:** `scripts/research_cli.py` on main still constructs its V1 dispatcher with `--bridge`, but not explicit `--dolphin`/`--dolphin-user`/`--config`/`--catalog`; draft #195 addresses that. Do not call the main V1 path "clean-Dolphin enforced" until the exact relevant fix is merged and checked. Similarly `--live` and `--send-live-swing` are distinct opt-in surfaces; success of either is not evidence of actual contact.

## A45 vs 89-sample trace: never change semantics by guessing

The string `45` appears in **different source-owned experiments**:

- **Menu final A:** `menu_sequence.planned_menu_phases(final_a=45)` emits **45 requested per-frame button RPCs** after A+B release. This is not proven wall-clock/emulator-frame duration.
- **Separate A-prime:** `collect_outcome_transition.run_session(a_prime_requests=...)` is **button-only priming before the swing**, and is not the same as initial menu A.
- **V1 observed-frame A-lead:** `collect_outcome_transition.run_session(a_lead_frames=...)` uses an observed-frame A hold before the existing swing; earlier human-observed contact with **45 A-lead** is recorded in [#94](https://github.com/Nate27624/Wii-AI-Golf/issues/94), and the no-hit after `--a-lead-frames 0` is explicitly investigated in draft #198.
- **Neutral/held-A trace samples:** `probe_swing.build_probe()` generates the actual waveform; its setup and follow-through timing are independent. The original 89-sample waveform must remain source-pinned for comparable studies, with exact digest and bridge revision.

**Agent rule:** read the specific target script and previously witnessed trial before specifying any `45` flag. Do not re-create an A-only calibration by selecting a similarly named integer argument. Distinguish per-request dispatch, observed emulator frames, and physics contact.

## Evidence ladder and private-data boundary

```text
synthetic unittest / hosted CI:
  code behavior only, not game result

source address / field write:
  memory candidate, not verified physical ball XYZ

Dolphin/bridge ACK:
  method scheduled or acknowledged, not guest-applied frame

human visually confirmed hit / miss:
  independent operator observation, not verified units or collision tick

same-shot source-gated PRE/POST/SETTLED position + distinct controls:
  stronger association candidate, still not proven independent physics

non-censored, validated real-game outcome:
  possible score/learning label only after separate S000/S002 gate
```

RAW native MEM1/MEM2 banks, per-frame word/pointer records, ROM, savestates, private configs and original trace payloads stay under the ignored sibling `Wii-AI-Golf-Data`. Current-main `research_cli.publish_summary()` uses a **separate Git clone and `research/observations` branch**, pushes only constructed allowlisted summaries, and preserves a local sanitized result when remote publication fails. Never invent an upload mechanism for standalone private analyzers. Any important positive **or negative** result belongs in the owning issue/PR FINDING and reviewed ledger integration.

## How to safely add/change behavior

1. **Read current evidence** from issue #121 and the relevant owner issue/PR first. Identify the exact audited function; do not use a generic memory scan where S002 has already rejected pointer aliases or idle confounds.
2. **Claim files** in the owning issue. For shared CLI, S000 review; for Dolphin/menu/swing, S001; for private memory/outcome, S002. Use a new branch. If another agent owns the file, offer an independent test/guide rather than editing their code.
3. **Make the minimum change** and keep functional boundaries: upstream launch state, submitted trace, memory watch, score, publisher and learning are distinct. Do not turn source candidates into training fields or copy private RAM into fixtures.
4. **Test in layers**: pure synthetic unit tests; relevant Windows+Ubuntu regression; full Windows suite as merge gate; separate exact-source owner review; only then a separately approved ONE-shot live test if genuinely necessary. Known Windows fixture failures on main are being handled by [#170](https://github.com/Nate27624/Wii-AI-Golf/pull/170).
5. **Provide an agent Handoff** with actual branch/commit, source identity, tests, what remains unverified and one next owner. The user's operator action, when needed, is **one complete, self-locating PowerShell block**; never an instruction to open the GUI or manually operate Dolphin.

## Read-only PowerShell entrypoint for understanding source (no Dolphin)

The following is **offline and does not publish any user data**; it's only for an operator who explicitly requests a local code diagnostic. Otherwise, agent fetches sources via GitHub and **no operator action is required**.

```powershell
$ErrorActionPreference = 'Stop'
$repo = 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
Set-Location -LiteralPath $repo
py scripts/golf.py doctor
if ($LASTEXITCODE -ne 0) { throw 'Doctor failed; no game started' }
```

**This guide is itself an additional document, not a replacement for README/AGENTS.** S000's open #196 owns those files. Any new onboarding link should be added there by that owner after review; do not edit another agent's shared policy branch.
