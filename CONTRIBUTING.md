# Contributing to Wii AI Golf

This is **one project with multiple owned modules**, not independent competing golf launchers. Read [AGENTS.md](AGENTS.md), [research/README.md](research/README.md) and [docs/cli.md](docs/cli.md) before adding new scripts.

## Standard development commands

~~~powershell
py scripts/golf.py --help
py scripts/golf.py test
py scripts/golf.py test --pattern "test_unified_cli.py"
py scripts/golf.py demo
~~~

The source-local `scripts/golf.py` intentionally imports the **current checkout** without requiring `pip install -e .`. Existing specialized scripts remain compatible and are not to be deleted merely for style.

## Adding functionality

1. **Claim a scope** on its GitHub issue before editing shared code. Work in an isolated `agent/<role>/<slug>` branch; do not overwrite another agent's files or rebase their branch without coordination.
2. **Put domain logic in its owned module** (`integration/`, measurement/audit, modeling, learning). Reuse the existing Felk RPC and canonical menu sequence; never introduce competing hardcoded A/A+B/A startup timings.
3. **Expose a CLI adapter** through `src/wii_ai_golf/cli.py` only if the tool is useful to operators. Delegate to a vetted existing entrypoint or a narrow module API, rather than copying behavior. Keep safe read-only operations offline and clearly label live mutations.
4. **Add tests** in `tests/`: CLI help and source-local imports under `python -I` / fake stale install; dry-run must not launch; live commands must reach the canonical launcher once; child cannot secretly reset or double-launch; pass flags/exit status faithfully.
5. **Record evidence**: study ID, source (synthetic/human/live game/verified measurement), exact action, attempt budget, failures and saved artifact provenance. A bridge ACK or gauge screenshot isn't a score.
6. **Review and merge a PR** with exact commands/tests actually run. Do not claim a Windows Dolphin test ran merely because Python mocks pass on another machine.

## Documentation conventions

- `README.md` is the high-level single project overview; `docs/cli.md` is the **canonical operator command reference**.
- `docs/architecture.md` defines layers; `docs/milestones.md` defines current acceptance gates.
- `research/README.md` is the shared study lifecycle; `research/queue.jsonl` is a proposed-study manifest, not a live execution queue.
- `research/ledger.md` is append-only history; do not erase old failures to make present status look cleaner.
- Detailed agent-specific research notes stay under their owned folder, with links to shared canonical docs rather than standalone conflicting startup scripts.
- Keep personal Dolphin game paths, savestate catalogs, traces, ROMs, screenshots and binaries out of Git (local `Wii-AI-Golf-Data`).

## PR checklist

- [ ] Claimed paths and nonoverlapping agent ownership
- [ ] User-facing command is consistent with `golf` or documented advanced-only
- [ ] Focused/full tests listed with **actual** results and limitations
- [ ] Canonical fresh boot/intro and source-local import regressions covered
- [ ] Distinction between synthetic, user-observed, RPC-ack and validated score
- [ ] Study hypothesis, attempts/failures, holdout procedure and versioned evidence
- [ ] No secret, copyrighted game asset, personal path or accidental savestate write
