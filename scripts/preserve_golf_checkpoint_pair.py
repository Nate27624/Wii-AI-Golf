"""Preserve a paused native MRAM+ExRAM pair safely for memory-first research.

One invocation per GUI-paused checkpoint AFTER Dolphin Memory -> Export ->
Dump MRAM and Dump ExRAM. NO Dolphin commands, controller, RPC or network.
The source Dolphin Dump/{mem1,mem2}.raw files are overwritten every export,
so this tool copies them to a fresh private directory BEFORE the next run.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import mmap
import os
from pathlib import Path
import shutil
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.audit.golf_cross_bank_state import (
    audit_pair, MEM1_SIZE, MEM2_SIZE,
)

PHASES = {
    "B0": "idle_baseline",
    "B1": "idle_delayed",
    "B2": "wasd_aim_only",
    "B3": "idle_after_aim",
    "B4": "landed_after_observed_shot",
}
SCHEMA_VERSION = 1
MANIFEST_NAME = "checkpoint-manifest-PRIVATE.json"
MAX_MANIFEST_BYTES = 32768


def _digest(path):
    hash_ = hashlib.sha256()
    with Path(path).open("rb") as reader:
        for chunk in iter(lambda: reader.read(1024 * 1024), b""):
            hash_.update(chunk)
    return hash_.hexdigest()


def _source(path, *, required_name, required_size):
    p = Path(path)
    if (p.is_symlink() or not p.is_file() or
            p.name.lower() != required_name or
            p.stat().st_size != required_size):
        raise ValueError("Missing, wrong-name or wrong-size native Dolphin dump")
    return p


def _read_manifest(path):
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("Unsafe existing private checkpoint manifest")
    with path.open("r", encoding="utf-8") as f:
        content = json.load(f)
    if (not isinstance(content, dict) or
            content.get("kind") != "local-private-golf-paired-checkpoints" or
            content.get("schema_version") != SCHEMA_VERSION or
            type(content.get("checkpoints")) is not dict or
            type(content.get("session_id")) is not str):
        raise ValueError("Private manifest schema does not match")
    return content


def preserve_pair(*, mem1_source, mem2_source, private_root,
                  checkpoint, paused_confirmed=False, shot_observed=False,
                  trusted_data_root=None):
    """Validate, source-gate and preserve one pair; fail closed on stale files.

    trusted_data_root is restricted to sibling Wii-AI-Golf-Data in the CLI.
    Unit tests may inject their own private root without any emulator.
    """
    if checkpoint not in PHASES or paused_confirmed is not True:
        raise ValueError("Checkpoint must be recognized and GUI pause confirmed")
    if shot_observed and checkpoint != "B4":
        raise ValueError("Shot-observed flag is only meaningful at B4")
    if checkpoint == "B4" and shot_observed is not True:
        raise ValueError("B4 requires independent operator-observed landed shot")
    private = Path(private_root)
    if private.is_symlink() or not private.is_dir():
        raise ValueError("Choose an existing, nonsymlink private session folder")
    dest_root = private.resolve(strict=True)
    trusted = Path(trusted_data_root or (ROOT.parent / "Wii-AI-Golf-Data"))
    if (not trusted.is_dir() or trusted.is_symlink()
            or not dest_root.is_relative_to(trusted.resolve(strict=True))
            or dest_root == trusted.resolve(strict=True)):
        raise ValueError("Private session folder must be within Wii-AI-Golf-Data")
    src1 = _source(mem1_source, required_name="mem1.raw", required_size=MEM1_SIZE)
    src2 = _source(mem2_source, required_name="mem2.raw", required_size=MEM2_SIZE)
    if src1.resolve() == src2.resolve():
        raise ValueError("MEM1 and MEM2 cannot be the same source")
    srcstats = (src1.stat(), src2.stat())
    if srcstats[1].st_mtime_ns < srcstats[0].st_mtime_ns:
        raise ValueError("Dump ExRAM must be newer than Dump MRAM")
    if srcstats[1].st_mtime_ns - srcstats[0].st_mtime_ns > 300*10**9:
        raise ValueError("Dump MRAM/ExRAM are >5 minutes apart")
    manifest_path = private / MANIFEST_NAME
    prior = _read_manifest(manifest_path)
    keys = tuple(prior["checkpoints"].keys()) if prior else ()
    ordered = tuple(PHASES.keys())
    if (len(keys) >= len(ordered) or keys != ordered[:len(keys)]
            or checkpoint != ordered[len(keys)]):
        raise ValueError("Only sequential new B0 -> B1 -> B2 -> B3 -> B4 captures")
    if prior:
        last = prior["checkpoints"][keys[-1]]
        if (srcstats[0].st_mtime_ns <= last["source_mtime_ns"]["MEM1"]
                or srcstats[1].st_mtime_ns <= last["source_mtime_ns"]["MEM2"]):
            raise ValueError("Stale Dolphin dump: re-export both banks AFTER pausing")
    destinations = (
        private / f"{checkpoint}-MEM1.bin",
        private / f"{checkpoint}-MEM2.bin")
    if any(p.exists() or p.is_symlink() for p in destinations):
        raise ValueError("Preserved checkpoint already exists; never overwrite")
    tempmanifest = private / (MANIFEST_NAME + ".tmp")
    if tempmanifest.exists() or tempmanifest.is_symlink():
        raise ValueError("Incomplete prior manifest transaction")
    copied = []
    try:
        for source, dst in zip((src1,src2), destinations):
            with source.open("rb") as stream, dst.open("xb") as output:
                copied.append(dst)
                shutil.copyfileobj(stream, output, 1024*1024)
        for original, before, dst in zip((src1,src2),srcstats,destinations):
            after = original.stat()
            if (after.st_size != before.st_size or
                    after.st_mtime_ns != before.st_mtime_ns or
                    dst.stat().st_size != before.st_size):
                raise ValueError("Dump changed while being copied")
        # Source-backed scene+sport+mode+backlink check on COPIES only.
        with destinations[0].open("rb") as f1, destinations[1].open("rb") as f2:
            with mmap.mmap(f1.fileno(),0,access=mmap.ACCESS_READ) as mem1:
                with mmap.mmap(f2.fileno(),0,access=mmap.ACCESS_READ) as mem2:
                    checked = audit_pair(mem1,mem2)
        hashes = {
            "MEM1": _digest(destinations[0]),
            "MEM2": _digest(destinations[1]),
        }
        if prior and all(
                hashes[bank] == last["sha256"][bank]
                for bank in ("MEM1", "MEM2")):
            raise ValueError("Two banks identical to previous checkpoint; no independent new state")
        info = {
            "phase_operator_label": PHASES[checkpoint],
            "operator_reports_gui_paused": True,
            "operator_reports_observed_landed_shot": bool(shot_observed),
            "scene_source_chain_gated": (
                checked["source_chain"]["scene_backlink_matches_manager"]),
            "observed_game_mode": checked["conditions"]["game_mode"],
            "source_mtime_ns": {
                "MEM1": srcstats[0].st_mtime_ns,
                "MEM2": srcstats[1].st_mtime_ns,
            },
            "sha256": hashes,
            "native_sizes_valid": True,
            "same_emulator_frame_proven": False,
            "same_boot_proven": False,
            "physical_ball_xyz_verified": False,
            "shot_power_verified": False,
        }
        if prior:
            entry = prior
        else:
            entry = {
                "schema_version": SCHEMA_VERSION,
                "kind": "local-private-golf-paired-checkpoints",
                "session_id": uuid.uuid4().hex,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "checkpoints": {},
                "allowed_to_publish": False,
                "no_raw_memory_or_runtime_addresses_uploaded": True,
                "note": "Dolphin GUI-pause and phase labels are operator assertions only. "
                        "MEM1 and MEM2 dumps are sequential, not atomic. "
                        "A matching session ID does NOT prove one boot.",
            }
        entry["checkpoints"][checkpoint] = info
        with tempmanifest.open("x", encoding="utf-8") as target:
            json.dump(entry,target,indent=2,sort_keys=True,allow_nan=False)
            target.write("\n")
        os.replace(tempmanifest,manifest_path)
        return {
            "kind": "local-private-checkpoint-preservation-ack",
            "checkpoint": checkpoint,
            "phase_operator_label": PHASES[checkpoint],
            "saved_native_banks": 2,
            "scene_source_identity_gated": True,
            "previous_checkpoints_preserved": len(keys),
            "phase_labels_independently_verified": False,
            "same_frame_or_boot_proven": False,
            "ball_position_or_power_verified": False,
            "allowed_to_publish": False,
        }
    except Exception:
        # Never disturb the manifest or prior checkpoints on failed preflight.
        if tempmanifest.exists():
            tempmanifest.unlink()
        for file in copied:
            if file.exists():
                file.unlink()
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root",type=Path,required=True)
    parser.add_argument("--checkpoint",choices=PHASES.keys(),required=True)
    parser.add_argument("--paused-confirmed",action="store_true",required=True)
    parser.add_argument("--shot-observed",action="store_true")
    dump = Path(os.environ.get("APPDATA", "")) / "Dolphin Emulator" / "Dump"
    parser.add_argument("--mem1-source",type=Path,default=dump/"mem1.raw")
    parser.add_argument("--mem2-source",type=Path,default=dump/"mem2.raw")
    args = parser.parse_args(argv)
    try:
        ack = preserve_pair(
            mem1_source=args.mem1_source,
            mem2_source=args.mem2_source,
            private_root=args.private_root,
            checkpoint=args.checkpoint,
            paused_confirmed=args.paused_confirmed,
            shot_observed=args.shot_observed)
    except (OSError,ValueError,TypeError,KeyError,RuntimeError):
        print("Private paired checkpoint preservation REFUSED. "
              "Review source freshness, scene identity, sequence, pause and "
              "private destination; no raw memory was uploaded.",
              file=sys.stderr)
        return 1
    print(json.dumps(ack,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
