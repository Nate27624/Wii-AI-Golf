"""Offline synthetic tests; NO Dolphin, no savestate modifications, no live RPC."""
from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from dataclasses import dataclass

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "p0_forward_speed_sweep.py"
spec = importlib.util.spec_from_file_location("p0_forward_speed_sweep", MODULE)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


@dataclass(frozen=True)
class FakeProfile:
    name: str = "green-pre-start"
    slot: int = 2


class Tests(unittest.TestCase):
    def test_four_arms_have_exact_expected_speeds_and_hashes(self):
        arms = p.make_traces()  # actual repo original build_probe and serializer
        self.assertEqual([x["arm"] for x in arms],
                         ["F100", "F040", "F070", "F100R"])
        self.assertEqual([x["changed_numeric_fields"] for x in arms],
                         [0, 20, 20, 0])
        self.assertEqual(
            [round(x["requested_forward_speed_m_s"], 5) for x in arms],
            [3.5, 1.4, 2.45, 3.5])
        self.assertEqual(arms[0]["trace_sha256"], arms[-1]["trace_sha256"])
        self.assertEqual(len(set(x["trace_sha256"] for x in arms)), 3)

    def test_no_backwards_speed_distance_angle_or_a_changes(self):
        baseline, slow, mid, repeat = [x["samples"] for x in p.make_traces()]
        for i in range(89):
            self.assertEqual(baseline[i], repeat[i])
            for other in (slow, mid):
                self.assertEqual(other[i].hold_a, baseline[i].hold_a)
                self.assertEqual(other[i].direction, baseline[i].direction)
                self.assertEqual(other[i].distance_m, baseline[i].distance_m)
                self.assertEqual(other[i].return_speed_m_s, baseline[i].return_speed_m_s)
                self.assertEqual(other[i].angle_rad, baseline[i].angle_rad)
                if 27 <= i < 47:
                    self.assertNotEqual(other[i].speed_m_s, baseline[i].speed_m_s)
                else:
                    self.assertEqual(other[i].speed_m_s, baseline[i].speed_m_s)

    def test_canonical_source_digest_kept_for_baselines(self):
        from collect_outcome_transition import _build_v1_trace_and_digest
        baseline, digest = _build_v1_trace_and_digest(
            motion_scale=1.0, speed_scale=1.0, backswing_scale=1.0)
        arms = p.make_traces()
        self.assertEqual(len(baseline), 89)
        self.assertEqual(arms[0]["trace_sha256"], digest)
        self.assertEqual(arms[-1]["trace_sha256"], digest)

    def test_atomic_a45_samples_all_keep_77_12_mask(self):
        for variant in p.make_traces():
            trace = variant["samples"]
            self.assertEqual([s.hold_a for s in trace],
                             [True] * 77 + [False] * 12)
            self.assertEqual(len(trace), 89)

    def test_existing_registered_prestart_profile_qualifies(self):
        from wii_ai_golf.integration.savestates import StateCatalog, StateProfile
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "savestates.local.json"
            catalog = StateCatalog(source)
            catalog.add(StateProfile("green-pre-start", 2))
            catalog.add(StateProfile("different", 3))
            catalog.save()
            self.assertEqual(p.preflight_catalog(source).slot, 2)

    def test_catalog_missing_profile_fails_without_any_actions(self):
        from wii_ai_golf.integration.savestates import StateCatalog, StateProfile
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "savestates.local.json"
            catalog = StateCatalog(source)
            catalog.add(StateProfile("other", 2))
            catalog.save()
            with self.assertRaisesRegex(ValueError, "unknown savestate profile"):
                p.preflight_catalog(source)

    def test_no_save_and_same_dolphin_reuse_for_reset(self):
        calls = []

        class FakeRPC:
            def __init__(self, *, port, timeout_s=15):
                calls.append(("connect", port))
            def __enter__(self):
                return self
            def __exit__(self, *args):
                calls.append(("disconnect",))
            def close(self):
                calls.append(("close",))

        class StateManager:
            def __init__(self, rpc):
                calls.append(("state_manager",))
            def request_load(self, profile):
                calls.append(("load", profile.name, profile.slot))
                return {"action": "load_requested", "slot": profile.slot}
            def request_capture(self, *_args, **_kwargs):
                raise AssertionError("savestate may NEVER be saved")

        def run_menu(rpc, phases, *, remote):
            calls.append(("menu", remote))
            return [{"phase": item.label} for item in phases]

        with patch.object(p.AtomicA45SwingTraceClient, "require_capability",
                          side_effect=lambda _: calls.append(("atomic_capability",))):
            report = p.load_and_replay_intro(
                port=55355, profile=FakeProfile(),
                reader=lambda prompt: "RELOAD-STATE", connect=FakeRPC,
                healthy=lambda *_: FakeRPC(port=55355),
                state_manager=StateManager, menu=run_menu)
        self.assertEqual(len(report), 7)
        self.assertEqual([x for x in calls if x[0] == "load"],
                         [("load", "green-pre-start", 2)])
        self.assertEqual([x for x in calls if x[0] == "menu"], [("menu", 0)])
        self.assertLess(calls.index(("load", "green-pre-start", 2)),
                        calls.index(("menu", 0)))
        self.assertLess(calls.index(("atomic_capability",)),
                        calls.index(("menu", 0)))

    def test_reset_decline_has_no_rpc_calls(self):
        def forbidden(**kwargs):
            raise AssertionError("no connection allowed before operator consent")
        with self.assertRaisesRegex(p.RefuseTrial, "declined"):
            p.load_and_replay_intro(
                port=55355, profile=FakeProfile(),
                reader=lambda _: "q", connect=forbidden)

    def test_unverified_save_load_response_refused_before_menu(self):
        class FakeRPC:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        class FakeManager:
            def __init__(self, rpc):
                pass
            def request_load(self, profile):
                return {"action": "save_requested", "slot": profile.slot}

        with self.assertRaisesRegex(p.RefuseTrial, "load acknowledgement mismatch"):
            p.load_and_replay_intro(
                port=55355, profile=FakeProfile(),
                reader=lambda _: "RELOAD-STATE",
                connect=FakeRPC, state_manager=FakeManager,
                healthy=lambda *_: self.fail("healthy should not run"),
                menu=lambda *_args, **_kwargs: self.fail("menu should not run"))

    def test_observe_after_shot_can_keep_unknown_results(self):
        result = {"human_observation": {"visible_result_class_human": "transitioned"}}
        answers = iter(("101", "no", "yes", "left"))
        info = p.observe_after_shot(result, reader=lambda _: next(answers))
        self.assertEqual(info["human_power_pct"], 101)
        self.assertEqual(info["result_entered_while_visible_human"], "no")
        self.assertEqual(info["red_shot_human"], "yes")
        self.assertEqual(info["visible_curve_or_rotation_human"], "left")

    def test_private_ledger_exclusive_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "one.jsonl"
            p.append_private(path, {"training_approved": False}, first=True)
            with self.assertRaises(FileExistsError):
                p.append_private(path, {"training_approved": False}, first=True)
            p.append_private(path, {"training_approved": False}, first=False)
            rows = [json.loads(x) for x in path.read_text().splitlines()]
            self.assertEqual(len(rows), 2)
            self.assertFalse(rows[0]["training_approved"])

    def test_human_power_with_late_screen_not_landing_qualified(self):
        arm = p.make_traces()[0]
        human = {"initial_club_pose_human": "back", "contact_human": "yes",
                 "terminal_screen_seen_before_transition_human": False,
                 "visible_result_class_human": "transitioned",
                 "displayed_distance_source": "unseen_or_not_recorded"}
        notes = {"human_power_pct": 101, "human_power_confidence": "clear",
                 "result_entered_while_visible_human": "no",
                 "red_shot_human": "yes",
                 "visible_curve_or_rotation_human": "left"}
        observed = {"pose_detail_human": "partial-back",
                    "selected_club_human": "iron",
                    "club_change_human": "wedge-to-iron"}
        row = p.make_row(arm, {"human_observation": human},
                         observed, notes, scenario="speedtrial01",
                         bridge_sha="sha", catalog_slot=2, reset_index=0)
        self.assertTrue(row["power_comparison_eligible_human_only"])
        self.assertFalse(row["outcome_eligible_human_only"])
        self.assertFalse(row["score_carry_verified"])
        self.assertFalse(row["club_angular_velocity_game_verified"])
        self.assertFalse(row["training_approved"])

    def test_batch_runs_four_shots_three_resets_with_manual_approvals(self):
        events = []
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            bridge = temp / "atomic.py"
            bridge.write_text("synthetic no real emu", encoding="utf-8")

            class FakeRPC:
                def __init__(self, **_):
                    events.append("connect")
                def __enter__(self):
                    return self
                def __exit__(self, *_):
                    events.append("close")

            class AtomicClient:
                @staticmethod
                def require_capability(_):
                    events.append("capability")
                def __init__(self, _client, port):
                    self.port = port
                def run(self, samples):
                    events.append(("swing", p._digest(samples)))
                    return {"kind": "atomic_a45_swing",
                            "prehold_applied_frames": 45,
                            "applied_frames": 89}

            def fake_session(_rpc, **kwargs):
                # Exercise the real pre-A pose/club gates.
                fn = kwargs["input_fn"]
                fn("BEFORE pressing A, initial club position [back/center/forward/unknown]: ")
                # The injected custom swing function must be invoked once.
                kwargs["swing_fn"](_rpc)
                return {"human_observation": {
                    "initial_club_pose_human": "back",
                    "contact_human": "yes",
                    "terminal_screen_seen_before_transition_human": False,
                    "visible_result_class_human": "transitioned",
                    "displayed_distance_source": "unseen_or_not_recorded"}}

            def reply(prompt):
                if "RUN-FOUR" in prompt:
                    return "RUN-FOUR"
                if "RELOAD-STATE" in prompt:
                    return "RELOAD-STATE"
                if "initial club position" in prompt:
                    return "back"
                if "precise visual club position" in prompt:
                    return "partial-back"
                if "currently selected club" in prompt:
                    return "iron"
                if "manually change WEDGE" in prompt:
                    return "yes"
                if "Observed gauge" in prompt:
                    return "101"
                if "result G/M" in prompt:
                    return "no"
                if "marked RED" in prompt:
                    return "yes"
                if "curve or rotation" in prompt:
                    return "unknown"
                raise AssertionError(prompt)

            def fake_reload(**kwargs):
                events.append("reload")
                self.assertEqual(kwargs["profile"].slot, 2)
                self.assertEqual(kwargs["port"], 55355)
                self.assertEqual(kwargs["reader"]("Type RELOAD-STATE: "), "RELOAD-STATE")
                return [{"phase": x.label} for x in p.planned_menu_phases()]

            with patch.object(p, "FelkRPC", FakeRPC), \
                 patch.object(p, "AtomicA45SwingTraceClient", AtomicClient), \
                 patch.object(p, "run_session", side_effect=fake_session), \
                 patch.object(p, "release_buttons", side_effect=lambda *_args, **_kwargs: None), \
                 patch.object(p, "preflight_catalog", return_value=FakeProfile()), \
                 patch.object(p, "preflight_source", return_value=hashlib.sha256(
                     bridge.read_bytes()).hexdigest()), \
                 patch.object(p, "load_and_replay_intro", side_effect=fake_reload):
                rows = p.run_sweep(scenario="speedtrial01",
                                   catalog=temp / "catalog.json",
                                   bridge_source=bridge, reader=reply,
                                   data_dir=temp)
            self.assertEqual(len(rows), 4)
            self.assertEqual(events.count("reload"), 3)
            strokes = [v[1] for v in events if isinstance(v, tuple) and v[0] == "swing"]
            self.assertEqual(len(strokes), 4)
            self.assertEqual(strokes[0], strokes[3])
            self.assertEqual([row["human_power_pct"] for row in rows],
                             [101, 101, 101, 101])
            self.assertEqual([row["reset_before_shot"] for row in rows],
                             [False, True, True, True])
            records = list((temp / "forward-speed-speedtrial01.jsonl").read_text().splitlines())
            self.assertEqual(len(records), 4)
            self.assertTrue(all(not row["training_approved"] for row in rows))
            # Keep the synthetic catalog/source guards active on the second
            # invocation. An already-existing ledger must refuse before any
            # new user approval, reset, or controller call.
            before = len(events)
            with patch.object(p, "preflight_catalog", return_value=FakeProfile()), \
                 patch.object(p, "preflight_source", return_value=hashlib.sha256(
                     bridge.read_bytes()).hexdigest()):
                with self.assertRaisesRegex(p.RefuseTrial, "already exists"):
                    p.run_sweep(scenario="speedtrial01",
                                catalog=temp / "catalog.json",
                                bridge_source=bridge, reader=reply,
                                data_dir=temp)
            self.assertEqual(before, len(events))


if __name__ == "__main__":
    unittest.main()
