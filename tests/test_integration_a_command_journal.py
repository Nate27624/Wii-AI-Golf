"""Mocked RPC event-capture tests; never launch Dolphin."""
import sys
import unittest
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC in sys.path:
    sys.path.remove(_SRC)
sys.path.insert(0, _SRC)

from wii_ai_golf.integration.a_command_journal import ACommandJournal


class RPC:
    def __init__(self, fail=None):
        self.fail = fail
        self.calls = []

    def call(self, method, params=None):
        self.calls.append((method, params))
        if method == self.fail:
            raise TimeoutError("injected RPC failure")
        if method == "trace.submit_swing":
            return {"state": "scheduled", "kind": "swing"}
        if method == "trace.status":
            return {"state": "complete", "applied_frames": 89}
        return None


def sequence(journal, *, premature=False):
    journal.call("controller.set_wiimote_buttons", [0, {"A": True, "B": False}])
    samples = [[i < 77, 0, 0, 0, 0, 0, 0, 0] for i in range(89)]
    if premature:
        samples[38][0] = False
    journal.call("trace.submit_swing", [0, samples])
    journal.call("trace.status", [])
    journal.call("controller.set_wiimote_buttons", [0, {"A": False, "B": False}])


class JournalTests(unittest.TestCase):
    def test_same_rpc_sequence_and_clean_continuity(self):
        rpc = RPC()
        journal = ACommandJournal(rpc)
        sequence(journal)
        self.assertEqual([x[0] for x in rpc.calls],
                         ["controller.set_wiimote_buttons", "trace.submit_swing",
                          "trace.status", "controller.set_wiimote_buttons"])
        report = journal.report()
        self.assertEqual(report["continuity"]["status"], "pass")
        self.assertFalse(report["game_a_recognition_verified"])

    def test_premature_release_detected(self):
        journal = ACommandJournal(RPC())
        sequence(journal, premature=True)
        self.assertEqual(journal.report()["continuity"]["status"], "fail")

    def test_missing_complete_status_is_unknown(self):
        journal = ACommandJournal(RPC())
        journal.call("controller.set_wiimote_buttons", [0, {"A": True}])
        self.assertEqual(journal.report()["continuity"]["status"], "unknown")

    def test_timeout_never_reported_clean(self):
        journal = ACommandJournal(RPC(fail="trace.submit_swing"))
        journal.call("controller.set_wiimote_buttons", [0, {"A": True}])
        with self.assertRaises(TimeoutError):
            journal.call("trace.submit_swing", [0, []])
        self.assertEqual(journal.report()["continuity"]["status"], "unknown")

    def test_no_private_path_in_report(self):
        journal = ACommandJournal(RPC())
        sequence(journal)
        self.assertNotIn("path", str(journal.report()).lower())


if __name__ == "__main__":
    unittest.main()
