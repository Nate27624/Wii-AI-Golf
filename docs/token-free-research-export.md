# Token-free research sharing from the canonical CLI

## Recommended: one command, no manual JSON handoff

From the **clean main checkout** (not a detached audit/worktree branch):

```powershell
py scripts/golf.py research test
```

This wraps the pre-existing `scripts/research_cli.py test` pathway: trusted
main sync, offline regression tests, strict allowlisted test result, and Git
push to `research/observations`. It uses Git's **existing configured
authentication** (Git Credential Manager or SSH); no new personal access
token is necessary if Git push already works. If the remote is not yet
authenticated, Git may prompt or fail visibly. This is not a background
service, and it never launches Dolphin.

For offline tests **without any publication**:

```powershell
py scripts/golf.py research test --local-only
```

To see the proposed 10-shot power study without launching Dolphin:
`py scripts/golf.py research study`.

**Success:** the existing research CLI prints that it published a sanitized
test record to `research/observations`. A passing test is **not** a golf
shot, a ball contact, or a verified score. S002's separate capture pathway
is responsible for actual game observation evidence.

## Optional: local execution-status backup

`lab export` does **not** send anything to other agents. It's an optional
offline-only artifact for troubleshooting/review. If you do not need a local
backup, skip these commands entirely.

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

**Manual handoff (optional):** If you explicitly need to share this Lab backup, attach the exported file for independent schema review and separate publication. Otherwise, use the recommended `research test` command. The backup exporter itself never uploads and cannot borrow ChatGPT's connected GitHub credentials.

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
