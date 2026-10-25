# Script-only research workflow

Use Git Bash on Windows or a POSIX shell. PowerShell users can run `py scripts/golf.py` directly. All commands share the same Python package, typed registry (`research/experiments.json`), local evidence storage and canonical Dolphin startup.

| Need | Command |
|---|---|
| Safely update merged tests/code | `bash scripts/golf.sh sync` |
| Find experiment IDs | `bash scripts/golf.sh list` |
| Inspect a run before execution | `bash scripts/golf.sh plan core.tests` |
| Run offline tests | `bash scripts/golf.sh run core.tests` |
| One approved game trial | `bash scripts/golf.sh run integration.swing --live` |
| Latest recorded executions | `bash scripts/golf.sh history` |
| Sanitized local human observations | `bash scripts/golf.sh reports` |
| Source-local setup diagnosis | `bash scripts/golf.sh doctor` |

The previous Tkinter GUI is no longer a supported entry point. Shell prompts are the intended interaction; previous GUI-only modal prompts are not required. You can set `WII_GOLF_DIALOGS=1` only if you intentionally want the optional legacy popup input, but no shell commands enable it.

## GitHub data flow

1. Research agents own branches `agent/<role>/<topic>`, commit tested source and `tests/test_*.py`, and open PRs to `main`.
2. Merge coordinator reviews the changes, resolves conflicts and merges passing/reviewed work by default.
3. Operator runs `bash scripts/golf.sh sync` on a clean local `main`; this uses the repo's trusted-remote / fast-forward-only guard and refuses dirty working trees or concurrent Lab jobs.
4. Operator runs `list` to discover newly merged tests and `plan` before `run`. Sync **never executes new code**.
5. Experiment outputs and raw captures remain under `Wii-AI-Golf-Data` locally. PRs may include independently sanitized research summaries but **never** raw RAM, ROMs, savestates, personal paths, credentials or local logs.

Do not use `git add -A && git push` on the data directory. Auto-uploading *all* local run files is unsafe; GitHub agent code/tests are uploaded through reviewed PRs, and a future data publisher must implement an explicit schema allowlist and provenance check before any unattended upload.

## Operational requirements

- **LIVE:** `lab run ... --live` triggers one canonical full launch and explicit operator approval; failed RPC dispatch is not a golf score.
- **OFFLINE:** tests and synthetic models must never start Dolphin.
- **MERGE:** the original S001/S002/S003/S004/S005 components remain in this same repository; don't fork separate UI repositories or per-agent runners.
- **PLANNED:** studies not yet registered or calibrated remain planned and cannot run.
- **NO BACKGROUND MONITOR:** the shell does not continuously poll GitHub. Re-run `sync` when you want new merged work, or arrange an external scheduler explicitly.
