#!/usr/bin/env python3
"""Agent-only validation of the safe game-memory variable catalog.

This never reads game RAM, modifies Dolphin, or uploads anything.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys

REGISTRY = Path(__file__).resolve().parents[1] / "research/memory-variables/registry.json"
STATUSES = {"unresolved", "source_candidate", "snapshot_correlated", "runtime_verified", "rejected"}
KINDS = {"pointer_chain", "pointer_chain_hypothesis", "unresolved"}
ID = re.compile(r"^[a-z][a-z0-9]*(?:[._][a-z0-9]+)*$")
HEX = re.compile(r"^0x[0-9A-Fa-f]{8}$")
# Session-specific RAM heap pointers must not become persistent training locators.
STATIC_REV1_ROOTS = {"0x804BF4D8", "0x804BF868"}
REQUIRED = ("id", "name", "role", "priority", "status", "datatype", "unit",
            "memory_locator", "evidence", "game", "phase_provenance",
            "limitations", "required_controls", "owner", "training",
            "review", "last_evidence_date")


# Same bounded, symlink-rejecting local metadata admission as historical #154.
# Allow growth beyond today's 35 entries, but never read unlimited user input.
MAX_REGISTRY_BYTES = 512_000


def load_registry(path: Path) -> object:
    """Read reviewed local JSON metadata only, bound to the checked file descriptor.

    This is a local file-integrity check, not proof of independent source/shot
    identity, and cannot prevent every possible concurrent file mutation.
    """
    before = path.lstat()  # Never silently follow an attacker-selected symlink.
    if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_REGISTRY_BYTES:
        raise ValueError("registry must be a bounded regular file")
    identity = (before.st_dev, before.st_ino, before.st_size)
    with path.open("rb") as source:
        opened = os.fstat(source.fileno())
        if (not stat.S_ISREG(opened.st_mode)
                or (opened.st_dev, opened.st_ino, opened.st_size) != identity):
            raise ValueError("registry opened file does not match checked path")
        content = source.read(MAX_REGISTRY_BYTES + 1)
        closed_over = os.fstat(source.fileno())
        after = path.lstat()
        if (len(content) != before.st_size
                or not stat.S_ISREG(closed_over.st_mode)
                or not stat.S_ISREG(after.st_mode)
                or (closed_over.st_dev, closed_over.st_ino, closed_over.st_size) != identity
                or (after.st_dev, after.st_ino, after.st_size) != identity
                or closed_over.st_mtime_ns != opened.st_mtime_ns):
            raise ValueError("registry changed during bounded read")
    return json.loads(content.decode("utf-8-sig"))


def validate_registry(payload: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["registry must be a JSON object"]
    if payload.get("schema_version") != 1 or payload.get("kind") != "wii-golf-memory-variable-registry":
        errors.append("unsupported registry schema_version or kind")
    records = payload.get("variables")
    if not isinstance(records, list) or not records:
        return errors + ["variables must be a nonempty array"]

    seen: set[str] = set()
    for i, variable in enumerate(records):
        prefix = f"variables[{i}]"
        if not isinstance(variable, dict):
            errors.append(f"{prefix}: expected object")
            continue
        for key in REQUIRED:
            if key not in variable:
                errors.append(f"{prefix}: missing {key}")
        name = variable.get("id")
        if not isinstance(name, str) or not ID.fullmatch(name):
            errors.append(f"{prefix}: invalid stable variable id")
        elif name in seen:
            errors.append(f"{prefix}: duplicate id {name}")
        else:
            seen.add(name)
        prefix = name if isinstance(name, str) else prefix
        if variable.get("status") not in STATUSES:
            errors.append(f"{prefix}: invalid status")
        for key in ("name", "role", "priority", "datatype", "unit", "owner", "phase_provenance", "last_evidence_date"):
            if not isinstance(variable.get(key), str) or not variable[key].strip():
                errors.append(f"{prefix}: {key} must be a nonempty string")
        game = variable.get("game")
        if not isinstance(game, dict) or game.get("game_id") != "RSPE01" or game.get("disc_revision") != 1 or game.get("endianness") != "big":
            errors.append(f"{prefix}: unsupported game revision or endian")
        locator = variable.get("memory_locator")
        if not isinstance(locator, dict):
            errors.append(f"{prefix}: missing memory locator")
        else:
            kind = locator.get("kind")
            if kind not in KINDS:
                errors.append(f"{prefix}: invalid locator kind")
            address = locator.get("root_static_address")
            if address is not None and (not isinstance(address, str) or address not in STATIC_REV1_ROOTS):
                errors.append(f"{prefix}: locator root is not a documented Rev1 static singleton")
            expr = locator.get("expression")
            if expr is not None and (not isinstance(expr, str) or not expr.strip()):
                errors.append(f"{prefix}: invalid expression")
            if kind == "unresolved" and (expr is not None or locator.get("steps") != []):
                errors.append(f"{prefix}: unresolved locator must have null expression and no fake steps")
            if kind == "pointer_chain" and (not isinstance(expr, str) or not isinstance(locator.get("steps"), list) or len(locator["steps"]) < 2):
                errors.append(f"{prefix}: pointer chain needs expression and typed steps")
            if kind != "unresolved" and isinstance(expr, str) and re.search(r"0x9[0-3][0-9A-Fa-f]{6}", expr):
                errors.append(f"{prefix}: dynamic MEM2 address must not be hardcoded")
        evidence = variable.get("evidence")
        if not isinstance(evidence, dict):
            errors.append(f"{prefix}: missing evidence object")
        else:
            urls = evidence.get("source_urls")
            if not isinstance(urls, list) or not urls or not all(isinstance(u, str) and u.startswith("https://") for u in urls):
                errors.append(f"{prefix}: source_urls required as HTTPS references")
            for key in ("capture_groups", "observed_behavior", "source_confidence"):
                item = evidence.get(key)
                if (key == "capture_groups" and not isinstance(item, list)) or (key != "capture_groups" and (not isinstance(item, str) or not item.strip())):
                    errors.append(f"{prefix}: missing evidence.{key}")
        for key in ("limitations", "required_controls"):
            if not isinstance(variable.get(key), list) or not variable[key] or not all(isinstance(v, str) and v.strip() for v in variable[key]):
                errors.append(f"{prefix}: nonempty {key} list required")
        training = variable.get("training")
        review = variable.get("review")
        if not isinstance(training, dict):
            errors.append(f"{prefix}: missing training gate")
            continue
        if not isinstance(training.get("approved"), bool) or any(not isinstance(training.get(k), bool) for k in ("eligible_as_input", "eligible_as_label")):
            errors.append(f"{prefix}: training eligibility must be explicit booleans")
            continue
        if training.get("eligible_as_input") and training.get("eligible_as_label"):
            errors.append(f"{prefix}: a field may not silently be both a causal input and future label")
        if not training["approved"] and (training.get("eligible_as_input") or training.get("eligible_as_label")):
            errors.append(f"{prefix}: unapproved fields cannot be training features or labels")
        if not isinstance(training.get("reason"), str) or not training["reason"].strip():
            errors.append(f"{prefix}: training reason required")
        if not isinstance(review, dict):
            errors.append(f"{prefix}: review object required")
            continue
        if training["approved"]:
            if variable.get("status") != "runtime_verified":
                errors.append(f"{prefix}: training approval requires runtime_verified")
            if variable.get("phase_provenance") != "verified_frame_aligned":
                errors.append(f"{prefix}: training approval requires verified_frame_aligned provenance")
            if not isinstance(review.get("reviewer"), str) or not review.get("reviewer"):
                errors.append(f"{prefix}: training approval requires S002 reviewer")
            if not isinstance(review.get("approved_at"), str) or not review.get("approved_at"):
                errors.append(f"{prefix}: training approval requires review timestamp")
            if not isinstance(training.get("validation_artifact"), str) or not training.get("validation_artifact", "").startswith("https://"):
                errors.append(f"{prefix}: training approval requires reviewed validation evidence URL")
            if not isinstance(training.get("dataset_contract"), str) or not training.get("dataset_contract", "").startswith("https://"):
                errors.append(f"{prefix}: training approval requires versioned dataset contract URL")
            if variable.get("unit") in ("unknown", "game_units_unverified"):
                errors.append(f"{prefix}: training approval cannot use unknown units")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    args = parser.parse_args(argv)
    try:
        payload = load_registry(args.registry)
    except (OSError, ValueError):
        # No local/private path or supplied JSON content in public CI diagnostics.
        print("INVALID: registry missing, linked, modified, oversized or malformed", file=sys.stderr)
        return 2
    errors = validate_registry(payload)
    if errors:
        for error in errors:
            print("INVALID:", error, file=sys.stderr)
        print(f"Registry rejected: {len(errors)} errors", file=sys.stderr)
        return 1
    approved = sum(bool(x["training"]["approved"]) for x in payload["variables"])
    print(f"VALID: {len(payload['variables'])} variables, {approved} training approved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
