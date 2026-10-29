"""PRIVATE full Wii MEM1+MEM2 streaming capture from an ALREADY RUNNING Felk bridge.

Writes native binary banks, not JSON-only windows. No Dolphin start/reset, pause,
controller input, savestate mutation, bridge patching, or automatic publication.

CRITICAL: Felk RPC is polled once per advancing emulator frame. These are
ROLLING, MULTI-FRAME reads and cannot be used as same-pause PRE/POST snapshots.
Do not feed them to the native paused-pair S002/P0 snapshot analyzers.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Callable, Iterator, Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = str(ROOT / "src")
if SRC in sys.path:
    sys.path.remove(SRC)
sys.path.insert(0, SRC)

from wii_ai_golf.integration.rpc import FelkRPC  # noqa: E402

DATA_ROOT = ROOT.parent / "Wii-AI-Golf-Data"
CAPTURE_ROOT = DATA_ROOT / "captures"
REV1_HEADER = b"RSPE01\x00\x01"
MAX_RPC_CHUNK = 16384  # 32KiB encoded, well below default FelkRPC 64KiB limit
GAME_CONFIG_PTR = 0x804BF8C4
MODE_OFFSET = 0x94
ALLOWED_PHASES = ("PRE", "POST", "RESULT", "CONTROL")
SAFE_SESSION = re.compile(r"^FULLRAM-[A-Za-z0-9_-]{4,65}-PRIVATE$")


@dataclass(frozen=True)
class Bank:
    name: str
    address: int
    length: int
    filename: str


BANKS = (
    Bank("MEM1", 0x80000000, 24 * 1024 * 1024, "mem1.raw"),
    Bank("MEM2", 0x90000000, 64 * 1024 * 1024, "mem2.raw"),
)


def _is_ram_pointer(p: Any) -> bool:
    return type(p) is int and ((0x80000000 <= p < 0x81800000)
                               or (0x90000000 <= p < 0x94000000))


def _frame(rpc: Any) -> int:
    value = rpc.call("frame.get_count", [])
    if type(value) is not int or value < 0:
        raise ValueError("invalid emulator frame count")
    return value


def _read_exact(rpc: Any, address: int, size: int) -> bytes:
    if type(size) is not int or not 1 <= size <= MAX_RPC_CHUNK:
        raise ValueError("invalid bounded RPC size")
    encoded = rpc.call("memory.read_bytes", [address, size])
    if not isinstance(encoded, str) or len(encoded) != size * 2:
        raise ValueError("invalid bridge byte read length")
    try:
        raw = bytes.fromhex(encoded)
    except ValueError as exc:
        raise ValueError("bridge returned invalid hexadecimal bytes") from exc
    if len(raw) != size:
        raise ValueError("bridge returned wrong native byte count")
    return raw


def _check_header_and_mode(rpc: Any, *, require_mode: bool) -> None:
    if _read_exact(rpc, BANKS[0].address, 8) != REV1_HEADER:
        raise RuntimeError("not Wii Sports RSPE01 revision 1; capture refused")
    if require_mode:
        ptr = rpc.call("memory.read_u32", [GAME_CONFIG_PTR])
        if not _is_ram_pointer(ptr) or not _is_ram_pointer(ptr + MODE_OFFSET):
            raise RuntimeError("Golf config pointer invalid")
        mode = rpc.call("memory.read_u32", [ptr + MODE_OFFSET])
        if type(mode) is not int or mode != 4:
            raise RuntimeError("Hitting the Green (mode 4) is not active")


def _secure_root(data_root: Path) -> Path:
    """Use only the ignored sibling Data root; reject linked directory ancestry."""
    if data_root.name != "Wii-AI-Golf-Data" or data_root.parent != ROOT.parent:
        raise ValueError("private root must be the ignored sibling Data directory")
    for p in (data_root, data_root / "captures"):
        if p.is_symlink():
            raise ValueError("refusing linked private capture directory")
        p.mkdir(exist_ok=True)
        if not p.is_dir() or p.is_symlink():
            raise ValueError("unsafe private capture directory")
    return data_root / "captures"


def _check_session(session: str) -> None:
    if not isinstance(session, str) or not SAFE_SESSION.fullmatch(session):
        raise ValueError("session must be FULLRAM-<safe-id>-PRIVATE, not a path")


def _safe_phase(phase: str, *, confirmed: bool, observed_displacement: bool) -> None:
    if phase not in ALLOWED_PHASES:
        raise ValueError("invalid phase")
    if not confirmed:
        raise ValueError("operator must explicitly confirm visible requested phase")
    if observed_displacement and phase != "POST":
        raise ValueError("displacement claim only applies to POST")
    if phase == "POST" and not observed_displacement:
        raise ValueError("POST needs visible displacement; otherwise use CONTROL")


@contextmanager
def _exclusive_session_phase(captures: Path, session: str, phase: str) -> Iterator[Path]:
    folder = captures / session
    if folder.is_symlink():
        raise ValueError("linked session refused")
    folder.mkdir(exist_ok=True)
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError("unsafe session")
    lock = folder / "capture-active.lock"
    try:
        with lock.open("x", encoding="ascii") as fp:
            fp.write("active; private\n")
    except FileExistsError as exc:
        raise RuntimeError("private session is busy; do not run a second capture") from exc
    try:
        dest = folder / (phase + "-ROLLING")
        if dest.exists() or dest.is_symlink():
            raise FileExistsError("phase already exists: never overwrite native RAM")
        dest.mkdir()
        yield dest
    finally:
        lock.unlink(missing_ok=True)


def _record_bank(rpc: Any, bank: Bank, target: Path, *, chunk_bytes: int,
                 progress: Callable[[str], None], require_mode: bool,
                 check_interval: int = 1 << 20) -> dict[str, Any]:
    if not 1 <= chunk_bytes <= MAX_RPC_CHUNK:
        raise ValueError("chunk size out of bounds")
    written = 0
    next_check = check_interval
    sha = hashlib.sha256()
    started = _frame(rpc)
    with target.open("xb") as fp:
        for offset in range(0, bank.length, chunk_bytes):
            n = min(chunk_bytes, bank.length - offset)
            blob = _read_exact(rpc, bank.address + offset, n)
            fp.write(blob)
            sha.update(blob)
            written += n
            if written >= next_check:
                _check_header_and_mode(rpc, require_mode=require_mode)
                progress(f"{bank.name}: {written // (1024*1024)} / {bank.length // (1024*1024)} MiB")
                next_check += check_interval
    ended = _frame(rpc)
    if written != bank.length or target.stat().st_size != bank.length or ended < started:
        raise RuntimeError("incomplete full bank or backwards emulator frame counter")
    return {"bank": bank.name, "guest_base": f"0x{bank.address:08X}",
            "filename": target.name, "bytes": written,
            "sha256": sha.hexdigest(), "start_frame": started, "end_frame": ended,
            "frame_span": ended - started}


def capture(rpc: Any, *, captures: Path, session: str, phase: str,
            confirmed: bool, observed_displacement: bool = False,
            chunk_bytes: int = MAX_RPC_CHUNK,
            banks: Sequence[Bank] = BANKS,
            progress: Callable[[str], None] = print) -> dict[str, Any]:
    """Live rolling full-bank binary capture; never claims a snapshot."""
    _check_session(session)
    _safe_phase(phase, confirmed=confirmed, observed_displacement=observed_displacement)
    if type(chunk_bytes) is not int or not 1 <= chunk_bytes <= MAX_RPC_CHUNK:
        raise ValueError("invalid chunk_bytes")
    if not banks or any(type(b.length) is not int or b.length <= 0 for b in banks):
        raise ValueError("invalid banks")
    require_mode = phase in ("PRE", "POST")
    info = rpc.call("bridge.ping", [])
    if not isinstance(info, dict) or not isinstance(info.get("bridge_version"), str):
        raise RuntimeError("Felk bridge did not respond to ping")
    first = _frame(rpc)
    time.sleep(0.08)
    if _frame(rpc) <= first:
        raise RuntimeError("Dolphin is paused/not advancing; full-bank bridge capture requires RUNNING emulation")
    _check_header_and_mode(rpc, require_mode=require_mode)
    begun = datetime.now(timezone.utc).isoformat()
    with _exclusive_session_phase(captures, session, phase) as dest:
        try:
            records = []
            for bank in banks:
                progress(f"Reading {bank.name} (rolling, live frames; do not pause Dolphin)...")
                records.append(_record_bank(rpc, bank, dest / (bank.filename + ".part"),
                                            chunk_bytes=chunk_bytes, progress=progress,
                                            require_mode=require_mode))
            _check_header_and_mode(rpc, require_mode=require_mode)
            last = _frame(rpc)
            for record, bank in zip(records, banks):
                source = dest / (bank.filename + ".part")
                if source.stat().st_size != bank.length:
                    raise RuntimeError("corrupt binary bank size")
                with source.open("rb") as fp:
                    hasher = hashlib.sha256()
                    for block in iter(lambda: fp.read(1024*1024), b""):
                        hasher.update(block)
                if hasher.hexdigest() != record["sha256"]:
                    raise RuntimeError("disk hash differs from streamed hash")
            for bank in banks:
                os.rename(dest / (bank.filename + ".part"), dest / bank.filename)
            report = {
                "kind": "local-private-full-ram-rolling-bridge-capture",
                "schema_version": 1, "session": session, "phase_operator_label": phase,
                "operator_confirmed_phase": True,
                "operator_reported_displaced_ball": observed_displacement,
                "game_id": "RSPE01", "disc_revision": 1,
                "golf_mode4_verified_at_intervals": require_mode,
                "started_utc": begun, "finished_utc": datetime.now(timezone.utc).isoformat(),
                "banks": records, "start_frame": first, "end_frame": last,
                "non_atomic_frame_span": last - first,
                "full_memory_banks_present": len(banks) == 2 and tuple((x.name, x.length) for x in banks) == tuple((x.name, x.length) for x in BANKS),
                "same_guest_frame_verified": False,
                "same_paused_bank_pair": False,
                "approved_for_native_prepost_comparator": False,
                "gameplay_outcome_verified": False,
                "approved_for_model_training": False,
                "allowed_to_publish": False,
                "warning": "The full binary files are ROLLING live-RPC reads across many frames, not atomic paused exports. They cannot be substituted for native same-pause PRE/POST snapshots.",
            }
            meta = dest / "capture-meta-PRIVATE.json"
            with (dest / (meta.name + ".tmp")).open("x", encoding="utf-8") as fp:
                json.dump(report, fp, indent=2, sort_keys=True)
                fp.write("\n")
            os.replace(dest / (meta.name + ".tmp"), meta)
            return report
        except BaseException:
            for bank in banks:
                (dest / bank.filename).unlink(missing_ok=True)
            (dest / "capture-meta-PRIVATE.json.tmp").unlink(missing_ok=True)
            raise


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    action = ap.add_mutually_exclusive_group()
    action.add_argument("--capture", action="store_true", help="opt in to live, read-only complete RAM dump")
    action.add_argument("--probe", action="store_true", help="read-only small live RPC compatibility probe; no files")
    ap.add_argument("--session", help="safe ID FULLRAM-...-PRIVATE; reuse for sequential phases")
    ap.add_argument("--phase", choices=ALLOWED_PHASES, default="PRE")
    ap.add_argument("--confirm-phase", action="store_true", help="operator visually confirmed PRE/POST/RESULT/CONTROL")
    ap.add_argument("--observed-displacement", action="store_true", help="POST only: ball visibly moved before reset")
    ap.add_argument("--chunk-bytes", type=int, default=MAX_RPC_CHUNK,
                    help="1..16384 bytes/read; defaults 16KiB and 32KiB encoded response")
    ap.add_argument("--port", type=int, default=55355)
    args = ap.parse_args(argv)
    if not 1 <= args.port <= 65535:
        ap.error("port must be 1..65535")
    session = args.session or ("FULLRAM-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-PRIVATE")
    try:
        _check_session(session)
        if args.probe:
            with FelkRPC(port=args.port, timeout_s=20.0, max_response_bytes=65536) as rpc:
                info = rpc.call("bridge.ping", [])
                if not isinstance(info, dict) or not isinstance(info.get("bridge_version"), str):
                    raise RuntimeError("bridge ping failed")
                first = _frame(rpc)
                time.sleep(0.08)
                last = _frame(rpc)
                if last <= first:
                    raise RuntimeError("Dolphin is paused/not advancing")
                _check_header_and_mode(rpc, require_mode=args.phase in ("PRE", "POST"))
                for bank in BANKS:
                    _read_exact(rpc, bank.address, 256)
            print("PROBE OK: RSPE01 Rev1, active Felk, advancing frames, both bank origins readable")
            print("No output files created; full capture requires --capture --confirm-phase")
            return 0
        if not args.capture:
            print("DRY RUN ONLY: 24 MiB MEM1 + 64 MiB MEM2 raw binary under ignored sibling Data/captures")
            print("Session:", session, "Phase:", args.phase,
                  "Chunk:", args.chunk_bytes, "bytes; NO emulator/RAM touched")
            print("Note: live RPC reads span thousands of advancing frames, not atomic snapshots")
            return 0
        _safe_phase(args.phase, confirmed=args.confirm_phase,
                    observed_displacement=args.observed_displacement)
        if not 1 <= args.chunk_bytes <= MAX_RPC_CHUNK:
            raise ValueError("invalid chunk size")
        captures = _secure_root(DATA_ROOT)
        with FelkRPC(port=args.port, timeout_s=30.0, max_response_bytes=65536) as rpc:
            report = capture(rpc, captures=captures, session=session, phase=args.phase,
                             confirmed=True, observed_displacement=args.observed_displacement,
                             chunk_bytes=args.chunk_bytes)
        print("BINARY FULL BANKS SAVED LOCALLY:")
        for bank in report["banks"]:
            print(f"{report['session']}/{args.phase}-ROLLING/{bank['filename']} "
                  f"({bank['bytes'] // (1024*1024)} MiB)")
        print("Non-atomic frame span:", report["non_atomic_frame_span"])
        print("Raw RAM and private hashes are NOT uploaded to GitHub")
        return 0
    except (OSError, RuntimeError, ValueError, FileExistsError, TimeoutError) as exc:
        # Stable safe error codes instead of dumping bridge/private exception text.
        reason = str(exc).lower()
        if "paused" in reason or "not advancing" in reason or "frame counter" in reason:
            code = "DOLPHIN_PAUSED_OR_STALLED"
        elif "mode 4" in reason or "hitting the green" in reason:
            code = "NOT_IN_HITTING_GREEN"
        elif "rspe01" in reason or "revision" in reason:
            code = "WRONG_GAME_OR_REVISION"
        elif "byte read" in reason or "hexadecimal" in reason or "byte count" in reason:
            code = "BRIDGE_RAM_REPLY_INVALID"
        elif "already exist" in reason or "phase already" in reason or "busy" in reason:
            code = "DUPLICATE_OR_BUSY_SESSION"
        elif "not found" in reason or "refused" in reason or "timed out" in reason:
            code = "BRIDGE_OR_FILE_UNAVAILABLE"
        elif "confirm" in reason or "displacement" in reason:
            code = "PHASE_CONFIRMATION_REQUIRED"
        else:
            code = type(exc).__name__.upper()
        print(f"Full-RAM capture FAILED [{code}]. No finished native pair was claimed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
