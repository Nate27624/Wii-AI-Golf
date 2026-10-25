# Wii AI Golf — One Script, One Repository

This repository is the maintained source for all S001–S005 Wii Sports Golf research. **The desktop GUI was retired**. Agents develop, review and merge Python changes to GitHub; the operator runs commands locally on the Windows machine with Dolphin, and a small sanitized run record is automatically pushed back to GitHub for agent review.

## Windows operator commands

From your existing checkout:

```powershell
cd "D:\Projects\Wii Golf AI\Wii-AI-Golf"

# Safe fast-forward from approved GitHub origin/main, without launching Dolphin.
py scripts/research_cli.py sync

# Automatically sync and run unit tests; publish a compact PASS/FAIL record.
py scripts/research_cli.py test --pattern "test_research_cli.py"

# Sync, launch fresh Dolphin + existing green-pre-start checkpoint + A/A+B/A,
# use the isolated historical V1 bridge, record human pose/contact, upload
# ONLY approved sanitized labels and controller fingerprints.
# Close Dolphin first; one human-authorized shot only.
py scripts/research_cli.py v1 --live --a-lead 0
```

Use `--a-lead 45` only for an explicitly controlled alternative timing test. **Do not change swing power/velocity and A timing in the same study.** Each live command needs `--live` and human interaction; nothing launches Dolphin automatically from an agent push.

By default every `test` or `v1 --live` command does a verified clean-main fast-forward *before execution*, writes a local sanitized JSON record under sibling `Wii-AI-Golf-Data/research-cli/`, and attempts a Git push to the dedicated [research/observations branch](https://github.com/Nate27624/Wii-AI-Golf/tree/research/observations). The agent reads those summaries directly from GitHub to develop follow-on studies. Use `--no-upload` to store only locally.

The source updater refuses dirty local edits, unapproved remotes, detached/non-main branches and divergent histories. It only fast-forwards; it never stash/resets/forces. A publication error does NOT delete local results. Pushing requires normal Git authentication in your existing checkout. **Private RAW RAM JSONL, ROMs, Dolphin savestates, the generated bridge, and arbitrary local files are never uploaded.** Only allowlisted human annotations, exact trace hashes and experiment exit statuses are published; an exit code or trace ACK is not proof of ball contact or score.

## Research pipeline

1. **S001 integration:** Felk Dolphin, Wii Remote and known first-shot launcher (`scripts/run_golf_experiment.py`).
2. **S002 evidence:** read-only snapshots, human labels and independent decoder validation (`scripts/collect_outcome_transition.py`).
3. **S003 modeling:** calibrated response surface from real human-verified shots.
4. **S004 learning:** bounded optimization after verified score data; synthetic demonstrations are labeled as synthetic.
5. **S005 generalization:** separate holdout scenarios and matched evaluation budgets.

Specialized diagnostic scripts and existing Python modules remain for agents and developers; they share the **same repository and underlying codebase**. The retired UI's `lab.core` helpers remain only for trusted Git sync/test metadata compatibility; no Tkinter app is part of the operator workflow.

## Trust and experiment rules

- Never treat a completed controller trace as a confirmed strike or game score.
- Do not overwrite existing savestates or launch Dolphin twice.
- Never commit ROMs, private RAM, personal filesystem paths or generated bridge scripts.
- The initial club-pose hypothesis is unverified: a human-confirmed V1 strike followed by a miss with the same intended trace suggests startup/pose repeatability needs controlled study, **not blindly increasing power**.
- Before comparing trials, preserve bridge source SHA, waveform fingerprint, A lead, initial pose label and any game-displayed distance units.

See `docs/cli-only-workflow.md` for publication safety, errors and other diagnostic commands. Historical Lab GUI documentation is archival and no longer applicable.
