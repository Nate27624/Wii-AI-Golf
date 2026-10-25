# Automatic GitHub publication of safe experiment status

This first phase uploads **sanitized execution metadata only**. It does not publish golf scores, human observations, minimap bytes, memory pointers, file paths, commands, subprocess logs or raw captures. The authoritative local files remain under the sibling `Wii-AI-Golf-Data` directory.

## Windows / Git Bash setup

Create a GitHub token with **Contents: Read and write** for `Nate27624/Wii-AI-Golf`. Keep it outside the repository. In a Git Bash shell:

```bash
export WII_GOLF_GITHUB_TOKEN='your-token-here'
export WII_GOLF_AUTO_PUBLISH=1
bash scripts/golf.sh run core.tests
```

The token is used for a direct GitHub REST upload. Each completed Lab execution creates one `research/auto-results/<run_id>.json` file on the **`research-results` branch**, never on `main`. The branch is created if missing using the existing `main` commit as the starting point. It may require credentials with permission to create branches. Agents can read the branch on GitHub and correlate run identifiers. No GitHub Actions or background daemon is required.

**Important:** With these environment variables absent, experiments behave as before; publication is not configured. A failed upload does not change the experiment exit status and is recorded locally in `publish_status`. Rerun your experiment to retry. Use `unset WII_GOLF_GITHUB_TOKEN WII_GOLF_AUTO_PUBLISH` to disable.

### Integrity and privacy

Only an allowlist of `schema_version`, `run_id`, `experiment_id`, `mode`, `execution_status`, `exit_code`, and an explicit `PROCESS_STATUS_ONLY_NOT_A_GOLF_SCORE` claim leaves the machine. Other fields are ignored, even if the local record includes raw RAM or secret-bearing file paths. The publisher validates identifier characters and supports only finalized statuses. It never force pushes, deletes files, or modifies the source branch `main`.

Publishing validated *scientific observations* will require a separate, reviewed field schema and explicit distinction between human labels and verified game scores. Do not send raw S002 capture or broad local JSON as a shortcut.

## Tests

```bash
python -m unittest discover -s tests -p 'test_lab_publish.py' -v
python -m unittest discover -s tests -v
```
