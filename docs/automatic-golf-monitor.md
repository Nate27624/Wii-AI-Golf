# Automatic, read-only Hitting the Green monitor (S002)

**Purpose:** remove per-shot Enter prompts. Automatically sample *currently decoded* game scene positions from Felk Dolphin, log **all** snapshots locally, detect field changes, and publish a small shareable numerical report after collection. This does **not** yet automatically detect ball strikes, ball trajectories, shot number 1–10, or the final displayed score; these variables have not been mapped.

## Run (new collector branch, canonical code repo)

Use `D:\Projects\Wii Golf AI\Wii-AI-Golf` for the code and the integrator's single savestate/scenario catalogs. The raw data folder is its sibling `Wii-AI-Golf-Data\captures`. If the new PR is not merged, use a clean dedicated Git worktree on the PR branch to run the script.

```powershell
cd 'D:\Projects\Wii Golf AI\Wii-AI-Golf'
py scripts/monitor_hitting_green.py --interval 1 --minutes 15
```

Prepare the Wii Sports Hitting the Green screen. Keep Dolphin unpaused and with exactly one responsive Felk bridge at port 55355. Then **play the game normally**, swinging and advancing through shots manually. No Enter keys are needed after starting. The script detects changes in current training mode, raw current-hole field, and pin/start/cup candidate translations. It reports changes but DOES NOT label changes as shot completions. On timeout, or Ctrl+C, it saves a complete local JSONL history and a compact JSON summary, and attempts an authenticated Git push of only the sanitized numerical summary to a unique `data/hitting-green-<runid>` branch in `Nate27624/Wii-AI-Golf`. If `gh` is installed, it tries posting that link to Issue #3. `--no-upload` disables all external publishing.

### Small live test without GitHub uploads

```powershell
py scripts/monitor_hitting_green.py --interval 1 --samples 5 --no-upload
```

### What's automatically observed

- RSPE01 disc rev 1 game ID, field `game_mode_raw` from `RPGolConfig` and raw current-hole field; cannot assume the raw hole field counts training shots.
- Per-poll time and multi-frame RPC interval, Wii Remote button/acceleration/angular velocity state.
- Pin/cup/start candidate world translation and scale vector, plus derived planar/distance geometry in **unverified game coordinate units**.
- Detected significant pin/cup/start changes (tolerance 0.05 game units), changes to golf mode or raw current-hole field.
- Periodic 10-second numerical summaries for a GitHub report; every sample locally as JSONL for later debugging.

### What's **NOT** automatic yet

- Actual moving **ball XYZ** and its frame-by-frame trajectory (no verified object address), swing-start/strike event, carry, final ball-to-cup distance, landing outcome, score and displayed units.
- The monitor's current RPC approach spans tens of emulator frames for each snapshot and thus can miss a complete fast ball flight. If high-rate trajectory matters, the integrator should add a **batch memory read on one emulation frame**, after identifying the ball struct.
- There is no remote access from ChatGPT to your Windows Dolphin socket: this local process must run on the machine playing the game, then GitHub shares numerical results so ChatGPT can review them.

### Scientific and privacy controls

Only version-gated **read-only** calls are made; no memory writes, save loads or Wii Remote injection. Every full sample is saved **locally** in `Wii-AI-Golf-Data\captures\hitting-green-monitor-RUNID.jsonl`. GitHub publication uses a strict whitelist inherited from the existing S002 `golf_collection.summarize`; it doesn't upload ROM/savestates/screenshots/memory hex/local filesystem paths. The numerical observations ARE publicly visible if the repo is public. The local series may include personal gameplay timing and controller metadata—keep it private unless knowingly sharing.

### Validation

Unit tests use synthetic read-only samples only. Results that look like game events should be independently checked against a screen recording or repeated manual observations; no score/ball detection is claimed. If RPC fails five consecutive attempts the monitor stops, saves the local series and prints an error; it does not delete evidence.