"""Synthetic and real-serializer discovery checks. No Dolphin/game/ROM access."""
from __future__ import annotations
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / "scripts" / "p0_input_discovery_sweep.py"
spec = importlib.util.spec_from_file_location("p0_input_discovery_sweep", PATH)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class Tests(unittest.TestCase):
    def test_eight_input_arms_exact_differences(self):
        rows = p.make_variants()  # actual S002 waveform and actual repo serializer
        self.assertEqual([v["arm"] for v in rows], [
            "CTRL", "ZERO", "BACK0", "FWD0", "PULSE2",
            "TINY", "REVFWD", "CTRL_R"])
        self.assertEqual([v["changed_numeric_fields"] for v in rows], [
            0, 35*4, 15*4, 20*4, 18*4, 35*3, 20, 0])
        self.assertEqual(len({v["trace_sha256"] for v in rows}), 7)
        self.assertEqual(rows[0]["trace_sha256"], rows[-1]["trace_sha256"])
        for row in rows:
            self.assertEqual(len(row["samples"]), 89)
            self.assertEqual([s.hold_a for s in row["samples"]],
                             [True]*77 + [False]*12)

    def test_zero_negative_control_schedules_no_swing_motion(self):
        base, zero, *_ = [r["samples"] for r in p.make_variants()]
        for i in range(89):
            self.assertEqual(zero[i].hold_a, base[i].hold_a)
            if 12 <= i < 47:
                self.assertEqual(zero[i].direction, (0., 0., 0.))
                self.assertEqual(zero[i].distance_m, 0)
                self.assertEqual(zero[i].speed_m_s, 0)
                self.assertEqual(zero[i].return_speed_m_s, 0)
            else:
                self.assertEqual(zero[i], base[i])

    def test_back0_forward0_and_pulse2_are_localized(self):
        base, _, back0, fwd0, pulse, *_ = [r["samples"] for r in p.make_variants()]
        for i in range(89):
            if i not in range(12, 27):
                self.assertEqual(back0[i], base[i])
            if i not in range(27, 47):
                self.assertEqual(fwd0[i], base[i])
            if i not in range(29, 47):
                self.assertEqual(pulse[i], base[i])
        self.assertEqual(pulse[27:29], base[27:29])
        self.assertTrue(all(x.speed_m_s == 0 for x in pulse[29:47]))

    def test_micro_and_reverse_still_preserve_hold_mask(self):
        base, _, _, _, _, tiny, reverse, _ = [r["samples"]
                                                for r in p.make_variants()]
        for i in range(89):
            self.assertEqual(tiny[i].hold_a, base[i].hold_a)
            self.assertEqual(reverse[i].hold_a, base[i].hold_a)
            self.assertEqual(reverse[i].angle_rad, base[i].angle_rad)
            if 12 <= i < 47:
                self.assertEqual(tiny[i].distance_m, .02)
                self.assertEqual(tiny[i].speed_m_s, .10)
                self.assertEqual(tiny[i].return_speed_m_s, .10)
            if 27 <= i < 47:
                self.assertEqual(reverse[i].direction, (0., -1., 0.))
                self.assertEqual(reverse[i].speed_m_s, base[i].speed_m_s)

    def test_manual_club_motion_observation_handles_unknown(self):
        self.assertEqual(p.ask_motion(lambda _: "yes"), "yes")
        self.assertEqual(p.ask_motion(lambda _: "unknown"), "unknown")
        self.assertEqual(p.ask_motion(lambda _: "blah"), "unknown")

    def test_no_contact_is_logged_as_negative_control(self):
        arm = p.make_variants()[1]
        human = {
            "initial_club_pose_human": "back",
            "contact_human": "no",
            "terminal_screen_seen_before_transition_human": False,
            "visible_result_class_human": "transitioned",
            "displayed_distance_source": "unseen_or_not_recorded"
        }
        obs = {"pose_detail_human": "partial-back",
               "selected_club_human": "iron",
               "club_change_human": "wedge-to-iron"}
        notes = {"human_power_pct": None,
                 "human_power_confidence": "unknown",
                 "result_entered_while_visible_human": "no",
                 "red_shot_human": "unknown",
                 "visible_curve_or_rotation_human": "unknown",
                 "club_motion_human": "no"}
        row = p.record_row(arm, {"human_observation": human}, obs, notes,
                           scenario="discover01", bridge_sha="abc",
                           savestate_slot=2, index=1)
        self.assertEqual(row["contact_human"], "no")
        self.assertEqual(row["club_motion_human"], "no")
        self.assertFalse(row["power_comparison_eligible_human_only"])
        self.assertFalse(row["outcome_eligible_human_only"])
        self.assertFalse(row["training_approved"])
        self.assertEqual(row["arm"], "ZERO")

    def test_eight_shots_seven_reloads_and_new_ledger_only(self):
        events = []
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            bridge = tmp/"atomic.py"
            bridge.write_text("mock source, never run", encoding="utf-8")
            source_hash = hashlib.sha256(bridge.read_bytes()).hexdigest()

            class FakeRPC:
                def __init__(self, **kw):
                    events.append(("connect", kw.get("port")))
                def __enter__(self):
                    return self
                def __exit__(self, *exc):
                    events.append(("close",))

            class FakeAtomic:
                @staticmethod
                def require_capability(_):
                    events.append(("capability",))
                def __init__(self, *a, **kw):
                    pass
                def run(self, samples):
                    events.append(("swing", p._digest(samples)))
                    return {"kind": "atomic_a45_swing", "applied_frames": 89,
                            "prehold_applied_frames": 45}

            def answer(prompt):
                if "RUN-EIGHT" in prompt:
                    return "RUN-EIGHT"
                if "initial club position" in prompt:
                    return "back"
                if "precise visual club position" in prompt:
                    return "partial-back"
                if "currently selected club" in prompt:
                    return "iron"
                if "manually change WEDGE" in prompt:
                    return "yes"
                if "Observed gauge" in prompt:
                    return ""
                if "result G/M" in prompt:
                    return "no"
                if "marked RED" in prompt:
                    return "unknown"
                if "curve or rotation" in prompt:
                    return "unknown"
                if "virtual club visibly MOVE" in prompt:
                    return "unknown"
                raise AssertionError("unhandled prompt: "+prompt)

            def fake_session(client, **kwargs):
                kwargs["input_fn"](
                    "BEFORE pressing A, initial club position [back/center/forward/unknown]: ")
                kwargs["swing_fn"](client)
                return {"human_observation": {
                    "initial_club_pose_human": "back",
                    "contact_human": "no",
                    "terminal_screen_seen_before_transition_human": False,
                    "visible_result_class_human": "transitioned",
                    "displayed_distance_source": "unseen_or_not_recorded"}}

            def reload(**kwargs):
                events.append(("reload",))
                self.assertEqual(kwargs["profile"].slot, 2)
                self.assertEqual(kwargs["reader"], answer)

            profile = type("Profile", (), {"name": "green-pre-start", "slot": 2})()
            with patch.object(p, "make_variants", wraps=p.make_variants), \
                 patch.object(p, "preflight_catalog", return_value=profile), \
                 patch.object(p, "preflight_source", return_value=source_hash), \
                 patch.object(p, "FelkRPC", FakeRPC), \
                 patch.object(p, "AtomicA45SwingTraceClient", FakeAtomic), \
                 patch.object(p, "run_session", side_effect=fake_session), \
                 patch.object(p, "release_buttons", side_effect=lambda *a, **kw: None), \
                 patch.object(p, "load_and_replay_intro", side_effect=reload):
                rows = p.run_discovery(scenario="discover01",
                                       catalog=tmp/"catalog",
                                       bridge_source=bridge,
                                       reader=answer, data_dir=tmp)
            self.assertEqual(len(rows), 8)
            self.assertEqual(events.count(("reload",)), 7)
            traces = [a[1] for a in events if a[0] == "swing"]
            self.assertEqual(len(traces), 8)
            self.assertEqual(traces[0], traces[-1])
            self.assertEqual(len((tmp/"input-discovery-discover01.jsonl").
                                 read_text().splitlines()), 8)
            self.assertTrue(all(r["training_approved"] is False for r in rows))
            # Fails before any approval or RPC once ledger exists.
            with patch.object(p, "preflight_catalog", return_value=profile), \
                 patch.object(p, "preflight_source", return_value=source_hash):
                with self.assertRaisesRegex(p.RefuseTrial, "already exists"):
                    p.run_discovery(scenario="discover01",
                                    catalog=tmp/"catalog",
                                    bridge_source=bridge, reader=answer,
                                    data_dir=tmp)

    def test_operator_can_cancel_before_first_swing(self):
        with tempfile.TemporaryDirectory() as td:
            tmp=Path(td)
            bridge=tmp/"bridge.py"
            bridge.write_text("mock", encoding="utf-8")
            profile=type("P", (), {"slot":2, "name":"green-pre-start"})()
            with patch.object(p, "preflight_catalog", return_value=profile), \
                 patch.object(p, "preflight_source", return_value="fake"), \
                 patch.object(p, "FelkRPC",
                              side_effect=AssertionError("no controller calls")):
                with self.assertRaisesRegex(p.RefuseTrial, "declined"):
                    p.run_discovery(scenario="discover02", catalog=tmp/"cat",
                                    bridge_source=bridge, reader=lambda _: "q",
                                    data_dir=tmp)

if __name__ == "__main__":
    unittest.main()
