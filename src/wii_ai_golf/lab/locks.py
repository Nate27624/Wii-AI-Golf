"""Crash-safe local Lab locking; process death automatically releases new locks.

On Windows use msvcrt.locking; on Unix use fcntl.flock. Existing JSON PID
lockfiles created by old Lab versions are honored if their owner is alive.
Dead legacy owners do NOT require the operator to delete any file.
"""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import errno
import json
import os
from pathlib import Path
from typing import Iterator


def pid_running(pid: int) -> bool:
    """Conservatively distinguish gone legacy owners from possibly active ones."""
    if type(pid) is not int or pid <= 0:
        return True
    if pid == os.getpid():
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError as exc:
        # Windows reports invalid/nonexistent PID as winerror 87 or 1168.
        if exc.errno == errno.ESRCH or getattr(exc, "winerror", None) in (87, 1168):
            return False
        return True
    return True


def _lock_one_byte(file) -> None:
    file.seek(0)
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_one_byte(file) -> None:
    file.seek(0)
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(file.fileno(), fcntl.LOCK_UN)


def _legacy_active(raw: bytes) -> bool:
    contents = raw.strip(b"\x00 \r\n\t")
    if not contents:
        return False
    try:
        entry = json.loads(contents)
        pid = entry["pid"]
        if type(pid) is not int or pid <= 0:
            return True
    except (ValueError, KeyError, TypeError):
        # Unfamiliar legacy lock: never assume it is safe to bypass.
        return True
    return pid_running(pid)


@contextmanager
def session_lock(path: Path, *, label: str = "Lab experiment") -> Iterator[None]:
    """Use an OS-released lock, not an O_EXCL file that survives a crash.

    It is safe to keep the lock file on disk: busy means held by a process,
    NOT merely exists. Preserve active locks from legacy O_EXCL builds by
    checking their PID only after obtaining the OS advisory lock.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # The file remains present after successful release, unlike the old
    # exclusive-create implementation. No deletion/unlink races.
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(fd, "r+b", buffering=0) as file:
        file.seek(0)
        if not file.read(1):
            file.seek(0)
            file.write(b"\x00")  # Windows byte-range lock needs a real byte
        acquired = False
        owns_record = False
        try:
            try:
                _lock_one_byte(file)
                acquired = True
            except (OSError, IOError) as exc:
                raise ValueError(f"{label} is already active. "
                                 "The Lab will not start a second job.") from exc
            file.seek(0)
            raw = file.read(2048)
            if _legacy_active(raw):
                raise ValueError(
                    f"{label} may still be running under an older Lab version "
                    f"({path.name}); no files were deleted. Close the old job "
                    "or check its process before starting another.")
            file.seek(0)
            file.truncate()
            file.write(json.dumps({
                "pid": os.getpid(),
                "utc": datetime.now(timezone.utc).isoformat(),
                "protocol": "os-advisory-v1",
            }).encode("utf-8"))
            file.flush()
            owns_record = True
            yield
        finally:
            if acquired and owns_record:
                # Leave a zero-byte sentinel to be safe for subsequent Windows
                # byte-range acquisitions without an O_EXCL race.
                file.seek(0)
                file.write(b"\x00")
                file.truncate(1)
                file.flush()
                _unlock_one_byte(file)
            elif acquired:
                _unlock_one_byte(file)


def lock_busy(path: Path) -> bool:
    """Check actual OS-held or active legacy lock, not file existence.

    A malformed, unreadable or concurrently locked record fails closed.
    """
    if not Path(path).exists():
        return False
    try:
        with session_lock(path, label="Lab task"):
            pass
        return False
    except (ValueError, OSError):
        return True


def any_lab_job_busy(data: Path) -> bool:
    return any(lock_busy(Path(data) / name)
               for name in ("run-session.lock", "live-session.lock"))
