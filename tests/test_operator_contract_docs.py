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

    def test_contributor_and_pr_template_enforce_operator_contract(self):
        contrib = read("CONTRIBUTING.md")
        template = read(".github/pull_request_template.md")
        self.assertIn("docs/operator-powershell-contract.md", contrib[:1700])
        self.assertIn("docs/repository-map.md", contrib[:1700])
        self.assertIn("Windows PowerShell", contrib[:1700])
        for word in ("PowerShell", "A45", "S001", "Dolphin", "owner",
                     "synthetic", "FULL Windows suite", "human"):
            with self.subTest(word=word):
                self.assertIn(word.casefold(), template.casefold())

    def test_agents_requires_automatic_safe_upload_and_finding_handoff(self):
        text = read("AGENTS.md")[:6500]
        for term in ("MANDATORY automatic GitHub result publication",
                     "research/observations", "scripts/research_cli.py",
                     "SANITIZED", "FINDING", "research/ledger.md",
                     "NOT UPLOADED", "auto-publication", "no custom"):
            with self.subTest(term=term):
                self.assertIn(term.casefold(), text.casefold())

    def test_operator_contract_describes_publisher_failure_and_privacy(self):
        text = read("docs/operator-powershell-contract.md")
        for term in ("Automatic GitHub publication", "same invocation",
                     "research/observations", "publish_summary",
                     "allowlisted", "PRIVATE", "NOT UPLOADED",
                     "--no-upload", "S000/S002", "research/ledger.md",
                     "FINDING", "human-observed", "negative",
                     "missing adapter"):
            with self.subTest(term=term):
                self.assertIn(term.casefold(), text.casefold())

    def test_repo_map_and_readme_define_upload_vs_local_data(self):
        readme = read("README.md")[:4800]
        maptext = read("docs/repository-map.md")
        workflow = read("docs/cli-only-workflow.md")
        for contents in (readme, maptext, workflow):
            with self.subTest(source=contents[:55]):
                self.assertIn("research/observations", contents)
                self.assertIn("research/ledger.md", contents)
                self.assertIn("sanitized", contents.lower())
                self.assertIn("NOT UPLOADED", contents)

    def test_contributor_pr_template_have_upload_and_finding_gate(self):
        text = read("CONTRIBUTING.md") + read(".github/pull_request_template.md")
        for term in ("automatically", "research/observations", "FINDING",
                     "research/ledger.md", "NOT UPLOADED", "S000/S002",
                     "RAW", "privacy"):
            with self.subTest(term=term):
                self.assertIn(term.casefold(), text.casefold())

    def test_existing_publisher_still_automatic_only_for_supported_modes(self):
        source = read("scripts/research_cli.py")
        self.assertIn('OBS_BRANCH = "research/observations"', source)
        self.assertIn("if not args.no_upload:", source)
        self.assertIn("publish_summary(summary)", source)
        self.assertIn("Local sanitized result:", source)
        self.assertIn("Upload NOT completed", source)
        self.assertIn('"--no-upload"', source)
        self.assertIn('_ALLOWED = {"test", "v1"}', source)

    def test_no_draft_feature_claimed_as_merged(self):
        text = read("docs/operator-powershell-contract.md")
        self.assertIn("draft until merged", text)
        self.assertIn("review", text)
        self.assertIn("no", text.lower())


if __name__ == "__main__":
    unittest.main()
