# Token-free evidence handoff from the canonical CLI

**Status:** offline execution-status export only. No Dolphin and no GitHub token.
This does not publish to GitHub or verify any golf score.

## Operator workflow (Windows)

From the normal Wii-AI-Golf checkout:

```powershell
git pull --ff-only origin main
py scripts/golf.py lab run core.tests
py scripts/golf.py lab export
py scripts/golf.py lab verify-export
```

Or using the established Git Bash wrapper:

```bash
bash scripts/golf.sh export
bash scripts/golf.sh verify-export
```

- `lab export` selects up to 20 most recent **finalized, valid** local run records.
- It rebuilds each record using the existing strict `lab.publish.public_record` allowlist.
- It writes a stable `status-bundle-<sha256>.json` under the **private sibling** directory `Wii-AI-Golf-Data/lab/exports/`, never into the Git checkout.
- It re-reads and validates the bundle after writing and refuses conflicting content at the same output filename.
- `lab verify-export` checks the latest export's schema, record count, exact safe fields and SHA-256. Or pass an explicit JSON path to check a specific bundle.
- `lab export --json` prints only the same sanitized JSON to standard output. `--limit 1..100` changes the maximum number of run statuses.

**Handoff to agents:** Attach the exported `.json` file to the ChatGPT conversation and explicitly request publishing it to the `research-results` branch. The connected GitHub integration can handle that separate action after independent validation. **The CLI cannot use ChatGPT's GitHub login**, and the bundle is not automatically uploaded. If the external integration is unavailable, the bundle stays local.

**IMPORTANT:** Raw `lab history --json` and `lab reports --json` can include private filesystem locations and are **not** suitable publication artifacts. Share only the validated `lab export` bundle.

## Security and scientific limitations

Export allowlist: `schema_version`, `run_id`, `experiment_id`, `mode`,
`execution_status`, `exit_code`, and the fixed claim
`PROCESS_STATUS_ONLY_NOT_A_GOLF_SCORE`. Everything else is dropped; no
logs, usernames, paths, memory bytes, ROM names, bridge files, tokens,
savestates, trace payloads, or arbitrary narrative fields. Invalid/incomplete
runs are skipped, not converted into successes. Offline export does not access
the network, launch Dolphin or invoke the previously implemented optional
token-based auto-publisher.

The bundle includes only execution statuses. `finished` and exit code 0
mean *process success*, **not** an observed golf hit or verified score.
Observations must remain separate under the S002-reviewed schema, with unique
per-trial identifiers, provenance, and verified/unverified source labels.
See `docs/evidence-integration-contract.md` and pending PR #91.

## Implementation tests

```powershell
py -m unittest discover -s tests -p "test_lab_export.py" -v
py -m unittest discover -s tests -v
```

No new package, token, credential setup or GitHub Actions needed.
