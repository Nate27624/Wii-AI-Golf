"""Offline V1 observed-frame watched collector regressions, with synthetic RPC ONLY.

No Dolphin, ROM, game input, raw RAM or network access in these tests.
"""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import record_selected_ball_swing_v1_private as v1
from probe_swing import build_probe


class FakeRPC:
    def __init__(self):
        self.calls = []
        self.statuses = ["recording", "complete"]
    def call(self, name, params=None):
        self.calls.append((name, params))
        if name == "bridge.ping":
            return {"version": 3}
        if name == "golf.ball_watch.v1_provenance":
            return {
                "swing_protocol": 1, "legacy_neutral_swing_events": True,
                "a_lead_observed_frames_required_by_operator_baseline": 45,
                "a_lead_applied": False, "live_contact_verified": False,
                "training_allowed": False,
            }
        if name == "golf.ball_watch.status":
            return {"state": self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]}
        if name == "golf.ball_watch.drain":
            return {"status": {"state": "complete"}, "samples": [{}]}
        if name == "frame.get_count":
            return 100
        return {"state": "acknowledged"}


def samples():
    return build_probe("forward", follow_through_frames=30, a_setup_frames=12)


def fake_idle(rpc, *, frames):
    assert frames == 24
    rpc.calls.append(("test.idle_24_observed_frames", []))
    return {"observed_idle_frame_delta": 24}


def fake_hold(rpc, *, frames, remote):
    assert frames == 45 and remote == 0
    rpc.call("controller.set_wiimote_buttons", [0, {"A": True, "B": False}])
    return {"observed_frame_delta": 45, "a_button_only_requests": 1,
            "game_a_recognition_verified": False}


def fake_trace(rpc, values):
    assert len(values) == 89
    rpc.calls.append(("test.frozen_trace", [len(values)]))
    return {"state": "complete", "total_frames": 89, "applied_frames": 89, "id": 1}


class V1ObservedCaptureTests(unittest.TestCase):
    def test_dry_run_does_not_connect_or_send_input(self):
        with patch.object(v1, "FelkRPC", side_effect=AssertionError("must not connect")):
            self.assertEqual(v1.main([]), 0)

    def test_frozen_waveform_is_identical_to_reviewer_sha(self):
        self.assertEqual(v1.validate_frozen_trace(samples()),
                         "b63a1818ba5086c64b0fe7338236a498240e4be97bbd111809a772d783699891")

    def test_preflight_verifies_v1_and_never_calls_controller(self):
        rpc = FakeRPC()
        self.assertTrue(v1.preflight(rpc)["v1_provenance_checked"])
        self.assertTrue(all(not name.startswith("controller.") for name, _ in rpc.calls))

    def test_preflight_rejects_wrong_protocol_and_active_watch(self):
        rpc = FakeRPC()
        original = rpc.call
        def bad(name, args):
            if name == "golf.ball_watch.v1_provenance":
                result = original(name,args)
                result["swing_protocol"] = 2
                return result
            return original(name,args)
        rpc.call = bad
        with self.assertRaisesRegex(RuntimeError, "wrong bridge"):
            v1.preflight(rpc)
        self.assertTrue(all(not name.startswith("controller.") for name,_ in rpc.calls))
        rpc = FakeRPC()
        rpc.statuses = ["recording"]
        with self.assertRaisesRegex(RuntimeError, "wrong bridge"):
            v1.preflight(rpc)

    def test_controller_phases_45_observed_frames_and_single_button_request(self):
        rpc = FakeRPC()
        result = v1.capture_one(rpc, samples(), idle_wait=fake_idle,
                                hold_a=fake_hold, run_trace=fake_trace, sleep=lambda _:None)
        self.assertEqual(result["hold"]["observed_frame_delta"], 45)
        self.assertEqual(result["trace"]["applied_frames"], 89)
        names = [x[0] for x in rpc.calls]
        self.assertLess(names.index("test.idle_24_observed_frames"),
                        names.index("controller.set_wiimote_buttons"))
        self.assertLess(names.index("controller.set_wiimote_buttons"),
                        names.index("test.frozen_trace"))
        self.assertEqual([parameters for name,parameters in rpc.calls
                          if name == "golf.ball_watch.stage"],
                         [["a_prime"],["trace"],["posttrace"]])
        self.assertEqual(len([x for x in rpc.calls if x[0] == "test.frozen_trace"]),1)
        self.assertEqual(names.count("golf.ball_watch.drain"), 1)
        self.assertEqual(names.count("controller.set_wiimote_buttons"), 4)
        self.assertEqual([params for name,params in rpc.calls if name == "golf.ball_watch.arm"],
                         [[280,4]])

    def test_low_observed_lead_aborts_without_trace_and_releases(self):
        rpc=FakeRPC()
        def short_hold(rpc, *, frames, remote):
            return {"observed_frame_delta":44,"a_button_only_requests":1,
                    "game_a_recognition_verified":False}
        with self.assertRaisesRegex(RuntimeError, "45-frame A lead"):
            v1.capture_one(rpc, samples(), idle_wait=fake_idle,
                           hold_a=short_hold, run_trace=fake_trace, sleep=lambda _:None)
        self.assertNotIn("test.frozen_trace", [x[0] for x in rpc.calls])
        self.assertEqual(sum(x[0]=="controller.set_wiimote_buttons" for x in rpc.calls),3)

    def test_rpc_count_instead_of_observed_lead_is_refused(self):
        rpc=FakeRPC()
        def rpc_only(rpc, *, frames, remote):
            return {"button_only_requests":45,"observed_frame_delta":0,
                    "game_a_recognition_verified":False}
        with self.assertRaises(RuntimeError):
            v1.capture_one(rpc, samples(), idle_wait=fake_idle,
                           hold_a=rpc_only, run_trace=fake_trace, sleep=lambda _:None)

    def test_source_failure_refuses_partial_drain(self):
        rpc=FakeRPC()
        rpc.statuses=["source_gate_failed"]
        with self.assertRaisesRegex(RuntimeError,"failed closed"):
            v1.capture_one(rpc,samples(),idle_wait=fake_idle,hold_a=fake_hold,
                           run_trace=fake_trace,sleep=lambda _:None)
        self.assertFalse(any(n=="golf.ball_watch.drain" for n,_ in rpc.calls))

    def test_no_trace_completion_refuses_draining(self):
        rpc=FakeRPC()
        def partial(rpc,samples):
            return {"state":"running","total_frames":89,"applied_frames":70}
        with self.assertRaises(RuntimeError):
            v1.capture_one(rpc,samples(),idle_wait=fake_idle,hold_a=fake_hold,
                           run_trace=partial,sleep=lambda _:None)
        self.assertFalse(any(n=="golf.ball_watch.drain" for n,_ in rpc.calls))

    def test_bad_source_hash_cannot_pass_local_preflight(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/v1.WATCHED_BRIDGE_NAME
            p.write_text("fake source",encoding="utf-8")
            with self.assertRaises(ValueError):
                v1.verify_local_bridge(p)

    def test_wrong_target_before_attach_never_starts_game(self):
        with patch.object(v1,"FelkRPC",side_effect=AssertionError("RPC must not open")):
            with self.assertRaises(SystemExit):
                v1.main(["--send-live-swing"])

    def test_post_boot_handoff_exactly_once(self):
        from wii_ai_golf.integration.post_boot import post_boot_action_args
        out=post_boot_action_args("record_selected_ball_swing_v1_private.py",
                                  ["--send-live-swing"])
        self.assertEqual(out,["--attach-running","--send-live-swing"])
        with self.assertRaises(ValueError):
            post_boot_action_args("record_selected_ball_swing_v1_private.py",
                                  ["--attach-running","--send-live-swing"])


if __name__ == "__main__":
    unittest.main()
