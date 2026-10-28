"""No-game redacted structural diagnosis regression tests (synthetic data only)."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "scripts" / "diagnose_v1_selected_watch_bridge_private.py"
spec = importlib.util.spec_from_file_location("diagnose_v1_watch", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def synthetic():
    return (
        m.PATCH_MARKER + "\n" + m.SWING_MARKER + "\n"
        + "HANDLERS = {\n"
        + '    "trace.submit_swing": _wii_ai_submit_swing,\n'
        + "}\n"
        + "while True:\n"
        + "    await event.frameadvance()\n"
        + "    _frame_count += 1\n"
        + "    _wii_ai_tick()\n"
        + "    _poll_sockets()\n"
    )


class DiagnosisTests(unittest.TestCase):
    def test_wrong_hash_is_the_first_blocker(self):
        report = m.inspect_text(synthetic(), actual_sha256="0" * 64)
        self.assertEqual(report["preflight"], "ORIGINAL_SHA256_DIFFERENT")
        self.assertFalse(report["marker_checks"]["exact_historical_hit_source_sha256"])
        self.assertNotIn("0"*64, str(report))

    def test_correct_hash_and_source_anchors_have_exact_counts(self):
        report = m.inspect_text(synthetic(), actual_sha256=m.KNOWN_CONTACT_V1_SHA256)
        self.assertEqual(report["preflight"], "SOURCE_PREFLIGHT_PASS")
        self.assertEqual(report["source_anchor_counts_capped_at_three"], {
            "handler_table": 1, "swing_handler_registration": 1, "frame_loop_tick": 1,
        })

    def test_missing_and_duplicate_frame_loop_are_visible_as_count_only(self):
        for text, count in (
            (synthetic().replace("    _poll_sockets()", "    _poll_socketz()"), 0),
            (synthetic() + "\n    _wii_ai_tick()\n    _poll_sockets()\n", 2),
        ):
            with self.subTest(count=count):
                report = m.inspect_text(text, actual_sha256=m.KNOWN_CONTACT_V1_SHA256)
                self.assertEqual(report["preflight"], "SOURCE_ANCHOR_LAYOUT_MISMATCH")
                self.assertEqual(report["source_anchor_counts_capped_at_three"]["frame_loop_tick"], count)

    def test_v2_and_autoload_downgrade_refused(self):
        for suffix in (m.BOOT_MARKER, m.SWING_NEUTRAL_V2_MARKER, m.BALL_WATCH_MARKER):
            report = m.inspect_text(synthetic()+suffix, actual_sha256=m.KNOWN_CONTACT_V1_SHA256)
            self.assertEqual(report["preflight"], "SOURCE_MARKER_POLICY_MISMATCH")

    def test_never_expose_source_text_or_pointer(self):
        raw = synthetic() + "\nSECRET_0x90001234 = 0xDEADBEEF\n"
        report = m.inspect_text(raw, actual_sha256="wrong")
        self.assertNotIn("SECRET", str(report))
        self.assertNotIn("0x90001234", str(report))
        self.assertNotIn("DEADBEEF", str(report))
        self.assertFalse(report["live_use_approved"])
        self.assertFalse(report["new_bridge_created"])

    def test_bad_source_path_does_not_read_or_create(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "private-V1-bridge.py"
            path.write_text(synthetic(), encoding="utf-8")
            report = m.diagnostic(path)
            self.assertIn(report["preflight"], {"SOURCE_PATH_REJECTED", "SOURCE_NOT_FOUND"})
            self.assertTrue(path.exists())
            self.assertFalse(report["new_bridge_created"])

    def test_interleaved_source_loop_uses_ast_not_literal_adjacency(self):
        source = synthetic().replace("    _wii_ai_tick()\n    _poll_sockets()",
                                     "    _wii_ai_tick()\n    unrelated_housekeeping()\n    _poll_sockets()")
        report = m.inspect_text(source, actual_sha256=m.KNOWN_CONTACT_V1_SHA256)
        self.assertEqual(report["preflight"], "SOURCE_PREFLIGHT_PASS")
        self.assertEqual(report["source_anchor_counts_capped_at_three"]["frame_loop_tick"], 0)
        self.assertTrue(report["marker_checks"]["single_structurally_verified_frame_loop_tick"])


if __name__ == "__main__":
    unittest.main()
