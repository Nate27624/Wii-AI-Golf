"""Opt-in Windows dialogs for operator prompts; CLI remains terminal-first.

WII_GOLF_DIALOGS=1 is set by a trusted UI launcher, never by downloaded
experiment registry data. The caller still owns verification of game state.
"""
from __future__ import annotations

import os


def operator_input(message: str) -> str:
    """Return terminal-compatible input; cancel maps to 'q' (fail closed)."""
    if os.environ.get("WII_GOLF_DIALOGS") != "1":
        return input(message)
    try:
        import tkinter as tk
        from tkinter import simpledialog
        root = tk.Tk()
        root.withdraw()
        try:
            value = simpledialog.askstring(
                "Wii AI Golf — experiment input", message,
                parent=root,
            )
        finally:
            root.destroy()
    except (ImportError, RuntimeError, tk.TclError) as exc:
        # Do not implicitly approve a live experiment if the UI is unavailable.
        raise RuntimeError("Operator dialog unavailable; experiment canceled") from exc
    return "q" if value is None else value
