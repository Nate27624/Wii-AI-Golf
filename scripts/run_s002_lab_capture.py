"""Reviewed S002 live action adapter for the sibling evaluation checkout.

Maintains one fresh physical Dolphin boot inside the source-gated S002 recorder.
No arbitrary code path or argument is accepted from the UI.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
EVAL=ROOT.parent/"Wii-AI-Golf-Data"
ACTIONS={"landmarks":("probe_landmark_control.py","aim_only",20),
         "minimap_camera":("probe_minimap_effect.py","aim_only",20),
         "minimap_swing":("probe_minimap_effect.py","swing",25)}

def command(action: str, game: Path):
    if action not in ACTIONS:raise ValueError("unapproved S002 action")
    if not game.is_file() or game.suffix.lower() not in (".wbfs",".iso"):
        raise ValueError("Owned Wii Sports .wbfs/.iso game file required")
    script,phase,seconds=ACTIONS[action]
    target=EVAL/"scripts"/script
    if not target.is_file() or not (EVAL/"scripts"/"session_bootstrap.py").is_file():
        raise FileNotFoundError("S002 evaluation checkout missing. Update Wii-AI-Golf-Data to reviewed S002 branch first.")
    from importlib.util import spec_from_file_location, module_from_spec
    bootstrap=EVAL/"scripts"/"session_bootstrap.py"
    spec=spec_from_file_location("_s002_bootstrap_preflight",bootstrap)
    if spec is None or spec.loader is None:
        raise RuntimeError("S002 bootstrap cannot be loaded")
    module=module_from_spec(spec)
    spec.loader.exec_module(module)
    for label, path in (("Felk Dolphin",module.DEFAULT_DOLPHIN),
                        ("Felk read-only RPC bridge",module.DEFAULT_BRIDGE)):
        if not Path(path).is_file():
            raise FileNotFoundError(f"{label} missing: {path}. Fix local settings before running.")
    if not (ROOT/"research"/"savestates.local.json").is_file():
        print("NOTE: physical S002 mode navigates manually; no savestate required.",flush=True)
    return [sys.executable,str(target),
            "--controller-mode","physical","--startup","fresh",
            "--game",str(game),"--ready-timeout","180",
            "--phase",phase,"--seconds",str(seconds)]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study",choices=tuple(ACTIONS),required=True)
    args=parser.parse_args()
    from pathlib import Path
    from json import loads
    config=ROOT/"research"/"launch.local.json"
    saved=None
    if config.is_file():
        try:saved=loads(config.read_text(encoding="utf-8")).get("game")
        except (OSError,ValueError,AttributeError):pass
    game=Path(saved) if isinstance(saved,str) and saved else None
    if game is None or not game.is_file():
        print("Enter your locally owned Wii Sports Rev1 .wbfs/.iso image path (never uploaded):",flush=True)
        game=Path(input("Game path: ").strip().strip('"'))
    cmd=command(args.study,game)
    print("S002 live capture selected:",args.study,flush=True)
    print("Fresh physical Wii Remote mode: close Dolphin before launching.",flush=True)
    print("Dolphin will launch once. Navigate manually to Hitting the Green.",flush=True)
    print("Press ENTER only when the *capture script* says the tee is ready.",flush=True)
    return subprocess.run(cmd,cwd=EVAL,check=False).returncode
if __name__=="__main__":
    raise SystemExit(main())
