# S003 Ten-shot power calibration (preregistered)

Observed on real Wii Sports Golf (human labels; not verified memory):
- Speed-only 0.8 and 0.9: both struck ball, ~75% visible gauge, off green with 100.0ft capped penalty.
- Backswing-only 0.8: struck ball, ~75% visible gauge, off green with 100.0ft penalty.
- Working control: 45 observed frames A-only lead + V1 bridge + fixed 89 frame A-held trace; two baseline 1.0 shots struck.
- Therefore the available data **does not provide a continuous distance response**. Do not fit a regression to the off-green 100.0ft value.

## Design

`py scripts/research_cli.py study` displays a frozen schedule of ten individually approved, independent fresh-boot trials **on the same first-ball scene**. This does not navigate ten game holes; multi-hole scene transitions aren't validated, and pooling different hole geometries without scenario labels would confound the power study.

Five conditions repeated twice in balanced order (speed scale, backswing scale):
1. (1.0, 1.0) control
2. (0.8, 1.0)
3. (1.0, 1.2)
4. (0.9, 1.0)
5. (1.0, 0.8)
6. (1.0, 1.0) control
7. (1.0, 0.8)
8. (0.9, 1.0)
9. (1.0, 1.2)
10. (0.8, 1.0)

Only one parameter changes per trial; original speed, distance, A lead 45 and bridge otherwise remain fixed. Operators close Dolphin before each command and respond to a live shot confirmation. Each shot uses `--study-id S003-POWER-MAP-10-V1 --trial-index N` to make the output joinable in the sanitized GitHub observations branch. Invalid combinations are rejected before launching the game.

## Measurements and stop criteria

For EACH shot, record initial pose (back/center/forward/unknown), ball contact, visible power percentage if shown, on-green yes/no, displayed score and unit, and whether the settled capture preceded screen transition. Use `t` if the result screen already changed.

Primary outcome: proportion of **human-observed successful ball contacts** in each condition. Secondary: on-green success and the reported power gauge; 100.0ft off-green is penalty/censored score, not physical carry distance. Do not claim shot distance/verified score without game-state validation.

Stop for incorrect start scene, changed bridge, failed continuous A hold, or inconsistent start pose that invalidates matching. Compare both control trials with earlier two verified-by-human contacts. **If all five conditions remain ~75% power, further parameter tweaks are low information; investigate the underlying power-meter response and physical controller simulation before new sweeps.**

The first 10-shot stage is observation collection, not automatic optimization. Do not adapt trial order mid-study based on intermediate performance; subsequent experiments should be preregistered separately.
