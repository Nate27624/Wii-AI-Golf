"""Private, fail-closed native-bank staging for an existing S002 capture reader.

Not an emulator client or a capture engine. Consumers use the two returned
file names with their *existing* reader and keeper. No network or publication.
Failures preserve incomplete private files in a uniquely named FAILED folder;
a successful keeper call cleans only files created in this attempt's stage.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import re
import secrets
from typing import Iterator

_PHASES = frozenset(("PRE", "POST", "RESULT"))
_SESSION_NAME = re.compile(r"SHOT-[A-Za-z0-9_-]{1,80}-PRIVATE\Z")


def _validate_session(session: Path, phase: str) -> Path:
    if phase not in _PHASES:
        raise ValueError("Unknown native bank phase")
    path = Path(session)
    if (not path.is_absolute() or not _SESSION_NAME.fullmatch(path.name)
            or path.parent.name != "captures"
            or path.parent.parent.name != "Wii-AI-Golf-Data"):
        raise ValueError("Native stage requires a PRIVATE SHOT session in ignored Data/captures")
    # Do not follow a symlink that can redirect native RAM into a checkout.
    for directory in (path.parent.parent, path.parent, path):
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("Native stage requires existing non-linked private directories")
    return path


@contextmanager
def staged_native_bank_phase(session: Path, phase: str) -> Iterator[tuple[Path, Path]]:
    """Yield unique exclusive mem1.raw/mem2.raw filenames for the S002 keeper.

    The calling code must perform its real bank reads, identity checks, and
    keeper.preserve(...) *inside* this context. A successful block indicates
    only that caller operations returned; it is NOT evidence of a paused guest,
    same-frame bank pair, impact, distance, or permission to train/publish.

    If the caller raises (including KeyboardInterrupt), incomplete private RAM
    is renamed to FAILED-<phase>-<nonce> rather than deleted or overwritten.
    Previous FAILED/STAGING directories are never touched. The same phase may
    then be retried using a fresh stage, subject to the canonical keeper's
    phase-order and shot-evidence guards. Concurrent phase writes are NOT
    serialized here; the canonical runner must keep one session active.
    """
    root = _validate_session(Path(session), phase)
    nonce = secrets.token_hex(12)
    staged = root / f"STAGING-{phase}-{nonce}"
    failed = root / f"FAILED-{phase}-{nonce}"
    # Fail closed on a token collision instead of reusing an old private folder.
    staged.mkdir(mode=0o700, exist_ok=False)
    try:
        yield staged / "mem1.raw", staged / "mem2.raw"
    except BaseException:
        try:
            staged.rename(failed)  # preserve partial evidence for offline review
        except OSError:
            pass  # never hide the original exception or erase evidence
        raise
    else:
        try:
            items = list(staged.iterdir())
            expected = {"mem1.raw", "mem2.raw"}
            if ({p.name for p in items} != expected or len(items) != 2
                    or any(p.is_symlink() or not p.is_file() for p in items)):
                raise RuntimeError("Native staging contents changed; preserving privately")
            for p in items:
                p.unlink()
            staged.rmdir()
        except BaseException:
            if staged.exists():
                try:
                    staged.rename(failed)
                except OSError:
                    pass
            raise
