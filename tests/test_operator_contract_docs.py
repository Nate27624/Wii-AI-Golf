"""Static, synthetic-only consistency checks for the operator's active instructions.

No Dolphin, RAM, game files, network, repo writes or subprocesses.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class OperatorContractDocsTests(unittest.TestCase):
    def test_readme_has_active_links_and_powershell_first(self):
        top = read("README.md")[:3700]
        self.assertIn("START HERE", top)
        self.assertIn("docs/operator-powershell-contract.md", top)
        self.assertIn("docs/repository-map.md", top)
        self.assertIn("PowerShell", top)
        self.assertIn("Set-Location -LiteralPath $repo", top)
        self.assertIn("No Lab GUI", top)

    def test_agents_have_active_precedence_before_old_gui(self):
        text = read("AGENTS.md")
        start = text[:4200]
        self.assertIn("ACTIVE OPERATOR RULES", start)
        self.assertIn("docs/operator-powershell-contract.md", start)
        self.assertIn("docs/repository-map.md", start)
        self.assertIn("copy/paste-ready", start)
        self.assertIn("supersedes", start.lower())
        self.assertGreater(text.find("ARCHIVED"), text.find("ACTIVE OPERATOR RULES"))

    def test_old_gui_headings_no_longer_claim_active_authority(self):
        agents = read("AGENTS.md")
        readme = read("README.md")
        self.assertNotIn("## CURRENT OPERATOR DECISION — ONE GUI WITH CLI BACKEND", agents)
        self.assertNotIn("## Current workflow: One Lab, desktop and Git Bash", readme)
        self.assertIn("## ARCHIVED", agents)
        self.assertIn("## ARCHIVED", readme)

    def test_contract_requires_full_powershell_and_exact_existing_setup(self):
        text = read("docs/operator-powershell-contract.md")
        for required in (
            "Windows PowerShell", "Set-Location -LiteralPath $repo",
            "$ErrorActionPreference = 'Stop'",
            "D:\\Projects\\Wii Golf AI\\Wii-AI-Golf",
            "D:\\Projects\\Wii Golf AI\\Wii-AI-Golf-Data",
            "$LASTEXITCODE", "sanitized", "one", "source-pinned",
            "89-sample", "No unsafe live", "historical",
        ):
            with self.subTest(required=required):
                self.assertIn(required.casefold(), text.casefold())

    def test_a45_ambiguous_variants_spelled_out(self):
        text = read("docs/operator-powershell-contract.md")
        for label in ("final A", "45", "A-prime", "A-lead", "neutral trace",
                      "follow-through", "NOT equivalent", "trace hash"):
            with self.subTest(label=label):
                self.assertIn(label.casefold(), text.casefold())

    def test_contract_explicitly_forbids_manual_dolphin(self):
        text = read("docs/operator-powershell-contract.md")
        for label in ("NEVER tell the operator", "load", "Dolphin", "GUI",
                      "Git Bash", "single", "PowerShell"):
            with self.subTest(label=label):
                self.assertIn(label, text)

    def test_root_map_explains_components_and_private_data(self):
        text = read("docs/repository-map.md")
        for label in ("scripts/research_cli.py", "scripts/golf.py",
                      "scripts/run_golf_experiment.py", "scripts/launch_golf.py",
                      "menu_sequence.py", "Wii-AI-Golf-Data",
                      "research/observations", "S000", "S001", "S002", "S003",
                      "S004", "S005", "PR", "named savestate"):
            with self.subTest(label=label):
                self.assertIn(label.casefold(), text.casefold())

    def test_cli_guides_point_to_active_rules(self):
        for path in ("docs/cli-only-workflow.md", "docs/cli.md"):
            with self.subTest(path=path):
                content = read(path)
                self.assertIn("operator-powershell-contract.md", content[:1100])
                self.assertIn("repository-map.md", content[:1100])
                self.assertIn("PowerShell", content[:1100])

    def test_powershell_examples_auto_cd_and_guard_failure(self):
        text = read("docs/operator-powershell-contract.md")
        blocks = re.findall(r"~~~powershell\n(.*?)\n~~~", text, flags=re.S)
        self.assertGreaterEqual(len(blocks), 2)
        for block in blocks:
            with self.subTest(command=block[:90]):
                self.assertIn("$ErrorActionPreference = 'Stop'", block)
                self.assertIn("$repo =", block)
                self.assertIn("Set-Location -LiteralPath $repo", block)
                self.assertIn("$LASTEXITCODE", block)
                self.assertNotIn("Start-Process", block)
                self.assertNotIn("bash ", block)

    def test_no_draft_feature_claimed_as_merged(self):
        text = read("docs/operator-powershell-contract.md")
        self.assertIn("draft until merged", text)
        self.assertIn("review", text)
        self.assertIn("no", text.lower())


if __name__ == "__main__":
    unittest.main()
