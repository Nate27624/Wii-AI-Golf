"""Manual UI workflow tests: no real Dolphin or GitHub calls."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from wii_ai_golf.golf_collection import (
    _GIT_REMOTE, collect, human_result, make_run_id, persist_local,
    session_steps, summarize,
)


class GuidedCollectionTests(unittest.TestCase):
    def test_default_ten_shots_and_boundaries(self):
        steps = session_steps()
        self.assertEqual([x["shot_index"] for x in steps], list(range(1, 11)))
        self.assertEqual([x["checkpoint"] for x in steps], [None] * 10)
        self.assertEqual([x["shot_index"] for x in session_steps(start_shot=9, shots=2)], [9, 10])
        with self.assertRaises(ValueError):
            session_steps(start_shot=9, shots=3)

    def test_plan_shows_observed_checkpoints_and_split(self):
        plan = {
            "schema_version": 1, "seed": 7,
            "attempts": [
                {"attempt": 4, "challenge": "hitting-green", "shot_index": 3,
                 "checkpoint": "green-three", "scenario": "pin-left", "variant": "left", "split": "train"},
                {"attempt": 5, "challenge": "hitting-green", "shot_index": 7,
                 "checkpoint": "green-seven", "scenario": "pin-right", "variant": "right", "split": "holdout"},
            ],
        }
        steps = session_steps(shots=2, plan=plan)
        self.assertEqual(steps[0]["checkpoint"], "green-three")
        self.assertEqual(steps[1]["split"], "holdout")
        self.assertEqual(steps[1]["shot_index"], 7)
        with self.assertRaises(ValueError):
            session_steps(shots=2, plan={"schema_version": 1, "attempts": []})

    def test_explicit_summary_whitelist_blocks_raw_data(self):
        before = {
            "captured_utc": "2026-10-24T07:00:00+00:00", "frame_start": 10, "frame_end": 18,
            "controller": {"buttons": {"A": False}, "acceleration_m_s2": [0, 0, 0],
                           "angular_velocity_rad_s": [0, 0, 0]},
            "memory": [{"hex": "1234PRIVATE"}], "screenshot": {"path": "C:/private/file.png"},
        }
        spatial = {
            "game_id": "RSPE01", "disc_revision": 1, "mode_label": "GAMEMODE_TR_NEARPIN",
            "current_hole_raw": "0x00000001",
            "map_objects": {"current_pin_obj_ptr": {
                "object_pointer": "0x924B8214",
                "inline_translation_offset_0x30": {"xyz_raw": [210.1, -7, -350.5]},
                "inline_scale_offset_0x3c": {"xyz_raw": [1, 1, 1]},
            }},
            "relative_geometry_unverified": {"start_to_pin": {"distance_3d": 210}},
        }
        result = summarize(before, spatial)
        serialized = json.dumps(result)
        self.assertNotIn("PRIVATE", serialized)
        self.assertNotIn("C:/private", serialized)
        self.assertNotIn("0x924B8214", serialized)
        self.assertEqual(result["objects"]["current_pin_obj_ptr"]["translation_xyz_unverified"][0], 210.1)

    def test_human_score_optional_and_actual_display_unit(self):
        answers = iter(["y", "green", "12.5", "ft"])
        res = human_result(lambda prompt: next(answers))
        self.assertTrue(res["ball_struck_human_observed"])
        self.assertEqual(res["score_unit_as_displayed"], "ft")
        self.assertEqual(res["score_number_human_unverified"], 12.5)
        answers = iter(["n"])
        res = human_result(lambda prompt: next(answers))
        self.assertFalse(res["ball_struck_human_observed"])
        self.assertIsNone(res["score_number_human_unverified"])

    def test_local_report_rewrites_only_own_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = {"run_id": "20261024T120000Z-12345678", "attempts": []}
            target = persist_local(doc, Path(tmp))
            self.assertEqual(json.loads(target.read_text())["attempts"], [])
            doc["attempts"].append({"before": 1})
            persist_local(doc, Path(tmp))
            self.assertEqual(len(json.loads(target.read_text())["attempts"]), 1)
            self.assertFalse(target.with_suffix(".json.tmp").exists())

    def test_interactive_one_shot_no_upload_when_disabled(self):
        ready = iter(["", "", "y", "green", "", "q"])
        def snap(_rpc, _port, label):
            return {"label": label, "game_id": "RSPE01"}
        with tempfile.TemporaryDirectory() as tmp, \
             patch("wii_ai_golf.golf_collection.read_stage", side_effect=snap), \
             patch("wii_ai_golf.golf_collection.publish_sanitized") as publish, \
             contextlib.redirect_stdout(io.StringIO()):
            saved, link = collect(
                steps=session_steps(shots=2), port=55355, data_dir=Path(tmp),
                code_root=Path(tmp), upload=False, rpc_factory=object,
                input_fn=lambda prompt: next(ready),
            )
            self.assertIsNone(link)
            self.assertEqual(len(json.loads(saved.read_text())["attempts"]), 1)
            report = json.loads(saved.read_text())
            self.assertTrue(report["attempts"][0]["capture_complete"])
            publish.assert_not_called()

    def test_no_shots_no_upload(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch("wii_ai_golf.golf_collection.publish_sanitized") as publish, \
             contextlib.redirect_stdout(io.StringIO()):
            path, url = collect(
                steps=session_steps(shots=1), port=55355,
                data_dir=Path(tmp), code_root=Path(tmp),
                rpc_factory=object, input_fn=lambda _p: "q",
            )
            self.assertIsNone(path)
            self.assertIsNone(url)
            publish.assert_not_called()

    def test_upload_remote_is_pinned_to_repo(self):
        self.assertTrue(_GIT_REMOTE.search("https://github.com/Nate27624/Wii-AI-Golf.git"))
        self.assertTrue(_GIT_REMOTE.search("git@github.com:Nate27624/Wii-AI-Golf.git"))
        self.assertFalse(_GIT_REMOTE.search("https://github.com/other/fake.git"))
        self.assertFalse(_GIT_REMOTE.search("https://evil.com/github.com/Nate27624/Wii-AI-Golf.git"))

    def test_run_id_format(self):
        import re
        self.assertRegex(make_run_id(), r"^\d{8}T\d{6}Z-[0-9a-f]{8}$")


if __name__ == "__main__":
    unittest.main()
