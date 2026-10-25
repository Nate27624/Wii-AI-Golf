# Controlled A-button lead: V1 isolated bridge

Status: experimental and not yet verified by a real Wii Sports ball strike.

## Operator observation

The user reports the isolated older V1 bridge nearly struck the ball, but the club may have started moving before the game recognized the A press. This is a visual timing hypothesis, not a game-state fact. Repeating a button RPC N times is NOT the same as holding A for N emulated frames. Previous speculative A priming changes also had misses, so do not assume a longer lead automatically succeeds.

## One-variable timing experiment

The shared helper wii_ai_golf.shared.controller_timing.hold_a_for_observed_frames first calls the EXISTING S001 prime_a_button for one A-only RPC, then repeatedly samples frame.get_count until >=12 Dolphin frames have actually elapsed with A requested as pressed. Only then does the ORIGINAL SwingTraceClient forward waveform run. The wave direction, distance/speed, 89 sample count, 30-frame follow-through, V1 bridge, menu intro and savestate are unchanged. No swing RPC occurs before measured A lead completion. A timeout or invalid frame counter fails before the swing and performs button-release cleanup.

The action flag --a-lead-frames 12 is opt-in only; the collector default remains zero. The old --a-prime-requests is mutually exclusive. The report records actual observed lead delta, counter start/end, one button-only RPC, and trace SHA256. This does not establish that the game received A or registered a strike.

## Offline validation

From PowerShell, canonical repository:

    cd "D:\Projects\Wii Golf AI\Wii-AI-Golf"
    git pull --ff-only
    py -m unittest discover -s tests -p "test_shared_controller_timing.py" -v
    py -m unittest discover -s tests -p "test_outcome_capture_cli.py" -v
    py -m unittest discover -s tests -p "test_outcome_compare.py" -v

The operator already audited the locally installed current V2 and backup V1. The following isolated V1 file is available ONLY after the previous optional audit --prepare-legacy-trial created it without overwriting the active bridge:

    D:\Projects\Wii Golf AI\tools\mcp_bridge_swing_legacy_eval.py

Close Dolphin completely before the ONE live run, then execute this SINGLE command (PowerShell accepts one line):

    py scripts/run_golf_experiment.py --send-live --game "G:\Applications\Dolphin\Wii Games\Wii Sports (USA) (Rev 1).wbfs" --bridge "D:\Projects\Wii Golf AI\tools\mcp_bridge_swing_legacy_eval.py" --script collect_outcome_transition.py -- --send-live-swing --a-lead-frames 12

The wrapper launches one fresh Dolphin/game, restores the EXISTING named green-pre-start state, configures Emulated Wii Remote, and executes the canonical A / A+B / A intro before experiment. No second emulator or new save state. On screen, check distinctly: A visibly held before club motion? Club moved? Ball actually moved? Did the game display distance with original unit? A trace-complete acknowledgement is not a hit.

If the game already transitioned by the landing prompt, type t and label screen timing uncertain. Stop after one trial; do not blindly escalate A lead or swing power. Compare with the V1 zero-lead control rather than treating a different bridge or waveform as identical.

## Cross-agent coordination

S001 continues to own the actual swing/bridge/controller primitive. This helper is reusable for S001 and S002. S002 has only the narrow outcome collection option. Issue #47 S000 lab agent owns registry, GUI and unified runner; no competing launcher has been created. The new outcome comparison metadata detects differences in measured lead time, preventing a false claim of identical controller programs.
