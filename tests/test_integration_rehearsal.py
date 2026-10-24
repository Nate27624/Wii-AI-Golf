import unittest

from wii_ai_golf.integration.rehearsal import OfflineFelkBridge, TraceEvent, TraceRehearsal


class TraceTests(unittest.TestCase):
    def test_offline_trace_has_audit_and_release(self):
        mock = OfflineFelkBridge()
        actions = [TraceEvent(0, (0.0, 1.0, 0.0)), TraceEvent(12, (0.0, 2.0, 0.0))]
        result = TraceRehearsal(mock).run(actions)
        self.assertEqual(result.source, "rpc-rehearsal-unverified-game")
        self.assertEqual(result.event_count, 2)
        self.assertEqual(len(result.trace_sha256), 64)
        self.assertGreater(result.end_frame, result.start_frame)
        self.assertEqual(mock.commands[-2][0], "controller.set_wiimote_buttons")
        self.assertEqual(mock.commands[-2][1][1], {"A": False})
        self.assertEqual([x[0] for x in mock.commands if x[0].startswith("controller.set")][:-1],
                         ["controller.set_wiimote_buttons", "controller.set_wiimote_acceleration"] * 2)

    def test_reject_unsorted_and_duplicate_offsets(self):
        events = [TraceEvent(5, (0, 1, 0)), TraceEvent(5, (0, 2, 0))]
        with self.assertRaises(ValueError):
            TraceRehearsal(OfflineFelkBridge()).run(events)

    def test_reject_nonfinite_and_bad_sample_range(self):
        for accel in [(float("nan"), 1, 0), (50, 1, 0), (float("inf"), 0, 0)]:
            with self.assertRaises(ValueError):
                TraceEvent(0, accel)

    def test_invalid_port(self):
        with self.assertRaises(ValueError):
            TraceRehearsal(OfflineFelkBridge(), port=4)

    def test_old_bridge_version_rejected(self):
        class Old(OfflineFelkBridge):
            def call(self, method, params=None):
                if method == "bridge.ping":
                    return {"bridge_version": "0.1.0"}
                return super().call(method, params)
        with self.assertRaisesRegex(RuntimeError, "v0.2.0"):
            TraceRehearsal(Old()).preflight()

    def test_mock_frame_progress(self):
        probe = TraceRehearsal(OfflineFelkBridge()).preflight()
        self.assertTrue(probe["frame_progressed"])

    def test_release_button_after_command_error(self):
        class FailOnce(OfflineFelkBridge):
            failed = False
            def call(self, method, params=None):
                if method == "controller.set_wiimote_acceleration" and not self.failed:
                    self.failed = True
                    raise RuntimeError("control unavailable")
                return super().call(method, params)
        fake = FailOnce()
        with self.assertRaisesRegex(RuntimeError, "control unavailable"):
            TraceRehearsal(fake).run([TraceEvent(0, (0, 2, 0))])
        self.assertEqual(fake.commands[-1][1][1], {"A": False})


if __name__ == "__main__":
    unittest.main()
