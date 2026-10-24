"""Offline tests; do not claim shots, moving ball or score are auto-detected."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
from wii_ai_golf.golf_monitor import changed_fields, run_monitor, build_public_report


def state(*, x=210.1, start=2.2, raw_hole="0x00000001", mode="GAMEMODE_TR_NEARPIN"):
    return {
        "captured_utc": "2026-10-24T04:00:00+00:00",
        "frame_start": 50, "frame_end": 66, "game_id": "RSPE01",
        "disc_revision": 1, "mode": mode, "current_hole_raw": raw_hole,
        "objects": {
            "current_pin_obj_ptr": {"translation_xyz_unverified": [x, -7.0, -350.5]},
            "cup_obj_ptr": {"translation_xyz_unverified": [x, -7.04, -350.5]},
            "current_start_obj_ptr": {"translation_xyz_unverified": [start, -5.5, -318]},
        },
        "controller": {"buttons": {"A": False}},
    }


class MonitorTests(unittest.TestCase):
    def test_changes_are_not_shot_detection(self):
        a = state()
        self.assertEqual(changed_fields(None, a), ["initial"])
        self.assertEqual(changed_fields(a, a), [])
        self.assertEqual(changed_fields(a, state(x=210.11)), [])
        self.assertIn("current_pin_obj_ptr_translation_changed",
                      changed_fields(a, state(x=230.5)))
        self.assertIn("current_hole_raw_changed",
                      changed_fields(a, state(raw_hole="0x00000002")))
        self.assertIn("mode_changed",
                      changed_fields(a, state(mode="other_or_unknown")))
        self.assertFalse(any("shot" in k or "ball" in k for k in
                             changed_fields(a, state(x=230.5))))

    def test_unknown_coords_handled(self):
        a = state()
        b = state()
        b["objects"]["cup_obj_ptr"]["translation_xyz_unverified"] = None
        self.assertEqual(changed_fields(a, b), ["cup_obj_ptr_translation_changed"])

    def test_parameter_validation(self):
        with tempfile.TemporaryDirectory() as t:
            kwargs = dict(code_root=Path(t), local_dir=Path(t), upload=False)
            with self.assertRaises(ValueError):
                run_monitor(interval_s=0.01, **kwargs)
            with self.assertRaises(ValueError):
                run_monitor(max_minutes=-1, **kwargs)
            with self.assertRaises(ValueError):
                run_monitor(max_samples=-1, **kwargs)

    def test_record_every_sample_locally_and_upload_only_summary(self):
        seen = [state(), state(), state(x=240.0)]
        uploads = []
        def uploader(report, root):
            uploads.append(report)
            return "https://github.com/Nate27624/Wii-AI-Golf/blob/data/example.json"
        with tempfile.TemporaryDirectory() as t, patch(
                "wii_ai_golf.golf_monitor.make_run_id", return_value="20261024T120000Z-12345678"
            ), patch("builtins.print"):
            p, link = run_monitor(
                code_root=Path(t), local_dir=Path(t), max_samples=3,
                interval_s=.2, max_minutes=15, upload=True,
                sample_reader=lambda n: seen[n],
                sleep_fn=lambda _s: None, upload_fn=uploader)
            lines = [json.loads(x) for x in p.read_text().splitlines()]
            self.assertEqual(len(lines), 3)
            self.assertEqual(len(uploads), 1)
            self.assertEqual(uploads[0]["sample_count"], 3)
            self.assertEqual(uploads[0]["recorded_events"][0]["changes"], ["initial"])
            self.assertEqual(uploads[0]["recorded_events"][1]["changes"],
                             ["current_pin_obj_ptr_translation_changed", "cup_obj_ptr_translation_changed"])
            self.assertIsNotNone(link)
            self.assertNotIn("memory", p.read_text())

    def test_continues_after_one_failure(self):
        def read(n):
            if len(calls) == 0:
                calls.append(1)
                raise RuntimeError("mock socket issue")
            return state()
        calls = []
        with tempfile.TemporaryDirectory() as t, patch("builtins.print"):
            p, link = run_monitor(code_root=Path(t), local_dir=Path(t),
                                  max_samples=1, upload=False, max_minutes=15,
                                  sample_reader=read, interval_s=.2,
                                  sleep_fn=lambda _s: None)
            rows = [json.loads(x) for x in p.read_text().splitlines()]
            self.assertIn("error_type", rows[0])
            self.assertIn("state", rows[1])
            self.assertIsNone(link)

    def test_does_not_publish_on_wrong_game(self):
        with tempfile.TemporaryDirectory() as t, patch("builtins.print"):
            p, url = run_monitor(
                code_root=Path(t), local_dir=Path(t), max_samples=1,
                interval_s=.2, upload=True, max_minutes=1,
                sleep_fn=lambda _s: None,
                sample_reader=lambda _n: dict(state(), game_id="XXXXXX"),
                upload_fn=lambda report, _root: self.fail("must not publish"))
            self.assertIsNone(url)
            self.assertEqual(len([json.loads(x) for x in p.read_text().splitlines()]), 5)

    def test_public_report_truncation(self):
        report = build_public_report("run", started_utc="t", samples=502,
                                     events=[{"sample_index": i} for i in range(502)],
                                     heartbeats=[{"sample_index": i} for i in range(121)],
                                     errors=[], local_complete=True)
        self.assertEqual(len(report["recorded_events"]), 500)
        self.assertTrue(report["events_truncated_before_recent_500"])
        self.assertEqual(len(report["periodic_samples"]), 120)
        self.assertIn("unverified", report["source"])


if __name__ == "__main__":
    unittest.main()
