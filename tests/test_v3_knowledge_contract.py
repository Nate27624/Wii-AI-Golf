"""Offline structural checks for the initial staged V3 knowledge seed.

These checks are not semantic review, operator goal approval or fenced publication.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("ONBOARDING.md", "GOALS.md", "ROADMAP.md", "FINDINGS.md")


class KnowledgeSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = {name: (ROOT / name).read_text(encoding="utf-8") for name in NAMES}

    def test_relative_document_links_exist(self):
        for name, text in self.docs.items():
            for target in re.findall(r"\]\(([^)]+)\)", text):
                if target.startswith(("https://", "#")):
                    continue
                with self.subTest(document=name, target=target):
                    self.assertTrue((ROOT / target.split("#", 1)[0]).is_file())

    def test_unique_goals_milestones_and_findings(self):
        goals = re.findall(r"^## (G-[A-Z]+) ", self.docs["GOALS.md"], re.M)
        milestones = re.findall(r"^\| (M-[A-Z]+) \|", self.docs["ROADMAP.md"], re.M)
        findings = re.findall(r"^## (F-[A-Z]+-\d{3}) ", self.docs["FINDINGS.md"], re.M)
        for ids in (goals, milestones, findings):
            self.assertTrue(ids)
            self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(goals), {"G-ORCHESTRATION", "G-RESEARCH"})
        refs = re.findall(r"Goal/milestone: (G-[A-Z]+) / (M-[A-Z]+)\.", self.docs["FINDINGS.md"])
        self.assertEqual(len(refs), len(findings))
        for goal, milestone in refs:
            self.assertIn(goal, goals)
            self.assertIn(milestone, milestones)

    def test_staged_authority_boundary(self):
        self.assertIn("V2 authoritative until explicit cutover", self.docs["ONBOARDING.md"])
        self.assertIn("staged for operator pinning", self.docs["GOALS.md"])
        self.assertIn("LocalOps is the sole human Work Queue console", self.docs["ONBOARDING.md"])
        self.assertIn("Fenced curation is not yet activated", self.docs["FINDINGS.md"])
        self.assertIn("merging.md", self.docs["ONBOARDING.md"])


if __name__ == "__main__":
    unittest.main()
