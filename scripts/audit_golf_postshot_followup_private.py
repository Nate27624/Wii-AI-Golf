"""PRIVATE optional SETTLED and RESULT extensions to S002 #180's PRE/POST.

No emulator, controller, screenshots, auto-shots, memory writes or network.
SETTLED is compared only while the ball visibly rests before reset.
RESULT can be after a reset; its banks are preserved/hash-checked but
never force-read as a live ball. Human UI distance is a PRIVATE label,
not a decoded RAM number or known game-unit conversion.
"""
from __future__ import annotations

from contextlib import ExitStack
import argparse
import hashlib
import json
import math
import mmap
import os
from pathlib import Path
import re
import stat
import struct
import sys

import audit_selected_ball_prepost_shot_private as prepost
import audit_golf_two_bank_roster_private as roster
import audit_selected_ball_start_link_private as selected

MANIFEST = "shot-followup-manifest-PRIVATE.json"
KIND = "local-private-golf-shot-followup"
PHASES = ("SETTLED", "RESULT")
SIZES = {"MEM1": roster.MEM1_SIZE, "MEM2": roster.MEM2_SIZE}
SHA = re.compile(r"^[0-9a-f]{64}$")
UNITS = {"feet", "yards", "meters"}


def validate_followup(doc):
    if (not isinstance(doc, dict) or doc.get("kind") != KIND
            or doc.get("schema_version") != 1
            or doc.get("operator_reports_same_dolphin_process") is not True
            or doc.get("operator_reports_same_one_shot") is not True):
        raise ValueError("Missing follow-up session provenance")
    phases = doc.get("checkpoints")
    if not isinstance(phases, dict) or not set(phases).issubset(PHASES):
        raise ValueError("Unrecognized follow-up phase")
    for phase, label in (("SETTLED", "settled_before_reset"),
                         ("RESULT", "visible_results_screen")):
        if phase not in phases:
            continue
        item = phases[phase]
        if (not isinstance(item, dict) or item.get("phase_operator_label") != label
                or item.get("operator_reports_gui_paused") is not True
                or item.get("operator_reports_both_exports_same_pause") is not True):
            raise ValueError("Pause/phase attestation absent")
        if phase == "SETTLED" and (
                item.get("operator_reports_ball_visibly_stopped") is not True
                or item.get("operator_reports_no_hole_or_reset_transition") is not True):
            raise ValueError("SETTLED requires visible stopped ball before reset")
        if phase == "RESULT" and item.get("operator_reports_result_screen_visible") is not True:
            raise ValueError("RESULT must be visibly observed")
        h = item.get("sha256")
        if (not isinstance(h, dict) or set(h) != set(SIZES)
                or any(not isinstance(h[k], str) or not SHA.fullmatch(h[k])
                       for k in SIZES)):
            raise ValueError("Missing/invalid native memory hashes")
    ui = doc.get("human_displayed_result_distance")
    if ui is not None:
        if not isinstance(ui, dict) or set(ui) != {"value", "unit"}:
            raise ValueError("Human UI label must contain number and visible unit")
        value = ui.get("value")
        if (type(value) not in (float, int) or not math.isfinite(value)
                or not 0 <= value <= 10000 or ui.get("unit") not in UNITS):
            raise ValueError("Invalid human UI result distance")
        if "RESULT" not in phases:
            raise ValueError("UI result label requires a RESULT checkpoint")
    if not phases:
        raise ValueError("At least one optional follow-up checkpoint is required")
    return doc


def _hash(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _f32(word):
    if type(word) is not int or not 0 <= word < 2**32:
        raise ValueError("Invalid source coordinate word")
    x = struct.unpack(">f", struct.pack(">I", word))[0]
    if not math.isfinite(x) or abs(x) > 1e6:
        raise ValueError("Nonfinite or unreasonable coordinate candidate")
    return x


def pin_words(read_u32):
    # FieldManager selected PIN getter source: field+0x44 -> obj+0x4C.
    field = read_u32(roster.GOLF_FIELD_STATIC)
    if roster._bank(field, 0x80) != "MEM2":
        raise ValueError("Field object not mapped in MEM2")
    pin_obj = read_u32(field + 0x44)
    if roster._bank(pin_obj, 0x50) != "MEM2":
        raise ValueError("Selected PIN object outside MEM2")
    vec = read_u32(pin_obj + 0x4C)
    # Source-backed RPGolMapObjBase constructor stores an inline +0x30
    # translation self-reference at +0x4C. In-bounds alone is insufficient:
    # an unrelated MEM2 vector must never be accepted as the current PIN.
    if vec != pin_obj + 0x30:
        raise ValueError("Selected PIN translation selfref mismatches source constructor")
    if roster._bank(vec, 12) != "MEM2":
        raise ValueError("Selected PIN translation outside MEM2")
    words = tuple(read_u32(vec + 4*i) for i in range(3))
    for word in words:
        _f32(word)
    return words


def _gap2(ball, pin):
    # Candidate component 0/2 geometry ONLY; not yards, true XZ or physics.
    return sum((_f32(ball[i]) - _f32(pin[i]))**2 for i in (0, 2))


def evaluate_settled(pre, moving, settled, ppre, pmoving, psettled):
    if any(x.get("source_gates") is not True for x in (pre, moving, settled)):
        raise ValueError("Source candidate missing")
    if (len({s["owner"] for s in (pre, moving, settled)}) != 1
            or len({s["slot"] for s in (pre, moving, settled)}) != 1
            or len({s["hole"] for s in (pre, moving, settled)}) != 1):
        raise ValueError("Selected actor identity or hole changed")
    # An identical PIN coordinate triplet cannot establish the same PIN
    # object: historical B0-to-flight comparisons observed pin pointer drift.
    # Require source-validated object identity in all three same-shot phases.
    pin_objects = tuple(s.get("pin_object") for s in (pre, moving, settled))
    if any(type(x) is not int for x in pin_objects) or len(set(pin_objects)) != 1:
        raise ValueError("Selected PIN object identity changed or unverified")
    start_stable = pre["start_words"] == moving["start_words"] == settled["start_words"]
    pin_stable = ppre == pmoving == psettled
    moved = pre["ball_words"] != settled["ball_words"]
    movement_to_post = pre["ball_words"] != moving["ball_words"]
    movement_post_to_settled = moving["ball_words"] != settled["ball_words"]
    relative = "unavailable"
    if start_stable and pin_stable and moved:
        start = _gap2(pre["ball_words"], ppre)
        end = _gap2(settled["ball_words"], psettled)
        threshold = max(1e-5, 1e-5*max(abs(start), abs(end)))
        relative = ("closer_candidate" if end < start - threshold else
                    "farther_candidate" if end > start + threshold else
                    "indistinguishable_candidate")
    return {
        "source_owner_slot_hole_stable_pre_moving_settled": True,
        "source_start_translation_unchanged": start_stable,
        "source_pin_translation_unchanged": pin_stable,
        "selected_ball_candidate_changed_pre_to_post": movement_to_post,
        "selected_ball_candidate_changed_post_to_settled": movement_post_to_settled,
        "selected_ball_candidate_changed_pre_to_settled": moved,
        "candidate_component_0_2_gap_to_pin_trend": relative,
        "game_coordinate_axes_or_distance_units_verified": False,
    }


def assemble(base, doc, settled=None, pins=None, result_bank_changed=None):
    validate_followup(doc)
    if base.get("source_gates_verified_both_phases") is not True:
        raise ValueError("Canonical PRE/POST audit not source verified")
    phases = doc["checkpoints"]
    if ("SETTLED" in phases) != (settled is not None):
        raise ValueError("Unvalidated SETTLED phase")
    if ("RESULT" in phases) != (result_bank_changed is not None):
        raise ValueError("Unvalidated RESULT phase")
    report = {
        "kind": "local_private_postshot_settled_result_shape",
        "schema_version": 1,
        "game_id": "RSPE01",
        "mode": 4,
        "revision": 1,
        "prepost_source_chain_verified": True,
        "settled_memory_pair_hash_verified": "SETTLED" in phases,
        "results_screen_memory_pair_hash_verified": "RESULT" in phases,
        "result_bank_change_observed": result_bank_changed,
        "operator_entered_ui_distance_private":
            doc.get("human_displayed_result_distance") is not None,
        "operator_entered_ui_distance_unit":
            doc["human_displayed_result_distance"]["unit"]
            if doc.get("human_displayed_result_distance") else None,
        "game_result_distance_decoded_from_ram": False,
        "result_screen_ball_pointer_validated": False,
        "world_ball_xyz_verified": False,
        "physical_distance_to_hole_verified": False,
        "game_unit_to_ui_unit_conversion_verified": False,
        "ball_velocity_verified": False,
        "swing_power_verified": False,
        "approved_for_model_training": False,
        "allowed_to_publish": False,
    }
    if settled is not None:
        if not isinstance(pins, tuple) or len(pins) != 3:
            raise ValueError("SETTLED source pin controls missing")
        report.update(evaluate_settled(*settled, *pins))
    else:
        report["candidate_component_0_2_gap_to_pin_trend"] = "unavailable"
    report["warning"] = (
        "A RESULTS screenshot's human-read distance is a private label, "
        "not an independently decoded RAM field. A settled source-selected "
        "ball/pin component-0/2 separation is only a candidate planar "
        "relation, NOT a calibrated distance in yards/feet or proven "
        "world-space coordinates. RESULT may occur after ball reset."
    )
    return report


def _approved_private_session(folder):
    root = selected.DATA_ROOT.resolve(strict=True)
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError("Private session unavailable")
    path = folder.resolve(strict=True)
    if path == root or not path.is_relative_to(root):
        raise ValueError("Session outside Data root")
    cur = folder
    while cur.resolve() != root:
        if cur.is_symlink():
            raise ValueError("Symlinked session ancestor")
        p = cur.parent
        if p == cur:
            raise ValueError("Session ancestry invalid")
        cur = p
    return path


def _file_identity(path, expected_size):
    """Identity of a regular native file, rejecting symlink path substitution."""
    info = os.stat(path, follow_symlinks=False)
    if (not stat.S_ISREG(info.st_mode) or info.st_size != expected_size
            or not info.st_ino):
        raise ValueError("Native private bank changed during offline analysis")
    return (info.st_dev, info.st_ino, info.st_size)


def _hash_open_file(fh):
    """Hash the SAME file descriptor used for mmap, not a reopened pathname."""
    digest = hashlib.sha256()
    fh.seek(0)
    for block in iter(lambda: fh.read(1 << 20), b""):
        digest.update(block)
    fh.seek(0)
    return digest.hexdigest()


def _recheck_phase(folder, phase, hashset, *, identities=None):
    """Post-map original SHA and path identity; never print private metadata."""
    for name in ("MEM1", "MEM2"):
        path = folder / f"{phase}-{name}.bin"
        before = _file_identity(path, SIZES[name])
        if identities is not None and identities[name] != before:
            raise ValueError("Native private bank changed during offline analysis")
        if _hash(path) != hashset[name]:
            raise ValueError("Native private bank changed during offline analysis")
        if _file_identity(path, SIZES[name]) != before:
            raise ValueError("Native private bank changed during offline analysis")


def _phase_read(folder, phase, hashset, *, source):
    identities = {}
    with ExitStack() as stack:
        banks, verified = [], {}
        for name in ("MEM1", "MEM2"):
            path = folder / f"{phase}-{name}.bin"
            identity = _file_identity(path, SIZES[name])
            digest = _hash(path)
            if digest != hashset[name]:
                raise ValueError("Native bank SHA does not match typed manifest")
            fh = stack.enter_context(path.open("rb"))
            actual = os.fstat(fh.fileno())
            # Both the object and its mapped bytes must be the original
            # SHA-attested bank. Re-hashing the pathname alone cannot
            # distinguish a rename/symlink race between hash and mmap.
            if ((actual.st_dev, actual.st_ino, actual.st_size) != identity
                    or _file_identity(path, SIZES[name]) != identity
                    or _hash_open_file(fh) != hashset[name]):
                raise ValueError("Native private bank changed during offline analysis")
            banks.append(stack.enter_context(mmap.mmap(
                fh.fileno(), 0, access=mmap.ACCESS_READ)))
            identities[name] = identity
            verified[name] = digest
        if source:
            reader = roster.TwoBankReader(*banks)
            sample = prepost.snapshot_candidate(reader.u32, reader.header())
            pin = pin_words(reader.u32)  # constructor selfref already validated
            sample["pin_object"] = reader.u32(sample["owner"][3] + 0x44)
            result = (sample, pin, verified)
        else:
            result = (None, None, verified)
    # Files and maps are closed; detect replacement, symlink substitution
    # or content changes that occurred during the source read.
    _recheck_phase(folder, phase, hashset, identities=identities)
    return result


def run_local(folder):
    folder = _approved_private_session(folder)
    base = prepost.run_local(folder)   # Fully hashes/validates canonical PRE+POST.
    follow_path = folder / MANIFEST
    if (follow_path.is_symlink() or not follow_path.is_file()
            or not 1 <= follow_path.stat().st_size <= 16384):
        raise ValueError("Missing/oversized follow-up manifest")
    with follow_path.open("r", encoding="utf-8") as f:
        doc = validate_followup(json.load(f))
    canonical = prepost._manifest(folder)
    settled, pins, result_changed = None, None, None
    if "SETTLED" in doc["checkpoints"]:
        # PRE/POST must also be source-readable in this original phase, no
        # re-labeling a results-screen state as a same-object settled ball.
        pre, ppre, _ = _phase_read(folder, "PRE", canonical["PRE"]["sha256"], source=True)
        post, ppost, _ = _phase_read(folder, "POST", canonical["POST"]["sha256"], source=True)
        rest, prest, _ = _phase_read(folder, "SETTLED", doc["checkpoints"]["SETTLED"]["sha256"], source=True)
        settled, pins = (pre, post, rest), (ppre, ppost, prest)
    if "RESULT" in doc["checkpoints"]:
        _, _, result_sha = _phase_read(folder, "RESULT", doc["checkpoints"]["RESULT"]["sha256"], source=False)
        result_changed = (result_sha["MEM2"] != canonical["POST"]["sha256"]["MEM2"]
                          or result_sha["MEM1"] != canonical["POST"]["sha256"]["MEM1"])
    report = assemble(base, doc, settled, pins, result_changed)
    # Preserve the original, operator-attested manifest contract for the
    # entire analysis, not just one phase's pre-mmap check. Recheck every
    # bank AFTER all source reads, including PRE/POST initially read by
    # the inherited audit and RESULT banks never decoded as live ball.
    if prepost._manifest(folder) != canonical:
        raise ValueError("Private PRE/POST manifest changed during analysis")
    if (follow_path.is_symlink() or not follow_path.is_file()
            or not 1 <= follow_path.stat().st_size <= 16384):
        raise ValueError("Private follow-up manifest changed during analysis")
    with follow_path.open("r", encoding="utf-8") as f:
        if validate_followup(json.load(f)) != doc:
            raise ValueError("Private follow-up manifest changed during analysis")
    for phase in ("PRE", "POST"):
        _recheck_phase(folder, phase, canonical[phase]["sha256"])
    for phase, metadata in doc["checkpoints"].items():
        _recheck_phase(folder, phase, metadata["sha256"])
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-root", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        report = run_local(args.private_root)
    except (OSError, ValueError, TypeError, KeyError, OverflowError, struct.error):
        print("Private post-shot SETTLED/RESULT audit FAILED CLOSED; "
              "review local pause, phase, source, and hashes. "
              "No raw RAM, coordinates or paths exposed.", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
