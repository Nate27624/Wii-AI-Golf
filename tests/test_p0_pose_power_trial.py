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
                "expected_pose_detail": "partial-back",
                "initial_pose_detail_human": "partial-back",
                "human_power_confidence": "clear",
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
        p.precheck([], p.setup("B1", "back", "same01", pose_detail="partial-back"), "hash")
        with self.assertRaises(p.RefuseTrial):
            p.precheck([self.row()], p.setup("B1", "back", "same01", pose_detail="partial-back"), "hash")

    def test_second_baseline_requires_valid_first(self):
        p.precheck([self.row()], p.setup("B2", "back", "same01", pose_detail="partial-back"), "hash")
        with self.assertRaises(p.RefuseTrial):
            p.precheck([self.row(power=None)], p.setup("B2", "back", "same01", pose_detail="partial-back"), "hash")

    def test_contrast_requires_two_stable_controls(self):
        p.precheck([self.row(), self.row(arm="B2", power=78)],
                   p.setup("X1", "back", "same01", pose_detail="partial-back"), "hash")
        with self.assertRaises(p.RefuseTrial):
            p.precheck([self.row(), self.row(arm="B2", power=85)],
                       p.setup("X1", "back", "same01", pose_detail="partial-back"), "hash")

    def test_pose_and_bridge_consistency(self):
        with self.assertRaises(p.RefuseTrial):
            p.precheck([self.row(pose="center")], p.setup("B2", "back", "same01", pose_detail="partial-back"), "hash")
        with self.assertRaises(p.RefuseTrial):
            p.precheck([self.row(sha="other")], p.setup("B2", "back", "same01", pose_detail="partial-back"), "hash")

    def test_club_and_aim_consistency(self):
        changed = self.row()
        changed["expected_club"] = "iron"
        with self.assertRaises(p.RefuseTrial):
            p.precheck([changed], p.setup("B2", "back", "same01", pose_detail="partial-back"), "hash")
        changed = self.row()
        changed["aim_marker"] = "left05"
        with self.assertRaises(p.RefuseTrial):
            p.precheck([changed], p.setup("B2", "back", "same01", pose_detail="partial-back"), "hash")

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
                            p.setup("B1", "back", "same01", pose_detail="partial-back"), bridge_sha="sha",
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

    def test_live_rejects_host_polled_a45_before_any_bridge_action(self):
        # On the failed Windows live attempt, a short A pulse was dispatched
        # and the host observed a >1-frame gap. Do not allow a retry of
        # that timing mode, regardless of launch/bridge availability.
        with patch.object(p, "assert_payload_contrast",
                          side_effect=AssertionError("never run")):
            with self.assertRaisesRegex(p.RefuseTrial, "requires the isolated atomic A45"):
                p.run_live(p.setup("B1", "back", "firstball02", pose_detail="partial-back"),
                           port=55355, bridge_source=Path("not-loaded.py"),
                           atomic=False)

    def test_atomic_runtime_capability_precedes_shot_session(self):
        # All bridge/game objects are FAKE. Verify source-file qualification
        # cannot substitute for an in-process capability response, and no
        # human prompt/shot can run before the runtime check.
        events = []
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            bridge = home / "fake-atomic.py"
            bridge.write_text("fake source, never executed", encoding="utf-8")
            bridge_sha = hashlib.sha256(bridge.read_bytes()).hexdigest()

            class FakeRPC:
                def __init__(self, *, port, timeout_s):
                    self.port = port
                def __enter__(self):
                    return self
                def __exit__(self, *_):
                    return False

            class FakeAtomicClient:
                @staticmethod
                def require_capability(rpc):
                    events.append("capability")
                    raise RuntimeError("RUNTIME_CAPABILITY_ABSENT")

            rpc_mod = types.ModuleType("wii_ai_golf.integration.rpc")
            rpc_mod.FelkRPC = FakeRPC
            atomic_mod = types.ModuleType("wii_ai_golf.integration.atomic_a45_client")
            atomic_mod.AtomicA45SwingTraceClient = FakeAtomicClient
            collector = types.ModuleType("collect_outcome_transition")

            def forbidden_session(*_args, **_kwargs):
                events.append("shot_session")
                raise AssertionError("no shot without in-process atomic capability")

            collector.run_session = forbidden_session
            modules = {
                "wii_ai_golf.integration.rpc": rpc_mod,
                "wii_ai_golf.integration.atomic_a45_client": atomic_mod,
                "collect_outcome_transition": collector,
            }
            with patch.dict(sys.modules, modules), \
                 patch.object(p, "assert_payload_contrast", return_value={"test": "fake"}), \
                 patch.object(p, "inspect_bridge", return_value=bridge_sha):
                with self.assertRaisesRegex(RuntimeError, "RUNTIME_CAPABILITY_ABSENT"):
                    p.run_live(p.setup("B1", "back", "firstball02", pose_detail="partial-back"),
                               port=55355, bridge_source=bridge,
                               atomic=True, data_dir=home,
                               reader=lambda _: (_ for _ in ()).throw(
                                   AssertionError("no prompt before capability")))
            self.assertEqual(events, ["capability"])
            self.assertFalse((home / "pose-power-firstball02.jsonl").exists())


    def test_power_over_100_is_retained(self):
        self.assertEqual(p.parse_power_observation("120"), (120.0, "clear"))
        self.assertEqual(p.parse_power_observation("120%"), (120.0, "clear"))
        self.assertEqual(p.parse_power_observation("120?"), (120.0, "uncertain"))
        self.assertEqual(p.parse_power_observation(">100"), (100.0, "lower_bound"))
        self.assertEqual(p.parse_power_observation("100+"), (100.0, "lower_bound"))
        self.assertEqual(p.parse_power_observation(""), (None, "unknown"))

    def test_no_promotion_of_uncertain_or_bound_power(self):
        row = self.row(power=120)
        self.assertTrue(p.eligible(row))
        for confidence in ("uncertain", "lower_bound", "unknown"):
            row["human_power_confidence"] = confidence
            self.assertFalse(p.eligible(row))
        row["human_power_confidence"] = "clear"
        row["human_power_pct"] = None
        self.assertFalse(p.eligible(row))

    def test_power_parser_rejects_nonfinite_and_invalid(self):
        for bad in ("NaN", "inf", "-1", "501", "more than 100", "120??"):
            with self.assertRaises(p.RefuseTrial):
                p.parse_power_observation(bad)

    def test_partial_back_pose_detail_checked_before_a(self):
        plan = p.setup("B1", "back", "firstball03",
                       pose_detail="partial-back")
        messages = []
        answers = iter(("back", "partial-back"))
        got = p.gated_pose_reader(plan, "BEFORE pressing A, initial club position [back/center/forward/unknown]: ",
                                  reader=lambda prompt: (messages.append(prompt), next(answers))[1],
                                  observed={})
        self.assertEqual(got, "back")
        self.assertEqual(len(messages), 2)

    def test_full_back_cannot_masquerade_as_partial(self):
        plan = p.setup("B1", "back", "firstball03",
                       pose_detail="partial-back")
        answers = iter(("back", "full-back"))
        with self.assertRaisesRegex(p.RefuseTrial, "Detailed starting club pose"):
            p.gated_pose_reader(
                plan, "BEFORE pressing A, initial club position [back/center/forward/unknown]: ",
                reader=lambda _: next(answers), observed={})

    def test_pose_detail_consistency_between_trials(self):
        control = self.row()
        control["expected_pose_detail"] = "full-back"
        control["initial_pose_detail_human"] = "full-back"
        with self.assertRaises(p.RefuseTrial):
            p.precheck([control], p.setup("B2", "back", "same01",
                                         pose_detail="partial-back"), "hash")

    def test_reduced_backswing_arm(self):
        self.assertEqual(p.setup("XLOW", "back", "firstball03",
                                 pose_detail="partial-back")["backswing_scale"], .8)
        self.assertIn("reduced_trace_sha256", self.payload())
        controls = [self.row(power=110), self.row(arm="B2", power=113)]
        p.precheck(controls, p.setup("XLOW", "back", "same01",
                                     pose_detail="partial-back"), "hash")

    def test_no_reuse_of_old_uncertain_b1_as_calibration_control(self):
        old = self.row(power=100, scenario="firstball02")
        old["expected_pose_detail"] = None
        old["initial_pose_detail_human"] = None
        old["human_power_confidence"] = None
        self.assertFalse(p.eligible(old))
        with self.assertRaises(p.RefuseTrial):
            p.precheck([old], p.setup("B2", "back", "firstball02",
                                     pose_detail="partial-back"), "hash")

    def test_summary_preserves_uncertain_above_hundred(self):
        human = {"initial_club_pose_human": "back", "contact_human": "yes",
                 "terminal_screen_seen_before_transition_human": True,
                 "finished_on_green_human": "no",
                 "displayed_distance_source": "offgreen_100ft_penalty"}
        request = {"trace_sha256": "trace", "generated_trace_frames": 89,
                   "backswing_scale": 1.0, "a_lead_requested_frames": 45}
        record = p.summarize(
            {"human_observation": human, "known_good_swing_request": request},
            p.setup("B1", "back", "firstball03", pose_detail="partial-back"),
            bridge_sha="bridge", payload={"baseline_trace_sha256": "trace",
                                           "contrast_trace_sha256": "high",
                                           "reduced_trace_sha256": "low"},
            observed_pose_detail="partial-back", power=(120, "uncertain"))
        self.assertEqual(record["human_power_pct"], 120)
        self.assertEqual(record["human_power_confidence"], "uncertain")
        self.assertFalse(p.eligible(record))
        self.assertEqual(record["initial_pose_detail_human"], "partial-back")
        self.assertFalse(record["training_approved"])

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
