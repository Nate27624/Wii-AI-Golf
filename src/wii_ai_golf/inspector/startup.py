"""Explicit Windows PowerShell handoff to the existing, operator-approved golf launcher.

This is separate from the live inspector's read-only Felk sampling connection.
Only the UI button initiates the game-changing startup/savestate/menu workflow.
No generated shell scripts, Dolphin input implementation, or arbitrary shell text.
"""
from __future__ import annotations

from pathlib import Path
import socket


class StartupError(ValueError):
    """Required local runtime configuration or safe handoff is unavailable."""


def runtime_checkout(inspector_checkout: Path) -> Path:
    """Locate canonical Wii-AI-Golf worktree with PRIVATE launch catalog.

    The inspector often lives in a sibling detached worktree. Its gitignored
    research/savestates.local.json is not automatically present there.
    Never silently use a different research catalog when canonical is available.
    """
    root = inspector_checkout.resolve()
    canonical = root if root.name.lower() == 'wii-ai-golf' else root.parent / 'Wii-AI-Golf'
    canonical = canonical.resolve()
    launcher = canonical / 'scripts' / 'launch_golf.py'
    attach = canonical / 'scripts' / 'launch_hitting_green.py'
    catalog = canonical / 'research' / 'savestates.local.json'
    if not (launcher.is_file() and attach.is_file()):
        raise StartupError('Canonical Wii-AI-Golf checkout missing launch_golf.py / launch_hitting_green.py')
    if not catalog.is_file():
        raise StartupError('Registered savestate catalog is missing from canonical research/savestates.local.json')
    return canonical


def occupied_bridge(port: int) -> bool:
    """Only test loopback TCP availability; launcher independently validates Felk."""
    if type(port) is not int or not 1 <= port <= 65535:
        raise StartupError('Invalid bridge port (must be 1..65535)')
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=0.3):
            return True
    except OSError:
        return False


def _ps_literal(value: str | Path) -> str:
    """Safe PowerShell SINGLE-quoted literal, no shell interpolation or injection."""
    return "'" + str(value).replace("'", "''") + "'"


def powershell_command(runtime: Path, python: Path, port: int, *, attach: bool) -> list[str]:
    """Create argv for a NEW VISIBLE Windows PowerShell, not shell=True.

    Fresh launch = existing configurable launcher. Running bridge = existing
    savestate reset plus A/A+B/A intro. Neither path includes --swing.
    """
    if type(port) is not int or not 1 <= port <= 65535:
        raise StartupError('Invalid bridge port (must be 1..65535)')
    runtime = runtime.resolve()
    script = runtime / 'scripts' / ('launch_hitting_green.py' if attach else 'launch_golf.py')
    if not script.is_file():
        raise StartupError('Canonical launcher was not found')
    if not python.is_file():
        raise StartupError('Python interpreter was not found')
    flags = ("--attach-running --send-live" if attach else '')
    desc = ('Attach to existing Felk Dolphin and reload the registered pre-start checkpoint'
            if attach else 'Start Felk Dolphin from the registered pre-start checkpoint')
    body = (
        "$ErrorActionPreference = 'Stop'; "
        f"Set-Location -LiteralPath {_ps_literal(runtime)}; "
        f"Write-Host {_ps_literal(desc)} -ForegroundColor Cyan; "
        f"& {_ps_literal(python)} -I {_ps_literal(script)} --profile green-pre-start --port {port} {flags}; "
        "$golfExit = $LASTEXITCODE; "
        "if ($golfExit -ne 0) { Write-Host 'Golf startup failed; inspect the error above.' -ForegroundColor Red } "
        "else { Write-Host 'Menu inputs dispatched. VISUALLY VERIFY golfer at the ball, then Connect LIVE in the inspector. No shot was fired.' -ForegroundColor Green }"
    )
    return ['powershell.exe', '-NoProfile', '-NoExit', '-Command', body]
