"""Mock-only tests for pre-start menu button timing and cleanup."""
import unittest

from wii_ai_golf.menu_sequence import MenuPhase, planned_menu_phases, execute_menu_phases


class FakeBridge:
    def __init__(self, fail_at=None):
        self.calls = []
        self.fail_at = fail_at
        self.attempts = 0

    def call(self, method, params=None):
        self.attempts += 1
        if self.attempts == self.fail_at:
            raise OSError("mock bridge disconnected")
        self.calls.append((method, params))
        return None


class MenuSequenceTests(unittest.TestCase):
    def test_requested_order_and_button_edges(self):
        phases = planned_menu_phases(startup=2, a_press=3, between=4,
                                     ab_press=5, gap=2, final_a=3, settle=2)
        bridge = FakeBridge()
        result = execute_menu_phases(bridge, phases)
        self.assertEqual(len(result), 7)
        expected = (
            [(False, False)] * 2 + [(True, False)] * 3
            + [(False, False)] * 4 + [(True, True)] * 5
            + [(False, False)] * 2 + [(True, False)] * 3
            + [(False, False)] * 2 + [(False, False)] * 3
        )
        actual = [(x[1][1]["A"], x[1][1]["B"]) for x in bridge.calls]
        self.assertEqual(actual, expected)
        self.assertTrue(all(x[0] == "controller.set_wiimote_buttons"
                            and x[1][0] == 0 for x in bridge.calls))

    def test_can_set_another_remote(self):
        bridge = FakeBridge()
        execute_menu_phases(bridge, (MenuPhase("A+B", True, True, 1),), remote=2)
        self.assertTrue(all(call[1][0] == 2 for call in bridge.calls))

    def test_failure_still_releases_both_buttons(self):
        bridge = FakeBridge(fail_at=2)
        with self.assertRaises(OSError):
            execute_menu_phases(bridge, (MenuPhase("A+B", True, True, 5),))
        self.assertEqual(bridge.calls[-1][1][1], {"A": False, "B": False})

    def test_bad_frame_counts_fail_before_dispatch(self):
        for number in (0, -1, 601, True, 1.5):
            with self.subTest(number=number), self.assertRaises(ValueError):
                planned_menu_phases(a_press=number)

    def test_bad_remote_fails_without_sending(self):
        bridge = FakeBridge()
        with self.assertRaises(ValueError):
            execute_menu_phases(bridge, planned_menu_phases(), remote=4)
        self.assertEqual(bridge.calls, [])

    def test_calibrated_defaults(self):
        stages = planned_menu_phases()
        self.assertEqual([p.requests for p in stages], [120, 30, 315, 60, 135, 45, 300])

    def test_all_phases_bounded(self):
        stages = planned_menu_phases()
        self.assertEqual([p.label for p in stages],
                         ["state settle", "first A", "wait", "A+B",
                          "release between presses", "final A", "game transition"])
        self.assertTrue(all(1 <= p.requests <= 600 for p in stages))

    def test_empty_and_invalid_phase_rejected(self):
        for phases in ((), ("bad",)):
            with self.subTest(phases=phases), self.assertRaises(ValueError):
                execute_menu_phases(FakeBridge(), phases)


if __name__ == "__main__":
    unittest.main()
