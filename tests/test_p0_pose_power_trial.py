"""Offline tests: synthetic RPCs only. Never starts Dolphin or sends real game input."""
import importlib.util
from pathlib import Path
import tempfile
import json
import unittest
from unittest.mock import patch
from dataclasses import dataclass
import hashlib
import sys
import types

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "p0_pose_power_trial.py"
spec = importlib.util.spec_from_file_location("p0_pose_power_trial", MODULE)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


@dataclass(frozen=True)
class Sample:
    hold_a: bool
    direction: tuple
    distance_m: float
    speed_m_s: float
    return_speed_m_s: float
    angle_rad: float


def build(*, motion_scale, speed_scale, backswing_scale):
    assert motion_scale == 1.0 and speed_scale == 1.0
    trace = (
        [Sample(True, (0., 0., 0.), 0, 0, 0, 0)] * 12
        + [Sample(True, (0., -1., 0.), 0.25 * backswing_scale, 1.2, 1.2, 0)] * 15
        + [Sample(True, (0., 1., 0.), 0.6, 3.5, 2.0, 0)] * 20
        + [Sample(True, (0., 0., 0.), 0, 0, 0, 0)] * 30
        + [Sample(False, (0., 0., 0.), 0, 0, 0, 0)] * 12
    )
    raw = json.dumps([[s.hold_a, *s.direction, s.distance_m,
                      s.speed_m_s, s.return_speed_m_s, s.angle_rad]
                      for s in trace], separators=(",", ":"))
    return trace, hashlib.sha256(raw.encode()).hexdigest()


class SwingTraceClient:
    def __init__(self, rpc, port):
        self.rpc, self.port = rpc, port

    def submit(self, trace):
        return self.rpc.call("trace.submit_swing", [self.port,
            [[s.hold_a, *s.direction, s.distance_m, s.speed_m_s,
              s.return_speed_m_s, s.angle_rad] for s in trace]])


class TestPosePilot(unittest.TestCase):
    def payload(self):
        collection = types.ModuleType("collect_outcome_transition")
        collection._build_v1_trace_and_digest = build
        wii = types.ModuleType("wii_ai_golf")
        integration = types.ModuleType("wii_ai_golf.integration")
        swing = types.ModuleType("wii_ai_golf.integration.swing_client")
        swing.SwingTraceClient = SwingTraceClient
        with patch.dict(sys.modules, {
            "collect_outcome_transition": collection,
            "wii_ai_golf": wii,
            "wii_ai_golf.integration": integration,
            "wii_ai_golf.integration.swing_client": swing,
        }):
            return p.assert_payload_contrast()

    def row(self, arm="B1", pose="back", power=75, sha="hash", scenario="same01"):
        return {"arm": arm, "expected_pose": pose, "initial_pose_human": pose,
                "scenario": scenario, "wind": 0, "bridge_sha256": sha,
                "expected_club": "unknown", "aim_marker": "unknown",
                "contact_human": "yes", "terminal_seen_human": True,
                "human_power_pct": power}

    def test_single_parameter_payload(self):
        report = self.payload()
        self.assertEqual(report["samples"], 89)
        self.assertEqual(report["changed_fields"], 15)
        self.assertNotEqual(report["baseline_trace_sha256"], report["contrast_trace_sha256"])

    def test_plan_and_wind(self):
        x = p.setup("X1", "back", "firstball01")
        self.assertEqual(x["wind"], 0)
        self.assertEqual(x["a_lead"], 45)
        self.assertEqual(x["backswing_scale"], 1.2)

    def test_invalid_plan(self):
        for arm, pose, scenario in (("X2", "back", "firstball01"),
                                    ("B1", "unknown", "firstball01"),
                                    ("B1", "back", "X")):
            with self.assertRaises(p.RefuseTrial):
                p.setup(arm, pose, scenario)

    def test_pose_mismatch_blocks_before_swing(self):
        for got in ("center", "forward", "unknown"):
            with self.assertRaises(p.RefuseTrial):
                p.pose_gate("back", "BEFORE pressing A, initial club position [back/center/forward/unknown]: ",
                            lambda _: got)

    def test_pose_match_keeps_input(self):
        got = p.pose_gate("back", "BEFORE pressing A, initial club position [back/center/forward/unknown]: ",
                          lambda _: "back")
        self.assertEqual(got, "back")

    def test_other_prompts_are_passed(self):
        self.assertEqual(p.pose_gate("back", "Press ENTER to execute: ", lambda _: "q"), "q")

    def test_first_baseline_requires_empty_ledger(self):
        p.precheck([], p.setup("B1", "back", "same01"), "hash")
        with self.assertRaises(p.RefuseTrial):
            p.precheck([self.row()], p.setup("B1", "back", "same01"), "hash")

    def test_second_baseline_requires_valid_first(self):
        p.precheck([self.row()], p.setup("B2", "back", "same01"), "hash")
        with self.assertRaises(p.RefuseTrial):
            p.precheck([self.row(power=None)], p.setup("B2", "back", "same01"), "hash")

    def test_contrast_requires_two_stable_controls(self):
        p.precheck([self.row(), self.row(arm="B2", power=78)],
                   p.setup("X1", "back", "same01"), "hash")
        with self.assertRaises(p.RefuseTrial):
            p.precheck([self.row(), self.row(arm="B2", power=85)],
                       p.setup("X1", "back", "same01"), "hash")

    def test_pose_and_bridge_consistency(self):
        with self.assertRaises(p.RefuseTrial):
            p.precheck([self.row(pose="center")], p.setup("B2", "back", "same01"), "hash")
        with self.assertRaises(p.RefuseTrial):
            p.precheck([self.row(sha="other")], p.setup("B2", "back", "same01"), "hash")

    def test_club_and_aim_consistency(self):
        changed = self.row()
        changed["expected_club"] = "iron"
        with self.assertRaises(p.RefuseTrial):
            p.precheck([changed], p.setup("B2", "back", "same01"), "hash")
        changed = self.row()
        changed["aim_marker"] = "left05"
        with self.assertRaises(p.RefuseTrial):
            p.precheck([changed], p.setup("B2", "back", "same01"), "hash")

    def test_no_censored_carry_claim(self):
        human = {"initial_club_pose_human": "back", "contact_human": "yes",
                 "terminal_screen_seen_before_transition_human": True,
                 "displayed_power_percent_human": 76,
                 "finished_on_green_human": "no",
                 "displayed_distance_source": "offgreen_100ft_penalty"}
        request = {"trace_sha256": "hash", "generated_trace_frames": 89,
                   "backswing_scale": 1.0, "a_lead_requested_frames": 45}
        with patch.object(p, "datetime") as clock:
            clock.now.return_value.isoformat.return_value = "2026-11-10T00:00:00Z"
            r = p.summarize({"human_observation": human, "known_good_swing_request": request},
                            p.setup("B1", "back", "same01"), bridge_sha="sha",
                            payload={"baseline_trace_sha256": "hash", "contrast_trace_sha256": "other"})
        self.assertEqual(r["displayed_distance_source"], "offgreen_100ft_penalty")
        self.assertFalse(r["score_carry_verified"])
        self.assertFalse(r["power_game_verified"])
        self.assertFalse(r["training_approved"])

    def test_lost_contact_refuses(self):
        bad = self.row()
        bad["contact_human"] = "no"
        self.assertFalse(p.eligible(bad))
        bad["contact_human"] = "yes"
        bad["terminal_seen_human"] = False
        self.assertFalse(p.eligible(bad))

    def test_file_provenance_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "file.jsonl"
            self.assertEqual(p.read_rows(path), [])
            path.write_text(json.dumps(self.row()) + "\n", encoding="utf8")
            self.assertEqual(len(p.read_rows(path)), 1)
            path.write_text("{", encoding="utf8")
            with self.assertRaises(p.RefuseTrial):
                p.read_rows(path)

    def test_symlink_rejected(self):
        """Use a real link where permitted; simulate Windows WinError 1314 otherwise.

        Neither a normal Windows account nor CI is required to hold the
        SeCreateSymbolicLinkPrivilege; the refusal branch must still be tested.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "file.jsonl"
            target = Path(tmp) / "target"
            target.write_text("{}\n")
            try:
                path.symlink_to(target)
            except OSError as exc:
                if sys.platform != "win32" or getattr(exc, "winerror", None) != 1314:
                    raise
                # Native symlink creation was denied. Exercise the security
                # guard deterministically, without Developer Mode/admin rights.
                with patch.object(Path, "is_symlink", return_value=True) as is_link:
                    with self.assertRaisesRegex(p.RefuseTrial, "unsafe ledger target"):
                        p.read_rows(path)
                    is_link.assert_called_once_with()
            else:
                with self.assertRaisesRegex(p.RefuseTrial, "unsafe ledger target"):
                    p.read_rows(path)


if __name__ == "__main__":
    unittest.main()
