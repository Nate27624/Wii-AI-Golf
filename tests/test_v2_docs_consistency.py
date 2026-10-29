"""Static V2 onboarding regressions; no emulator, filesystem writes or network."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class V2DocumentationConsistencyTests(unittest.TestCase):
    def read(self, path):
        return (ROOT / path).read_text(encoding="utf-8")

    def test_current_start_pages_point_to_authoritative_contract(self):
        for path in ("README.md", "AGENTS.md"):
            with self.subTest(path=path):
                body = self.read(path)
                for token in ("docs/v2-navigation.md", "docs/v2-agent-charter.md",
                              "docs/v2-agent-continuity.md", "merging.md"):
                    self.assertIn(token, body)
                self.assertIn("scripts/golf.py", body)
                self.assertIn("scripts/agent_handoff.py", body)
                self.assertIn("CLI", body)
                self.assertIn("separate explicit operator authorization", body)

    def test_canonical_roles_and_transfers_not_ambiguous(self):
        body = self.read("AGENTS.md")
        for role in ("S000", "S001", "S002", "S003", "S004", "S005"):
            self.assertRegex(body, rf"(?m)^\| {role} \|")
        self.assertIn("CONTINUE V2", body)
        self.assertIn("HANDOFF V2", body)
        self.assertIn("SUCCESSION HANDOFF", body)
        self.assertIn("merging.md", body)
        self.assertIn("100-foot", body)

    def test_no_competing_active_gui_or_legacy_launcher_runbooks(self):
        current = self.read("README.md") + self.read("AGENTS.md")
        banned = (
            "## Current workflow: One Lab, desktop and Git Bash",
            "## CURRENT OPERATOR DECISION — ONE GUI WITH CLI BACKEND",
            "## New: one shared Research Lab",
            "## Operator-first in-app game diagnostics",
            "**Instead of chasing agent-specific scripts, launch the Windows app:**",
            "## Mandatory fresh-boot command contract (user directive 2026-10-24)",
        )
        for heading in banned:
            with self.subTest(heading=heading):
                self.assertNotIn(heading, current)
        self.assertIn("not the V2", current)

    def test_historical_originals_preserved_and_disclaimed(self):
        for archive, sha, old_heading in (
            ("docs/archive/README-pre-v2-20261029.md",
             "52a997296c867d3027ccbd4c1eded3462a8b16c0",
             "## Current workflow: One Lab, desktop and Git Bash"),
            ("docs/archive/AGENTS-pre-v2-20261029.md",
             "201903c9708dd72b86340f0345f0f9775720404d",
             "## CURRENT OPERATOR DECISION — ONE GUI WITH CLI BACKEND"),
        ):
            with self.subTest(path=archive):
                body = self.read(archive)
                self.assertIn("NON-AUTHORITATIVE SNAPSHOT", body)
                self.assertIn("Original bytes remain in Git history", body)
                self.assertIn(sha, body)
                self.assertIn(old_heading, body)
                self.assertGreater(len(body), 15000)

    def test_current_relative_markdown_links_exist(self):
        for path in ("README.md", "AGENTS.md"):
            with self.subTest(path=path):
                body = self.read(path)
                for target in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", body):
                    if "://" in target:
                        continue
                    referenced = (ROOT / path).parent / target
                    self.assertTrue(referenced.exists(),
                                    f"{path}: missing relative target {target}")


if __name__ == "__main__":
    unittest.main()
