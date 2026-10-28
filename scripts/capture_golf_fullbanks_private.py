"""Read complete Wii Sports MEM1/MEM2 from a paused Dolphin into PRIVATE binary files.

Requires the operator to pause the already running FelkDolphin-Clean process.
The external Dolphin Memory Engine works when the frame-polled bridge cannot.
No emulator launch, input, reset, savestate write or network publication.
"""
import argparse
from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT.parent / "Wii-AI-Golf-Data"
BANKS = (("MEM1", "mem1.raw", 0x80000000, 24 * 1024 * 1024),
         ("MEM2", "mem2.raw", 0x90000000, 64 * 1024 * 1024))


def read_bank(reader, start, size, output):
    """Bounded 1 MiB reads; never silently truncate or overwrite."""
    with output.open("xb") as f:
        for offset in range(0, size, 1024 * 1024):
            count = min(1024 * 1024, size - offset)
            raw = reader.read_bytes(start + offset, count)
            if type(raw) is not bytes or len(raw) != count:
                raise RuntimeError("Incomplete Wii RAM read")
            f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    if output.stat().st_size != size:
        raise RuntimeError("Incorrect native bank size")


def save_pair(*, session, phase, reader, keeper, shot=False, same_process=False,
              same_hole=False, result=False, distance=None, unit=None):
    session = Path(session)
    if phase not in ("PRE", "POST", "RESULT"):
        raise ValueError("Invalid phase")
    tmp = session / ("STAGING-" + phase)
    tmp.mkdir(exist_ok=False)
    files = []
    for _bank, filename, start, size in BANKS:
        out = tmp / filename
        read_bank(reader, start, size, out)
        files.append(out)
    with files[0].open("rb") as f:
        if f.read(8) != b"RSPE01\x00\x01":
            raise RuntimeError("Not Wii Sports RSPE01 Rev1 guest memory")
    # Reuse existing S002 strict paused-pair manifest and native-bank copier.
    report = keeper.preserve(
        private_root=session, mem1_source=files[0], mem2_source=files[1],
        checkpoint=phase, paused_confirmed=True, shot_observed=shot,
        same_process_confirmed=same_process, same_hole_confirmed=same_hole,
        result_visible=result, displayed_distance=distance, ui_unit=unit)
    for f in files:
        f.unlink()
    tmp.rmdir()
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--session", type=Path, required=True)
    p.add_argument("--phase", choices=("PRE", "POST", "RESULT"), required=True)
    p.add_argument("--paused-confirmed", action="store_true")
    p.add_argument("--shot-observed", action="store_true")
    p.add_argument("--same-process-confirmed", action="store_true")
    p.add_argument("--same-hole-confirmed", action="store_true")
    p.add_argument("--result-visible", action="store_true")
    p.add_argument("--displayed-distance", type=float)
    p.add_argument("--ui-unit", choices=("ft", "yd", "m"))
    a = p.parse_args()
    try:
        session = a.session.resolve(strict=True)
        private_root = PRIVATE.resolve(strict=True)
        if (not a.paused_confirmed or PRIVATE.name != "Wii-AI-Golf-Data"
            or session == private_root or not session.is_relative_to(private_root)
            or not session.name.startswith("SHOT-") or not session.name.endswith("-PRIVATE")
            or a.session.is_symlink() or PRIVATE.is_symlink()):
            raise ValueError("Requires operator-paused Dolphin and ignored SHOT private session")
        if a.phase == "POST" and not (
            a.shot_observed and a.same_process_confirmed and a.same_hole_confirmed):
            raise ValueError("POST must visibly displace ball before reset")
        if a.phase == "RESULT" and not a.result_visible:
            raise ValueError("RESULT needs visible result")
        import dolphin_memory_engine as dolphin
        import preserve_golf_shot_distance_checkpoint_private as keeper
        dolphin.hook()
        if not dolphin.is_hooked():
            raise RuntimeError("Dolphin memory engine did not hook")
        try:
            if dolphin.read_bytes(0x80000000, 8) != b"RSPE01\x00\x01":
                raise RuntimeError("Expected Wii Sports Rev1 memory header missing")
            report = save_pair(
                session=session, phase=a.phase, reader=dolphin, keeper=keeper,
                shot=a.shot_observed, same_process=a.same_process_confirmed,
                same_hole=a.same_hole_confirmed, result=a.result_visible,
                distance=a.displayed_distance, unit=a.ui_unit)
        finally:
            dolphin.un_hook()
        print(json.dumps({
            "phase": a.phase, "native_banks_saved": report["preserved_native_banks"],
            "MEM1_bytes": BANKS[0][3], "MEM2_bytes": BANKS[1][3],
            "paused_operator_attested": True,
            "same_guest_frame_independently_verified": False,
            "allowed_to_publish": False, "training_allowed": False,
        }, indent=2))
        return 0
    except (OSError, RuntimeError, ValueError, ImportError, TypeError) as e:
        print("Native private bank capture refused: " + str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
