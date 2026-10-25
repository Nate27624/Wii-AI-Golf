"""Safely synchronize reviewed Golf Lab experiments from origin/main only.

Never execute arbitrary remote manifests or silently replace local changes.
The operator must restart after a successful update.
"""
from __future__ import annotations
from pathlib import Path
import subprocess

def sync_reviewed_main(root: Path, *, runner=subprocess.run) -> dict:
    root=Path(root)
    def git(*args):
        result=runner(["git","-C",str(root),*args],capture_output=True,text=True,
                      check=False,timeout=25)
        if result.returncode:
            raise RuntimeError("git "+args[0]+" failed: "+(result.stderr or result.stdout).strip()[:400])
        return result.stdout.strip()
    branch=git("branch","--show-current")
    if branch!="main":
        raise ValueError("Safe sync only works on the main branch. Merge reviewed experiment PRs first.")
    if git("status","--porcelain"):
        raise ValueError("Uncommitted changes: refusing to update")
    if git("remote","get-url","origin").removesuffix(".git").rstrip("/") not in (
            "https://github.com/Nate27624/Wii-AI-Golf",
            "git@github.com:Nate27624/Wii-AI-Golf"):
        raise ValueError("origin must be the canonical Wii-AI-Golf repository")
    before=git("rev-parse","HEAD")
    git("fetch","origin","main")
    git("merge","--ff-only","origin/main")
    after=git("rev-parse","HEAD")
    return {"updated":before!=after,"before":before,"after":after,
            "action":"Restart Golf Lab to reload imported code and experiment registry"}
