"""Synthetic tests for read-only Wedge/Iron source-global pair protocol."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
p = ROOT / "scripts" / "p0_live_club_pair_private.py"
spec = importlib.util.spec_from_file_location("pair_probe", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture():
    rows = []
    for phase, expected, _ in m.STAGES:
        label = expected if expected else ("IRON" if phase == "BLIND1" else "WEDGE")
        index = 1 if label == "IRON" else 2
        rows.append({"phase": phase, "club": label, "index": index,
                     "aim_candidate_word": 11 if phase in (
                         "AIM", "IRON2", "WEDGE2", "BLIND1", "BLIND2") else 10})
    for e in rows[7:]:
        e["prediction"] = m.prediction(rows[:7], e["index"])
    return rows


class TestTwoLabelClubPair(unittest.TestCase):
    def test_two_label_success_is_candidate_only(self):
        r = m.assess(fixture())
        self.assertEqual(r["status"], "P0_TWO_LABEL_CLUB_SELECTOR_CANDIDATE_SUPPORTED")
        self.assertEqual(r["index_by_operator_label"], {"WEDGE": 2, "IRON": 1})
        self.assertFalse(r["game_club_id_verified"])
        self.assertFalse(r["four_club_mapping_verified"])
        self.assertFalse(r["training_approved"])

    def test_no_distinct_club_memory_rejected(self):
        e = fixture()
        for row in e:
            row["index"] = 0
        self.assertEqual(m.prediction(e[:7], 0), "UNKNOWN")
        self.assertFalse(m.assess(e)["checks"]["two_distinct_indices"])

    def test_idle_drift_rejected(self):
        e = fixture()
        e[1]["index"] = 3
        self.assertFalse(m.assess(e)["checks"]["idle_index_stable"])

    def test_repeated_wedge_drift_rejected(self):
        e = fixture()
        e[6]["index"] = 3
        self.assertFalse(m.assess(e)["checks"]["wedge_repeated_index"])

    def test_repeated_iron_drift_rejected(self):
        e = fixture()
        e[5]["index"] = 3
        self.assertFalse(m.assess(e)["checks"]["iron_repeated_index"])

    def test_aim_confound_not_accepted(self):
        e = fixture()
        e[4]["index"] = 3
        self.assertFalse(m.assess(e)["checks"]["aim_only_index_stable"])

    def test_aim_control_must_actually_change_candidate(self):
        e = fixture()
        e[4]["aim_candidate_word"] = e[3]["aim_candidate_word"]
        self.assertEqual(m.prediction(e[:7], 1), "UNKNOWN")
        self.assertFalse(m.assess(e)["checks"]["aim_candidate_changed"])

    def test_wrong_blind_prediction_rejected(self):
        e = fixture()
        e[-1]["prediction"] = "IRON"
        self.assertFalse(m.assess(e)["checks"]["blind_predictions_match"])

    def test_unknown_prediction_rejected(self):
        e = fixture()
        e[-1]["prediction"] = "UNKNOWN"
        self.assertFalse(m.assess(e)["checks"]["blind_predictions_match"])

    def test_blind_truth_must_cover_both_clubs(self):
        e = fixture()
        e[8]["club"] = "IRON"
        self.assertFalse(m.assess(e)["checks"]["both_blind_truths_present"])

    def test_operator_labeled_calibration_mismatch_rejected(self):
        e = fixture()
        e[2]["club"] = "WEDGE"
        self.assertFalse(m.assess(e)["checks"]["operator_labeled_phases"])

    def test_reordered_phases_abstain(self):
        e = fixture()
        e[0], e[1] = e[1], e[0]
        with self.assertRaises(m.core.Abstain):
            m.assess(e)

    def test_missing_phase_abstain(self):
        with self.assertRaises(m.core.Abstain):
            m.assess(fixture()[:-1])

    def test_boolean_index_rejected(self):
        e = fixture()
        e[0]["index"] = True
        with self.assertRaises(m.core.Abstain):
            m.assess(e)

    def test_out_of_bounds_index_rejected(self):
        e = fixture()
        e[0]["index"] = 4
        with self.assertRaises(m.core.Abstain):
            m.assess(e)

    def test_private_repo_root_rejected(self):
        with self.assertRaises(m.core.Abstain):
            m.private_folder(ROOT)

    def test_private_synced_root_rejected(self):
        with tempfile.TemporaryDirectory(prefix="onedrive-private-") as t:
            with self.assertRaises(m.core.Abstain):
                m.private_folder(Path(t))

    def test_source_pointer_join_stays_unverified(self):
        self.assertEqual(m.core.GLOBAL_SLOT, 0x804BF900)
        self.assertEqual(m.core.PLAYER_MANAGER_GLOBAL, 0x804BF8D0)
        self.assertEqual(m.core.FIELD_OFFSET, 0x1C)


if __name__ == "__main__":
    unittest.main()
