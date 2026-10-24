# Contributing

Read [AGENTS.md](AGENTS.md) before working. Claim a GitHub issue; use a separate agent-role branch and pull request; describe what was *measured* separately from what is *hypothesized*. Avoid conflicting edits.

Local checks:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m wii_ai_golf.demo
```

PR checklist:
- [ ] Linked claimed issue and listed touched files
- [ ] Tests added/executed with commands and results
- [ ] Dataset splits, attempt budget, seed and failure counts explicit
- [ ] Real vs synthetic source labeled clearly
- [ ] Research queue/ledger updated if needed
- [ ] No ROMs, savestates, tokens, personal data or giant binary checkpoints
