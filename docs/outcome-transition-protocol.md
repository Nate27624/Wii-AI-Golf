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

You confirm the first ball is ready. It records three pre-shot snapshots, asks you to press Enter for exactly ONE 89-frame forward swing with the existing 30-frame A-held follow-through, collects eight post-swing snapshots, waits until YOU confirm that ball/result has settled, then collects three settled snapshots. You enter whether the ball was struck, whether it landed on the green, and the exact displayed distance and unit if visible. No invisible score is invented.

Raw samples are written immediately to a uniquely named, exclusive-create **outcome-RUNID-RAW-PRIVATE.jsonl** file under Wii-AI-Golf-Data/captures. **Never upload raw dumps.** A separate local **outcome-RUNID-candidates.json** contains candidate addresses, before/settled possible u32/s32/f32 readings, persistence statistics and the manually entered result. It contains no screenshot. Inspect that summary before sharing.

## Interpretation and stop rules

The algorithm looks for identical raw values across the pre-shot phase, a different but repeated settled value, and records any intermediate changes. It explicitly rejects claims of automatically knowing ball position or game score. A numerical match to one manually entered distance is NOT sufficient evidence of an actual scoring field: one-off coincidences, unit mismatches, transforms and UI effects are possible. Sampling spans many emulation frames; fast flight motion may be missed.

Collect three fresh-boot repetitions with the same swing and at least two distinct actual on-screen outcomes, then compare persistent field values against visible landed-ball/distance evidence. If the game changes mode to a result screen, if pointers are missing, or if no score is visible, preserve negative/partial results and investigate rather than reporting a fake success. A later candidate will require validation on a genuinely different scene/pin and independent outcome measurements.

## Offline verification

~~~powershell
py -m unittest discover -s tests -p "test_outcome_transition.py" -v
py -m unittest discover -s tests -p "test_outcome_capture_cli.py" -v
py -m unittest discover -s tests -v
py -I scripts/collect_outcome_transition.py --help
~~~

Thirteen focused tests passed in a minimal Python 3 setup with mocked/stubbed bridge and swing modules; the actual full Windows repo suite and emulator launch have not been run by this agent. No Dolphin memory is changed. The active evaluation PR #14 is untouched.

Coordination: [S002 Issue #3](https://github.com/Nate27624/Wii-AI-Golf/issues/3).
