"""Shared multi-agent laboratory. Only reviewed, typed workflow kinds can run.

All live experiments delegate to the canonical fresh Dolphin launcher.
A process success is NEVER interpreted as ball contact, score, or policy gain.
Local manifests contain provenance and execution state, not raw RAM dumps.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
from typing import Any, Callable, Iterator, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"
CATALOG = ROOT / "research" / "experiments.json"
DATA = ROOT.parent / "Wii-AI-Golf-Data" / "lab"
OWNER_IDS = frozenset({"S000", "S001", "S002", "S003", "S004", "S005"})
KINDS = {
    "tests_all": "offline", "tests_integration": "offline",
    "tests_evaluation": "offline", "tests_learning": "offline",
    "bridge_inspect": "offline", "compare": "offline",
    "motion_audit": "offline", "recover": "offline", "demo": "offline",
    "focused_trace": "offline",
    "swing": "live", "capture": "live", "unavailable": "planned",
}


@dataclass(frozen=True)
class Plan:
    experiment: dict[str, str]
    command: tuple[str, ...]
    live: bool

    def summary(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment["id"],
            "owner": self.experiment["owner"],
            "mode": self.experiment["mode"],
            "command": list(self.command),
            "fresh_canonical_boot": self.live,
            "game_outcome": "not_observed_or_verified",
        }


def load_catalog(path: Path = CATALOG) -> list[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported experiment catalog schema")
    entries = data.get("experiments")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Experiment registry must be a nonempty array")
    result = []
    seen: set[str] = set()
    for e in entries:
        if not isinstance(e, dict):
            raise ValueError("Registry entry must be an object")
        for field in ("id", "owner", "title", "description", "mode", "kind"):
            if not isinstance(e.get(field), str) or not e[field]:
                raise ValueError(f"Registry entry missing {field}")
        if not re.fullmatch(r"[a-z][a-z0-9_-]*\.[a-z][a-z0-9_-]*", e["id"]):
            raise ValueError(f"Unsafe or invalid experiment ID: {e['id']}")
        if e["id"] in seen:
            raise ValueError(f"Duplicate experiment ID: {e['id']}")
        if e["owner"] not in OWNER_IDS or KINDS.get(e["kind"]) != e["mode"]:
            raise ValueError(f"Unrecognized owner/kind/mode for {e['id']}")
        seen.add(e["id"])
        result.append({f: e[f] for f in
                       ("id", "owner", "title", "description", "mode", "kind")})
    return result


def get_experiment(identifier: str, *, catalog: Sequence[dict[str, str]]) -> dict[str, str]:
    for item in catalog:
        if item["id"] == identifier:
            return item
    raise ValueError(f"Unknown lab experiment: {identifier}. Run 'golf lab list'.")


def _child(script: str, *args: str, root: Path = ROOT, python: str = sys.executable) -> list[str]:
    # Whitelisted, non-configurable script filename. Never pass arbitrary
    # repo-relative script targets from a JSON catalog or GUI text field.
    allowed = {
        "run_golf_experiment.py", "launch_golf.py",
        "compare_outcome_runs.py", "audit_motion_candidates.py",
        "recover_outcome_capture.py", "analyze_focused_trace.py",
    }
    if script not in allowed or not (root / "scripts" / script).is_file():
        raise ValueError(f"Unsupported/missing reviewed script: {script}")
    return [python, str(root / "scripts" / script), *args]


def plan(
    identifier: str, *, catalog: Sequence[dict[str, str]] | None = None,
    root: Path = ROOT, python: str = sys.executable,
    input_path: str | None = None, second_input: str | None = None,
    output_path: str | None = None, a_prime: int = 0,
    follow_through: int = 30, contact: str | None = None,
    green: str | None = None, distance: str | None = None,
) -> Plan:
    entries = load_catalog(root / "research" / "experiments.json") if catalog is None else catalog
    exp = get_experiment(identifier, catalog=entries)
    kind = exp["kind"]
    if exp["mode"] == "planned":
        raise ValueError(f"{identifier} is planned, NOT runnable; {exp['description']}")
    if type(a_prime) is not int or not 0 <= a_prime <= 180:
        raise ValueError("--a-prime must be 0..180")
    if type(follow_through) is not int or not 0 <= follow_through <= 180:
        raise ValueError("--follow-through must be 0..180")
    if input_path is not None and kind not in {"compare", "recover", "motion_audit", "focused_trace"}:
        raise ValueError("--input is unsupported for this experiment")
    if second_input is not None and kind != "compare":
        raise ValueError("--second-input is only for evaluation.compare")
    if output_path is not None and kind not in {"compare", "motion_audit", "recover", "focused_trace"}:
        raise ValueError("--out is unsupported for this experiment")
    if kind == "recover":
        if contact not in {"yes", "no", "unknown"} or green not in {"yes", "no", "unknown"}:
            raise ValueError("evaluation.recover requires --contact and --green (yes/no/unknown)")
    elif any(x is not None for x in (contact, green, distance)):
        raise ValueError("--contact/--green/--distance are only for evaluation.recover")
    if a_prime != 0 and kind not in {"capture", "swing"}:
        raise ValueError("--a-prime is only for live capture/swing")
    if follow_through != 30 and kind != "swing":
        raise ValueError("--follow-through is only for integration.swing")

    def require(value: str | None, option: str) -> str:
        if not value:
            raise ValueError(f"{identifier} requires {option}")
        return value

    if kind.startswith("tests_"):
        patterns = {
            "tests_all": "test_*.py",
            "tests_integration": "test_integration_*.py",
            "tests_evaluation": "test_outcome_*.py",
            "tests_learning": "test_learning.py",
        }
        command = [python, "-m", "unittest", "discover", "-s", "tests",
                   "-p", patterns[kind], "-v"]
    elif kind == "bridge_inspect":
        # No subprocess RPC. The public CLI reads the generated file.
        command = [python, str(root / "scripts" / "golf.py"), "bridge", "inspect"]
    elif kind == "demo":
        command = [python, "-m", "wii_ai_golf.demo"]
    elif kind == "swing":
        command = _child("launch_golf.py", "--profile", "green-pre-start",
                         "--swing", "--preset", "forward",
                         "--a-setup-frames", "12",
                         "--a-prime-frames", str(a_prime),
                         "--follow-through-frames", str(follow_through),
                         root=root, python=python)
    elif kind == "capture":
        # Must not call collect_outcome_transition.py bare. Exactly one outer
        # launcher restores the named savestate and completes A/A+B/A menus.
        command = _child("run_golf_experiment.py", "--script",
                         "collect_outcome_transition.py", "--send-live", "--",
                         "--send-live-swing", "--a-prime-requests", str(a_prime),
                         "--pre-samples", "3", "--post-samples", "2",
                         "--settled-samples", "3", "--interval", "0.0",
                         root=root, python=python)
    elif kind == "compare":
        command = _child("compare_outcome_runs.py", "--input",
                         require(input_path, "--input"),
                         require(second_input, "--second-input"),
                         root=root, python=python)
        if output_path:
            command += ["--out", output_path]
    elif kind == "recover":
        command = _child("recover_outcome_capture.py",
                         "--raw", require(input_path, "--input"),
                         "--contact", str(contact), "--green", str(green),
                         root=root, python=python)
        if distance is not None:
            command += ["--distance", distance]
        if output_path is not None:
            command += ["--out", output_path]
    elif kind == "focused_trace":
        command = _child("analyze_focused_trace.py", "--input",
                         require(input_path, "--input"), root=root, python=python)
        if output_path:
            command += ["--output", output_path]
    elif kind == "motion_audit":
        command = _child("audit_motion_candidates.py", "--input",
                         require(input_path, "--input"), root=root, python=python)
        if output_path:
            command += ["--out", output_path]
    else:
        raise ValueError(f"Unsupported experiment kind: {kind}")
    return Plan(exp, tuple(command), exp["mode"] == "live")


def _git_revision(root: Path) -> str | None:
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              text=True, timeout=3, check=False)
        return proc.stdout.strip() if proc.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def local_bridge_fingerprint(root: Path) -> dict[str, str | None]:
    p = root.parent / "tools" / "mcp_bridge_swing.py"
    if not p.is_file():
        return {"sha256": None, "present": "false"}
    # Limited to a generated local script, not RAM/ROM bytes.
    return {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "present": "true"}


@contextmanager
def live_session_lock(data: Path = DATA) -> Iterator[None]:
    """Fail closed on a parallel lab live session, including stale lockfiles.

    Does not kill Dolphin or unlink someone else's lock. In case of a crash,
    an operator must inspect that no process is active before clearing it.
    """
    data.mkdir(parents=True, exist_ok=True)
    lock = data / "live-session.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError(f"Another lab live experiment may be active: {lock}. "
                         "Do not delete this while Dolphin is running.") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"pid": os.getpid(),
                       "utc": datetime.now(timezone.utc).isoformat()}, f)
        yield
    finally:
        # Only this process can remove this lock while its context is active.
        lock.unlink(missing_ok=True)


def history(data: Path = DATA, *, limit: int = 20) -> list[dict[str, Any]]:
    folder = data / "runs"
    if not folder.is_dir():
        return []
    result = []
    for file in sorted(folder.glob("*.json"), reverse=True)[:min(max(limit, 0), 100)]:
        try:
            row = json.loads(file.read_text(encoding="utf-8"))
            if isinstance(row, dict) and "run_id" in row:
                result.append(row)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return result


def execute(
    trial: Plan, *, allow_live: bool = False, data: Path = DATA, root: Path = ROOT,
    run_command: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    if trial.live and not allow_live:
        raise ValueError("LIVE experiment requires explicit --live approval; "
                         "Dolphin must be closed before starting")
    if not trial.live and allow_live:
        raise ValueError("--live is only for a registered live experiment")
    stamp = datetime.now(timezone.utc)
    run_id = stamp.strftime("%Y%m%dT%H%M%S%fZ-") + uuid.uuid4().hex[:8]
    folder = data / "runs"
    folder.mkdir(parents=True, exist_ok=True)
    file = folder / (run_id + ".json")
    record: dict[str, Any] = {
        "run_id": run_id, "utc_started": stamp.isoformat(),
        **trial.summary(), "execution_status": "running",
        "revision": _git_revision(root),
        "bridge_on_disk": local_bridge_fingerprint(root),
        "note": "Execution status is not a golf hit, landing, or score.",
    }

    def write() -> None:
        # Unique run id, local-only metadata (no raw RAM, no network).
        with file.open("w", encoding="utf-8") as stream:
            json.dump(record, stream, indent=2, sort_keys=True)
            stream.write("\n")

    def do_run() -> None:
        write()
        try:
            env = os.environ.copy()
            previous_path = env.get("PYTHONPATH")
            env["PYTHONPATH"] = os.pathsep.join(
                [str(root / "src"), str(root)] +
                ([previous_path] if previous_path else []))
            # Real Dolphin interaction must keep stdin/stdout connected to the
            # operator's terminal for ENTER and human observation prompts.
            # Offline tests can be safely captured and saved for GUI review.
            if trial.live:
                proc = run_command(list(trial.command), cwd=root, check=False, env=env)
            else:
                proc = run_command(list(trial.command), cwd=root, check=False,
                                   env=env, capture_output=True, text=True)
                log = folder / (run_id + ".log")
                text_out = str(getattr(proc, "stdout", "") or "")
                text_err = str(getattr(proc, "stderr", "") or "")
                with log.open("x", encoding="utf-8") as stream:
                    stream.write(("STDOUT\n" + text_out[:1_000_000] +
                                  "\nSTDERR\n" + text_err[:1_000_000] + "\n"))
                record["offline_log"] = str(log)
                if text_out:
                    print(text_out, end="" if text_out.endswith("\n") else "\n")
                if text_err:
                    print(text_err, end="" if text_err.endswith("\n") else "\n",
                          file=sys.stderr)
            record["exit_code"] = int(proc.returncode)
            record["execution_status"] = "finished" if proc.returncode == 0 else "failed"
        except OSError as exc:
            record["exit_code"] = None
            record["execution_status"] = "failed_to_start"
            record["launch_error"] = str(exc)
        finally:
            record["utc_finished"] = datetime.now(timezone.utc).isoformat()
            write()

    if trial.live:
        with live_session_lock(data):
            do_run()
    else:
        do_run()
    return record
