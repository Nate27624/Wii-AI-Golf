"""S001/S002 V1 observed-frame A-lead selected-player watcher: DRAFT, not live approved.

CLI-only; consumes one ALREADY booted canonical green-pre-start session.
No startup, reset, savestate write, GitHub upload, waveform modification, or
controller action before an explicit SWING confirmation.

S001 owner review, source/regression, native read-latency and S000 privacy
approval REQUIRED before any actual live use. The positive-contact control
is historical V1 with >=45 OBSERVED Dolphin frames A-held, NOT 45 RPC calls.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

from wii_ai_golf.integration.rpc import FelkRPC
from wii_ai_golf.integration.swing_client import SwingTraceClient
from wii_ai_golf.integration.button_prime import release_buttons
from wii_ai_golf.shared.controller_timing import hold_a_for_observed_frames
from probe_swing import build_probe
from record_selected_ball_swing_private import (
    PRIVATE_ROOT, validate_frozen_trace, summarize, _private_output,
)

KNOWN_WATCHED_V1_SHA256 = (
    "465b6b02a9ae3833c65233b0d7a26fca79c613330eedf4eeb1de2a5d89ff886b"
)
WATCHED_BRIDGE_NAME = "mcp_bridge_swing_legacy_watch_eval.py"
LEAD_FRAMES = 45
IDLE_FRAMES = 24
WATCH_FRAMES = 280
SAMPLE_INTERVAL = 4
TRACE_FRAMES = 89


def _count(rpc: Any) -> int:
    value = rpc.call("frame.get_count", [])
    if type(value) is not int or value < 0:
        raise RuntimeError("invalid bridge tick count")
    return value


def passive_frame_control(
    rpc: Any, *, frames: int = IDLE_FRAMES,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Ensure idle is >=24 advancing bridge ticks with NO controller calls."""
    if frames != IDLE_FRAMES:
        raise ValueError("non-canonical idle control")
    first = _count(rpc)
    start = clock()
    for _ in range(600):
        last = _count(rpc)
        if last < first:
            raise RuntimeError("bridge frame counter moved backwards")
        if last - first >= frames:
            return {"requested_idle_frames": frames, "observed_idle_frame_delta": last - first}
        if clock() - start > 7.0:
            break
        sleep(0.012)
    raise TimeoutError("24 observed no-controller idle frames not reached")


def verify_local_bridge(path: Path) -> str:
    """Only allow this exact, separately generated, local source; read-only."""
    local_parent = (ROOT.parent / "tools").resolve(strict=True)
    if path.is_symlink():
        raise ValueError("symlinked bridge refused")
    actual = path.resolve(strict=True)
    if (actual.parent != local_parent or actual.name != WATCHED_BRIDGE_NAME
            or not actual.is_file() or actual.stat().st_size > 200_000):
        raise ValueError("watched V1 source must be exact isolated local bridge")
    digest = hashlib.sha256(actual.read_bytes()).hexdigest()
    if digest != KNOWN_WATCHED_V1_SHA256:
        raise ValueError("watched V1 generated SHA mismatch; do not send inputs")
    return digest


def preflight(rpc: Any) -> dict:
    """Check an already-running V1 watcher, before any controller or arming."""
    ping = rpc.call("bridge.ping", [])
    provenance = rpc.call("golf.ball_watch.v1_provenance", [])
    status = rpc.call("golf.ball_watch.status", [])
    if (not isinstance(ping, dict) or not isinstance(provenance, dict)
            or provenance.get("swing_protocol") != 1
            or provenance.get("legacy_neutral_swing_events") is not True
            or provenance.get("a_lead_observed_frames_required_by_operator_baseline") != LEAD_FRAMES
            or provenance.get("a_lead_applied") is not False
            or provenance.get("live_contact_verified") is not False
            or provenance.get("training_allowed") is not False
            or not isinstance(status, dict) or status.get("state") != "idle"):
        raise RuntimeError("wrong bridge/watch provenance; no controller input sent")
    return {"v1_provenance_checked": True, "watch_idle": True}


def capture_one(
    rpc: Any, samples: list, *,
    idle_wait: Callable = passive_frame_control,
    hold_a: Callable = hold_a_for_observed_frames,
    run_trace: Callable | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Run strictly one controlled V1 contact attempt. No ROM/GUI operations.

    Hook functions exist for deterministic offline tests only; the CLI does
    not accept injected hooks. A-only hold always uses 45 OBSERVED frames.
    """
    digest = validate_frozen_trace(samples)
    if run_trace is None:
        def run_trace(target, values):
            return SwingTraceClient(target, port=0).run(values)

    rpc.call("golf.ball_watch.arm", [WATCH_FRAMES, SAMPLE_INTERVAL])
    trace = None
    hold = None
    try:
        idle = idle_wait(rpc, frames=IDLE_FRAMES)
        if type(idle.get("observed_idle_frame_delta")) is not int or idle["observed_idle_frame_delta"] < IDLE_FRAMES:
            raise RuntimeError("idle negative control did not advance 24 ticks")
        rpc.call("golf.ball_watch.stage", ["a_prime"])
        hold = hold_a(rpc, frames=LEAD_FRAMES, remote=0)
        if (type(hold.get("observed_frame_delta")) is not int
                or hold["observed_frame_delta"] < LEAD_FRAMES
                or hold.get("a_button_only_requests") != 1
                or hold.get("game_a_recognition_verified") is not False):
            raise RuntimeError("real 45-frame A lead was not observed")
        rpc.call("golf.ball_watch.stage", ["trace"])
        trace = run_trace(rpc, samples)
        if (not isinstance(trace, dict) or trace.get("state") != "complete"
                or trace.get("total_frames") != TRACE_FRAMES
                or trace.get("applied_frames") != TRACE_FRAMES):
            raise RuntimeError("frozen 89-sample swing not completely dispatched")
        rpc.call("golf.ball_watch.stage", ["posttrace"])
    finally:
        release_buttons(rpc, remote=0)

    # No more input commands. Wait for the full bounded watch window; do not
    # drain partial state. Timeout is bounded even if emulation is paused.
    started = time.monotonic()
    for _ in range(600):
        state = rpc.call("golf.ball_watch.status", [])
        if not isinstance(state, dict):
            raise RuntimeError("invalid watched state")
        if state.get("state") == "complete":
            report = rpc.call("golf.ball_watch.drain", [])
            if (not isinstance(report, dict)
                    or report.get("status", {}).get("state") != "complete"
                    or not isinstance(report.get("samples"), list)):
                raise RuntimeError("incomplete private watched evidence")
            return {"trace": trace, "hold": hold, "idle": idle, "digest": digest,
                    "report": report}
        if state.get("state") not in ("armed", "recording"):
            raise RuntimeError("watcher source/performance failed closed")
        if time.monotonic() - started > 12:
            raise TimeoutError("complete watch window not reached")
        rpc.call("frame.get_count", [])
        sleep(0.018)
    raise TimeoutError("bounded watch polling exhausted")


def _private_report_file() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return _private_output(PRIVATE_ROOT / "captures" /
                           ("selected-ball-frame-watch-v1-" + stamp + "-PRIVATE.json"))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--attach-running", action="store_true",
                   help="Only canonical run_golf_experiment.py may inject this flag")
    p.add_argument("--send-live-swing", action="store_true",
                   help="Explicitly authorize one motion after human SWING confirmation")
    p.add_argument("--port", type=int, default=55355)
    a = p.parse_args(argv)
    if not a.send_live_swing:
        print(json.dumps({
            "kind": "review-only-V1-51-word-observed45-dry-run",
            "dolphin_or_rpc_contacted": False,
            "trace_frames": TRACE_FRAMES,
            "required_A_observed_frames": LEAD_FRAMES,
            "A_RPC_request_count_is_not_frame_count": True,
            "watch_frames": WATCH_FRAMES,
            "private_only": True, "training_allowed": False,
            "live_use_approved": False,
        }, indent=2))
        return 0
    if not a.attach_running:
        p.error("live action requires canonical post-boot attach authorization")
    if not 1 <= a.port <= 65535:
        p.error("invalid local port")
    try:
        verify_local_bridge(ROOT.parent / "tools" / WATCHED_BRIDGE_NAME)
        samples = build_probe("forward", follow_through_frames=30, a_setup_frames=12)
        validate_frozen_trace(samples)
        output = _private_report_file()
        with FelkRPC(port=a.port, timeout_s=15) as rpc:
            preflight(rpc)
            print("Read-only provenance passed. One V1 swing would be sent only if explicitly approved.")
            if input("At first stationary ball, type SWING to proceed (anything else cancels): ").strip() != "SWING":
                print("Cancelled. No controller input sent.")
                return 0
            result = capture_one(rpc, samples)
        answer = (input("Human visual contact? [yes/no/unknown]: ").strip().lower() or "unknown")
        if answer not in ("yes", "no", "unknown"):
            answer = "unknown"
        samples_private = result["report"]["samples"]
        safe = summarize(samples_private, human_ball_moved=answer,
                         watch_state=result["report"]["status"]["state"])
        safe["a_lead_observed_frames"] = result["hold"]["observed_frame_delta"]
        safe["idle_observed_frames"] = result["idle"]["observed_idle_frame_delta"]
        safe["trace_sha256"] = result["digest"]
        safe["swing_protocol_v1_source_checked"] = True
        raw = {
            "kind": "PRIVATE-UNVERIFIED-selected-ball-frame-watch",
            "utc": datetime.now(timezone.utc).isoformat(),
            "operator_observation": answer,
            "watch_status": result["report"]["status"],
            "bridge_trace_status": result["trace"],
            "controller_timing": {"idle": result["idle"], "observed_A_lead": result["hold"]},
            "safe_summary": safe,
            "PRIVATE_UNVERIFIED_NUMERIC_VECTORS": samples_private,
        }
        # Exclusive create; never publish numeric words or runtime pointers.
        with output.open("x", encoding="utf-8") as stream:
            json.dump(raw, stream, indent=2, allow_nan=False)
            stream.write("\n")
        print(json.dumps(safe, indent=2, sort_keys=True))
        print("Private selected-player memory saved locally. No GitHub upload.")
        return 0
    except (OSError, RuntimeError, ValueError, TypeError, TimeoutError, KeyboardInterrupt):
        # No paths or raw values in failure messages.
        print("V1 watched pilot refused/stopped; no data publicly released.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
