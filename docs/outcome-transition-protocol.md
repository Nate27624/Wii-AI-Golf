# S002 experimental RAM outcome discovery

Goal: identify actual Wii Sports Hitting the Green landing/score fields using three distinct memory phases and an independently observed result. **No ball XYZ or score decoder is verified yet.** The unchanged known-good forward swing remains owned by the integrator.

The bounded reader uses public Wii Sports USA Rev 1 RPGolConfig, RPGolFieldManager, and RPSportsSequenceMgr static pointer hypotheses from [kiwi515/ogws_info](https://github.com/kiwi515/ogws_info). It requires RSPE01 disc revision byte 1 and RPGolConfig game mode 4. Up to 12 KiB of golf config, field/sequence and minimap-effect memory is collected per non-atomic read-only sample. This does not assume minimap effects are the physical ball.

## Run one genuine shot

Close Dolphin first. From PowerShell:

~~~powershell
cd "D:\Projects\Wii Golf AI\Wii-AI-Golf"
git pull --ff-only

py scripts/run_golf_experiment.py --send-live --game "G:\Applications\Dolphin\Wii Games\Wii Sports (USA) (Rev 1).wbfs" --script collect_outcome_transition.py -- --send-live-swing
~~~

The outer command starts Felk Dolphin, configures the emulated remote, restores the registered green-pre-start savestate and performs the successful A / A+B / A menu sequence. The new action only begins **after** this full startup. It never starts a second Dolphin or loads another savestate.

You confirm the first ball is ready. It records three pre-shot snapshots, asks you to press Enter for exactly ONE forward swing from the current swing generator (the actual frame count is recorded dynamically), then collects **two rapid post-swing snapshots (new default; previously eight)**. The collector immediately prompts you to press Enter when the ball first stops, **before** Wii Sports advances to the next screen. Type `t` if the result screen has already disappeared; the run is retained but its "settled" memory is marked as post-transition/uncertain, NOT verified ball-at-rest. Type `q` to stop without fabricating a result. The script then takes three settled snapshots and asks for a human contact/green/distance label.

Enter the display exactly as shown: **`100.0ft`**, `2.1 ft`, `3 yards`, or a bare number (then it asks for units). An invalid distance prompts again **without discarding the snapshots**. No automatic score is invented. The prompt still cannot detect the game's screen state by itself; if Wii Sports transitions during the swing or the first two reads, the data will not contain missing frames.

To tune observation timing, pass `--post-samples 2 --interval 0` through the full-launch wrapper after `--script collect_outcome_transition.py --` (the new defaults). Increasing `--post-samples` can delay the prompt and miss the result overlay.

Raw samples are written immediately to a uniquely named, exclusive-create **outcome-RUNID-RAW-PRIVATE.jsonl** file under Wii-AI-Golf-Data/captures. **Never upload raw dumps.** A separate local **outcome-RUNID-candidates.json** contains candidate addresses, before/settled possible u32/s32/f32 readings, persistence statistics and the manually entered result. It contains no screenshot. Inspect that summary before sharing.

## Swing regression correction (2026-10-24)

**Do not add a separate A-button prehold to this collector by default.** The user confirmed ball contact in two genuine outcome-collector runs (one 122-frame, one 89-frame forward trace) **without** a separate `prime_a_button` call. PR #40 then forced 60 additional A-only RPCs and the user immediately reported a non-strike. That priming program was not validated for this collector; reverting to the earlier unprimed action is an empirical correction, **not a new guarantee**.

The collector now calls `SwingTraceClient.run(build_probe("forward", follow_through_frames=30))` directly by default. It records `a_button_only_prime_requests: 0`, `a_button_prime_applied: false` and the actual waveform SHA-256. It does not change the canonical Dolphin launch, savestate restore, menu intro, or swing samples. If a specialist explicitly wants a controlled A-prehold experiment, pass `--a-prime-requests 60` to the **collector action**, never to the outer launcher. Treat primed and unprimed results as different controller programs.

**Bridge caveat:** The separate S001 agent has also revised the *generated local* swing bridge to V2. The V2 implementation changes how neutral motion frames are sent and can affect live behavior independently of the collector. Keep your existing locally installed bridge version fixed when comparing attempts and record its capabilities; a bridge upgrade or regression must be assessed as a separate change. This fix has not yet been validated on your machine.

## Recover the run that failed at `100.0ft` (OFFLINE)

A completed RAM capture is written to the local private `outcome-...-RAW-PRIVATE.jsonl` file **before** the label parser ran. An invalid text entry prevented a sanitized candidates JSON but **did not erase raw RAM**. The following command works without Dolphin because it only processes existing local data. The previous run's swing-dispatch metadata was not persisted and is **not recoverable** from memory snapshots; the recovered summary explicitly marks it unknown.

~~~powershell
cd "D:\Projects\Wii Golf AI\Wii-AI-Golf"
git pull --ff-only

$captures = "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\captures"
$raw = Get-ChildItem -LiteralPath $captures -Filter "outcome-*-RAW-PRIVATE.jsonl" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
$raw.FullName  # verify it is the run that failed at 100.0ft

py scripts/recover_outcome_capture.py --raw "$($raw.FullName)" --contact yes --green no --distance "100.0ft"
~~~

The output is a new local `outcome-...-candidates.json` file, generated with exclusive creation. The original `RAW-PRIVATE.jsonl` is never overwritten, transmitted, or committed. If you already have a matching candidates JSON, pass `--out` with another new filename (it will not overwrite existing files). This offline summary documents human-observed 100 ft/no-green and the persistent candidate memory values, **not** an automatic game score or recovered result-screen image.

## Interpretation and stop rules

The algorithm looks for identical raw values across the pre-shot phase, a different but repeated settled value, and records any intermediate changes. It explicitly rejects claims of automatically knowing ball position or game score. A numerical match to one manually entered distance is NOT sufficient evidence of an actual scoring field: one-off coincidences, unit mismatches, transforms and UI effects are possible. Sampling spans many emulation frames; fast flight motion may be missed.

Collect three fresh-boot repetitions with the same swing and at least two distinct actual on-screen outcomes, then compare persistent field values against visible landed-ball/distance evidence. If the game changes mode to a result screen, if pointers are missing, or if no score is visible, preserve negative/partial results and investigate rather than reporting a fake success. A later candidate will require validation on a genuinely different scene/pin and independent outcome measurements.

## Offline verification

~~~powershell
py -m unittest discover -s tests -p "test_outcome_transition.py" -v
py -m unittest discover -s tests -p "test_outcome_capture_cli.py" -v
py -m unittest discover -s tests -p "test_outcome_recovery.py" -v
py -m unittest discover -s tests -v
py -I scripts/collect_outcome_transition.py --help
~~~

Thirteen focused tests passed in a minimal Python 3 setup with mocked/stubbed bridge and swing modules; the actual full Windows repo suite and emulator launch have not been run by this agent. No Dolphin memory is changed. The active evaluation PR #14 is untouched.

Coordination: [S002 Issue #3](https://github.com/Nate27624/Wii-AI-Golf/issues/3).
