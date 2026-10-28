# Script-first Wii Sports Golf — GitHub results handoff

> **ACTIVE operator contract (2026-10-27):** give only complete self-locating Windows PowerShell blocks; never tell the operator to launch Dolphin manually, use a GUI/Git Bash, or replace source-validated A-button/swing methods with newly invented variants. Read [PowerShell-only operator contract](operator-powershell-contract.md) and [repository map](repository-map.md) first. Examples below are historical interface descriptions; confirm actual merged scripts and any required safe-clean Dolphin review before recommending LIVE commands. A draft PR is not deployed to main.

The retired Research Lab GUI is no longer supported. **Only one maintained source repository**: Nate27624/Wii-AI-Golf. Multiple agents submit normal PRs, coordinate through Issues #2–#6, and may merge reviewed safe changes. The user runs one centralized local script, which pulls merged GitHub code first and publishes sanitized output to a dedicated branch.

## Operator workflow (PowerShell)

```powershell
cd "D:\Projects\Wii Golf AI\Wii-AI-Golf"

py scripts/research_cli.py sync
py scripts/research_cli.py test --pattern test_research_cli.py
py scripts/research_cli.py test --pattern "test_*.py"
py scripts/research_cli.py v1 --live --a-lead 0
```

The V1 command carries out the canonical fresh Dolphin -> named `green-pre-start` savestate restore -> A / A+B / A intro -> existing S002 collector. It requires the separately prepared historical `tools/mcp_bridge_swing_legacy_eval.py`, asks for human initial club pose, prompts once before swing, and preserves human observation of contact versus score. For a different controlled protocol, `--a-lead 45` changes only the stationary A-hold duration before the same trace. No player score is automatically verified.

## How auto-sync works

Each script command runs the existing trusted `lab.github_sync.sync_merged_main` preflight before anything else:
- Only a clean local `main` at the exact approved `origin` (SSH or HTTPS).
- `git fetch origin main`, verified FF ancestry, `git merge --ff-only FETCH_HEAD`.
- No stash, reset, merge conflicts, force-update, or arbitrary PR checkout.
- If blocked, no Dolphin or test job starts. The sync-only command does not publish a result.
- Stale GUI lock files no longer block this script-first workflow. Keep one live CLI session at a time and close Dolphin between experiments.

## Mandatory result-upload coverage for new studies

**Operator rule:** Approved operator study/test runs must automatically upload a **sanitized and explicitly allowlisted GitHub result** in the same PowerShell command, without a separate manual upload. The current scripts/research_cli.py already does this for its reviewed test and v1 modes by default; not every arbitrary scripts/*.py P0 analyzer is integrated. Agents introducing new methods must first add S000/S002-reviewed safe adapters using that existing publisher, with synthetic tests for success, blocked private fields and failed remote; never claim an unmerged adapter works on main. A deliberate --no-upload request or privacy block takes precedence.

Keep native RAM, PRIVATE JSON, arbitrary terminal output and savestates local. A failed push preserves the local sanitized summary and must report **NOT UPLOADED**, not a fabricated URL. Important positive or negative findings require a dated owning issue/PR FINDING comment plus reviewed research/ledger.md entry linked to the uploaded safe run; see [operator contract](operator-powershell-contract.md#automatic-github-publication-and-durable-research-findings-mandatory).

## How GitHub output upload works

The operator grants one automatic publication per run unless `--no-upload`. The script generates a compact allowlisted JSON record in the private sibling `Wii-AI-Golf-Data/research-cli/` and publishes a copy to the isolated `research/observations` branch under `research/observations/<ID>.json`. For publication, it clones only that results branch into a temporary directory, adds the one output file, commits and pushes normally, and cleans up. The operator's checked-out `main` is not modified by results commits.

The public JSON has process exit status and test pattern, or (for live golf) initial pose, human-reported contact/landing distance and units, controller trace hash/A-lead metadata and selected bridge SHA. **Game scores are explicitly marked unverified.** It is not a full capture or a verified game state. RAW-PRIVATE JSONL, RAM candidate dumps, ROMs, savestates and generated bridge source are never copied into the publishing clone.

If the publisher fails (offline/network/auth/concurrent push), the sanitized record remains locally saved. A non-zero exit from the research script means something failed, not a golf score. The script refuses to initialize a missing results branch or overwrite any existing Git history.

## Maintainer contract

- Contribute code and tested experiments to `main` using reviewed branches/PRs.
- Share one central script entrypoint; don't build separate UIs, Dolphin launchers or per-agent workers.
- Use `scripts/research_cli.py` for user-facing tasks, extending with explicitly reviewed subcommands only.
- Keep game execution one-shot and explicitly authorized; automation covers source sync and results upload, **not unattended swings**.
- Any new research result record must be a small, explicitly allowlisted sanitized projection. Never blindly upload private capture JSON, local paths or environment metadata.
- Fix forward using GitHub PRs; avoid long-lived incompatible feature branches.

## Troubleshooting

If Git pull is blocked, inspect `git status --short` and `git branch --show-current`; preserve local edits rather than resetting them. If the results push is blocked, inspect Git credentials/remote auth and confirm the branch exists; the sanitized JSON is saved locally even if publication fails. If a swing process fails, capture the actual terminal exception and return code instead of treating the trial as a score or re-running without investigation.

Historical `docs/research-lab.md` documents the retired GUI and must not be used as the active workflow.
