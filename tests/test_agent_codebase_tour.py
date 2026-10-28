"""Synthetic documentation drift tests for the source-backed agent codebase tour.

Reads repository source text/AST only. No importing game modules, subprocess,
network, Dolphin, controller, local data, or writes.
"""
from __future__ import annotations

import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "agent-codebase-tour.md"


def source(path: str) -> str:
    target = ROOT / path
    if not target.is_file():
        raise AssertionError(f"Source path missing: {path}")
    return target.read_text(encoding="utf-8")


def has_function(path: str, name: str) -> bool:
    tree = ast.parse(source(path), filename=path)
    return any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
               and node.name == name for node in ast.walk(tree))


def has_class(path: str, name: str) -> bool:
    tree = ast.parse(source(path), filename=path)
    return any(isinstance(node, ast.ClassDef) and node.name == name
               for node in ast.walk(tree))


class AgentCodebaseTourTests(unittest.TestCase):
    def test_markdown_links_are_local_files(self):
        body = GUIDE.read_text(encoding="utf-8")
        hrefs = re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", body)
        self.assertGreaterEqual(len(hrefs), 15)
        for link in hrefs:
            if link.startswith(("https://", "http://")):
                continue
            with self.subTest(link=link):
                self.assertTrue((GUIDE.parent / link).is_file())

    def test_root_cli_wrapper_and_router_exist(self):
        self.assertIn("from wii_ai_golf.cli import main", source("scripts/golf.py"))
        for fun in ("build_parser", "execute", "main"):
            self.assertTrue(has_function("src/wii_ai_golf/cli.py", fun))
        self.assertIn("run_golf_experiment.py", source("src/wii_ai_golf/cli.py"))

    def test_research_cli_publisher_is_allowlisted_and_separate(self):
        cli = source("scripts/research_cli.py")
        self.assertTrue(has_function("scripts/research_cli.py", "publish_summary"))
        self.assertTrue(has_function("scripts/research_cli.py", "main"))
        for marker in ('OBS_BRANCH = "research/observations"',
                       '_ALLOWED = {"test", "v1"}',
                       "sync_merged_main(ROOT)", "publish_summary(summary)",
                       "research-cli", "--no-upload", "run_golf_experiment.py"):
            with self.subTest(marker=marker):
                self.assertIn(marker, cli)

    def test_canonical_launch_stages_still_match_guide(self):
        for path, functions in (
            ("scripts/run_golf_experiment.py",
             ("resolve_target", "build_commands", "main")),
            ("scripts/launch_golf.py",
             ("resolve_game", "make_start_command", "main")),
            ("scripts/launch_hitting_green.py", ("main",)),
            ("src/wii_ai_golf/menu_sequence.py",
             ("planned_menu_phases", "execute_menu_phases")),
            ("scripts/collect_outcome_transition.py",
             ("run_session", "main")),
        ):
            for fun in functions:
                with self.subTest(path=path, function=fun):
                    self.assertTrue(has_function(path, fun))
        self.assertIn('"green-pre-start"', source("scripts/run_golf_experiment.py"))
        self.assertIn("planned_menu_phases(", source("scripts/launch_hitting_green.py"))
        self.assertIn("execute_menu_phases(", source("scripts/launch_hitting_green.py"))
        self.assertIn("StateCatalog", source("scripts/launch_hitting_green.py"))

    def test_savestate_catalog_does_not_claim_physical_bytes(self):
        path = "src/wii_ai_golf/integration/savestates.py"
        self.assertTrue(has_class(path, "StateCatalog"))
        self.assertTrue(has_class(path, "StateManager"))
        self.assertTrue(has_function(path, "get"))
        self.assertTrue(has_function(path, "request_load"))
        self.assertIn("not physical save bytes", GUIDE.read_text(encoding="utf-8"))

    def test_a45_modes_remain_separate_code_paths(self):
        menu = source("src/wii_ai_golf/menu_sequence.py")
        outcome = source("scripts/collect_outcome_transition.py")
        self.assertRegex(menu, r"final_a:\s*int\s*=\s*45")
        self.assertIn("a_prime_requests", outcome)
        self.assertIn("a_lead_frames", outcome)
        self.assertIn("choose either RPC-count A prime OR frame-measured A lead", outcome)
        self.assertTrue(has_function("scripts/probe_swing.py", "build_probe"))
        guide = GUIDE.read_text(encoding="utf-8")
        for term in ("Menu final A", "Separate A-prime", "V1 observed-frame A-lead",
                     "Neutral/held-A trace", "89-sample", "not proven"):
            with self.subTest(term=term):
                self.assertIn(term.casefold(), guide.casefold())

    def test_s001_atomic_swing_handlers_are_source_linked(self):
        path = "src/wii_ai_golf/integration/atomic_client.py"
        self.assertTrue(has_class(path, "AtomicTraceClient"))
        self.assertTrue(has_function(path, "run"))
        self.assertTrue(has_function(
            "src/wii_ai_golf/integration/swing_patch.py",
            "extend_atomic_bridge_with_swing"))

    def test_direct_operator_contract_and_pr_draft_limitations_present(self):
        text = GUIDE.read_text(encoding="utf-8").casefold()
        for term in ("powershell", "no manual dolphin", "#196",
                     "#195", "#198", "draft", "not merged", "not an instruction",
                     "source", "verified", "candidate", "human", "frozen trace",
                     "raw", "not physical", "s000", "s001", "s002"):
            with self.subTest(term=term):
                self.assertIn(term.casefold(), text)

    def test_p0_merge_pressure_and_private_boundaries(self):
        text = GUIDE.read_text(encoding="utf-8")
        for term in ("#170", "#121", "Wii-AI-Golf-Data",
                     "research/observations", "publish_summary()",
                     "FINDING", "HANDOFF", "one complete",
                     "Windows", "Ubuntu"):
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_guide_has_self_locating_powershell_only_for_user(self):
        text = GUIDE.read_text(encoding="utf-8")
        blocks = re.findall(r"\x60{3}powershell\n(.*?)\n\x60{3}", text, re.S)
        self.assertEqual(len(blocks), 1)
        block = blocks[0]
        self.assertIn("$ErrorActionPreference = 'Stop'", block)
        self.assertIn("$repo = 'D:\\Projects\\Wii Golf AI\\Wii-AI-Golf'", block)
        self.assertIn("Set-Location -LiteralPath $repo", block)
        self.assertIn("py scripts/golf.py doctor", block)
        self.assertIn("$LASTEXITCODE", block)
        self.assertNotIn("Start-Process", block)
        self.assertNotIn("bash ", block)

    def test_main_v1_guard_remains_honestly_marked_as_draft(self):
        cli = source("scripts/research_cli.py")
        self.assertIn("draft #195", GUIDE.read_text(encoding="utf-8"))
        self.assertIn('"--send-live", "--bridge"', cli)
        self.assertNotIn("v1_clean_boot_args", cli)


if __name__ == "__main__":
    unittest.main()
