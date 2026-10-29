"""Single command-line entrypoint for Wii Sports golf research.

Commands:
    py scripts/research_cli.py test
    py scripts/research_cli.py v1 --a-lead 0
    py scripts/research_cli.py sync

Safe sequence: clean main fast-forward -> local experiment -> sanitized
result commit/push to the dedicated research/observations branch. Never
uploads ROMs, savestates, generated bridge code, RAW JSONL or RAM captures.
No Dolphin for offline tests. Live always requires --live.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from wii_ai_golf.lab.github_sync import sync_merged_main

DATA = ROOT.parent / "Wii-AI-Golf-Data"
OBS_BRANCH = "research/observations"
REPO_URL = "https://github.com/Nate27624/Wii-AI-Golf.git"
CAPTURES = DATA / "captures"
SAFE_LABELS = ("contact_human", "initial_club_pose_human",
               "finished_on_green_human", "displayed_distance_human",
               "displayed_unit_human", "shot_start_frame_before_controller_trace",
               "displayed_power_percent_human")
SAFE_TRACE = ("trace_sha256", "generated_trace_frames",
              "a_lead_requested_frames", "a_lead_observed_frame_delta",
              "a_lead_atomic_bridge_callback", "a_lead_bridge_button_dispatch_frames",
              "motion_scale", "speed_scale", "backswing_scale")
_ALLOWED = {"test", "v1"}


def _run(argv: list[str], *, cwd: Path = ROOT) -> int:
    return subprocess.run(argv, cwd=cwd, check=False).returncode


def _head() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                           text=True, capture_output=True, check=True, timeout=6)
        return r.stdout.strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "unavailable"


def _sha_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def v1_clean_boot_args(root: Path) -> list[str]:
    """Fail closed if the only vetted portable Dolphin launch is unavailable.

    This is an offline file-presence check. No Dolphin process, controller,
    savestate, network request or local configuration write is performed.
    The outer canonical runner retains sole control of fresh boot/intro.
    """
    clean = root.parent / "tools" / "FelkDolphin-Clean"
    executable = clean / "Dolphin.exe"
    user = clean / "User"
    config = root / "research" / "launch.local.json"
    catalog = root / "research" / "savestates.local.json"
    missing = []
    for label, present in (
        ("isolated clean Dolphin executable", executable.is_file()),
        ("portable.txt user-root selector", (clean / "portable.txt").is_file()),
        ("isolated clean Dolphin User directory", user.is_dir()),
        ("local launcher configuration", config.is_file()),
        ("local named-savestate catalog", catalog.is_file()),
    ):
        if not present:
            missing.append(label)
    if missing:
        raise RuntimeError(
            "P0 V1 safe launch blocked: missing " + ", ".join(missing) +
            ". Do not fall back to the old FelkDolphin installation; "
            "restore the clean portable setup and named checkpoint first."
        )
    return ["--dolphin", str(executable), "--dolphin-user", str(user),
            "--config", str(config), "--catalog", str(catalog)]



def _fresh_human_labels(start_time: datetime) -> dict:
    """Inspect one recent legacy candidate for LOCAL annotation only, never a shot join.

    File modification time does not authenticate run, action, game or terminal
    outcome. The legacy V1 path must not publish or train from this helper.
    """
    if not CAPTURES.is_dir():
        return {}
    options = [p for p in CAPTURES.glob("outcome-*-candidates.json")
               if p.is_file() and p.stat().st_mtime >= start_time.timestamp()]
    if len(options) != 1:
        return {"capture_status": "none_or_ambiguous"}
    path = options[0]
    try:
        if path.stat().st_size > 2_000_000:
            return {"capture_status": "summary_too_large"}
        content = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(content, dict) or not str(content.get("source", "")).startswith("live-emulator-"):
            return {"capture_status": "unexpected_summary_source"}
        human = content.get("human_observation") or {}
        swing = content.get("known_good_swing_request") or {}
        if not isinstance(human, dict) or not isinstance(swing, dict):
            return {"capture_status": "unexpected_summary_shape"}
        result = {"capture_status": "sanitized_human_annotation_only"}
        result["human"] = {k: human[k] for k in SAFE_LABELS if k in human
                           and (human[k] is None or type(human[k]) in (str, int, float, bool))}
        result["controller"] = {k: swing[k] for k in SAFE_TRACE if k in swing
                                and (swing[k] is None or type(swing[k]) in (str, int, float, bool))}
        observed = content.get("settled_screen_observation")
        # Never transmit arbitrary nested private collector content.
        result["settled_screen_observation"] = observed if type(observed) is str and observed in {
            "operator_confirmed_before_transition",
            "screen_had_already_transitioned_before_settled_samples",
            "already transitioned",
            "human_terminal_before_transition",
            "human_terminal_unseen_or_unknown",
        } else "unknown"
        return result
    except (OSError, ValueError, UnicodeError):
        return {"capture_status": "unreadable_summary"}



def _joined_visual_first(run_token: str, start: datetime, *,
                         a_lead: int, speed: float, backswing: float,
                         atomic_a45: bool = False) -> dict:
    """Read ONE exactly named child artifact; never infer identity via file mtime.

    All values are unverified human annotations/command metadata. No RAM or
    private file path is returned. Invalid/incomplete records fail closed.
    """
    invalid = {"capture_status": "visual_first_join_refused",
               "shot_dispatch_verified_by_collector": False}
    path = CAPTURES / ("outcome-" + run_token + "-candidates.json")
    try:
        if (not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z-[a-f0-9]{10}", run_token)
                or path.is_symlink() or not path.is_file()
                or not 0 < path.stat().st_size <= 2_000_000
                # On Windows temporary files may report coarser modification
                # times than UTC datetime.now(). The high-entropy exact run
                # token and semantic record checks remain the identity gate;
                # allow <=2 seconds timestamp rounding, not older captures.
                or path.stat().st_mtime < start.timestamp() - 2.0):
            return invalid
        item = json.loads(path.read_text(encoding="utf-8"))
        if type(item) is not dict or item.get("run_token") != run_token:
            return invalid
        if (item.get("source") != "human-terminal-result-no-ram-game-context-unverified"
                or item.get("outcome_collection_mode") != "human_terminal_first_no_ram"
                or item.get("raw_data_created") is not False
                or item.get("candidate_ranking") is not None):
            return invalid
        dispatch = item.get("swing_dispatch")
        swing = item.get("known_good_swing_request")
        human = item.get("human_observation")
        if not all(type(v) is dict for v in (dispatch, swing, human)):
            return invalid
        if (dispatch.get("state") != "complete"
                or type(swing.get("generated_trace_frames")) is not int
                or swing["generated_trace_frames"] != 89
                or type(dispatch.get("applied_frames")) is not int
                or dispatch["applied_frames"] != swing["generated_trace_frames"]
                or swing.get("preset") != "forward"
                or swing.get("motion_scale") != 1.0
                or swing.get("speed_scale") != speed
                or swing.get("backswing_scale") != backswing
                or swing.get("a_lead_requested_frames") != a_lead
                or type(swing.get("a_lead_observed_frame_delta")) is not int
                or swing["a_lead_observed_frame_delta"] < a_lead):
            return invalid
        if atomic_a45 and (
            swing.get("a_lead_atomic_bridge_callback") is not True
            or swing.get("a_lead_bridge_button_dispatch_frames") != 45
            or swing.get("a_button_only_prime_requests") != 0
            or dispatch.get("kind") != "atomic_a45_swing"
            or dispatch.get("prehold_applied_frames") != 45
            or dispatch.get("game_a_recognition_verified") is not False):
            return invalid
        digest = swing.get("trace_sha256")
        if type(digest) is not str or re.fullmatch(r"[a-f0-9]{64}", digest) is None:
            return invalid
        # An arbitrary 64-character digest does NOT bind an action to the
        # expected waveform. Rebuild the SAME pure requested trace used by
        # the child, then verify equality before accepting this result.
        from collect_outcome_transition import _build_v1_trace_and_digest
        expected_samples, expected_digest = _build_v1_trace_and_digest(
            motion_scale=1.0, speed_scale=speed, backswing_scale=backswing)
        if len(expected_samples) != 89 or digest != expected_digest:
            return invalid
        contact, green = human.get("contact_human"), human.get("finished_on_green_human")
        seen = human.get("terminal_screen_seen_before_transition_human")
        kind = human.get("visible_result_class_human")
        source = human.get("displayed_distance_source")
        value = human.get("displayed_distance_human")
        unit = human.get("displayed_unit_human")
        pose = human.get("initial_club_pose_human")
        power = human.get("displayed_power_percent_human")
        shot_start = human.get("shot_start_frame_before_controller_trace")
        if (type(pose) is not str or pose not in ("back", "center", "forward", "unknown")
                or type(shot_start) is not int or shot_start < 0
                or (power is not None and (type(power) not in (int, float)
                    or not math.isfinite(power) or not 0 <= power <= 100))
                or human.get("initial_club_pose_verified_by_memory") is not False
                or human.get("displayed_power_verified_by_memory") is not False
                or human.get("hitting_green_first_ball_context_human_confirmed") is not True
                or human.get("game_context_verified_by_memory") is not False):
            return invalid
        # Bridge callback ticks constrain the chronology of one action, but
        # are not guest physics frames or evidence of rendered ball contact.
        lead_start = swing.get("a_lead_start_frame")
        lead_last = swing.get("a_lead_last_observed_frame")
        trace_start = dispatch.get("start_frame")
        trace_completion = dispatch.get("completion_dispatch_frame")
        if any(type(v) is not int or v < 0 for v in
               (lead_start, lead_last, trace_start, trace_completion)):
            return invalid
        if (shot_start > lead_start
                or lead_last - lead_start != swing["a_lead_observed_frame_delta"]
                or trace_start <= lead_last
                or trace_completion != trace_start + 89):
            return invalid
        if atomic_a45:
            # The source-pinned atomic scheduler requires a contiguous
            # 45-tick prehold followed immediately by 89 movement ticks.
            # Independently cross-check both producer field representations.
            prehold_start = dispatch.get("prehold_start_frame")
            prehold_last = dispatch.get("last_prehold_frame")
            atomic_trace_start = dispatch.get("trace_start_frame")
            if (any(type(v) is not int or v < 0 for v in
                    (prehold_start, prehold_last, atomic_trace_start))
                    or prehold_start != lead_start + 1
                    or prehold_last != lead_last
                    or trace_start != lead_last + 1
                    or atomic_trace_start != trace_start):
                return invalid
        if (contact not in ("yes", "no", "unknown") or green not in ("yes", "no", "unknown")
                or not (type(seen) is bool or seen is None) or type(kind) is not str
                or kind not in ("green", "offgreen", "uncertain", "transitioned")
                or source not in ("offgreen_100ft_penalty", "offgreen_display_unverified",
                                  "ongreen_display_human", "unseen_or_not_recorded")
                or unit not in ("ft", "yd", "m", "unknown", "not-visible")
                or (value is not None and (type(value) not in (int, float)
                    or not math.isfinite(value) or not 0 <= value <= 100000))
                or human.get("game_distance_verified_by_memory") is not False):
            return invalid
        if ((kind == "green" and (green != "yes" or seen is not True))
                or (kind == "offgreen" and (green != "no" or seen is not True))
                or (kind in ("uncertain", "transitioned") and green != "unknown")
                or (kind == "transitioned" and seen is not False)
                or (kind == "uncertain" and seen is not None)
                or (source == "offgreen_100ft_penalty" and
                    not (kind == "offgreen" and value == 100.0 and unit == "ft"))
                or (source == "ongreen_display_human" and
                    not (kind == "green" and value is not None))
                or (source == "offgreen_display_unverified" and
                    not (kind == "offgreen" and value is not None))
                or (source == "unseen_or_not_recorded" and value is not None)
                or (kind in ("uncertain", "transitioned") and source != "unseen_or_not_recorded")
                or (kind == "green" and source not in
                    ("ongreen_display_human", "unseen_or_not_recorded"))
                or (kind == "offgreen" and source not in
                    ("offgreen_100ft_penalty", "offgreen_display_unverified",
                     "unseen_or_not_recorded"))
                or (value is None and unit != "not-visible")
                or (value is not None and unit == "not-visible")):
            return invalid
        screen = item.get("settled_screen_observation")
        if screen != ("human_terminal_before_transition" if seen is True
                      else "human_terminal_unseen_or_unknown"):
            return invalid
        informative = (contact == "yes" and seen is True
                       and kind in ("green", "offgreen"))
        return {
            "capture_status": "visual_first_joined",
            # The collector attests scheduled RPCs, not in-game ball contact.
            "informative_action_outcome_trial": informative,
            "hitting_green_first_ball_context_human_confirmed": True,
            "game_id_revision_mode_machine_verified": False,
            "shot_dispatch_verified_by_collector": True,
            "controller": {"trace_sha256": digest, "generated_trace_frames": 89,
                           "a_lead_requested_frames": a_lead,
                           "a_lead_observed_frame_delta": swing["a_lead_observed_frame_delta"],
                           "speed_scale": speed, "backswing_scale": backswing,
                           "motion_scale": 1.0,
                           **({"a_lead_atomic_bridge_callback": True,
                               "a_lead_bridge_button_dispatch_frames": 45}
                              if atomic_a45 else {})},
            "human": {"contact_human": contact, "finished_on_green_human": green,
                      "terminal_screen_seen_before_transition_human": seen,
                      "visible_result_class_human": kind,
                      "displayed_distance_source": source,
                      "displayed_distance_human": value,
                      "displayed_unit_human": unit,
                      "initial_club_pose_human": pose,
                      "shot_start_bridge_tick_before_trace": shot_start,
                      "displayed_power_percent_human": power},
            "settled_screen_observation": screen,
            "outcome_is_censored_penalty": source == "offgreen_100ft_penalty",
            # A human HUD number is never a measured physical carry distance.
            "numeric_distance_target_eligible": False,
            "train_approved": False,
            "verified_game_score": False,
            "physical_distance_verified": False,
        }
    except (OSError, ValueError, UnicodeError, TypeError, OverflowError):
        return invalid


def _fallback_human_observation(*, answer=input) -> dict:
    """Allow a human to save contact/pose when the normal collector lacks a summary.

    Never infer a hit from process status. A blank answer means unknown.
    """
    allowed = {"back", "center", "forward", "unknown"}
    pose = answer("Starting club pose [back/center/forward/unknown; blank=unknown]: ").strip().lower()
    if pose not in allowed:
        pose = "unknown"
    contact = answer("Did ball visibly make contact? [yes/no/unknown; blank=unknown]: ").strip().lower()
    if contact not in {"yes", "no", "unknown"}:
        contact = "unknown"
    timing = answer("Swing motion looked [early/late/on-time/unknown; blank=unknown]: ").strip().lower()
    if timing not in {"early", "late", "on-time", "unknown"}:
        timing = "unknown"
    return {"capture_status": "human_fallback_after_missing_collector_summary",
            "human": {"initial_club_pose_human": pose,
                      "contact_human": contact,
                      "motion_timing_human": timing},
            "verified_game_score": False,
            "warning": "Human memory only; collector did not publish a complete capture"}


def _missing_capture_needs_fallback(record: dict) -> bool:
    return record.get("capture_status") in (None, "none_or_ambiguous",
                                            "unreadable_summary",
                                            "unexpected_summary_shape",
                                            "unexpected_summary_source")



def _git(args: list[str], *, cwd: Path) -> str:
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                       text=True, check=False, timeout=60)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout or "Git command failed").strip()[:500])
    return p.stdout.strip()


def _public_observation_record(summary: dict) -> dict:
    """Re-authorize and project the ONLY two publishable record kinds.

    The CLI gate is not a trust boundary: direct Python callers can invoke
    publish_summary(). Never write the caller's dictionary to GitHub, even
    when it contains a plausible capture status or private extra fields.
    """
    if (type(summary) is not dict or type(summary.get("schema")) is not int
            or summary["schema"] != 1):
        raise ValueError("invalid observation schema")
    token, kind = summary.get("id"), summary.get("kind")
    if type(token) is not str or re.fullmatch(
            r"[0-9]{8}T[0-9]{6}Z-[a-f0-9]{10}", token) is None:
        raise ValueError("unsafe observation id")
    if kind not in ("test", "v1"):
        raise ValueError("unpublishable observation kind")
    if (type(summary.get("process_exit_code")) is not int
            or summary["process_exit_code"] != 0
            or summary.get("verified_game_score") is not False):
        raise ValueError("failed or unverified observation")
    try:
        start = datetime.fromisoformat(summary["started_utc"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid UTC timestamp") from exc
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("missing UTC offset")
    commit = summary.get("git_commit")
    if type(commit) is not str or not (
            commit == "unavailable"
            or re.fullmatch(r"[a-f0-9]{40}", commit)):
        raise ValueError("invalid Git commit identity")
    record = {
        "schema": 1, "id": token, "kind": kind,
        "started_utc": start.isoformat(), "git_commit": commit,
        "process_exit_code": 0, "verified_game_score": False,
    }
    if kind == "test":
        pattern = summary.get("test_pattern")
        if (summary.get("outcome") != "pass"
                or type(pattern) is not str or len(pattern) > 80
                or not re.fullmatch(r"[A-Za-z0-9_.?*-]+", pattern)):
            raise ValueError("invalid offline test status")
        record.update({"outcome": "pass", "test_pattern": pattern})
        return record

    # The present, exactly named no-RAM child report must STILL validate at
    # the publication boundary, not only when main() first joined it.
    if (summary.get("visual_first") is not True
            or summary.get("capture_status") != "visual_first_joined"
            or summary.get("shot_dispatch_verified_by_collector") is not True
            or summary.get("informative_action_outcome_trial") is not True
            or summary.get("hitting_green_first_ball_context_human_confirmed") is not True
            or summary.get("game_id_revision_mode_machine_verified") is not False
            or summary.get("numeric_distance_target_eligible") is not False
            or summary.get("train_approved") is not False
            or summary.get("physical_distance_verified") is not False
            or summary.get("bridge_source_changed_during_action") is True):
        raise ValueError("unjoined or ineligible V1 observation")
    controller = summary.get("controller")
    if type(controller) is not dict:
        raise ValueError("missing sanitized controller metadata")
    lead = summary.get("requested_a_lead_frames")
    speed = summary.get("requested_speed_scale")
    backswing = summary.get("requested_backswing_scale")
    atomic = controller.get("a_lead_atomic_bridge_callback") is True
    if (type(lead) is not int or lead != 45
            or type(speed) not in (float, int) or speed != 1.0
            or type(backswing) not in (float, int) or backswing not in (1.0, 1.2)
            or summary.get("requested_motion_scale") != 1.0):
        raise ValueError("unregistered V1 settings")
    joined = _joined_visual_first(token, start, a_lead=lead, speed=speed,
                                  backswing=backswing, atomic_a45=atomic)
    fields = (
        "capture_status", "shot_dispatch_verified_by_collector",
        "informative_action_outcome_trial",
        "hitting_green_first_ball_context_human_confirmed",
        "game_id_revision_mode_machine_verified", "controller", "human",
        "settled_screen_observation", "outcome_is_censored_penalty",
        "numeric_distance_target_eligible", "train_approved",
        "verified_game_score", "physical_distance_verified",
    )
    if (joined.get("capture_status") != "visual_first_joined"
            or joined.get("informative_action_outcome_trial") is not True
            or any(summary.get(key) != joined.get(key) for key in fields)):
        raise ValueError("V1 child identity or outcome changed before publication")
    # Source SHA is another independently checked parent precondition. An
    # externally constructed record must not skip the active bridge check.
    from wii_ai_golf.shared.bridge_provenance import inspect_bridge_file
    bridge = ROOT.parent / "tools" / (
        "mcp_bridge_swing_atomic_a45.py" if atomic
        else "mcp_bridge_swing_legacy_eval.py")
    bridge_identity = inspect_bridge_file(bridge)
    digest = summary.get("bridge_sha256")
    if (type(digest) is not str or re.fullmatch(r"[a-f0-9]{64}", digest) is None
            or bridge_identity.get("sha256") != digest
            or bridge_identity.get("revision") != (
                "V1-atomic-a45" if atomic else "V1-neutral-swing-calls")
            or (not atomic and bridge_identity.get("safe_for_isolated_legacy_copy") is not True)):
        raise ValueError("V1 bridge provenance unqualified")
    record.update({
        "visual_first": True, "bridge_sha256": digest,
        "requested_a_lead_frames": lead,
        "requested_motion_scale": 1.0,
        "requested_speed_scale": speed,
        "requested_backswing_scale": backswing,
        **{key: joined[key] for key in fields},
    })
    return record


def publish_summary(summary: dict) -> str:
    """Append a tiny allowlisted record to a separate branch, never main.

    Uses a temporary shallow clone to keep the operator's code working tree
    untouched. Refuses to create a new branch implicitly or force-push.
    """
    public = _public_observation_record(summary)  # validate BEFORE any Git/network operation
    with tempfile.TemporaryDirectory(prefix="wii-golf-observation-") as tmp:
        work = Path(tmp)
        # Reuse configured origin URL only after sync_merged_main verified it.
        url = _git(["remote", "get-url", "origin"], cwd=ROOT)
        from wii_ai_golf.lab.github_sync import _trusted_url
        if not _trusted_url(url):
            raise RuntimeError("Refusing publication to unapproved GitHub origin")
        _git(["clone", "--quiet", "--single-branch", "--branch", OBS_BRANCH,
              "--depth", "1", url, str(work / "repo")], cwd=work)
        repo = work / "repo"
        target = repo / "research" / "observations"
        target.mkdir(parents=True, exist_ok=True)
        name = public["id"] + ".json"
        file = target / name
        with file.open("x", encoding="utf-8") as out:
            json.dump(public, out, indent=2, sort_keys=True, allow_nan=False)
            out.write("\n")
        _git(["add", "--", str(file.relative_to(repo))], cwd=repo)
        _git(["-c", "user.name=Wii Golf Research Worker",
              "-c", "user.email=research-worker@users.noreply.github.com",
              "commit", "-m", "research: record sanitized " + public["kind"] + " result"], cwd=repo)
        # No force. Concurrent writers are never overwritten; operator can
        # retry publish from locally preserved summary if needed.
        _git(["push", "origin", "HEAD:" + OBS_BRANCH], cwd=repo)
    return "https://github.com/Nate27624/Wii-AI-Golf/tree/" + OBS_BRANCH + "/research/observations"



POWER_MAP_ID = "S003-POWER-MAP-10-V1"
# Five conditions twice, same first-ball scenario on independent fresh boots.
POWER_MAP_STUDY = ((1.0,1.0),(0.8,1.0),(1.0,1.2),(0.9,1.0),(1.0,0.8),
                   (1.0,1.0),(1.0,0.8),(0.9,1.0),(1.0,1.2),(0.8,1.0))


def power_map_commands() -> list[str]:
    return [("py scripts/research_cli.py v1 --live --a-lead 45 "
             f"--speed-scale {speed:.1f} --backswing-scale {back:.1f} "
             f"--study-id {POWER_MAP_ID} --trial-index {i}")
            for i, (speed, back) in enumerate(POWER_MAP_STUDY, 1)]


def show_power_map() -> None:
    print("S003 10-shot study: 10 fresh-boot FIRST-HOLE trials, NOT ten unique holes.")
    print("Close Dolphin between trials. Fixed V1 bridge, A lead 45, full forward travel.")
    print("For each: report contact, starting pose, visible power%, green and score.")
    print("Use 't' if the game transitions before the settled capture; 100ft off-green is a penalty.")
    for i, cmd in enumerate(power_map_commands(), 1):
        speed, back = POWER_MAP_STUDY[i - 1]
        print(f"\nTrial {i:02d}/10: speed {speed:.1f}x, backwards travel {back:.1f}x")
        print(cmd)
    print("Stop on unsafe state, failed button hold or unmatched bridge. No automatic multi-hole navigation.")



def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sync", help="Fast-forward clean trusted main; never start Dolphin")
    commands.add_parser("study", help="Print preregistered 10-shot plan; no Dolphin")
    t = commands.add_parser("test", help="Sync, run focused offline unittests, publish results")
    t.add_argument("--pattern", default="test_*.py")
    t.add_argument("--no-upload", action="store_true", help="Keep results local")
    v = commands.add_parser("v1", help="Sync, execute ONE isolated historic V1 shot, publish sanitized report")
    v.add_argument("--a-lead", type=int, default=0)
    v.add_argument("--backswing-scale", type=float, choices=(0.8, 1.0, 1.2), default=1.0,
                   help="Scale only backswing travel; all other motion/A unchanged")
    v.add_argument("--speed-scale", type=float, choices=(0.8, 0.9, 1.0, 1.1), default=1.0,
                   help="Change swing speed only; preserve club travel and A timing")
    v.add_argument("--motion-scale", type=float, choices=(0.6, 0.8, 1.0, 1.2), default=1.0,
                   help="Controlled motion calibration; 1.0 exactly reproduces verified baseline")
    v.add_argument("--study-id", choices=(POWER_MAP_ID,), default=None)
    v.add_argument("--trial-index", type=int, choices=range(1,11), default=None)
    v.add_argument("--live", action="store_true", help="Explicit consent to launch Dolphin")
    v.add_argument("--no-upload", action="store_true", help="Keep report local")
    v.add_argument("--atomic-a45", action="store_true",
                   help="Use separately prepared frame-callback A45 bridge; never replace legacy bridge")
    v.add_argument("--visual-first", action="store_true",
                   help="M1.5 one-shot terminal HUMAN result first; no RAM scoring")
    args = parser.parse_args(argv)
    try:
        report = sync_merged_main(ROOT)  # CLI workflow does not use retired GUI lockfiles
        print("GitHub main sync:", report.status, report.note, flush=True)
        if report.status not in ("updated", "up_to_date"):
            print("No experiment started; resolve sync blocker first.", file=sys.stderr)
            return 2
        if args.command == "sync":
            return 0
        if args.command == "study":
            show_power_map()
            return 0
        if args.command == "v1" and (not args.live or type(args.a_lead) is not int
                                     or not 0 <= args.a_lead <= 90):
            parser.error("v1 requires --live and --a-lead between 0 and 90")
        if args.command == "v1" and args.motion_scale != 1.0:
            parser.error("--motion-scale alters travel AND speeds; use --speed-scale for one-variable calibration")
        if args.command == "v1" and args.backswing_scale != 1.0 and args.speed_scale != 1.0:
            parser.error("change either --backswing-scale or --speed-scale, not both")
        if args.command == "v1":
            if args.atomic_a45 and (not args.visual_first or args.a_lead != 45):
                parser.error("--atomic-a45 requires --visual-first and --a-lead 45")
            # M1.5 is a preregistered B1/B2/X1 pilot, not a free-form sweep.
            # Refuse mismatched settings BEFORE touching the emulator or bridge.
            if args.visual_first and (args.a_lead != 45 or args.speed_scale != 1.0
                                      or args.backswing_scale not in (1.0, 1.2)):
                parser.error("M1.5 --visual-first requires --a-lead 45, "
                             "--speed-scale 1.0, and --backswing-scale 1.0 or 1.2")
            if args.visual_first and args.study_id is not None:
                parser.error("The M1.5 visual-first pilot is not the 10-shot power-map study")
            if (args.study_id is None) != (args.trial_index is None):
                parser.error("--study-id and --trial-index must be used together")
            if args.study_id:
                expected_speed, expected_back = POWER_MAP_STUDY[args.trial_index - 1]
                if (args.a_lead != 45 or args.motion_scale != 1.0
                    or args.speed_scale != expected_speed
                    or args.backswing_scale != expected_back):
                    parser.error("Trial settings differ from preregistered plan")
        begin = datetime.now(timezone.utc)
        run_token = begin.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:10]
        if args.command == "test":
            exit_code = _run([sys.executable, "-m", "unittest", "discover",
                              "-s", "tests", "-p", args.pattern, "-v"])
        else:
            bridge = ROOT.parent / "tools" / (
                "mcp_bridge_swing_atomic_a45.py" if args.atomic_a45
                else "mcp_bridge_swing_legacy_eval.py")
            expected_revision = "V1-atomic-a45" if args.atomic_a45 else "V1-neutral-swing-calls"
            from wii_ai_golf.shared.bridge_provenance import inspect_bridge_file
            identity = inspect_bridge_file(bridge)
            if identity["revision"] != expected_revision or (
                not args.atomic_a45 and not identity["safe_for_isolated_legacy_copy"]):
                raise RuntimeError("Requested isolated bridge revision missing; no Dolphin launch. "
                                   "For --atomic-a45 prepare via scripts/prepare_atomic_a45_bridge.py")
            # The bridge is a local source artifact, not authenticated in-process
            # code. Require a stable, typed preflight SHA for result-first shots.
            preflight_bridge_sha = identity.get("sha256")
            if args.visual_first and not (
                type(preflight_bridge_sha) is str and
                re.fullmatch(r"[a-f0-9]{64}", preflight_bridge_sha)
            ):
                raise RuntimeError("V1 bridge source SHA missing; no Dolphin launch")
            clean_boot = v1_clean_boot_args(ROOT)
            print("Close existing Dolphin before this ONE live trial.", flush=True)
            action = [sys.executable, str(ROOT / "scripts" / "run_golf_experiment.py"),
                      "--send-live", *clean_boot, "--bridge", str(bridge),
                      "--script", "collect_outcome_transition.py", "--",
                      "--send-live-swing", "--a-prime-requests", "0",
                      "--a-lead-frames", str(args.a_lead),
                      "--observe-start-pose", "--motion-scale", str(args.motion_scale),
                      "--speed-scale", str(args.speed_scale),
                      "--backswing-scale", str(args.backswing_scale),
                      "--ask-power"]
            if args.visual_first:
                action.extend(["--visual-first", "--run-token", run_token])
            if args.atomic_a45:
                action.append("--atomic-a45")
            exit_code = _run(action)
            bridge_source_changed = False
            if args.visual_first:
                # Inspect once more even if the child failed. A changed source
                # disqualifies the trial regardless of its outcome annotation.
                try:
                    post_identity = inspect_bridge_file(bridge)
                    bridge_source_changed = not (
                        post_identity.get("revision") == expected_revision
                        and (args.atomic_a45 or post_identity.get("safe_for_isolated_legacy_copy") is True)
                        and post_identity.get("sha256") == preflight_bridge_sha
                    )
                except (OSError, ValueError, UnicodeError, KeyError, TypeError):
                    bridge_source_changed = True
        summary = {"schema": 1,
                   "id": run_token,
                   "kind": args.command, "started_utc": begin.isoformat(),
                   "git_commit": _head(), "process_exit_code": exit_code,
                   "verified_game_score": False}
        if args.command == "test":
            summary["test_pattern"] = args.pattern
            summary["outcome"] = "pass" if exit_code == 0 else "fail"
        else:
            summary["requested_a_lead_frames"] = args.a_lead
            summary["requested_motion_scale"] = args.motion_scale
            summary["requested_speed_scale"] = args.speed_scale
            summary["requested_backswing_scale"] = args.backswing_scale
            if args.study_id:
                summary["study_id"] = args.study_id
                summary["trial_index"] = args.trial_index
                summary["trial_count"] = len(POWER_MAP_STUDY)
            summary["bridge_sha256"] = (
                preflight_bridge_sha if args.visual_first else _sha_file(bridge)
            )
            if args.visual_first:
                summary["visual_first"] = True
                if bridge_source_changed:
                    summary.update({
                        "bridge_source_changed_during_action": True,
                        "capture_status": "unqualified_bridge_source_change",
                        "shot_dispatch_verified_by_collector": False,
                        "informative_action_outcome_trial": False,
                        "train_approved": False,
                    })
                elif exit_code == 0:
                    summary.update(_joined_visual_first(
                        run_token, begin, a_lead=args.a_lead,
                        speed=args.speed_scale, backswing=args.backswing_scale,
                        atomic_a45=args.atomic_a45))
                else:
                    summary.update({"capture_status": "failed_or_cancelled_action",
                                    "shot_dispatch_verified_by_collector": False})
            elif exit_code == 0:
                summary.update(_fresh_human_labels(begin))
                if _missing_capture_needs_fallback(summary):
                    print("No unambiguous completed collector summary. "
                          "Recording HUMAN-only observation to avoid losing this trial.", flush=True)
                    summary.update(_fallback_human_observation())
            else:
                summary["capture_status"] = "failed_or_cancelled_action"
        if args.command == "v1" and not args.visual_first:
            # The old V1 child is discovered by file mtime, not an exact
            # run token, completed trace and witnessed terminal outcome.
            # Keep its optional sanitized human notes locally, but never
            # turn an apparent success or a fallback into published evidence.
            candidate_status = summary.get("capture_status", "missing")
            summary.update({
                "kind": "v1_attempt",
                "attempt_status": ("legacy_child_identity_unverified"
                                   if exit_code == 0
                                   else "failed_or_cancelled_action"),
                "capture_status": ("legacy_v1_local_only_unjoined"
                                   if exit_code == 0
                                   else "failed_or_cancelled_action"),
                "legacy_candidate_capture_status_unverified": candidate_status,
                "shot_dispatched": "unknown",
                "shot_dispatch_verified_by_collector": False,
                "trial_valid_for_action_outcome": False,
                "informative_action_outcome_trial": False,
                "train_approved": False,
                "physical_distance_verified": False,
                "numeric_distance_target_eligible": False,
            })
        private = DATA / "research-cli"
        private.mkdir(parents=True, exist_ok=True)
        dest = private / (summary["id"] + ".json")
        with dest.open("x", encoding="utf-8") as out:
            json.dump(summary, out, indent=2, sort_keys=True, allow_nan=False)
            out.write("\n")
        print("Local sanitized result:", dest, flush=True)
        # Never publish a failed/cancelled action, nor a visual result whose
        # unique child shot/trace token cannot be joined to this exact command.
        if args.command == "v1":
            if not args.visual_first:
                print("Legacy V1 annotation retained locally, not joined or "
                      "eligible for GitHub publication.", flush=True)
                return exit_code
            if (exit_code != 0
                    or summary.get("capture_status") != "visual_first_joined"
                    or summary.get("informative_action_outcome_trial") is not True):
                print("M1.5 outcome NOT eligible; no GitHub publication.", flush=True)
                return exit_code if exit_code != 0 else 2
        if not args.no_upload:
            try:
                url = publish_summary(summary)
                print("GitHub observation published:", url, flush=True)
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
                print("Upload NOT completed; local sanitized result remains saved:",
                      exc, file=sys.stderr, flush=True)
                return 3 if exit_code == 0 else exit_code
        return exit_code
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        print("Research command failed (no success claimed):", exc,
              file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
