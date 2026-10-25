"""Preregistered Wii Golf falsification studies: no unsafe pseudo-jobs."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf import cli
from wii_ai_golf.research_validation import validation_report, validation_studies

QUEUE = ROOT / "research" / "queue.jsonl"


class ValidationStudyTests(unittest.TestCase):
    def setUp(self):
        self.entries = [json.loads(line) for line in QUEUE.read_text(encoding="utf-8").splitlines()
                        if line.strip()]

    def scratch(self, mutator):
        rows = json.loads(json.dumps(self.entries))
        by_id = {row["study_id"]: row for row in rows}
        mutator(by_id)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "test_queue.jsonl"
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        return path

    def test_all_ten_studies_are_valid_and_prioritized(self):
        studies = validation_studies(QUEUE)
        self.assertEqual(len(studies), 10)
        self.assertEqual(studies[0]["priority"], 0)
        names = {s["study_id"] for s in studies}
        for needed in ("VAL-PUB-01", "VAL-PENALTY-02", "VAL-DRIFT-03",
                       "VAL-SOURCE-04", "VAL-SCENE-05", "VAL-LATENCY-06",
                       "VAL-CONTROL-07", "VAL-JOIN-08",
                       "VAL-PERTURB-09", "VAL-POWER-10"):
            self.assertIn(needed, names)
        self.assertFalse(validation_report(QUEUE)["execution_performed"])
        self.assertFalse(validation_report(QUEUE)["game_score_verified"])

    def test_live_shot_budgets_bounded_and_never_implicit(self):
        studies = validation_studies(QUEUE)
        for study in studies:
            budget = study["budget"]
            if study["mode"] != "approved-shot":
                self.assertEqual(budget["approved_shots"], 0)
            if study["mode"] == "offline":
                self.assertEqual(budget["read_only_sessions"], 0)
            self.assertLessEqual(budget["approved_shots"], 6)
            self.assertTrue(study["null_hypothesis"])
            self.assertGreaterEqual(len(study["controls"]), 2)
            self.assertTrue(study["stop_rule"])

    def test_rejects_unsafe_live_budget(self):
        p = self.scratch(lambda rows: rows["VAL-PUB-01"]["budget"].update(approved_shots=1))
        with self.assertRaisesRegex(ValueError, "Offline study includes a live action"):
            validation_studies(p)

    def test_rejects_missing_controls_or_null_hypothesis(self):
        p = self.scratch(lambda rows: rows["VAL-DRIFT-03"].update(controls=[]))
        with self.assertRaisesRegex(ValueError, "negative controls"):
            validation_studies(p)
        p = self.scratch(lambda rows: rows["VAL-DRIFT-03"].update(null_hypothesis=""))
        with self.assertRaisesRegex(ValueError, "preregistration field"):
            validation_studies(p)

    def test_rejects_cyclic_and_unresolved_dependencies(self):
        p = self.scratch(lambda rows: rows["VAL-PUB-01"].update(depends_on=["VAL-JOIN-08"]))
        with self.assertRaisesRegex(ValueError, "Cycle"):
            validation_studies(p)
        p = self.scratch(lambda rows: rows["VAL-JOIN-08"].update(depends_on=["VAL-GHOST-99"]))
        with self.assertRaisesRegex(ValueError, "Unknown"):
            validation_studies(p)

    def test_rejects_completion_without_independent_evidence(self):
        p = self.scratch(lambda rows: rows["VAL-PUB-01"].update(status="completed"))
        with self.assertRaisesRegex(ValueError, "cannot independently prove"):
            validation_studies(p)

    def test_cli_shows_studies_and_never_executes_experiments(self):
        with patch.object(cli, "_run") as subprocess, redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(["research", "validation", "--json"]), 0)
            subprocess.assert_not_called()
        public = json.loads(out.getvalue())
        self.assertEqual(public["count"], 10)
        self.assertFalse(public["execution_performed"])
        with patch.object(cli, "_run") as subprocess, redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(["research", "validation", "--study-id", "VAL-LATENCY-06"]), 0)
            subprocess.assert_not_called()
        self.assertIn("p95", out.getvalue())
        self.assertNotIn("VAL-PUB-01", out.getvalue())

    def test_plain_research_studies_lists_new_entries_without_run(self):
        with patch.object(cli, "_run") as subprocess, redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(["research", "studies"]), 0)
            subprocess.assert_not_called()
        self.assertIn("VAL-PUB-01", out.getvalue())
        self.assertIn("VAL-POWER-10", out.getvalue())
        self.assertIn("PLANNED", "PLANNED")


if __name__ == "__main__":
    unittest.main()
