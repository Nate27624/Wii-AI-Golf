"""Offline negative controls for commanded (not game-observed) A continuity."""
import unittest
from pathlib import Path
import sys

# Ensure this isolated worktree wins over stale editable installations.
_ROOT = Path(__file__).resolve().parents[1]
_SRC = str(_ROOT / 'src')
if _SRC in sys.path:
    sys.path.remove(_SRC)
sys.path.insert(0, _SRC)

from wii_ai_golf.integration.a_continuity_audit import (
    ButtonEvent, audit_a_continuity, expected_v1_events,
)


def original_trace():
    from wii_ai_golf.integration.swing_client import SwingSample
    def sample(hold):
        return SwingSample(hold, (0.0, 0.0, 0.0), 0.0, 0.0, 0.0, 0.0)
    return [sample(True) for _ in range(77)] + [sample(False) for _ in range(12)]


class ContinuityAuditTests(unittest.TestCase):
    def test_expected_v1_45_prehold_is_logically_continuous(self):
        result = audit_a_continuity(expected_v1_events(original_trace()))
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["unexpected_releases"], 0)
        self.assertFalse(result["game_verified"])
        self.assertEqual(len(result["transitions"]), 2)

    def test_mid_swing_a_off_on_is_failure(self):
        events = expected_v1_events(original_trace())
        events[75] = ButtonEvent(events[75].phase, events[75].index, False)
        result = audit_a_continuity(events)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["reason"], "unexpected_a_transition")

    def test_missing_release_is_unknown(self):
        events = expected_v1_events(original_trace())[:-12]
        self.assertEqual(audit_a_continuity(events)["status"], "unknown")

    def test_empty_is_unknown(self):
        self.assertEqual(audit_a_continuity([])["status"], "unknown")

    def test_mixed_observation_source_rejected(self):
        with self.assertRaises(ValueError):
            audit_a_continuity([
                ButtonEvent("prehold", 0, True),
                ButtonEvent("release", 1, False, "bridge_dispatch")])

    def test_nonmonotonic_index_rejected(self):
        with self.assertRaises(ValueError):
            audit_a_continuity([
                ButtonEvent("prehold", 2, True),
                ButtonEvent("release", 2, False)])

    def test_missing_prehold_is_unknown(self):
        events = expected_v1_events(original_trace(), prehold_frames=0)
        self.assertEqual(audit_a_continuity(events)["status"], "unknown")

    def test_wrong_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            expected_v1_events(original_trace()[:-1])


if __name__ == "__main__":
    unittest.main()
