"""Read-only Felk Dolphin startup-failure evidence triage (no game boot).

Classifies a local V2 bridge and its previously preserved V1 candidate,
compares only Python module *startup* AST structure and optionally parses
one Windows Application Error (Event ID 1000) XML export. Does not launch
Dolphin, load a savestate, perform controller/RPC/network operations, alter
a bridge, print local paths, publish logs, or infer swing physics.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import difflib
import hashlib
from pathlib import Path, PureWindowsPath
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.shared.bridge_provenance import (  # noqa: E402
    inspect_bridge_file,
)

BRIDGE_MAX = 2 * 1024 * 1024
EVENT_MAX = 256 * 1024
LOG_MAX = 1024 * 1024
DEFAULT_DOLPHIN_CRASH = 0xC0000005

def _check_file(p, *, limit, suffix):
    p = Path(p)
    if p.is_symlink() or not p.is_file() or p.suffix.lower() != suffix:
        raise ValueError("Required local input is missing, a symlink, or wrong type")
    if not 0 < p.stat().st_size <= limit:
        raise ValueError("Local input size outside bounded range")
    return p

def _module_startup(src):
    # Parsing never imports or executes the user's generated bridge.
    tree = ast.parse(src)
    # Top-level await is accepted by Felk generated script harnesses.
    compile(tree, "<offline-bridge-syntax>", "exec",
            flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
    groups = Counter()
    entries = []
    imports = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            groups["definitions"] += 1
            continue
        if (isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)):
            # The module docstring is not a startup action.
            groups["docstrings"] += 1
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            groups["imports"] += 1
            imports.append(ast.dump(node, include_attributes=False))
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            groups["assignments"] += 1
        elif isinstance(node, ast.Expr):
            groups["expressions"] += 1
        else:
            groups["control_or_other"] += 1
        # Digests are transient, never serialized or returned.
        entries.append(hashlib.sha256(ast.dump(node, include_attributes=False)
                                      .encode("utf-8")).digest())
    return groups, entries, set(imports)

def _bridge(path, desired):
    p = _check_file(path, limit=BRIDGE_MAX, suffix=".py")
    label = inspect_bridge_file(p)
    if label["revision"] != desired or label["autoload_marker"]:
        raise ValueError("Unexpected bridge revision or startup autoload marker")
    source = p.read_text(encoding="utf-8")
    groups, entries, imports = _module_startup(source)
    return {
        "revision": label["revision"],
        "marker_gate_passed": True,
        "python_syntax_gate_passed": True,
        "module_level_declaration_counts": dict(sorted(groups.items())),
    }, entries, imports

def _localname(value):
    return PureWindowsPath(str(value).replace("/", "\\")).name.lower()

def _module_bucket(text):
    name = _localname(text)
    if not name:
        return "unknown"
    if name == "dolphin.exe":
        return "dolphin_executable"
    if re.fullmatch(r"python\d*(?:\d+)?(?:_d)?\.dll", name):
        return "python_runtime"
    if name in ("ntdll.dll", "kernelbase.dll", "kernel32.dll", "ucrtbase.dll"):
        return "windows_runtime"
    if name in ("opengl32.dll", "d3d11.dll", "dxgi.dll", "vulkan-1.dll",
                "nvoglv64.dll", "atio6axx.dll", "igd10iumd64.dll"):
        return "graphics_stack"
    return "other_module"

def _read_event(path):
    if path is None:
        return {
            "application_error_event_supplied": False,
            "event_is_dolphin_app_error_1000": False,
            "event_exception_code_matches_exit_code": False,
            "faulting_module_bucket": "unknown",
        }
    p = _check_file(path, limit=EVENT_MAX, suffix=".xml")
    data = p.read_bytes()
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("Event XML with entities/DOCTYPE refused")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError("Cannot parse the selected Windows event") from exc
    def find(tag):
        # Windows Event XML often contains a default Microsoft namespace.
        return root.find(".//{*}" + tag)
    idnode = find("EventID")
    fields = {
        n.attrib.get("Name", "").lower(): (n.text or "").strip()
        for n in root.findall(".//{*}EventData/{*}Data")
        if n.attrib.get("Name")
    }
    app = fields.get("appname", "")
    module = fields.get("modulename", "")
    error = fields.get("exceptioncode", "")
    eid = idnode.text.strip() if idnode is not None and idnode.text else ""
    good = eid == "1000" and _localname(app) == "dolphin.exe"
    normalized = error.lower().replace("0x", "")
    correct = normalized == f"{DEFAULT_DOLPHIN_CRASH:08x}"
    return {
        "application_error_event_supplied": True,
        "event_is_dolphin_app_error_1000": good,
        "event_exception_code_matches_exit_code": good and correct,
        "access_violation_code_observed": good and correct,
        "faulting_module_bucket": _module_bucket(module) if good else "unknown",
        "faulting_module_specifically_identified": good and bool(module),
        "event_timestamp_present": (
            (node := find("TimeCreated")) is not None
            and bool(node.attrib.get("SystemTime"))
        ),
        "private_module_path_redacted": True,
    }

def _read_log(path):
    if path is None:
        return {"scripting_log_supplied": False}
    p = _check_file(path, limit=LOG_MAX, suffix=".txt")
    log = p.read_text(encoding="utf-8", errors="replace").lower()
    return {
        "scripting_log_supplied": True,
        "mentions_python_traceback": "traceback (most recent call last)" in log,
        "mentions_script_error": any(s in log for s in (
            "script error", "python error", "failed to load script")),
        "mentions_dolphin_access_violation": "c0000005" in log,
        "raw_log_suppressed": True,
    }

def triage_bridge_startup(current, legacy, *, event_xml=None, script_log=None):
    active, aentries, aimports = _bridge(current, "V2-neutral-button-only")
    prior, bentries, bimports = _bridge(legacy, "V1-neutral-swing-calls")
    matcher = difflib.SequenceMatcher(None, aentries, bentries, autojunk=False)
    edits = sum(max(i2-i1, j2-j1) for tag,i1,i2,j1,j2 in matcher.get_opcodes()
                if tag != "equal")
    event = _read_event(event_xml)
    return {
        "schema_version": 1,
        "kind": "local-only-felk-startup-crash-triage",
        "mode": "read-only-offline",
        "active": active,
        "legacy": prior,
        "bridge_source_inputs_distinct": Path(current).resolve() != Path(legacy).resolve(),
        "module_level_executable_structure_differs": edits > 0,
        "module_level_statement_edit_count": edits,
        "module_level_import_set_differs": aimports != bimports,
        "note": ("Module-level AST differences are diagnostics, NOT proof of "
                 "why native Dolphin exited. Function bodies, C++ plugins, "
                 "DLLs, emulator state and interpreter can still be responsible."),
        "windows_error_evidence": event,
        "scripting_log_evidence": _read_log(script_log),
        "prior_failed_boot_stage": "operator_reported_before_bridge_preflight",
        "process_exit_code_as_reported": "0xC0000005",
        "fresh_dolphin_started": False,
        "bridge_executed": False,
        "controller_input_sent": False,
        "savestate_loaded": False,
        "ball_movement_verified": False,
        "training_allowed": False,
        "allowed_to_publish": False,
        "recommended_next_step": (
            "If native crash evidence matches, inspect the identified module "
            "and scripting load boundary OFFLINE; do not rerun legacy shots. "
            "S001 must independently restore a known-good no-watch boot/ball "
            "contact before testing observer overhead, then S002 can verify "
            "selected-ball dynamic vector against fixed start."),
    }

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--current-bridge", type=Path, required=True)
    p.add_argument("--legacy-bridge", type=Path, required=True)
    p.add_argument("--event-xml", type=Path,
                   help="Optional PRIVATE XML of one Dolphin Application Error event 1000")
    p.add_argument("--scripting-log", type=Path,
                   help="Optional PRIVATE local Felk scripting log .txt")
    args = p.parse_args(argv)
    try:
        if (args.current_bridge.resolve(strict=True) ==
                args.legacy_bridge.resolve(strict=True)):
            raise ValueError("Current and legacy bridge paths cannot be the same")
        result = triage_bridge_startup(
            args.current_bridge, args.legacy_bridge,
            event_xml=args.event_xml, script_log=args.scripting_log)
    except (OSError, ValueError, UnicodeError, SyntaxError, RuntimeError):
        print("Offline crash triage REFUSED: check private input type/revision "
              "or source syntax; no paths or logs disclosed", file=sys.stderr)
        return 1
    import json
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
