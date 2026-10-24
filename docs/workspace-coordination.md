# Wii Golf scenario coverage and canonical workspace

**Worker 1 / Issue #2.** Use this alongside [savestate-workflow.md](savestate-workflow.md).

## Single source of truth

- **Source and CLI:** `D:\Projects\Wii Golf AI\Wii-AI-Golf` is the only runtime checkout. GitHub repository: `Nate27624/Wii-AI-Golf`.
- **Evidence/data:** `D:\Projects\Wii Golf AI\Wii-AI-Golf-Data` is a local output folder, not a second code repository. Store captures, plans and results there; never execute a copied `scripts/` directory in this folder.
- **One local checkpoint registry:** `D:\Projects\Wii Golf AI\Wii-AI-Golf\research\savestates.local.json`. Use its existing named slot mappings in every experiment. This registry is machine-local and Git-ignored.
- **One local scenario bank:** `D:\Projects\Wii Golf AI\Wii-AI-Golf\research\scenarios.local.json`; refer to these names in all training and evaluation plans. Keep the *actual* savestate bytes under the same Dolphin user profile; no game image or savestate is committed.
- Other workers may edit separate Git branches/worktrees but must merge code into the same canonical GitHub repository. Shared data contracts and responsibilities are tracked via issue comments, not invisible shared processes.

PowerShell setup (from a fresh terminal):

```powershell
$golf = 'D:\Projects\Wii Golf AI'
$repo = Join-Path $golf 'Wii-AI-Golf'
$data = Join-Path $golf 'Wii-AI-Golf-Data'
$catalog = Join-Path $repo 'research\savestates.local.json'
New-Item -ItemType Directory -Force -Path "$data\captures", "$data\plans", "$data\results" | Out-Null
Set-Location $repo
git pull --ff-only
py scripts/savestate_session.py list
```

When evaluation PR #14 is available, run captures from the canonical repo and pass `--out "$data\captures\green01-before.json"` explicitly; otherwise that capture script uses a relative default output path. Include `--shot-index` and `--savestate-profile` annotation. Never overwrite evidence captures.

## Why we need a bank, not one checkpoint

A 2007 GameFAQs Hitting the Green training guide describes ten repeatable hitting positions but changing pin locations. Treat that as a lead, not proof for the user's game revision: https://gamefaqs.gamespot.com/wii/933010-wii-sports/faqs/45923

Restoring one Dolphin savestate can replay one exact ball/pin/world/RNG state; even thousands of swings from it cannot test generalization to unobserved pin layouts. We do **not** know how to force arbitrary pin layouts, and these tools do **not** manufacture them. Record fresh *observed* variants by playing/restarting the actual game; do not assume all combinations are known or finite.

## Register observed, verified scenarios

Start with the existing, visually verified `green-first-shot` named checkpoint:

```powershell
py scripts/plan_scenarios.py add green-shot01-pinunknown --checkpoint green-first-shot --shot-index 1 --variant pin-unknown --condition pin=unmeasured --visually-verified
```

To capture another position (navigate to shot 2 before swinging, with an unused slot 21):

```powershell
py scripts/savestate_session.py register green-shot02-pin01 --slot 21 --description 'Shot 2, first observed layout'
py scripts/savestate_session.py capture green-shot02-pin01 --overwrite-slot
py scripts/savestate_session.py reset green-shot02-pin01
# After visually verifying the exact shot was restored:
py scripts/plan_scenarios.py add green-shot02-pin01 --checkpoint green-shot02-pin01 --shot-index 2 --variant pin01 --condition pin=unmeasured --visually-verified
```

Repeat for shot indices 1–10 and any *different actually observed* pin variants, each in a distinct named slot. Do not label a checkpoint visually verified just because a bridge RPC acknowledged. Slots are limited (0..99 in Felk Preview4 documentation).

## Predeclared reproducible scheduling

To build a smoke-test plan that rotates one registered variant per shot index per round:

```powershell
py scripts/plan_scenarios.py list
py scripts/plan_scenarios.py plan --rounds 3 --seed 42 --balance shot --out "$data\plans\exploratory-seed42.json"
```

By default only verified scenarios are included. `--balance shot` selects one variant per observed shot index each round, cycling observed pin variants; `--balance scenario` visits every observed checkpoint each round. The plan includes the seed, exact checkpoint slot, group, variant labels, observed shot indices and missing shot indices. Output is exclusive-create (will not replace an existing plan).

After real checkpoints at indices 8, 9 and 10 have been registered, predeclare a held-out evaluation group:

```powershell
py scripts/plan_scenarios.py plan --rounds 10 --seed 42 --balance shot --holdout-shots 8,9,10 --out "$data\plans\train-holdout-seed42.json"
```

All variants of each held-out shot index remain in holdout. Do not train on holdout trials; learning agent freezes models before evaluation. A strict unseen *pin* generalization test will additionally require holding out complete variants within seen shot indices, which is not yet implemented.

To restore an already planned attempt (does not perform a shot):

```powershell
py scripts/plan_scenarios.py load-attempt --plan "$data\plans\train-holdout-seed42.json" --attempt 1
```

**Do not claim success from a load acknowledgement.** Inspect whether Wii Sports visibly restored the intended state. No automatic physics, shot actuation, game randomness generation, score extraction or completed training is delivered by this scheduler.

## Worker boundaries

- Integrator #2: state reset/trigger, reproducible scenario bank and schedules.
- Evaluation #3 (PR #14): authoritative observed scene measurements and eventual audited scoring; captures with explicit absolute `--out` under the data folder.
- Modeling #4: identify genuine condition fields and calibrate controller motion.
- Learning #5 (PR #12): train/evaluate on the predeclared scenario plans; keep synthetic toy evaluations separate from real Wii Sports.
