"""Allowlisted execution-result publisher; never ships local captures or logs."""
from __future__ import annotations
import base64
import json
import os
import re
import urllib.error
import urllib.request

REPO = "Nate27624/Wii-AI-Golf"
BRANCH = "research-results"
RUN_ID = re.compile(r"^[0-9]{8}T[0-9]{12}Z-[a-f0-9]{8}$")
STUDY = re.compile(r"^[a-z][a-z0-9_.-]{0,79}$")
STATUSES = {"finished", "failed", "failed_to_start", "cancelled", "interrupted"}


def public_record(record: dict) -> dict:
    """Copy known-safe scalar fields ONLY. No file paths, commands, or RAM."""
    if not isinstance(record, dict):
        raise ValueError("Expected a run record")
    rid, study = record.get("run_id"), record.get("experiment_id")
    mode, status = record.get("mode"), record.get("execution_status")
    if not isinstance(rid, str) or not RUN_ID.fullmatch(rid):
        raise ValueError("Invalid run identifier")
    if not isinstance(study, str) or not STUDY.fullmatch(study):
        raise ValueError("Invalid study identifier")
    if mode not in ("offline", "live") or status not in STATUSES:
        raise ValueError("Unknown run mode/status")
    exit_code = record.get("exit_code")
    if exit_code is not None and (type(exit_code) is not int or not -65535 <= exit_code <= 65535):
        raise ValueError("Invalid exit code")
    return {"schema_version": 1, "run_id": rid, "experiment_id": study,
            "mode": mode, "execution_status": status, "exit_code": exit_code,
            "claim": "PROCESS_STATUS_ONLY_NOT_A_GOLF_SCORE"}


def _api(method: str, path: str, token: str, payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        "https://api.github.com/repos/" + REPO + path,
        data=body, method=method,
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "Content-Type": "application/json",
                 "User-Agent": "wii-ai-golf-research"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def publish_record(record: dict, *, token: str | None = None, api=_api) -> dict:
    clean = public_record(record)
    token = token if token is not None else os.environ.get("WII_GOLF_GITHUB_TOKEN", "")
    if not token:
        return {"status": "not_configured", "note": "Set WII_GOLF_GITHUB_TOKEN."}
    try:
        api("GET", "/git/ref/heads/" + BRANCH, token)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        main = api("GET", "/git/ref/heads/main", token)
        try:
            api("POST", "/git/refs", token,
                {"ref": "refs/heads/" + BRANCH, "sha": main["object"]["sha"]})
        except urllib.error.HTTPError as race:
            if race.code != 422:
                raise
    path = "/contents/research/auto-results/" + clean["run_id"] + ".json"
    content = base64.b64encode(
        (json.dumps(clean, sort_keys=True, indent=2) + "\n").encode()).decode("ascii")
    try:
        api("PUT", path, token, {
            "message": "results: sanitized execution " + clean["run_id"],
            "branch": BRANCH, "content": content})
    except urllib.error.HTTPError as exc:
        if exc.code == 422:
            return {"status": "already_published", "branch": BRANCH, "run_id": clean["run_id"]}
        raise
    return {"status": "published", "branch": BRANCH, "run_id": clean["run_id"]}
