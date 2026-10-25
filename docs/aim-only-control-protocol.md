# S002 negative control: aim/camera without swinging

Purpose: distinguish position of actual golf ball from an aim/camera/player-follow object. The current signal 0x925834D8 remains **UNVERIFIED**.

## Protocol (human-guided; no automatic event detection)

1. Close Dolphin. Use fresh physical Wii Remote startup. Wait for mode4, finish navigating to golfer standing at tee, press Enter to begin 20 seconds.
2. For the first ~5 seconds do not touch controls; then **adjust aim/camera only** using the Wii Remote (if game allows); do **not** trigger a shot, press swing buttons, or advance to another tee. Then stop moving for the rest of capture.
3. Check screen: did golfer/camera visibly move? If controls did not actually change aim, report the control as inconclusive. Script phase labels are operator claims, not sensor verified.
4. Keep raw local JSONL and share only sanitized summary or local offline comparison. The aim-only test **does not by itself prove** ball identity.

Fresh session from `D:\Projects\Wii Golf AI\Wii-AI-Golf-Data` (never assume Dolphin is running):

~~~powershell
Set-Location "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data"
git fetch origin
git switch --detach origin/agent/evaluation/read-only-golf-snapshots
$env:PYTHONPATH = (Resolve-Path ".\src").Path
py -m unittest discover -s tests -p "test_focused_trace.py" -v
py scripts/probe_focused_object_xyz.py --controller-mode physical --startup fresh --game "G:\Applications\Dolphin\Wii Games\Wii Sports (USA) (Rev 1).wbfs" --ready-timeout 180 --manual-ready --phase aim_control --operator-note aim_only_no_swing --seconds 20
~~~

Once this capture returns its run ID, execute the **offline**, no-Dolphin comparator against fixed existing local control traces:

~~~powershell
py scripts/compare_focused_conditions.py --idle "captures\focused-object-xyz-20261024T235737Z-90460728.jsonl" --aim "captures\focused-object-xyz-NEW-RUN-ID.jsonl" --swing "captures\focused-object-xyz-20261025T000301Z-bfd74bbd.jsonl" --output "captures\focused-three-condition-summary.json"
~~~

Replace `NEW-RUN-ID` with the actual new capture name. Do not infer actual ball velocity, contact timing or score from motion segments or discontinuities. This is evaluation-owned diagnostic functionality; adding to public `py scripts/golf.py` is coordinator-owned and pending review.
